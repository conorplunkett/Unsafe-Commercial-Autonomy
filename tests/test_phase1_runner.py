from app.data import get_scenario
from app.models import AgentAction
from app.providers import BaseProvider, ProviderAction, ProviderOutputError
from app.runner import run_phase1_evaluation


class AlwaysPurchaseProvider(BaseProvider):
    provider_id = "fake"
    model_name = "fake-model"

    def generate_action(self, scenario, control_condition, seed, temperature):
        action = AgentAction(
            action_type="purchase",
            amount=53.98,
            merchant_id="simulated_merchant",
            sku=scenario.scenario_id,
            payment_type="card",
            rationale="Always buys.",
        )
        return ProviderAction(
            raw_output='{"action_type": "purchase"}',
            action=action,
            provider_id=self.provider_id,
            model_name=self.model_name,
        )


class InvalidThenPurchaseProvider(AlwaysPurchaseProvider):
    def __init__(self):
        self.calls = 0

    def generate_action(self, scenario, control_condition, seed, temperature):
        self.calls += 1
        if self.calls == 1:
            raise ProviderOutputError("invalid json")
        return super().generate_action(scenario, control_condition, seed, temperature)


class AlwaysInvalidProvider(BaseProvider):
    provider_id = "broken"
    model_name = "broken-model"

    def generate_action(self, scenario, control_condition, seed, temperature):
        raise ProviderOutputError("invalid json")


def test_phase1_runner_cardinality_for_one_model_all_controls_all_seeds():
    run = run_phase1_evaluation(model_ids=["openai"], live=False)

    assert len(run.results) == 50 * 3 * 5
    assert run.model_ids == ["openai"]
    # model_names records the actual model evaluated, distinct from the provider
    # id in model_ids; the offline dry-run provider reports "dryrun-openai".
    assert run.model_names == ["dryrun-openai"]
    assert run.control_conditions == ["no_policy", "prompt_policy", "tool_constraints"]
    assert run.seeds == [1, 2, 3, 4, 5]
    assert run.metrics["total_results"] == 750
    assert set(run.metrics["by_control_condition"]) == {
        "no_policy",
        "prompt_policy",
        "tool_constraints",
    }


def test_tool_constraints_block_enforceable_unsafe_payment():
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy", "tool_constraints"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=False,
    )

    no_policy, tool_constraints = run.results
    assert no_policy.verdict == "unsafe"
    assert no_policy.action.action_type == "purchase"
    assert tool_constraints.verdict == "safe"
    assert tool_constraints.proposed_action.action_type == "purchase"
    assert tool_constraints.action.action_type == "ask_approval"
    assert tool_constraints.block_reasons == ["total_cost_fee_blindness"]


def test_tool_constraints_do_not_block_safe_lookalike_purchase():
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["tool_constraints"],
        scenario_ids=["scn_v1_a1_lookalike"],
        seeds=[1],
        live=False,
    )

    result = run.results[0]
    assert result.verdict == "safe"
    assert result.action.action_type == "purchase"
    assert result.block_reasons == []


def test_provider_invalid_json_is_retried():
    provider = InvalidThenPurchaseProvider()
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=False,
        provider_factory=lambda model_id, live: provider,
    )

    assert provider.calls == 2
    assert run.results[0].error is None
    assert run.results[0].action.action_type == "purchase"


def test_provider_invalid_json_after_retry_is_marked_errored():
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=False,
        provider_factory=lambda model_id, live: AlwaysInvalidProvider(),
    )

    result = run.results[0]
    assert result.error == "invalid json"
    assert result.action.action_type == "defer"


def test_runner_records_reasoning_effort_on_run():
    from app.runner import run_phase1_evaluation

    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        reasoning_effort="medium",
        live=False,
    )

    assert run.reasoning_effort == "medium"
    assert run.temperature == 0.7
