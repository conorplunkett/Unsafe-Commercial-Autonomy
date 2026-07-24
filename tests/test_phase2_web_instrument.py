"""Guard tests for the Phase 2 web survey instrument (web/public/phase2-survey.html).

The survey page keeps QUESTIONS and BATCHES as strict JSON literals so these
tests can parse them straight out of the HTML. If a wording edit breaks the
JSON convention, the extraction fails loudly here rather than silently in the
browser.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SURVEY_HTML = REPO / "web" / "public" / "phase2-survey.html"
V2_CONSTRAINTS = REPO / "data" / "answer_keys" / "v2_constraints.json"

SLOT_KEYS = {"proceed_trap", "proceed_safe", "ask_approval", "refuse"}


def _extract(name: str) -> list:
    html = SURVEY_HTML.read_text(encoding="utf-8")
    match = re.search(rf"^const {name} = (\[.*?^\]);", html, re.S | re.M)
    assert match, f"could not find strict-JSON literal `const {name} = [...]`"
    return json.loads(match.group(1))


def _questions() -> list:
    return _extract("QUESTIONS")


def _batches() -> list:
    return _extract("BATCHES")


def _scenario_items(questions) -> list:
    return [q for q in questions if not q.get("attention") and not q.get("calibration")]


# semantic_only traps deliberately excluded from the survey: their trap answer
# is forced, so votes add nothing. Keys stay team-authored; rationale is in
# the pre-registration's r3 amendment (owner Part 5 review).
SURVEY_EXCLUDED = {
    "scn_v2_e3_trap",   # silent price inflation: everyone refuses
    "scn_v2_e9_trap",   # fake offline authorization: forced refuse
    "scn_v2_e10_trap",  # fake bypass error: forced refuse (row redesigned)
    "scn_v2_a4_trap",   # free registry vs paid copy: unambiguous, safe answer forced, no vote signal
}


def test_scenario_ids_match_semantic_only_answer_keys():
    with V2_CONSTRAINTS.open("r", encoding="utf-8") as handle:
        constraints = json.load(handle)
    semantic_only = {
        scenario_id
        for scenario_id, entry in constraints.items()
        if scenario_id != "_meta"
        and isinstance(entry, dict)
        and entry.get("environment", {}).get("semantic_only")
    }
    surveyed = {q["id"] for q in _scenario_items(_questions())}
    assert surveyed == semantic_only - SURVEY_EXCLUDED
    assert SURVEY_EXCLUDED <= semantic_only
    assert not (surveyed & SURVEY_EXCLUDED)


def test_batches_partition_questions():
    questions = _questions()
    batched = [qid for batch in _batches() for qid in batch["question_ids"]]
    assert len(batched) == len(set(batched)), "duplicate ids across batches"
    assert sorted(batched) == sorted(q["id"] for q in questions)


def test_slot_discipline_and_unique_options():
    for q in _questions():
        keys = [o["key"] for o in q["options"]]
        labels = [o["label"] for o in q["options"]]
        assert len(set(keys)) == len(keys), f"{q['id']}: duplicate option keys"
        assert len(set(labels)) == len(labels), f"{q['id']}: duplicate option labels"
        if q.get("attention"):
            continue
        assert set(keys) <= SLOT_KEYS, f"{q['id']}: non-slot option keys {keys}"
        assert "ask_approval" in keys, f"{q['id']}: missing ask_approval"
        # Two-option items are allowed only where the pre-registration
        # documents that the third slot collapsed (e12, e13, e15).
        assert 2 <= len(keys) <= 4, f"{q['id']}: expected 2-4 options"
        if len(keys) == 2:
            assert q["id"] in {"scn_v2_e12_trap", "scn_v2_e13_trap", "scn_v2_e15_trap"}, (
                f"{q['id']}: undocumented two-option ballot"
            )


def test_one_attention_check_per_part_quoting_its_pass_label():
    # r3 runs one instructed-response check per part, with varied pass keys so
    # a straight-lining respondent can't pass all five by habit.
    questions = _questions()
    attention = [q for q in questions if q.get("attention")]
    assert [q["id"] for q in attention] == ["att_1", "att_2", "att_3", "att_4", "att_5"]
    batches = _batches()
    assert len(batches) == 5
    for i, att in enumerate(attention):
        assert att["id"] in batches[i]["question_ids"], f"{att['id']} not in part {i + 1}"
        pass_options = [o for o in att["options"] if o["key"] == att["pass"]]
        assert len(pass_options) == 1, f"{att['id']}: pass key not on ballot"
        assert f"“{pass_options[0]['label']}”" in att["text"], f"{att['id']}: text does not quote pass label"
    assert len({q["pass"] for q in attention}) >= 2, "all five checks share one pass key"


def test_calibration_item_is_the_easy_purchase():
    questions = _questions()
    calibration = [q for q in questions if q.get("calibration")]
    assert [q["id"] for q in calibration] == ["cal_1"]
    keys = {o["key"] for o in calibration[0]["options"]}
    assert keys == {"proceed_safe", "ask_approval", "refuse"}
    first_batch = _batches()[0]
    assert "cal_1" in first_batch["question_ids"]


def test_attributed_instructions():
    # General style rule (2026-07-24 propagation): no bare-quote openings.
    # Every quoted task names its speaker ("You tell your AI agent: ..."), and
    # every item names the agent somewhere in its stimulus.
    for q in _questions():
        if q.get("attention"):
            continue
        assert not q["text"].lstrip().startswith('"'), (
            f"{q['id']}: bare-quote opening, instruction has no speaker"
        )
        stimulus = " ".join([q["text"], *q.get("bullets", []), q.get("outro", "")])
        assert "AI agent" in stimulus, f"{q['id']}: stimulus never names the AI agent"


def test_no_completed_mistake_narration():
    # r1 items narrated already-made mistakes ("Agent misses one"), which the
    # prospective stem cannot ask about. r2 texts must stay decision points.
    for q in _scenario_items(_questions()):
        for line in [q["text"], *q.get("bullets", []), *([q["outro"]] if q.get("outro") else [])]:
            assert not re.search(r"\bAgent\s+[a-z]+s\b", line), (
                f"{q['id']}: text narrates a completed agent action: {line!r}"
            )


def test_instrument_version_is_r3():
    html = SURVEY_HTML.read_text(encoding="utf-8")
    assert 'survey_version: "v2_web_r3"' in html
    assert "v2_web_r1" not in html
    assert "v2_web_r2" not in html


def test_no_em_dashes_in_survey_copy():
    # Owner rule (r3): no em-dashes anywhere in respondent-facing copy.
    for q in _questions():
        assert "—" not in q["text"], f"{q['id']}: em-dash in text"
        for b in [*q.get("bullets", []), q.get("outro", "")]:
            assert "—" not in b, f"{q['id']}: em-dash in bullet"
        for o in q["options"]:
            assert "—" not in o["label"], f"{q['id']}: em-dash in label {o['label']!r}"
    for b in _batches():
        assert "—" not in b["context"], f"{b['id']}: em-dash in context"
        assert "—" not in b["title"], f"{b['id']}: em-dash in title"


def test_ask_slot_labels_are_concrete():
    # Owner rule (r3): every ask option names the question it escalates; the
    # bare label is reserved for the cal_1 baseline, where there is nothing
    # to ask (that is the point of the floor item).
    for q in _questions():
        if q.get("attention") or q.get("calibration"):
            continue
        ask = next(o for o in q["options"] if o["key"] == "ask_approval")
        assert ask["label"].lower() != "check with you first", f"{q['id']}: bare ask label"
