from app.agents import get_agent_action
from app.data import get_scenario, load_scenarios
from app.policies import evaluate_action


def test_baseline_agent_triggers_all_v1_trap_failures():
    trap_scenarios = [scenario for scenario in load_scenarios() if scenario.pair_role == "trap"]

    assert len(trap_scenarios) == 25

    for scenario in trap_scenarios:
        action = get_agent_action("baseline_surface_agent", scenario)
        result = evaluate_action(scenario, "baseline_surface_agent", "Baseline Surface Agent", action)

        assert result.verdict == "unsafe"
        assert scenario.measured_failure in result.failure_metrics


def test_baseline_agent_proceeds_on_v1_lookalikes():
    lookalike_scenarios = [scenario for scenario in load_scenarios() if scenario.pair_role == "lookalike"]

    assert len(lookalike_scenarios) == 25

    for scenario in lookalike_scenarios:
        action = get_agent_action("baseline_surface_agent", scenario)
        result = evaluate_action(scenario, "baseline_surface_agent", "Baseline Surface Agent", action)

        assert result.verdict == "safe"
        assert result.failure_metrics == []


def test_single_v1_failure_is_read_from_source_table():
    scenario = get_scenario("scn_v1_a1_trap")
    action = get_agent_action("baseline_surface_agent", scenario)
    result = evaluate_action(scenario, "baseline_surface_agent", "Baseline Surface Agent", action)

    assert "total_cost_fee_blindness" in result.failure_metrics


def test_audit_review_agent_avoids_unsafe_payments_on_v1_set():
    for scenario in load_scenarios():
        action = get_agent_action("audit_review_agent", scenario)
        result = evaluate_action(scenario, "audit_review_agent", "Audit Review Agent", action)

        assert result.unsafe_payment is False
        assert result.verdict == "safe"


def test_human_approval_agent_can_create_false_refusal():
    scenario = get_scenario("scn_v1_a1_lookalike")
    action = get_agent_action("human_approval_agent", scenario)
    result = evaluate_action(scenario, "human_approval_agent", "Human Approval Agent", action)

    assert result.verdict == "false_refusal"
    assert result.false_refusal is True
    assert "false_refusal" in result.failure_metrics
