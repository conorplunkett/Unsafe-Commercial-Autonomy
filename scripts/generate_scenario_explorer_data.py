"""Snapshot Phase 2's 113 trap/lookalike pairs for the admin Scenario Explorer.

Reads the merged Scenario records the same way app/main.py's
GET /api/phase2/scenarios does, groups the 226 scenarios into 113
trap/lookalike pairs by pair_id, and writes the result as the JSON asset
bundled into the admin-scenario-data Supabase Edge Function. This script is
the only way that function's data gets refreshed -- re-run it and redeploy
after any change to data/scenario_sets/v2_250_scenarios.md or
data/answer_keys/v2_constraints.json.

Pair order is NOT recomputed: it is exactly the first-seen order of pair_id
in load_scenarios() output, i.e. the Markdown file's own row order (category
A to E, ascending pair number within each category, including the numbering
gaps left by the 2026-07-24 twelve-pair cut -- e.g. category B skips to
B1, B3, B4, B5, B10...). Prev/Next in the UI walks this order.

Run from the repo root:  python scripts/generate_scenario_explorer_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data import load_scenarios  # noqa: E402
from app.models import model_to_dict  # noqa: E402
from app.phase2 import PHASE2_SCENARIO_SET  # noqa: E402

OUT_PATH = ROOT / "supabase" / "functions" / "admin-scenario-data" / "scenario_pairs.json"

EXPECTED_CATEGORY_COUNTS = {
    "spend_limits": 25,
    "authorization_scope": 14,
    "consent_and_escalation": 24,
    "privacy_and_disclosure": 25,
    "adversarial_robustness": 25,
}
EXPECTED_PAIR_COUNT = sum(EXPECTED_CATEGORY_COUNTS.values())


def build_pairs() -> List[Dict[str, Any]]:
    records = [model_to_dict(s) for s in load_scenarios(PHASE2_SCENARIO_SET)]

    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}
    order: List[str] = []
    for record in records:
        pair_id = record["pair_id"]
        role = record["pair_role"]
        if pair_id not in grouped:
            grouped[pair_id] = {}
            order.append(pair_id)
        if role in grouped[pair_id]:
            raise ValueError(f"Duplicate {role!r} for pair_id {pair_id!r}")
        grouped[pair_id][role] = record

    pairs: List[Dict[str, Any]] = []
    for pair_id in order:
        roles = grouped[pair_id]
        missing = {"trap", "lookalike"} - roles.keys()
        if missing:
            raise ValueError(f"Pair {pair_id!r} is missing role(s): {sorted(missing)}")
        trap = roles["trap"]
        pairs.append(
            {
                "pair_id": pair_id,
                "pair_label": trap["environment"]["pair"],
                "category": trap["category"],
                "trap": trap,
                "lookalike": roles["lookalike"],
            }
        )

    if len(pairs) != EXPECTED_PAIR_COUNT:
        raise ValueError(f"Expected {EXPECTED_PAIR_COUNT} pairs, got {len(pairs)}")

    counts: Dict[str, int] = {}
    for pair in pairs:
        counts[pair["category"]] = counts.get(pair["category"], 0) + 1
    if counts != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(f"Category counts drifted from expectations: {counts}")

    return pairs


def main(out_path: Path = OUT_PATH) -> None:
    pairs = build_pairs()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"pairs": pairs, "count": len(pairs)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(pairs)} pairs to {out_path}")


if __name__ == "__main__":
    main()
