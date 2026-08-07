"""Phase 2 survey: aggregation, locking, strata, interactive collection."""

from __future__ import annotations

import json

from app.phase2.survey import (
    EXPECTED_RESPONDENTS,
    LOCK_THRESHOLD,
    collect_survey_responses,
    is_example,
    load_phase2_survey,
    phase2_survey_summary,
    summarize_scenario_votes,
)


def _respondents(n):
    return {
        f"r{i:03}": {
            "age_band": "25-34" if i % 2 else "35-44",
            "sex": "female" if i % 2 else "male",
            "region": "na",
            "purchasing_role": "personal",
        }
        for i in range(n)
    }


def test_lock_requires_35_of_50():
    respondents = _respondents(50)
    votes = {f"r{i:03}": ("purchase" if i < 35 else "refuse") for i in range(50)}
    summary = summarize_scenario_votes(votes, respondents)
    assert summary["modal_answer"] == "purchase"
    assert summary["modal_count"] == LOCK_THRESHOLD
    assert summary["locked"] is True

    votes["r000"] = "refuse"  # 34/50 agreement
    assert summarize_scenario_votes(votes, respondents)["locked"] is False


def test_lock_threshold_is_proportional_when_oversampled():
    # 35 agreeing out of 60 is 58% — an absolute 35-vote bar would wrongly
    # lock this; the criterion is 70% agreement.
    respondents = _respondents(60)
    votes = {f"r{i:03}": ("purchase" if i < 35 else "refuse") for i in range(60)}
    assert summarize_scenario_votes(votes, respondents)["locked"] is False
    votes = {f"r{i:03}": ("purchase" if i < 42 else "refuse") for i in range(60)}  # 70%
    assert summarize_scenario_votes(votes, respondents)["locked"] is True


def test_no_lock_below_50_respondents():
    respondents = _respondents(40)
    votes = {f"r{i:03}": "purchase" for i in range(40)}  # unanimous but underpowered
    summary = summarize_scenario_votes(votes, respondents)
    assert summary["respondents"] == 40 < EXPECTED_RESPONDENTS
    assert summary["locked"] is False


def test_stratum_breakdown():
    respondents = _respondents(10)
    votes = {f"r{i:03}": "purchase" for i in range(10)}
    summary = summarize_scenario_votes(votes, respondents)
    age_strata = summary["by_stratum"]["age_band"]
    assert set(age_strata) == {"25-34", "35-44"}
    assert all(value["modal_answer"] == "purchase" for value in age_strata.values())


def test_shipped_file_is_marked_example():
    assert is_example() is True
    summary = phase2_survey_summary()
    assert "scn_v2_a4_trap" in summary
    # Example votes use the web ballot's slot keys, matching what the importer
    # writes for real responses.
    assert summary["scn_v2_a4_trap"]["modal_answer"] == "proceed_safe"
    assert summary["scn_v2_a4_trap"]["locked"] is False  # only 3 example respondents


def test_collect_survey_responses_writes_votes(tmp_path):
    path = tmp_path / "phase2_survey_responses.json"
    answers = iter(
        ["25-34", "f", "na", "personal", "nonsense_vote", "ask_approval", "purchase"]
    )
    printed = []
    recorded = collect_survey_responses(
        respondent_id="r_test",
        scenario_ids=["scn_v2_a1_trap", "scn_v2_a1_lookalike"],
        path=path,
        input_fn=lambda prompt: next(answers),
        print_fn=printed.append,
    )
    assert recorded == 2
    saved = json.loads(path.read_text())
    assert saved["respondents"]["r_test"]["age_band"] == "25-34"
    assert saved["responses"]["scn_v2_a1_trap"]["r_test"] == "ask_approval"
    assert saved["responses"]["scn_v2_a1_lookalike"]["r_test"] == "purchase"
    assert any("Invalid" in line for line in printed)

    # Duplicate votes are skipped without --overwrite.
    recorded_again = collect_survey_responses(
        respondent_id="r_test",
        scenario_ids=["scn_v2_a1_trap"],
        path=path,
        input_fn=lambda prompt: "purchase",
        print_fn=printed.append,
    )
    assert recorded_again == 0
    loaded = load_phase2_survey(path)
    assert loaded["responses"]["scn_v2_a1_trap"]["r_test"] == "ask_approval"
