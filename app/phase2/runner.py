"""Phase 2 runner: model x condition x framing x urgency x user_availability x scenario x seed."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

from ..data import DATA_DIR, load_scenarios
from ..metrics import _summarize_group, compute_metrics, distinct_model_names
from ..models import BenchmarkRun, EvaluationResult, Scenario
from ..policies import evaluate_phase1_action
from ..runner import _run_answer_key_status
from .providers import BaseEpisodeProvider, create_phase2_provider, resolve_phase2_model_ids
from .sandbox import (
    USER_AVAILABILITY_LEVELS,
    FRAMINGS,
    PHASE2_CONTROL_CONDITIONS,
    URGENCY_LEVELS,
    SandboxWorld,
    assemble_action,
    build_system_prompt,
    build_user_prompt,
)


PHASE2_SCENARIO_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
DEFAULT_PHASE2_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_PHASE2_TEMPERATURE = 0.7


def _select(values: Optional[Iterable[str]], allowed: List[str], label: str) -> List[str]:
    selected = list(values or allowed)
    if "all" in selected:
        return list(allowed)
    missing = set(selected) - set(allowed)
    if missing:
        raise KeyError(f"Unknown {label}: {', '.join(sorted(missing))}")
    return selected


def _select_scenarios(scenario_ids, scenario_set_path) -> List[Scenario]:
    scenarios = load_scenarios(scenario_set_path or PHASE2_SCENARIO_SET)
    if not scenario_ids:
        return scenarios
    wanted = set(scenario_ids)
    selected = [scenario for scenario in scenarios if scenario.scenario_id in wanted]
    missing = wanted - {scenario.scenario_id for scenario in selected}
    if missing:
        raise KeyError(f"Unknown scenarios: {', '.join(sorted(missing))}")
    return selected


def run_phase2_episode(
    provider: BaseEpisodeProvider,
    scenario: Scenario,
    control_condition: str,
    framing: str,
    seed: int,
    temperature: float,
    model_id: str,
    urgency: str = "none",
    user_availability: str = "none",
) -> EvaluationResult:
    world = SandboxWorld(scenario, control_condition)
    system_prompt = build_system_prompt(
        scenario, control_condition, framing, urgency, user_availability
    )
    user_prompt = build_user_prompt(scenario, seed)
    episode = provider.run_episode(world, system_prompt, user_prompt, seed, temperature)
    effective, proposed, block_reasons = assemble_action(world, error=episode.error)
    result = evaluate_phase1_action(
        scenario=scenario,
        model_id=model_id,
        model_name=provider.model_name,
        provider_id=provider.provider_id,
        control_condition=control_condition,  # type: ignore[arg-type]
        seed=seed,
        action=effective,
        proposed_action=proposed or effective,
        raw_model_output="\n".join(episode.raw_outputs) or None,
        block_reasons=block_reasons,
        error=episode.error,
    )
    result.framing = framing  # type: ignore[assignment]
    result.urgency = urgency  # type: ignore[assignment]
    result.user_availability = user_availability  # type: ignore[assignment]
    # Full tool transcript goes into the audit trail (audit-failure metric).
    result.audit_events.extend(
        {
            "event_type": "tool_call",
            "code": step["tool"],
            "detail": {
                "args": step["args"],
                "result": step["result"],
                "framing": framing,
                "urgency": urgency,
                "user_availability": user_availability,
            },
        }
        for step in world.transcript
    )
    return result


def run_phase2_evaluation(
    model_ids: Optional[Iterable[str]] = None,
    control_conditions: Optional[Iterable[str]] = None,
    framings: Optional[Iterable[str]] = None,
    urgencies: Optional[Iterable[str]] = None,
    user_availabilities: Optional[Iterable[str]] = None,
    scenario_ids: Optional[Iterable[str]] = None,
    scenario_set_path: Optional[Path] = None,
    seeds: Optional[Iterable[int]] = None,
    temperature: Optional[float] = None,
    reasoning_effort: Optional[str] = None,
    live: bool = False,
    provider_factory: Optional[Callable[[str, bool], BaseEpisodeProvider]] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> BenchmarkRun:
    selected_models = resolve_phase2_model_ids(model_ids)
    selected_conditions = _select(control_conditions, PHASE2_CONTROL_CONDITIONS, "Phase 2 control conditions")
    selected_framings = _select(framings, FRAMINGS, "framings")
    # Unlike framings/conditions, omitting these does NOT expand to every level.
    # Both pressure axes are opt-in: each one doubles the grid and the two
    # together quadruple it, and every existing caller (including the
    # scripted-agent test suite) calls this without them. Defaulting to "all"
    # would silently multiply their episode counts and API cost. Pass
    # urgencies=["all"] / user_availabilities=["all"] (or the levels explicitly) to
    # run the ablation. Keep this shape — it is the cost guard.
    selected_urgencies = _select(urgencies, URGENCY_LEVELS, "urgency levels") if urgencies else ["none"]
    selected_user_availabilities = (
        _select(user_availabilities, USER_AVAILABILITY_LEVELS, "user-availability levels")
        if user_availabilities
        else ["none"]
    )
    selected_scenarios = _select_scenarios(scenario_ids, scenario_set_path)
    selected_seeds = list(seeds or DEFAULT_PHASE2_SEEDS)
    resolved_temperature = DEFAULT_PHASE2_TEMPERATURE if temperature is None else temperature

    factory = provider_factory or (lambda model_id, is_live: create_phase2_provider(model_id, is_live))
    providers = {model_id: factory(model_id, live) for model_id in selected_models}
    if reasoning_effort:
        for provider in providers.values():
            if hasattr(provider, "reasoning_effort"):
                provider.reasoning_effort = reasoning_effort
    # Validate every provider up front so a misconfigured one (missing key,
    # wrong model id) aborts before the episode grid runs, instead of being
    # swallowed per-episode by the tool loop and saved as an all-error run.
    for provider in providers.values():
        provider.preflight()

    results: List[EvaluationResult] = []
    events: List[Dict[str, Any]] = []
    run_id = f"run_{uuid4().hex[:12]}"

    # Total (model, condition, framing, urgency, user_availability, scenario, seed)
    # episodes, so callers can drive a determinate progress bar over the grid below.
    total_units = (
        len(selected_models)
        * len(selected_conditions)
        * len(selected_framings)
        * len(selected_urgencies)
        * len(selected_user_availabilities)
        * len(selected_scenarios)
        * len(selected_seeds)
    )
    completed_units = 0

    for model_id in selected_models:
        provider = providers[model_id]
        for condition in selected_conditions:
            for framing in selected_framings:
                for urgency in selected_urgencies:
                    for user_availability in selected_user_availabilities:
                        for scenario in selected_scenarios:
                            for seed in selected_seeds:
                                if progress_cb is not None:
                                    progress_cb(
                                        completed_units,
                                        total_units,
                                        f"{model_id} / {condition} / {framing} / {urgency} / "
                                        f"{user_availability} / {scenario.scenario_id} / seed {seed}",
                                    )
                                result = run_phase2_episode(
                                    provider, scenario, condition, framing, seed,
                                    resolved_temperature, model_id, urgency, user_availability,
                                )
                                results.append(result)
                                for index, event in enumerate(result.audit_events):
                                    events.append(
                                        {
                                            "event_id": (
                                                f"{run_id}_{model_id}_{condition}_{framing}_"
                                                f"{urgency}_{user_availability}_"
                                                f"{scenario.scenario_id}_{seed}_{index}"
                                            ),
                                            "run_id": run_id,
                                            "scenario_id": scenario.scenario_id,
                                            "model_id": model_id,
                                            "control_condition": condition,
                                            "framing": framing,
                                            "urgency": urgency,
                                            "user_availability": user_availability,
                                            "seed": seed,
                                            **event,
                                        }
                                    )
                                completed_units += 1

    if progress_cb is not None:
        progress_cb(completed_units, total_units, "complete")

    metrics = compute_metrics(results)
    metrics["phase2"] = {
        "by_framing": {
            framing: _summarize_group([result for result in results if result.framing == framing])
            for framing in selected_framings
        },
        "by_condition_and_framing": {
            f"{condition}/{framing}": _summarize_group(
                [
                    result
                    for result in results
                    if result.control_condition == condition and result.framing == framing
                ]
            )
            for condition in selected_conditions
            for framing in selected_framings
        },
        "by_urgency": {
            urgency: _summarize_group([result for result in results if result.urgency == urgency])
            for urgency in selected_urgencies
        },
        "by_condition_and_urgency": {
            f"{condition}/{urgency}": _summarize_group(
                [
                    result
                    for result in results
                    if result.control_condition == condition and result.urgency == urgency
                ]
            )
            for condition in selected_conditions
            for urgency in selected_urgencies
        },
        "by_user_availability": {
            user_availability: _summarize_group(
                [result for result in results if result.user_availability == user_availability]
            )
            for user_availability in selected_user_availabilities
        },
        "by_condition_and_user_availability": {
            f"{condition}/{user_availability}": _summarize_group(
                [
                    result
                    for result in results
                    if result.control_condition == condition
                    and result.user_availability == user_availability
                ]
            )
            for condition in selected_conditions
            for user_availability in selected_user_availabilities
        },
        # The 2x2 the split exists for: separates "judgment degraded under a
        # deadline" from "behaviour changed when nobody was watching", and shows
        # whether the two interact rather than merely adding up.
        "by_urgency_and_user_availability": {
            f"{urgency}/{user_availability}": _summarize_group(
                [
                    result
                    for result in results
                    if result.urgency == urgency and result.user_availability == user_availability
                ]
            )
            for urgency in selected_urgencies
            for user_availability in selected_user_availabilities
        },
    }

    return BenchmarkRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        phase="phase2",
        agent_ids=[
            f"{model_id}:{condition}" for model_id in selected_models for condition in selected_conditions
        ],
        model_ids=selected_models,
        model_names=distinct_model_names(results),
        control_conditions=selected_conditions,  # type: ignore[arg-type]
        framings=selected_framings,  # type: ignore[arg-type]
        urgencies=selected_urgencies,  # type: ignore[arg-type]
        user_availabilities=selected_user_availabilities,  # type: ignore[arg-type]
        seeds=selected_seeds,
        temperature=resolved_temperature,
        reasoning_effort=reasoning_effort,
        live=live,
        # Derived from the scenarios actually run, not hardcoded: a Phase 2 run
        # over a locked set must not be stamped provisional by construction.
        # Reuses the Phase 1 rule (app/runner.py).
        answer_key_status=_run_answer_key_status(selected_scenarios),  # type: ignore[arg-type]
        scenario_ids=[scenario.scenario_id for scenario in selected_scenarios],
        results=results,
        events=events,
        metrics=metrics,
    )
