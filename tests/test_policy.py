import pytest

from app.agents import get_agent_action
from app.data import get_scenario, load_scenarios
from app.policies import evaluate_action


@pytest.mark.parametrize(
    ("scenario_id", "expected_failure"),
    [
        ("scn_shipping_over_budget", "total_cost_constraint_violation"),
        ("scn_subscription_trap", "recurring_payment_consent_violation"),
        ("scn_merchant_whitelist", "merchant_authorization_violation"),
        ("scn_approval_splitting", "approval_threshold_evasion"),
        ("scn_prompt_injection_checkout", "prompt_injection_compliance"),
        ("scn_prompt_injection_checkout", "privacy_leakage"),
        ("scn_x402_overuse", "unnecessary_paid_tool_usage"),
        ("scn_x402_underuse", "beneficial_paid_tool_underuse"),
        ("scn_stablecoin_irreversibility", "premature_irreversible_settlement"),
        ("scn_refund_policy_neglect", "refundability_violation"),
        ("scn_category_drift", "category_policy_violation"),
    ],
)
def test_baseline_agent_triggers_seed_policy_failures(scenario_id, expected_failure):
    scenario = get_scenario(scenario_id)
    action = get_agent_action("baseline_surface_agent", scenario)
    result = evaluate_action(scenario, "baseline_surface_agent", "Baseline Surface Agent", action)

    assert expected_failure in result.failure_metrics


def test_audit_review_agent_avoids_unsafe_payments_on_seed_set():
    for scenario in load_scenarios():
        action = get_agent_action("audit_review_agent", scenario)
        result = evaluate_action(scenario, "audit_review_agent", "Audit Review Agent", action)

        assert result.unsafe_payment is False
        assert result.verdict == "safe"


def test_human_approval_agent_can_create_false_refusal():
    scenario = get_scenario("scn_x402_overuse")
    action = get_agent_action("human_approval_agent", scenario)
    result = evaluate_action(scenario, "human_approval_agent", "Human Approval Agent", action)

    assert result.verdict == "false_refusal"
    assert result.false_refusal is True
    assert "false_refusal" in result.failure_metrics

