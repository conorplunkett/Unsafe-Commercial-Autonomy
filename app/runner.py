from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional
from uuid import uuid4

from .agents import AGENT_IDS, AGENT_PROFILES, get_agent_action
from .data import load_scenarios
from .metrics import compute_metrics, distinct_model_names
from .models import BenchmarkRun, ControlCondition, EvaluationResult, Scenario
from .policies import apply_tool_constraints, evaluate_action, evaluate_phase1_action
from .providers import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    DEFAULT_CONSECUTIVE_ERROR_LIMIT,
    DEFAULT_TRANSIENT_RETRIES,
    BaseProvider,
    ProviderAction,
    ProviderError,
    ProviderOutputError,
    RunAbortedError,
    backoff_delay,
    create_provider,
    is_retryable_provider_error,
    resolve_model_ids,
)


DEFAULT_CONTROL_CONDITIONS: List[ControlCondition] = [
    "no_policy",
    "prompt_policy",
    "tool_constraints",
]
DEFAULT_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_TEMPERATURE = 0.7

# Retry policy, the shared backoff schedule, and RunAbortedError now live in
# app/providers.py so Phase 2 can apply the same policy without importing this
# module. Re-exported here because `from app.runner import RunAbortedError` is
# the established import path for the CLI and the Phase 1 tests.
__all__ = [
    "BACKOFF_BASE_SECONDS",
    "BACKOFF_MAX_SECONDS",
    "DEFAULT_CONSECUTIVE_ERROR_LIMIT",
    "DEFAULT_CONTROL_CONDITIONS",
    "DEFAULT_SEEDS",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_TRANSIENT_RETRIES",
    "RunAbortedError",
    "run_phase1_evaluation",
]


def _select_scenarios(
    scenario_ids: Optional[Iterable[str]],
    scenario_set_path: Optional[Path] = None,
) -> List[Scenario]:
    scenarios = load_scenarios(scenario_set_path)
    if not scenario_ids:
        return scenarios
    selected_ids = set(scenario_ids)
    selected = [scenario for scenario in scenarios if scenario.scenario_id in selected_ids]
    missing = selected_ids - {scenario.scenario_id for scenario in selected}
    if missing:
        raise KeyError(f"Unknown scenarios: {', '.join(sorted(missing))}")
    return selected


def _select_agents(agent_ids: Optional[Iterable[str]]) -> List[str]:
    if not agent_ids:
        return AGENT_IDS
    selected = list(agent_ids)
    missing = set(selected) - set(AGENT_IDS)
    if missing:
        raise KeyError(f"Unknown agents: {', '.join(sorted(missing))}")
    return selected


def _select_control_conditions(
    control_conditions: Optional[Iterable[ControlCondition]],
) -> List[ControlCondition]:
    selected = list(control_conditions or DEFAULT_CONTROL_CONDITIONS)
    if "all" in selected:
        return DEFAULT_CONTROL_CONDITIONS.copy()
    missing = set(selected) - set(DEFAULT_CONTROL_CONDITIONS)
    if missing:
        raise KeyError(f"Unknown control conditions: {', '.join(sorted(missing))}")
    return selected


def _select_seeds(seeds: Optional[Iterable[int]]) -> List[int]:
    selected = list(seeds or DEFAULT_SEEDS)
    if not selected:
        raise ValueError("At least one seed is required.")
    return selected


def _run_answer_key_status(scenarios: List[Scenario]) -> str:
    # Dropped scenarios are out of the headline key by decision, so they do
    # not hold the run's key status at "provisional"; a run is locked when
    # every scenario that still carries a key claim is locked.
    keyed = [scenario for scenario in scenarios if scenario.answer_key_status != "dropped"]
    if keyed and all(scenario.answer_key_status == "locked" for scenario in keyed):
        return "locked"
    return "provisional"


def _error_provider_action(model_id: str, error: Exception) -> ProviderAction:
    from .models import AgentAction

    action = AgentAction(
        action_type="defer",
        rationale=f"Provider failed before producing a valid action: {error}",
    )
    return ProviderAction(
        raw_output="",
        action=action,
        provider_id=f"error_{model_id}",
        model_name=model_id,
    )


def _generate_with_retry(
    provider: BaseProvider,
    scenario: Scenario,
    control_condition: ControlCondition,
    seed: int,
    temperature: float,
    retries: int = 1,
    transient_retries: int = DEFAULT_TRANSIENT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[ProviderAction, Optional[str]]:
    """One grid cell, with separate budgets for the two ways a call can fail.

    Malformed JSON is the model's fault and retries immediately (``retries``).
    A transport failure is the network's fault and retries with exponential
    backoff (``transient_retries``) — a hotspot blip used to burn the whole
    remaining grid because every ProviderError broke out on the first attempt.
    The budgets are separate so a flapping link cannot consume the allowance
    for bad output, or vice versa.
    """
    last_error: Optional[Exception] = None
    output_retries_left = retries
    transient_retries_left = transient_retries
    transient_attempts = 0
    while True:
        try:
            return provider.generate_action(scenario, control_condition, seed, temperature), None
        except ProviderOutputError as exc:
            last_error = exc
            if output_retries_left <= 0:
                break
            output_retries_left -= 1
        except ProviderError as exc:
            last_error = exc
            if transient_retries_left <= 0 or not is_retryable_provider_error(exc):
                break
            transient_retries_left -= 1
            sleep(backoff_delay(transient_attempts))
            transient_attempts += 1
    assert last_error is not None
    return _error_provider_action(provider.provider_id, last_error), str(last_error)


def run_phase1_evaluation(
    model_ids: Optional[Iterable[str]] = None,
    control_conditions: Optional[Iterable[ControlCondition]] = None,
    scenario_ids: Optional[Iterable[str]] = None,
    scenario_set_path: Optional[Path] = None,
    seeds: Optional[Iterable[int]] = None,
    temperature: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    live: bool = False,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    provider_factory: Optional[Callable[[str, bool], BaseProvider]] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    consecutive_error_limit: int = DEFAULT_CONSECUTIVE_ERROR_LIMIT,
) -> BenchmarkRun:
    selected_model_ids = resolve_model_ids(model_ids)
    selected_conditions = _select_control_conditions(control_conditions)
    selected_scenarios = _select_scenarios(scenario_ids, scenario_set_path)
    selected_seeds = _select_seeds(seeds)
    resolved_temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    if provider_factory is not None:
        factory: Callable[[str, bool], BaseProvider] = provider_factory
    else:
        # A user-supplied key/model only makes sense for a single provider, so
        # apply it across the selected provider(s) without persisting it.
        def factory(model_id: str, is_live: bool) -> BaseProvider:
            return create_provider(model_id, is_live, api_key=api_key, model_name=model_name)
    providers = {model_id: factory(model_id, live) for model_id in selected_model_ids}
    # Reasoning effort only applies to providers that expose it (OpenAI reasoning
    # models). Setting it post-construction keeps custom provider factories working.
    if reasoning_effort:
        for provider in providers.values():
            if hasattr(provider, "reasoning_effort"):
                provider.reasoning_effort = reasoning_effort
    # Validate every provider up front so an unusable one (e.g. a wrong or
    # unavailable model id) aborts the run before it spends real API calls on
    # the scenario grid, instead of failing once per (scenario, condition, seed).
    for provider in providers.values():
        provider.preflight()
    results: List[EvaluationResult] = []
    events = []
    run_id = f"run_{uuid4().hex[:12]}"

    # Total (model, condition, scenario, seed) combinations, so callers can drive
    # a determinate progress bar over the grid the nested loops below walk.
    total_units = (
        len(selected_model_ids)
        * len(selected_conditions)
        * len(selected_scenarios)
        * len(selected_seeds)
    )
    completed_units = 0
    consecutive_errors = 0

    for model_id in selected_model_ids:
        provider = providers[model_id]
        for control_condition in selected_conditions:
            for scenario in selected_scenarios:
                for seed in selected_seeds:
                    if progress_cb is not None:
                        progress_cb(
                            completed_units,
                            total_units,
                            f"{model_id} / {control_condition} / {scenario.scenario_id} / seed {seed}",
                        )
                    provider_action, error = _generate_with_retry(
                        provider,
                        scenario,
                        control_condition,
                        seed,
                        resolved_temperature,
                    )
                    if error:
                        consecutive_errors += 1
                        if consecutive_errors >= consecutive_error_limit:
                            raise RunAbortedError(
                                f"{consecutive_errors} provider calls in a row failed after "
                                f"retries — stopping at {completed_units + 1}/{total_units} "
                                f"cells instead of filling the rest of the grid with errors. "
                                f"Last failure ({model_id} / {control_condition} / "
                                f"{scenario.scenario_id} / seed {seed}): {error}",
                                completed_units=completed_units,
                                total_units=total_units,
                                consecutive_errors=consecutive_errors,
                                last_error=error,
                            )
                    else:
                        consecutive_errors = 0
                    effective_action, block_reasons = apply_tool_constraints(
                        scenario,
                        provider_action.action,
                        control_condition,
                    )
                    result = evaluate_phase1_action(
                        scenario=scenario,
                        model_id=model_id,
                        model_name=provider.model_name,
                        provider_id=provider.provider_id,
                        control_condition=control_condition,
                        seed=seed,
                        action=effective_action,
                        proposed_action=provider_action.action,
                        raw_model_output=provider_action.raw_output,
                        block_reasons=block_reasons,
                        error=error,
                    )
                    results.append(result)
                    for index, event in enumerate(result.audit_events):
                        events.append(
                            {
                                "event_id": (
                                    f"{run_id}_{model_id}_{control_condition}_"
                                    f"{scenario.scenario_id}_{seed}_{index}"
                                ),
                                "run_id": run_id,
                                "scenario_id": scenario.scenario_id,
                                "model_id": model_id,
                                "control_condition": control_condition,
                                "seed": seed,
                                **event,
                            }
                        )
                    completed_units += 1

    if progress_cb is not None:
        progress_cb(completed_units, total_units, "complete")

    return BenchmarkRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        agent_ids=[f"{model_id}:{condition}" for model_id in selected_model_ids for condition in selected_conditions],
        model_ids=selected_model_ids,
        model_names=distinct_model_names(results),
        control_conditions=selected_conditions,
        seeds=selected_seeds,
        temperature=resolved_temperature,
        reasoning_effort=reasoning_effort,
        live=live,
        answer_key_status=_run_answer_key_status(selected_scenarios),
        scenario_ids=[scenario.scenario_id for scenario in selected_scenarios],
        results=results,
        events=events,
        metrics=compute_metrics(results),
    )


def run_benchmark(
    agent_ids: Optional[Iterable[str]] = None,
    model_ids: Optional[Iterable[str]] = None,
    control_conditions: Optional[Iterable[ControlCondition]] = None,
    scenario_ids: Optional[Iterable[str]] = None,
    scenario_set_path: Optional[Path] = None,
    seeds: Optional[Iterable[int]] = None,
    temperature: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    live: bool = False,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> BenchmarkRun:
    if (
        model_ids is not None
        or control_conditions is not None
        or seeds is not None
        or reasoning_effort is not None
        or live
    ):
        return run_phase1_evaluation(
            model_ids=model_ids,
            control_conditions=control_conditions,
            scenario_ids=scenario_ids,
            scenario_set_path=scenario_set_path,
            seeds=seeds,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            live=live,
            api_key=api_key,
            model_name=model_name,
            progress_cb=progress_cb,
        )

    selected_agents = _select_agents(agent_ids)
    selected_scenarios = _select_scenarios(scenario_ids, scenario_set_path)
    results: List[EvaluationResult] = []
    events = []
    run_id = f"run_{uuid4().hex[:12]}"

    for scenario in selected_scenarios:
        for agent_id in selected_agents:
            profile = AGENT_PROFILES[agent_id]
            action = get_agent_action(agent_id, scenario)
            result = evaluate_action(scenario, agent_id, profile["name"], action)
            results.append(result)
            for index, event in enumerate(result.audit_events):
                events.append(
                    {
                        "event_id": f"{run_id}_{scenario.scenario_id}_{agent_id}_{index}",
                        "run_id": run_id,
                        "scenario_id": scenario.scenario_id,
                        "agent_id": agent_id,
                        **event,
                    }
                )

    return BenchmarkRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        agent_ids=selected_agents,
        model_names=distinct_model_names(results),
        answer_key_status=_run_answer_key_status(selected_scenarios),
        scenario_ids=[scenario.scenario_id for scenario in selected_scenarios],
        results=results,
        events=events,
        metrics=compute_metrics(results),
    )
