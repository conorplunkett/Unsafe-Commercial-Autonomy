import httpx
import pytest

from app.data import DATA_DIR, get_scenario
from app.models import AgentAction
from app.providers import BaseProvider, ProviderAction, ProviderError, ProviderOutputError
from app.runner import RunAbortedError, _generate_with_retry, run_phase1_evaluation


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


class ReasoningCapturingProvider(AlwaysPurchaseProvider):
    """Like AlwaysPurchaseProvider, but also reports reasoning -- the shape a
    later vendor-adapter task will produce once it parses thinking
    blocks/reasoning_content/<think> tags out of the raw response."""

    def generate_action(self, scenario, control_condition, seed, temperature):
        provider_action = super().generate_action(scenario, control_condition, seed, temperature)
        return ProviderAction(
            raw_output=provider_action.raw_output,
            action=provider_action.action,
            provider_id=provider_action.provider_id,
            model_name=provider_action.model_name,
            reasoning="why",
        )


def test_phase1_runner_cardinality_for_one_model_all_controls_all_seeds():
    # Seeds are explicit here (the five-seed design), not the default -- see
    # test_phase1_runner_seeds_default_to_a_single_seed for that.
    run = run_phase1_evaluation(model_ids=["openai"], seeds=[1, 2, 3, 4, 5], live=False)

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


def test_phase1_runner_seeds_default_to_a_single_seed():
    # 2026-08-11: a bare run (no --seeds) now costs one seed, not five --
    # same "opt into the expensive axis on purpose" reasoning as Phase 2's
    # framing/urgency/user-availability axes (test_phase2_runner.py).
    run = run_phase1_evaluation(model_ids=["openai"], live=False)

    assert run.seeds == [1]
    assert len(run.results) == 50 * 3 * 1
    assert {result.seed for result in run.results} == {1}


def test_live_phase1_run_rejects_scenarios_with_stateful_checkout_controls():
    # d17/d23 (v2) author their trap as a checkout.controls checkbox -- Phase
    # 1 has no update_checkout-equivalent tool and render_offer_context has
    # no rendering for one, so a live run against either would silently show
    # the model less than it needs (2026-08-24 finding on d23). Caught before
    # any provider is constructed, so this never risks a real API call.
    v2_set = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
    with pytest.raises(KeyError, match="stateful checkout controls"):
        run_phase1_evaluation(
            model_ids=["openai"],
            scenario_ids=["scn_v2_d23_trap"],
            scenario_set_path=v2_set,
            live=True,
        )


def test_dry_run_phase1_preview_is_unaffected_by_the_checkout_control_guard():
    # DryRunProvider fabricates an action without ever building a prompt, so
    # the same scenario the live guard above refuses is fine to preview --
    # this is what keeps test_cli_eval_split_follows_the_scenario_set's
    # --dry-run sweep of the full v2 "survey" split (which includes several
    # checkout-control scenarios) working.
    v2_set = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
    run = run_phase1_evaluation(
        model_ids=["openai"],
        scenario_ids=["scn_v2_d23_trap"],
        scenario_set_path=v2_set,
        live=False,
    )
    assert len(run.results) == 1 * 3 * 1


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
    # The tool now reports the structured policy code it enforced against the
    # proposed action (the DryRun purchase is $53.98 over the $50 cap), not the
    # scenario's measured-failure label.
    assert tool_constraints.block_reasons == ["total_cost_constraint_violation"]


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


def test_provider_reasoning_flows_into_the_result():
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=False,
        provider_factory=lambda model_id, live: ReasoningCapturingProvider(),
    )

    assert run.results[0].raw_reasoning == "why"


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
    # The synthetic fallback action must not be graded as safe/refused_when_safe.
    assert result.verdict == "error"
    assert result.refused_when_safe is False
    assert result.unsafe_payment is False
    assert result.failure_metrics == []


def _transient(message: str = "connection failed") -> ProviderError:
    """A ProviderError wrapping a transport failure, as the providers raise it."""
    error = ProviderError(message)
    error.__cause__ = httpx.ConnectError(message)
    return error


class FlakyThenPurchaseProvider(AlwaysPurchaseProvider):
    """Fails with a transport error `failures` times, then succeeds."""

    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def generate_action(self, scenario, control_condition, seed, temperature):
        self.calls += 1
        if self.calls <= self.failures:
            raise _transient()
        return super().generate_action(scenario, control_condition, seed, temperature)


class AlwaysTerminalProvider(BaseProvider):
    """Fails with a non-retryable error (e.g. a 400), so retries are skipped."""

    provider_id = "terminal"
    model_name = "terminal-model"

    def __init__(self):
        self.calls = 0

    def generate_action(self, scenario, control_condition, seed, temperature):
        self.calls += 1
        raise ProviderError("bad request")


def test_transient_transport_error_is_retried_with_backoff():
    provider = FlakyThenPurchaseProvider(failures=2)
    delays: list[float] = []

    action, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=delays.append,
    )

    assert error is None
    assert action.action.action_type == "purchase"
    assert provider.calls == 3
    # Exponential, not a flat sleep.
    assert delays == [0.5, 1.0]


def test_transient_transport_error_gives_up_after_budget():
    provider = FlakyThenPurchaseProvider(failures=99)
    delays: list[float] = []

    _, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        transient_retries=3,
        sleep=delays.append,
    )

    assert error == "connection failed"
    assert provider.calls == 4  # one attempt plus three retries
    assert len(delays) == 3


def test_terminal_provider_error_is_not_retried():
    # A 400/404-class failure is deterministic: retrying only burns wall-clock,
    # so it must surface on the first attempt.
    provider = AlwaysTerminalProvider()
    delays: list[float] = []

    _, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=delays.append,
    )

    assert error == "bad request"
    assert provider.calls == 1
    assert delays == []


def test_output_and_transport_retry_budgets_are_separate():
    # Bad JSON must not consume the transport allowance: this provider emits one
    # transport failure and one bad-JSON response before succeeding, and both
    # should be absorbed.
    class MixedProvider(AlwaysPurchaseProvider):
        def __init__(self):
            self.calls = 0

        def generate_action(self, scenario, control_condition, seed, temperature):
            self.calls += 1
            if self.calls == 1:
                raise _transient()
            if self.calls == 2:
                raise ProviderOutputError("invalid json")
            return super().generate_action(scenario, control_condition, seed, temperature)

    provider = MixedProvider()
    action, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=lambda _: None,
    )

    assert error is None
    assert action.action.action_type == "purchase"
    assert provider.calls == 3


def test_run_aborts_after_consecutive_failures():
    provider = AlwaysTerminalProvider()

    with pytest.raises(RunAbortedError) as excinfo:
        run_phase1_evaluation(
            model_ids=["openai"],
            control_conditions=["no_policy"],
            scenario_ids=["scn_v1_a1_trap"],
            seeds=[1, 2, 3, 4, 5],
            live=False,
            provider_factory=lambda model_id, live: provider,
            consecutive_error_limit=3,
        )

    # Stopped at the limit rather than walking the rest of the grid.
    assert provider.calls == 3
    assert excinfo.value.consecutive_errors == 3
    assert excinfo.value.total_units == 5
    assert "bad request" in str(excinfo.value)


def test_consecutive_error_counter_resets_on_success():
    # Scattered blips are not an outage: two failures, a success, two more
    # failures must not trip a limit of three.
    class IntermittentProvider(AlwaysPurchaseProvider):
        def __init__(self):
            self.calls = 0

        def generate_action(self, scenario, control_condition, seed, temperature):
            self.calls += 1
            if self.calls in (1, 2, 4, 5):
                raise ProviderError("bad request")
            return super().generate_action(scenario, control_condition, seed, temperature)

    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1, 2, 3, 4, 5],
        live=False,
        provider_factory=lambda model_id, live: IntermittentProvider(),
        consecutive_error_limit=3,
    )

    assert len(run.results) == 5
    assert run.metrics["error_count"] == 4


def test_errored_results_excluded_from_rate_denominators():
    # Both a trap (over_refusal_scoring_enabled False) and a lookalike
    # (over_refusal_scoring_enabled True) error,
    # so the unsafe and false-refusal denominators should both be empty rather
    # than counting the fallback action as a real decision.
    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap", "scn_v1_a1_lookalike"],
        seeds=[1],
        live=False,
        provider_factory=lambda model_id, live: AlwaysInvalidProvider(),
    )

    metrics = run.metrics
    assert metrics["error_count"] == 2
    assert metrics["verdict_counts"] == {"error": 2}
    assert metrics["refused_when_safe_rate"] == 0.0
    assert metrics["refused_when_safe_ci"]["total"] == 0
    assert metrics["unsafe_payment_ci"]["total"] == 0


class FailingPreflightProvider(AlwaysPurchaseProvider):
    """Mimics a wrong/unavailable model id: preflight rejects before any call."""

    def __init__(self):
        self.calls = 0

    def preflight(self):
        raise ProviderError("model 'gpt-5.5-nano' is not available to this account")

    def generate_action(self, scenario, control_condition, seed, temperature):
        self.calls += 1
        return super().generate_action(scenario, control_condition, seed, temperature)


def test_preflight_failure_aborts_before_running_any_combo():
    # A bad model id should fail once, up front — not once per (scenario,
    # condition, seed) after burning real API calls.
    provider = FailingPreflightProvider()
    with pytest.raises(ProviderError, match="not available"):
        run_phase1_evaluation(
            model_ids=["openai"],
            control_conditions=["no_policy", "prompt_policy", "tool_constraints"],
            scenario_ids=["scn_v1_a1_trap", "scn_v1_a1_lookalike"],
            seeds=[1],
            provider_factory=lambda model_id, live: provider,
        )

    assert provider.calls == 0


def test_select_control_conditions_accepts_all():
    # `--conditions all` should expand to the full default set, mirroring
    # `--models all`, instead of raising "Unknown control conditions: all".
    from app.runner import DEFAULT_CONTROL_CONDITIONS, _select_control_conditions

    assert _select_control_conditions(["all"]) == DEFAULT_CONTROL_CONDITIONS
    with pytest.raises(KeyError, match="Unknown control conditions"):
        _select_control_conditions(["no_policy", "made_up"])


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


def test_runner_records_gemini_thinking_level_on_run():
    from app.runner import run_phase1_evaluation

    run = run_phase1_evaluation(
        model_ids=["gemini"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        gemini_thinking_level="high",
        live=False,
    )

    assert run.gemini_thinking_level == "high"


def _rate_limited(retry_after=None) -> ProviderError:
    request = httpx.Request("POST", "https://example.invalid/v1/responses")
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    response = httpx.Response(429, request=request, headers=headers)
    error = ProviderError("rate limited")
    error.__cause__ = httpx.HTTPStatusError("HTTP 429", request=request, response=response)
    return error


class RateLimitedThenPurchaseProvider(AlwaysPurchaseProvider):
    """429s `failures` times (optionally with a Retry-After hint), then succeeds."""

    def __init__(self, failures: int, retry_after=None):
        self.failures = failures
        self.retry_after = retry_after
        self.calls = 0

    def generate_action(self, scenario, control_condition, seed, temperature):
        self.calls += 1
        if self.calls <= self.failures:
            raise _rate_limited(self.retry_after)
        return super().generate_action(scenario, control_condition, seed, temperature)


def test_rate_limit_rides_the_minutes_budget_not_the_attempt_count():
    # Five consecutive 429s used to burn the 3-attempt budget (3.5 s total)
    # and record the cell as an error; the wall-clock budget rides them out.
    provider = RateLimitedThenPurchaseProvider(failures=5)
    delays: list[float] = []

    action, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=delays.append,
    )

    assert error is None
    assert action.action.action_type == "purchase"
    assert provider.calls == 6
    assert delays == [2.0, 4.0, 8.0, 16.0, 32.0]


def test_rate_limit_honors_the_providers_retry_after_hint():
    provider = RateLimitedThenPurchaseProvider(failures=1, retry_after=17)
    delays: list[float] = []

    _, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=delays.append,
    )

    assert error is None
    assert delays == [17.0]


def test_rate_limit_gives_up_once_the_wall_clock_budget_is_spent():
    provider = RateLimitedThenPurchaseProvider(failures=99, retry_after=150)
    delays: list[float] = []

    _, error = _generate_with_retry(
        provider,
        get_scenario("scn_v1_a1_trap"),
        "no_policy",
        seed=1,
        temperature=0.7,
        sleep=delays.append,
    )

    assert error == "rate limited"
    assert delays == [150.0, 150.0]  # two hints consume the 300 s budget, then stop
    assert provider.calls == 3
