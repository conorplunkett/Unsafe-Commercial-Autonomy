"""Generate the per-scenario record of where the enforced arm can fire.

`tool_constraints` runs on the scenarios whose pay rail can refuse a payment
their world offers, plus their pair partners (app/phase2/scope.py). That fact
is computed from the sandbox, so this file is a projection of it, not a second
answer: `app.phase2.sandbox.reachable_rail_findings` decides, and a test
regenerates this file and compares.

Unlike `phase2_research_contract.json`, this projection is *derived* — a
scenario edit that changes which structured field a world can trip is supposed
to move it. When the drift test fails, read the diff to see whether the scope
change was the one you intended, then commit the regenerated file with the
scenario change:

    python scripts/generate_phase2_enforcement_scope.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.data import load_scenarios  # noqa: E402
from app.phase2 import PHASE2_SCENARIO_SET  # noqa: E402
from app.phase2.sandbox import (  # noqa: E402
    RAIL_SURFACES,
    cheapest_surface,
    reachable_rail_findings,
)
from app.phase2.scope import enforcement_scope_ids  # noqa: E402

OUT_PATH = ROOT / "data" / "answer_keys" / "phase2_enforcement_scope.json"

SURFACE_NOTES = {
    "offer_as_listed": "the offer is refused exactly as the merchant presents it",
    "checkout_control": "a checkout control has to be moved off its opening value first",
    "payment_rail": "a rail other than the offer's default has to be chosen first",
    "optional_disclosure": "an optional checkout field has to be disclosed first",
    "unswept": "the checkout state space exceeded the sweep budget without deciding",
}


def build_projection(scenario_set: Path = PHASE2_SCENARIO_SET) -> Dict[str, Any]:
    scenarios = load_scenarios(scenario_set)
    in_arm = enforcement_scope_ids(scenarios)

    records: Dict[str, Any] = {}
    for scenario in scenarios:
        findings = list(reachable_rail_findings(scenario))
        records[scenario.scenario_id] = {
            "pair_id": scenario.pair_id,
            "pair_role": scenario.pair_role,
            "rail_reachable": bool(findings),
            "in_enforced_arm": scenario.scenario_id in in_arm,
            # The least the agent has to do before the rail fires. None when
            # nothing it can do makes the rail fire.
            "fires_on": cheapest_surface(findings),
            "decisions": sorted({finding.decision for finding in findings}),
            "reasons": sorted({reason for finding in findings for reason in finding.reasons}),
            "offers": sorted({finding.offer_id for finding in findings}),
        }

    pairs = {scenario.pair_id for scenario in scenarios if scenario.pair_id}
    pairs_in_arm = {
        scenario.pair_id
        for scenario in scenarios
        if scenario.pair_id and scenario.scenario_id in in_arm
    }
    surfaces = Counter(
        record["fires_on"] for record in records.values() if record["fires_on"]
    )
    return {
        "_meta": {
            "description": (
                "Per-scenario record of where the tool_constraints arm can fire, and "
                "which scenarios it therefore runs. Derived from the sandbox by "
                "app.phase2.sandbox.reachable_rail_findings; regenerate with "
                "scripts/generate_phase2_enforcement_scope.py."
            ),
            "scenario_set": str(scenario_set.relative_to(ROOT)),
            "arm_membership": (
                "in_enforced_arm is the pair closure of rail_reachable: a reachable "
                "trap brings its lookalike, so enforcement's harm reduction is always "
                "read next to what the same rail does to safe purchases."
            ),
            "reason_completeness": (
                "reasons and offers cover the checkout states actually swept; a world "
                "past the sweep budget can refuse for reasons not listed here. "
                "rail_reachable and in_enforced_arm are unaffected."
            ),
            "surfaces": SURFACE_NOTES,
        },
        "counts": {
            "scenarios": len(scenarios),
            "rail_reachable": sum(1 for record in records.values() if record["rail_reachable"]),
            "in_enforced_arm": len(in_arm),
            "pairs": len(pairs),
            "pairs_in_enforced_arm": len(pairs_in_arm),
        },
        "by_surface": {surface: surfaces[surface] for surface in RAIL_SURFACES if surfaces[surface]},
        "scenarios": records,
    }


def main(out_path: Path = OUT_PATH) -> None:
    projection = build_projection()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    counts = projection["counts"]
    print(
        f"Wrote {out_path}: {counts['rail_reachable']} rail-reachable, "
        f"{counts['in_enforced_arm']} in the enforced arm, of {counts['scenarios']}."
    )


if __name__ == "__main__":
    main()
