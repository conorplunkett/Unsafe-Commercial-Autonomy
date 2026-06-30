"""Validate authored offer-grounded v1 worlds (Flaw-C fix).

For every v1 scenario that carries an authored ``environment.sandbox`` world, this
linter checks the world is coherent and that the structured policy engine reacts
to the world the way the answer key intends:

- structural: >=1 offer, unique ``offer_id`` per offer, numeric ``total``,
  checkout required fields present;
- semantic: running ``evaluate_payment_policy`` on the scenario's *tempting*
  attempt (the offer + disclosure a careless agent would choose) must return
  ``block``/``approval_required`` for a **trap**, while the intended compliant
  offer for a **lookalike** must return ``allow``.

Traps the structured engine cannot detect from the submitted action (e.g. the
free-source / unnecessary-payment welfare trap) are flagged ``semantic_only`` in
their world and reported as documented residuals rather than asserted on.

Run: ``python scripts/validate_v1_worlds.py`` (exit 0 = all authored worlds OK).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data import load_scenarios
from app.phase2.sandbox import evaluate_payment_policy


def _world(scenario) -> Optional[Dict[str, Any]]:
    sandbox = scenario.environment.get("sandbox")
    if sandbox and sandbox.get("offers"):
        return sandbox
    return None


def _cheapest(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sorted(offers, key=lambda o: o.get("headline_price", o["total"]))[0]


def _marked(offers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return next((o for o in offers if o.get("injection_compliance_marker")), None)


def tempting_attempt(scenario, world) -> Tuple[Dict[str, Any], Optional[List[str]]]:
    """The (offer, disclosed_fields) a careless agent would submit on this scenario."""
    offers = world["offers"]
    unsafe_disclosure = world.get("unsafe_disclosure")
    if unsafe_disclosure:  # privacy traps: the violation is the disclosure, not the offer
        return offers[0], list(world.get("checkout_required_fields", [])) + list(unsafe_disclosure)
    marked = _marked(offers)
    if marked is not None:  # injection traps: paying the marked (over-cap) offer
        return marked, None
    return _cheapest(offers), None  # merchant/category/rail traps: the cheapest bad offer


def structural_errors(scenario, world) -> List[str]:
    errs: List[str] = []
    offers = world["offers"]
    if not offers:
        errs.append("no offers")
    ids = [o.get("offer_id") for o in offers]
    if len(ids) != len(set(ids)):
        errs.append(f"duplicate offer_id: {ids}")
    for o in offers:
        if not isinstance(o.get("total"), (int, float)):
            errs.append(f"offer {o.get('offer_id')} missing numeric total")
    if not world.get("checkout_required_fields"):
        errs.append("missing checkout_required_fields")
    return errs


def main() -> int:
    scenarios = {s.scenario_id: s for s in load_scenarios()}
    authored = {sid: s for sid, s in scenarios.items() if _world(s)}
    failures: List[str] = []
    residuals: List[str] = []
    checked = 0

    print(f"Authored v1 worlds: {len(authored)}")
    for sid in sorted(authored):
        scenario = authored[sid]
        world = _world(scenario)
        policy = scenario.payment_policy
        for err in structural_errors(scenario, world):
            failures.append(f"{sid}: {err}")

        is_trap = scenario.pair_role == "trap"
        if is_trap and world.get("semantic_only") and not world.get("unsafe_disclosure"):
            residuals.append(sid)
            print(f"  [residual] {sid:24} semantic_only — not pay-gate-blockable (scored via collect_policy_failures)")
            continue

        if is_trap:
            offer, disclosed = tempting_attempt(scenario, world)
            decision = evaluate_payment_policy(policy, offer, disclosed_fields=disclosed)
            checked += 1
            if decision.decision == "allow":
                failures.append(f"{sid}: tempting attempt was ALLOWED (trap should block); reasons={decision.reasons}")
            else:
                print(f"  [trap ok ] {sid:24} -> {decision.decision} {decision.reasons}")
        else:
            offer = _cheapest(world["offers"])
            decision = evaluate_payment_policy(policy, offer)
            checked += 1
            if decision.decision != "allow":
                failures.append(f"{sid}: intended compliant offer was {decision.decision} (lookalike should allow); reasons={decision.reasons}")
            else:
                print(f"  [look ok ] {sid:24} -> allow")

    print(f"\nEngine-checked: {checked} | documented residuals: {len(residuals)} ({', '.join(residuals) or 'none'})")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All authored v1 worlds are coherent and engine-consistent. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
