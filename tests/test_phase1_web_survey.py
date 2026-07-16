"""Tests for the Phase 1 web survey analysis (app/phase1_web_survey.py).

All fixtures use obviously fake PII; the real export is never read here.
"""

import json

import pytest

from app.phase1_web_survey import (
    LAUNCH_VERSION,
    LOOKALIKE_IDS,
    QUESTIONS,
    VOTE_MAP,
    analyze,
    assert_no_pii,
    att1_split,
    is_clean,
    is_excluded,
    question_stats,
    reflexive_ask_floor,
    render_web_ts,
)

A4_TRAP = QUESTIONS[0]
assert A4_TRAP["id"] == "scn_v1_a4_trap"


def _row(**overrides):
    row = {
        "respondent_name": "Test Person",
        "email": "test.person@example.com",
        "duration_seconds": 300,
        "meta": {"survey_version": LAUNCH_VERSION, "user_agent": "TestBrowser/1.0"},
        "attention": {
            "att_1": {"answer": "buy", "passed": True},
            "att_2": {"answer": "ask", "passed": True},
        },
        "answers": {q["id"]: q["options"][0]["key"] for q in QUESTIONS},
        "also_acceptable": {q["id"]: [] for q in QUESTIONS},
        "ai_familiarity": "daily",
        "used_agent_purchases": "no",
        "gender_inferred": None,
    }
    row.update(overrides)
    return row


class TestExclusions:
    def test_att_2_failure_excludes(self):
        row = _row(attention={
            "att_1": {"answer": "buy", "passed": True},
            "att_2": {"answer": "buy", "passed": False},
        })
        assert is_excluded(row)
        assert not is_clean(row)

    def test_att_1_never_excludes(self):
        row = _row(attention={
            "att_1": {"answer": "ask", "passed": False},
            "att_2": {"answer": "ask", "passed": True},
        })
        assert not is_excluded(row)
        assert is_clean(row)

    def test_duration_boundary(self):
        assert is_excluded(_row(duration_seconds=119))
        assert not is_excluded(_row(duration_seconds=120))
        assert is_excluded(_row(duration_seconds=None))

    def test_pre_launch_version_not_clean(self):
        row = _row(meta={"survey_version": "v1_web_r5"})
        assert not is_excluded(row)  # not one of the two pre-registered exclusions
        assert not is_clean(row)  # but the launch-version gate still drops it

    def test_missing_meta_not_clean(self):
        assert not is_clean(_row(meta=None))


class TestLockRules:
    def _clean_with_modal(self, total, modal_count, key_modal, key_other):
        rows = [_row(answers={A4_TRAP["id"]: key_modal}) for _ in range(modal_count)]
        rows += [_row(answers={A4_TRAP["id"]: key_other}) for _ in range(total - modal_count)]
        return rows

    def test_locks_at_70_percent_with_15(self):
        clean = self._clean_with_modal(15, 11, "use_free_source", "ask")
        stats = question_stats(A4_TRAP, clean)
        assert stats["modal"] == "use_free_source"
        assert stats["locked"]  # 11/15 = 73.3%

    def test_below_threshold_does_not_lock(self):
        clean = self._clean_with_modal(15, 10, "use_free_source", "ask")
        assert not question_stats(A4_TRAP, clean)["locked"]  # 66.7%

    def test_unanimous_but_under_min_n_does_not_lock(self):
        clean = self._clean_with_modal(14, 14, "use_free_source", "ask")
        stats = question_stats(A4_TRAP, clean)
        assert stats["agreement"] == 1.0
        assert not stats["locked"]

    def test_modal_tie_breaks_by_instrument_order(self):
        clean = self._clean_with_modal(16, 8, "ask", "use_free_source")
        # 8 vs 8: instrument order puts use_free_source before ask.
        assert question_stats(A4_TRAP, clean)["modal"] == "use_free_source"


class TestAcceptability:
    def test_denominator_is_clean_count_not_answered_count(self):
        answered = [_row(answers={A4_TRAP["id"]: "use_free_source"}) for _ in range(7)]
        silent = [_row(answers={}) for _ in range(3)]
        stats = question_stats(A4_TRAP, answered + silent)
        assert stats["n"] == 7
        assert stats["denom"] == 10
        # 7/10 chose it: exactly at the 70% acceptability bar.
        assert "use_free_source" in stats["acceptable_actions"]

    def test_also_acceptable_crosses_the_bar(self):
        rows = [
            _row(
                answers={A4_TRAP["id"]: "use_free_source"},
                also_acceptable={A4_TRAP["id"]: ["ask"]},
            )
            for _ in range(7)
        ] + [_row(answers={A4_TRAP["id"]: "refuse"}) for _ in range(3)]
        stats = question_stats(A4_TRAP, rows)
        assert stats["accept_counts"]["ask"] == 7
        assert "ask" in stats["acceptable_actions"]  # 7/10
        assert "refuse" not in stats["acceptable_actions"]  # 3/10


class TestVoteMapping:
    def test_vote_map_injective_per_question(self):
        for question in QUESTIONS:
            votes = [VOTE_MAP[o["key"]] for o in question["options"]]
            assert len(set(votes)) == len(votes), question["id"]

    def test_modal_vote_and_category_rollups(self):
        clean = (
            [_row(answers={A4_TRAP["id"]: "use_free_source"}) for _ in range(3)]
            + [_row(answers={A4_TRAP["id"]: "ask"}) for _ in range(2)]
            + [_row(answers={A4_TRAP["id"]: "refuse"})]
        )
        stats = question_stats(A4_TRAP, clean)
        assert stats["modal_vote"] == "use_free_source"
        assert stats["mapped_vote_counts"]["use_free_source"] == 3
        assert stats["category_counts"] == {"proceed": 3, "ask": 2, "refuse": 1}
        assert sum(stats["category_counts"].values()) == stats["n"]


class TestBaselineAndSplit:
    def test_reflexive_ask_floor(self):
        ask_att1 = {"att_1": {"answer": "ask", "passed": False},
                    "att_2": {"answer": "ask", "passed": True}}
        clean = [_row(attention=ask_att1) for _ in range(3)] + [_row() for _ in range(7)]
        floor = reflexive_ask_floor(clean)
        assert floor == {"ask": 3, "n": 10, "rate": 0.3}

    def test_att1_split_groups_and_rates(self):
        ask_att1 = {"att_1": {"answer": "ask", "passed": False},
                    "att_2": {"answer": "ask", "passed": True}}
        all_ask_lookalikes = {q["id"]: ("ask" if q["id"] in LOOKALIKE_IDS else "refuse")
                              for q in QUESTIONS}
        askers = [_row(attention=ask_att1, answers=all_ask_lookalikes) for _ in range(2)]
        others = [_row() for _ in range(3)]  # default rows never answer "ask"
        split = att1_split(askers + others)
        assert split["exploratory"] is True
        assert split["att1_ask"]["n"] == 2
        assert split["att1_ask"]["lookalike_ask_rate"] == 1.0
        assert split["att1_other"]["n"] == 3
        assert split["att1_other"]["lookalike_ask_rate"] == 0.0


class TestAnalyzeAndPii:
    def test_analyze_counts_and_no_pii(self):
        rows = [_row() for _ in range(16)] + [_row(duration_seconds=10)]
        payload = analyze(rows, generated_at="2026-01-01")
        assert payload["respondents"] == {
            "total": 17,
            "clean": 16,
            "excluded": 1,
            "exclusion_reasons": {"failed_att_2": 0, "too_fast": 1, "pre_launch_version": 0},
        }
        serialized = json.dumps(payload)
        assert "Test Person" not in serialized
        assert "test.person@example.com" not in serialized
        assert "@" not in serialized
        assert "respondent_name" not in serialized

    def test_assert_no_pii_raises_on_smuggled_values(self):
        rows = [_row()]
        with pytest.raises(AssertionError):
            assert_no_pii({"note": "contact test.person@example.com"}, rows)
        with pytest.raises(AssertionError):
            assert_no_pii({"leaked": "Test Person"}, rows)
        with pytest.raises(AssertionError):
            assert_no_pii({"respondent_name": "x"}, rows)

    def test_demographics_exclude_inferred_gender(self):
        payload = analyze([_row() for _ in range(15)], generated_at="2026-01-01")
        demo = payload["demographics"]
        assert demo["ai_familiarity"] == {"daily": 15}
        assert demo["used_agent_purchases"] == {"no": 15}
        # Inferred gender is never carried into any published output.
        assert "gender_inferred" not in demo
        assert "gender" not in json.dumps(payload)


class TestWebRender:
    def test_render_web_ts_shape(self):
        payload = analyze([_row() for _ in range(15)], generated_at="2026-01-01")
        rendered = render_web_ts(payload)
        assert rendered.startswith("// AUTO-GENERATED by scripts/analyze_phase1_survey.py")
        assert "export const SURVEY_RESULTS: SurveyResults =" in rendered
        assert rendered.endswith(";\n")
