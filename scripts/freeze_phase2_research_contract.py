"""Generate the frozen Phase 2 instrument and answer-key projection.

The committed projection protects the research contract without freezing the
sandbox implementation. It contains the exact web-survey instrument, authored
answer keys, and effective keys after any adopted survey re-key. Merchant copy,
offers, checkout controls, and other sandbox world state are deliberately
excluded.

Run from the repository root after an intentional contract change:

    python scripts/freeze_phase2_research_contract.py

Review the generated JSON diff before committing it. Ordinary sandbox work
must not regenerate the projection merely to silence its drift test.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data import load_scenarios  # noqa: E402
from app.phase2 import PHASE2_SCENARIO_SET  # noqa: E402
from app.phase2.web_survey import LAUNCH_VERSION  # noqa: E402

SURVEY_HTML = ROOT / "web" / "public" / "survey.html"
CONSTRAINTS = ROOT / "data" / "answer_keys" / "v2_constraints.json"
OUT_PATH = ROOT / "data" / "answer_keys" / "phase2_research_contract.json"

EXPECTED_SCENARIO_COUNT = 226
EXPECTED_QUESTION_COUNT = 50
EXPECTED_BATCH_COUNT = 5

AUTHORED_KEY_FIELDS = (
    "right_answer",
    "expected_action",
    "acceptable_actions",
    "over_refusal_scoring_enabled",
)
EFFECTIVE_KEY_FIELDS = (
    "right_answer",
    "expected_action",
    "acceptable_actions",
    "over_refusal_scoring_enabled",
    "answer_key_status",
    "survey_rekey",
)


def _extract_json_array(html: str, name: str) -> List[Any]:
    match = re.search(rf"^const {name} = (.*?);$", html, re.S | re.M)
    if not match:
        raise ValueError(f"Could not find strict-JSON literal `const {name} = [...]`")
    value = json.loads(match.group(1))
    if not isinstance(value, list):
        raise ValueError(f"Expected {name} to be a JSON array")
    return value


def _index_unique(items: List[Dict[str, Any]], label: str) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"{label} has no string id: {item!r}")
        if item_id in indexed:
            raise ValueError(f"Duplicate {label} id: {item_id}")
        indexed[item_id] = item
    return indexed


def build_projection() -> Dict[str, Any]:
    html = SURVEY_HTML.read_text(encoding="utf-8")
    questions = _extract_json_array(html, "QUESTIONS")
    batches = _extract_json_array(html, "BATCHES")
    slot_keys = _extract_json_array(html, "SLOT_KEYS")
    question_index = _index_unique(questions, "question")
    batch_index = _index_unique(batches, "batch")

    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise ValueError(f"Expected {EXPECTED_QUESTION_COUNT} questions, got {len(questions)}")
    if len(batches) != EXPECTED_BATCH_COUNT:
        raise ValueError(f"Expected {EXPECTED_BATCH_COUNT} batches, got {len(batches)}")

    raw_constraints = json.loads(CONSTRAINTS.read_text(encoding="utf-8"))
    raw_constraints.pop("_meta", None)
    scenarios = sorted(
        load_scenarios(PHASE2_SCENARIO_SET), key=lambda scenario: scenario.scenario_id
    )
    if len(scenarios) != EXPECTED_SCENARIO_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_SCENARIO_COUNT} scenarios, got {len(scenarios)}"
        )
    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Phase 2 scenario ids are not unique")
    if set(scenario_ids) != set(raw_constraints):
        missing = sorted(set(scenario_ids) - set(raw_constraints))
        extra = sorted(set(raw_constraints) - set(scenario_ids))
        raise ValueError(f"Scenario/constraint ids differ: missing={missing}, extra={extra}")

    authored_keys: Dict[str, Dict[str, Any]] = {}
    effective_keys: Dict[str, Dict[str, Any]] = {}
    for scenario in scenarios:
        scenario_id = scenario.scenario_id
        constraint = raw_constraints[scenario_id]
        authored_keys[scenario_id] = {
            "right_answer": scenario.right_answer,
            "expected_action": constraint.get("expected_action"),
            "acceptable_actions": constraint.get("acceptable_actions"),
            "over_refusal_scoring_enabled": constraint.get("over_refusal_scoring_enabled"),
        }
        effective_keys[scenario_id] = {
            "right_answer": scenario.right_answer,
            "expected_action": scenario.payment_policy.get("expected_action"),
            "acceptable_actions": scenario.payment_policy.get("acceptable_actions"),
            "over_refusal_scoring_enabled": scenario.over_refusal_scoring_enabled,
            "answer_key_status": scenario.answer_key_status,
            "survey_rekey": scenario.payment_policy.get("survey_rekey"),
        }

    return {
        "_meta": {
            "description": "Frozen projection of the Phase 2 research contract.",
            "update_command": "python scripts/freeze_phase2_research_contract.py",
            "protected": {
                "instrument": "Exact survey version, wording, options, keys, order, and batches.",
                "authored_keys": list(AUTHORED_KEY_FIELDS),
                "effective_keys": list(EFFECTIVE_KEY_FIELDS),
            },
            "not_protected": [
                "sandbox environments",
                "merchant and page copy",
                "offers and cart state",
                "checkout controls and tool implementation",
            ],
        },
        "instrument": {
            "survey_version": LAUNCH_VERSION,
            "slot_keys": slot_keys,
            "question_order": [question["id"] for question in questions],
            "questions": question_index,
            "batch_order": [batch["id"] for batch in batches],
            "batches": batch_index,
        },
        "authored_keys": authored_keys,
        "effective_keys": effective_keys,
    }


def main(out_path: Path = OUT_PATH) -> None:
    projection = build_projection()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote Phase 2 research contract to {out_path}")


if __name__ == "__main__":
    main()
