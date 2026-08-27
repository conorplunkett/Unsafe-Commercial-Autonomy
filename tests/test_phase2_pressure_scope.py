"""Pressure scope: which conditions the urgency/user_availability axes run on.

phase2_pressure_contrasts (app/metrics.py) reads its deltas from
structured_policy episodes alone, so crossing the pressure axes against
no_policy/tool_constraints too spends on cells no metric reads. --pressure-scope
headline_only (the default) skips that spend; --pressure-scope all restores the
pre-2026-08-26 full cross-product.
"""

from __future__ import annotations

import pytest

from app.metrics import HEADLINE_CONTROL_CONDITION
from app.phase2.runner import run_phase2_evaluation
from app.phase2.scope import PRESSURE_SCOPES, pressure_axes_by_condition

PAIR_IDS = ["scn_v2_a1_trap", "scn_v2_a1_lookalike"]


def test_headline_control_condition_is_structured_policy():
    # The scoping logic below is only correct if this still holds.
    assert HEADLINE_CONTROL_CONDITION == "structured_policy"


def test_pressure_axes_by_condition_scopes_non_headline_conditions_to_baseline():
    conditions = ["no_policy", "structured_policy", "tool_constraints"]
    per_condition = pressure_axes_by_condition(
        conditions, ["none", "time_pressure"], ["none", "unreachable"], "structured_policy"
    )
    assert per_condition["structured_policy"] == (["none", "time_pressure"], ["none", "unreachable"])
    assert per_condition["no_policy"] == (["none"], ["none"])
    assert per_condition["tool_constraints"] == (["none"], ["none"])


def test_pressure_axes_by_condition_all_scope_restores_the_full_cross_product():
    conditions = ["no_policy", "structured_policy"]
    per_condition = pressure_axes_by_condition(
        conditions, ["none", "time_pressure"], ["none"], "structured_policy", scope="all"
    )
    assert per_condition["no_policy"] == (["none", "time_pressure"], ["none"])
    assert per_condition["structured_policy"] == (["none", "time_pressure"], ["none"])


def test_pressure_axes_by_condition_is_a_noop_without_the_headline_condition():
    """A run that never includes structured_policy has no headline cell to
    protect from duplication, so the requested axes apply unmodified — an
    explicit --urgencies all on a no_policy-only run must still run it."""
    per_condition = pressure_axes_by_condition(
        ["no_policy"], ["none", "time_pressure"], ["none"], "structured_policy"
    )
    assert per_condition["no_policy"] == (["none", "time_pressure"], ["none"])


def test_unknown_pressure_scope_is_rejected():
    with pytest.raises(KeyError):
        pressure_axes_by_condition(["no_policy"], ["none"], ["none"], "structured_policy", scope="sometimes")


def test_pressure_scopes_are_exactly_headline_only_and_all():
    assert PRESSURE_SCOPES == ("headline_only", "all")


def test_runner_scopes_pressure_axes_to_the_headline_condition_by_default():
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy", "structured_policy", "tool_constraints"],
        urgencies=["all"],
        user_availabilities=["all"],
        scenario_ids=PAIR_IDS,
        seeds=[1],
        checkpoint=False,
    )
    seen = {(r.control_condition, r.urgency, r.user_availability) for r in run.results}
    # structured_policy runs the full 2x2.
    assert ("structured_policy", "none", "none") in seen
    assert ("structured_policy", "time_pressure", "unreachable") in seen
    assert ("structured_policy", "time_pressure", "none") in seen
    assert ("structured_policy", "none", "unreachable") in seen
    # no_policy and tool_constraints run pressure-axis baseline only.
    non_headline = {
        (condition, urgency, availability)
        for condition, urgency, availability in seen
        if condition != "structured_policy"
    }
    assert non_headline == {("no_policy", "none", "none"), ("tool_constraints", "none", "none")}
    assert run.pressure_scope == "headline_only"
    # 2 scenarios x (1 no_policy cell + 4 structured_policy cells + 1 tool_constraints cell)
    assert len(run.results) == 2 * (1 + 4 + 1)


def test_runner_pressure_scope_all_restores_the_full_cross_product():
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy", "structured_policy"],
        urgencies=["all"],
        user_availabilities=["none"],
        pressure_scope="all",
        scenario_ids=PAIR_IDS,
        seeds=[1],
        checkpoint=False,
    )
    seen = {(r.control_condition, r.urgency) for r in run.results}
    assert seen == {
        ("no_policy", "none"),
        ("no_policy", "time_pressure"),
        ("structured_policy", "none"),
        ("structured_policy", "time_pressure"),
    }
    assert run.pressure_scope == "all"
    assert len(run.results) == 2 * 2 * 2  # 2 scenarios x 2 conditions x 2 urgencies


def test_runner_pressure_scope_is_a_noop_without_structured_policy_selected():
    """--conditions no_policy --urgencies all must still run both urgency
    levels: there is no headline cell in this run to spare no_policy from
    duplicating, so headline_only's narrowing does not apply."""
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy"],
        urgencies=["all"],
        scenario_ids=PAIR_IDS,
        seeds=[1],
        checkpoint=False,
    )
    assert {r.urgency for r in run.results} == {"none", "time_pressure"}
    assert len(run.results) == 2 * 2  # 2 scenarios x 2 urgencies
