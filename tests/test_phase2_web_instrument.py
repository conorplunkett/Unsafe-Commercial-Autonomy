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
    assert surveyed == semantic_only


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
        assert 3 <= len(keys) <= 4, f"{q['id']}: expected 3-4 options"


def test_attention_check_text_quotes_its_pass_label():
    questions = _questions()
    attention = [q for q in questions if q.get("attention")]
    assert [q["id"] for q in attention] == ["att_2"]
    att = attention[0]
    pass_options = [o for o in att["options"] if o["key"] == att["pass"]]
    assert len(pass_options) == 1
    assert f"“{pass_options[0]['label']}”" in att["text"]


def test_calibration_item_is_the_easy_purchase():
    questions = _questions()
    calibration = [q for q in questions if q.get("calibration")]
    assert [q["id"] for q in calibration] == ["cal_1"]
    keys = {o["key"] for o in calibration[0]["options"]}
    assert keys == {"proceed_safe", "ask_approval", "refuse"}
    first_batch = _batches()[0]
    assert "cal_1" in first_batch["question_ids"]


def test_no_completed_mistake_narration():
    # r1 items narrated already-made mistakes ("Agent misses one"), which the
    # prospective stem cannot ask about. r2 texts must stay decision points.
    for q in _scenario_items(_questions()):
        assert not re.search(r"\bAgent\s+[a-z]+s\b", q["text"]), (
            f"{q['id']}: text narrates a completed agent action: {q['text']!r}"
        )


def test_instrument_version_is_r2():
    html = SURVEY_HTML.read_text(encoding="utf-8")
    assert 'survey_version: "v2_web_r2"' in html
    assert "v2_web_r1" not in html
