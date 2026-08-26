"""Which scenarios each Phase 2 control condition runs on.

`no_policy` and `structured_policy` differ from each other in the prompt alone,
so every scenario in the set can move between them: all 226 carry information
for those two arms.

`tool_constraints` is not like that. It shows the same policy JSON as
`structured_policy` and adds one sentence, and its only other difference is
that `pay` consults the policy engine before completing. Where no payment the
world can produce evaluates to anything but `allow`, that engine never fires:
the arm spends a full tool loop per episode to re-measure what the unenforced
arm already measured. Across the v2 set that is most of it — the rail can
refuse in 88 of 226 scenarios, 83 pairs once each reachable scenario brings its
partner, leaving 30 pairs where enforcement has nothing to enforce.

So the enforced arm runs on the pair closure of the reachable scenarios, and
the other two run on everything selected. Closure matters: a trap the rail
blocks and its lookalike are one measurement. Dropping the lookalike would
report enforcement's harm reduction with no read on what the same rail does to
purchases it should let through, which is the one comparison this benchmark
exists to keep honest.

Scope is a property of the scenario set, not of a run's `--scenario-ids`: a
lookalike selected on its own is still in scope when its partner is reachable.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set

from ..models import Scenario
from .sandbox import rail_reachable


# Conditions whose pay tool consults the policy engine. `no_policy` and
# `structured_policy` complete every payment the model asks for.
ENFORCED_CONDITIONS = ("tool_constraints",)

# "rail_reachable" runs the enforced arm on the pair closure of the scenarios
# whose rail can refuse something; "all" runs it on everything selected, the
# pre-2026-08-24 grid.
ENFORCEMENT_SCOPES = ("rail_reachable", "all")
DEFAULT_ENFORCEMENT_SCOPE = "rail_reachable"


def rail_reachable_ids(scenarios: Iterable[Scenario]) -> Set[str]:
    """Ids whose own world gives the rail something to refuse."""
    return {scenario.scenario_id for scenario in scenarios if rail_reachable(scenario)}


def enforcement_scope_ids(scenarios: Iterable[Scenario]) -> Set[str]:
    """Ids the enforced arm runs on: reachable scenarios plus their pair partners."""
    catalogue = list(scenarios)
    reachable = rail_reachable_ids(catalogue)
    pairs: Dict[str, List[str]] = {}
    for scenario in catalogue:
        if scenario.pair_id:
            pairs.setdefault(scenario.pair_id, []).append(scenario.scenario_id)
    scope = set(reachable)
    for members in pairs.values():
        if scope & set(members):
            scope.update(members)
    return scope


def scenarios_by_condition(
    conditions: Sequence[str],
    selected: Sequence[Scenario],
    catalogue: Sequence[Scenario],
    scope: str = DEFAULT_ENFORCEMENT_SCOPE,
) -> Dict[str, List[Scenario]]:
    """The scenario list each condition's episodes are built from.

    ``selected`` is what the run asked for; ``catalogue`` is the whole scenario
    set the scope is computed against, so pair closure holds even when only one
    half of a pair was selected.
    """
    if scope not in ENFORCEMENT_SCOPES:
        raise KeyError(
            f"Unknown enforcement scope: {scope}. "
            f"Expected one of: {', '.join(ENFORCEMENT_SCOPES)}."
        )
    if scope == "all" or not any(condition in ENFORCED_CONDITIONS for condition in conditions):
        return {condition: list(selected) for condition in conditions}

    in_scope = enforcement_scope_ids(catalogue)
    enforced = [scenario for scenario in selected if scenario.scenario_id in in_scope]
    if not enforced:
        raise ValueError(
            f"{', '.join(c for c in conditions if c in ENFORCED_CONDITIONS)} was selected, but "
            f"none of the {len(selected)} scenario(s) chosen are in the enforcement scope: the "
            "pay rail cannot refuse any payment their worlds offer, so the arm would be a copy "
            "of structured_policy with one extra sentence. Run it anyway with "
            "--enforcement-scope all, or select scenarios the rail can reach."
        )
    return {
        condition: list(enforced) if condition in ENFORCED_CONDITIONS else list(selected)
        for condition in conditions
    }
