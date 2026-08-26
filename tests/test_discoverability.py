"""The discoverability manifest and the surface it makes claims about.

The manifest (data/answer_keys/discoverability.json) is the guard against the
bug class found by hand on 2026-08-26: a trap whose deciding rule lived only in
the hidden payment_policy, so under no_policy the model was scored against a
fact it could never see (seven traps), or a lookalike premise no sandbox
channel delivered (E21). Every trap must either name its deciding fact as
patterns that provably appear in the no_policy-visible surface, or declare
"policy_only" on purpose — a counted decision, never an accident.
"""

import json
import re

from app.data import DATA_DIR, DISCOVERABILITY_PATH, load_scenarios
from app.phase2.sandbox import no_policy_surface

V2_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"


def _manifest():
    manifest = json.loads(DISCOVERABILITY_PATH.read_text(encoding="utf-8"))
    manifest.pop("_meta", None)
    return manifest


def _scenarios():
    return {scenario.scenario_id: scenario for scenario in load_scenarios(V2_SET)}


def _matches(pattern, surface: str) -> bool:
    if isinstance(pattern, dict):
        return re.search(pattern["regex"], surface, re.IGNORECASE) is not None
    return pattern.lower() in surface.lower()


def test_manifest_covers_exactly_the_traps_with_wellformed_entries():
    manifest = _manifest()
    scenarios = _scenarios()
    trap_ids = {sid for sid, s in scenarios.items() if s.pair_role == "trap"}
    # Exactly one entry per trap; extra ids are orphans (a rename left a stale
    # entry, or a lookalike was keyed by mistake — lookalike entries are
    # allowed, but must at least resolve to a real scenario).
    assert set(manifest) >= trap_ids, sorted(trap_ids - set(manifest))
    assert set(manifest) <= set(scenarios), sorted(set(manifest) - set(scenarios))
    for scenario_id, entry in manifest.items():
        has_patterns = bool(entry.get("deciding_fact"))
        is_policy_only = entry.get("grounding") == "policy_only"
        assert has_patterns != is_policy_only, (
            f"{scenario_id}: exactly one of deciding_fact / grounding=policy_only"
        )
        # A hidden rule is a deliberate design decision, so it has to say why.
        if is_policy_only:
            assert entry.get("notes"), f"{scenario_id}: policy_only requires notes"


def test_every_deciding_fact_appears_in_the_no_policy_surface():
    manifest = _manifest()
    scenarios = _scenarios()
    for scenario_id, entry in manifest.items():
        patterns = entry.get("deciding_fact") or []
        if not patterns:
            continue
        surface = no_policy_surface(scenarios[scenario_id])
        for pattern in patterns:
            assert _matches(pattern, surface), (
                f"{scenario_id}: deciding fact {pattern!r} is not in the "
                "no_policy-visible surface — the trap announces a fact the "
                "model cannot read, the exact bug this manifest exists to stop"
            )


def test_the_2026_08_26_fixes_are_world_grounded():
    # The seven traps whose rules moved into the task, plus E21's trap: all
    # must carry patterned entries — regressing any of them back to a hidden
    # rule requires an explicit policy_only declaration here.
    manifest = _manifest()
    for scenario_id in (
        "scn_v2_c1_trap",
        "scn_v2_c4_trap",
        "scn_v2_c9_trap",
        "scn_v2_b4_trap",
        "scn_v2_b10_trap",
        "scn_v2_b22_trap",
        "scn_v2_b25_trap",
        "scn_v2_e21_trap",
    ):
        assert manifest[scenario_id].get("deciding_fact"), scenario_id


def test_world_grounded_flag_and_counts_follow_the_manifest():
    scenarios = _scenarios()
    traps = [s for s in scenarios.values() if s.pair_role == "trap"]
    world = sorted(s.scenario_id for s in traps if s.world_grounded)
    policy = sorted(s.scenario_id for s in traps if not s.world_grounded)
    # Pinned so a rebalance is a deliberate test update, not silent drift
    # (mirrors test_semantic_only_flag_marks_exactly_the_survey_dependent_traps).
    assert len(world) == 110
    assert policy == ["scn_v2_b11_trap", "scn_v2_b17_trap", "scn_v2_b19_trap"]
    # Lookalikes carry no grounding claim.
    assert not any(s.world_grounded for s in scenarios.values() if s.pair_role == "lookalike")
