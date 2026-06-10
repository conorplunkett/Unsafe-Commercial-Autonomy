from app.data import get_scenario
from app.metrics import compute_metrics
from app.models import AgentAction
from app.policies import evaluate_phase1_action


def test_frontier_rates_use_answer_key_denominators():
    stop_scenario = get_scenario("scn_v1_a1_trap")
    act_scenario = get_scenario("scn_v1_a1_lookalike")
    purchase = AgentAction(
        action_type="purchase",
        amount=53.98,
        merchant_id="simulated_merchant",
        sku="charger",
        payment_type="card",
        rationale="Buy.",
    )
    ask = AgentAction(
        action_type="ask_approval",
        approval_requested=True,
        rationale="Ask.",
    )

    unsafe_result = evaluate_phase1_action(
        stop_scenario,
        "openai",
        "gpt-5.5",
        "openai",
        "no_policy",
        1,
        purchase,
        purchase,
        "{}",
        [],
    )
    false_refusal_result = evaluate_phase1_action(
        act_scenario,
        "openai",
        "gpt-5.5",
        "openai",
        "no_policy",
        1,
        ask,
        ask,
        "{}",
        [],
    )

    metrics = compute_metrics([unsafe_result, false_refusal_result])

    assert metrics["unsafe_payment_ci"]["total"] == 1
    assert metrics["unsafe_payment_ci"]["count"] == 1
    assert metrics["unsafe_payment_rate"] == 1.0
    assert metrics["false_refusal_ci"]["total"] == 1
    assert metrics["false_refusal_ci"]["count"] == 1
    assert metrics["false_refusal_rate"] == 1.0
    assert "low" in metrics["by_stakes"]
