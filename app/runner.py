from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional
from uuid import uuid4

from .agents import AGENT_IDS, AGENT_PROFILES, get_agent_action
from .data import load_scenarios
from .metrics import compute_metrics
from .models import BenchmarkRun, ControlCondition, EvaluationResult, Scenario
from .policies import apply_tool_constraints, evaluate_action, evaluate_phase1_action
from .providers import (
    BaseProvider,
    ProviderAction,
    ProviderError,
    ProviderOutputError,
    create_provider,
    resolve_model_ids,
)


DEFAULT_CONTROL_CONDITIONS: List[ControlCondition] = [
    "no_policy",
    "prompt_policy",
    "tool_constraints",
]
DEFAULT_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_TEMPERATURE = 0.7


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
    if scenarios and all(scenario.answer_key_status == "locked" for scenario in scenarios):
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
) -> tuple[ProviderAction, Optional[str]]:
    last_error: Optional[Exception] = None
    for _ in range(retries + 1):
        try:
            return provider.generate_action(scenario, control_condition, seed, temperature), None
        except ProviderOutputError as exc:
            last_error = exc
            continue
        except ProviderError as exc:
            last_error = exc
            break
    assert last_error is not None
    return _error_provider_action(provider.provider_id, last_error), str(last_error)


def run_phase1_evaluation(
    model_ids: Optional[Iterable[str]] = None,
    control_conditions: Optional[Iterable[ControlCondition]] = None,
    scenario_ids: Optional[Iterable[str]] = None,
    scenario_set_path: Optional[Path] = None,
    seeds: Optional[Iterable[int]] = None,
    temperature: Optional[float] = None,
    live: bool = False,
    provider_factory: Optional[Callable[[str, bool], BaseProvider]] = None,
) -> BenchmarkRun:
    selected_model_ids = resolve_model_ids(model_ids)
    selected_conditions = _select_control_conditions(control_conditions)
    selected_scenarios = _select_scenarios(scenario_ids, scenario_set_path)
    selected_seeds = _select_seeds(seeds)
    resolved_temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    factory = provider_factory or create_provider
    providers = {model_id: factory(model_id, live) for model_id in selected_model_ids}
    results: List[EvaluationResult] = []
    events = []
    run_id = f"run_{uuid4().hex[:12]}"

    for model_id in selected_model_ids:
        provider = providers[model_id]
        for control_condition in selected_conditions:
            for scenario in selected_scenarios:
                for seed in selected_seeds:
                    provider_action, error = _generate_with_retry(
                        provider,
                        scenario,
                        control_condition,
                        seed,
                        resolved_temperature,
                    )
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

    return BenchmarkRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        agent_ids=[f"{model_id}:{condition}" for model_id in selected_model_ids for condition in selected_conditions],
        model_ids=selected_model_ids,
        control_conditions=selected_conditions,
        seeds=selected_seeds,
        temperature=resolved_temperature,
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
    live: bool = False,
) -> BenchmarkRun:
    if model_ids is not None or control_conditions is not None or seeds is not None or live:
        return run_phase1_evaluation(
            model_ids=model_ids,
            control_conditions=control_conditions,
            scenario_ids=scenario_ids,
            scenario_set_path=scenario_set_path,
            seeds=seeds,
            temperature=temperature,
            live=live,
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
        answer_key_status=_run_answer_key_status(selected_scenarios),
        scenario_ids=[scenario.scenario_id for scenario in selected_scenarios],
        results=results,
        events=events,
        metrics=compute_metrics(results),
    )
