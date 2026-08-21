"""Phase 2 runner: model x condition x framing x urgency x user_availability x scenario x seed."""

from __future__ import annotations

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional
from uuid import uuid4

from ..data import DATA_DIR, load_scenarios
from ..metrics import (
    _summarize_group,
    compute_metrics,
    distinct_model_names,
    phase2_paired_contrasts,
)
from ..models import BenchmarkRun, EvaluationResult, Scenario
from ..policies import evaluate_phase1_action
from ..providers import DEFAULT_CONSECUTIVE_ERROR_LIMIT, RateLimitGate, RunAbortedError
from ..runner import _run_answer_key_status
from .checkpoint import CheckpointStore, EpisodeKey, episode_key, grid_fingerprint
from .providers import BaseEpisodeProvider, create_phase2_provider, resolve_phase2_model_ids
from .sandbox import (
    FRAMINGS,
    PHASE2_CONTROL_CONDITIONS,
    URGENCY_LEVELS,
    USER_AVAILABILITY_LEVELS,
    SandboxWorld,
    assemble_action,
    build_system_prompt,
    build_user_prompt,
    completed_payment_actions,
)


PHASE2_SCENARIO_SET = DATA_DIR / "scenario_sets" / "v2_250_scenarios.md"
# A bare `phase2-eval` (no --seeds) now costs one seed, not five (2026-08-11;
# previously [1, 2, 3, 4, 5]) -- the same "opt into the expensive axis on
# purpose" reasoning as selected_framings/selected_urgencies below. Pass
# --seeds 1,2,3,4,5 explicitly for the full five-seed design.
DEFAULT_PHASE2_SEEDS = [1]
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


@dataclass(frozen=True)
class GridCell:
    """One episode's coordinates in the (model x condition x framing x urgency
    x user_availability x scenario x seed) grid."""

    model_id: str
    control_condition: str
    framing: str
    urgency: str
    user_availability: str
    scenario: Scenario
    seed: int

    @property
    def key(self) -> EpisodeKey:
        return episode_key(
            self.model_id,
            self.control_condition,
            self.framing,
            self.urgency,
            self.user_availability,
            self.scenario.scenario_id,
            self.seed,
        )

    @property
    def label(self) -> str:
        return (
            f"{self.model_id} / {self.control_condition} / {self.framing} / "
            f"{self.urgency} / {self.user_availability} / "
            f"{self.scenario.scenario_id} / seed {self.seed}"
        )


def _grid_cells(
    models: List[str],
    conditions: List[str],
    framings: List[str],
    urgencies: List[str],
    user_availabilities: List[str],
    scenarios: List[Scenario],
    seeds: List[int],
) -> Iterator[GridCell]:
    """The grid, flattened in its canonical order.

    Same nesting the loops used to walk, kept as the one definition of episode
    order: resume skips against it, the thread pool submits against it, and
    results are sorted back into it before metrics — so a serial run, a
    resumed run and an N-worker run all produce the same BenchmarkRun.
    """
    for model_id in models:
        for condition in conditions:
            for framing in framings:
                for urgency in urgencies:
                    for user_availability in user_availabilities:
                        for scenario in scenarios:
                            for seed in seeds:
                                yield GridCell(
                                    model_id, condition, framing, urgency,
                                    user_availability, scenario, seed,
                                )


def _episode_events(run_id: str, cell: GridCell, result: EvaluationResult) -> List[Dict[str, Any]]:
    """Audit events for one episode, keyed by its grid coordinates.

    Shared by freshly-run and checkpoint-restored results so the two paths
    cannot drift — the checkpoint stores only the result and these are rebuilt.
    """
    return [
        {
            "event_id": (
                f"{run_id}_{cell.model_id}_{cell.control_condition}_{cell.framing}_"
                f"{cell.urgency}_{cell.user_availability}_{cell.scenario.scenario_id}_"
                f"{cell.seed}_{index}"
            ),
            "run_id": run_id,
            "scenario_id": cell.scenario.scenario_id,
            "model_id": cell.model_id,
            "control_condition": cell.control_condition,
            "framing": cell.framing,
            "urgency": cell.urgency,
            "user_availability": cell.user_availability,
            "seed": cell.seed,
            **event,
        }
        for index, event in enumerate(result.audit_events)
    ]


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
    user_prompt = build_user_prompt(scenario)
    episode = provider.run_episode(world, system_prompt, user_prompt, seed, temperature)
    blocked_without_terminal_action = bool(world.blocked_attempts) and not (
        world.completed_payments
        or world.approval_request is not None
        or world.finish_call is not None
    )
    error = episode.error
    if error and (world.completed_payments or world.blocked_attempts or world.sent_messages):
        # The "error" verdict exists for episodes where nothing happened, and
        # metrics exclude it from every denominator. A completed or blocked
        # payment, or an outbound delivery, is an observed model action even if
        # the episode later dies. Grade it so realized harm cannot disappear
        # behind a provider error.
        error = None
    effective, proposed, block_reasons = assemble_action(world, error=error)
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
        raw_reasoning="\n\n".join(episode.reasoning_outputs) or None,
        block_reasons=block_reasons,
        error=error,
        completed_payment_actions=completed_payment_actions(world) or None,
        blocked_without_terminal_action=blocked_without_terminal_action,
    )
    result.framing = framing  # type: ignore[assignment]
    result.urgency = urgency  # type: ignore[assignment]
    result.user_availability = user_availability  # type: ignore[assignment]
    # Outbound deliveries stay as first-class episode events even if a later
    # payment becomes the effective action.
    result.audit_events.extend(
        {
            "event_type": "outbound_message",
            "code": "delivered",
            "detail": dict(message),
        }
        for message in world.sent_messages
    )
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


def phase2_metrics_block(
    results: List[EvaluationResult],
    conditions: List[str],
    framings: List[str],
    urgencies: List[str],
    user_availabilities: List[str],
) -> Dict[str, Any]:
    """The ``metrics["phase2"]`` breakdowns, from results and the run's axes.

    Factored out of run_phase2_evaluation so the ``recompute`` CLI command can
    rebuild a stored Phase 2 run's metrics under the current definitions
    without re-running episodes — the axis lists come from the stored run's
    own ``framings``/``urgencies``/``user_availabilities`` fields.
    """
    return {
        "episode_descriptives": {
            "unit": "episode",
            "confidence_interval": "Wilson score, 95%",
        },
        "paired_contrasts": phase2_paired_contrasts(results),
        "by_framing": {
            framing: _summarize_group([result for result in results if result.framing == framing])
            for framing in framings
        },
        "by_condition_and_framing": {
            f"{condition}/{framing}": _summarize_group(
                [
                    result
                    for result in results
                    if result.control_condition == condition and result.framing == framing
                ]
            )
            for condition in conditions
            for framing in framings
        },
        "by_urgency": {
            urgency: _summarize_group([result for result in results if result.urgency == urgency])
            for urgency in urgencies
        },
        "by_condition_and_urgency": {
            f"{condition}/{urgency}": _summarize_group(
                [
                    result
                    for result in results
                    if result.control_condition == condition and result.urgency == urgency
                ]
            )
            for condition in conditions
            for urgency in urgencies
        },
        "by_user_availability": {
            user_availability: _summarize_group(
                [result for result in results if result.user_availability == user_availability]
            )
            for user_availability in user_availabilities
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
            for condition in conditions
            for user_availability in user_availabilities
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
            for urgency in urgencies
            for user_availability in user_availabilities
        },
    }


class _ProviderPool:
    """One provider instance per worker, leased for the length of an episode.

    Live providers carry per-episode conversation state on the instance
    (``_messages``, ``_previous_response_id``, ``_last_assistant_content``), so
    the single shared instance the serial loop reuses cannot be driven by two
    threads at once. At concurrency 1 this is that same single instance.
    """

    def __init__(self, model_ids: List[str], factory: Callable[[str, bool], Any], live: bool, size: int):
        self._instances: Dict[str, List[Any]] = {
            model_id: [factory(model_id, live) for _ in range(size)] for model_id in model_ids
        }
        self._available: Dict[str, queue.Queue] = {}
        for model_id, instances in self._instances.items():
            available: queue.Queue = queue.Queue()
            for instance in instances:
                available.put(instance)
            self._available[model_id] = available

    def all_instances(self) -> Iterator[Any]:
        for instances in self._instances.values():
            yield from instances

    def representative(self, model_id: str) -> Any:
        return self._instances[model_id][0]

    def lease(self, model_id: str) -> Any:
        return self._available[model_id].get()

    def release(self, model_id: str, instance: Any) -> None:
        self._available[model_id].put(instance)


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
    run_id: Optional[str] = None,
    checkpoint: bool = True,
    resume: bool = False,
    concurrency: int = 1,
    consecutive_error_limit: int = DEFAULT_CONSECUTIVE_ERROR_LIMIT,
    checkpoint_root: Optional[Path] = None,
    on_resume: Optional[Callable[[int, int], None]] = None,
) -> BenchmarkRun:
    selected_models = resolve_phase2_model_ids(model_ids)
    # Omitting --conditions does NOT expand to every level: the policy
    # conditions (structured_policy/tool_constraints) are opt-in ablations,
    # same reasoning as the pressure axes below. Bare no_policy is the only
    # condition that runs with zero flags passed. Pass
    # control_conditions=["all"] (or the levels explicitly) to add the rest.
    selected_conditions = (
        _select(control_conditions, PHASE2_CONTROL_CONDITIONS, "Phase 2 control conditions")
        if control_conditions
        else ["no_policy"]
    )
    # The framing axis has a single level since the "evaluation" framing was
    # cut on 2026-08-17 (see FRAMING_PREAMBLES in sandbox.py) — it told the
    # tested agent it was being evaluated. The axis itself stays: stored runs
    # group by framing, and _select still rejects unknown values, so
    # framings=["evaluation"] now fails as unknown instead of running.
    selected_framings = _select(framings, FRAMINGS, "framings") if framings else ["deployment"]
    # Omitting these does NOT expand to every level either, same as conditions
    # and framings above. Both pressure axes are opt-in: each one doubles the
    # grid and the two together quadruple it, and every existing caller
    # (including the scripted-agent test suite) calls this without them.
    # Defaulting to "all" would silently multiply their episode counts and API
    # cost. Pass urgencies=["all"] / user_availabilities=["all"] (or the levels
    # explicitly) to run the ablation. Keep this shape — it is the cost guard.
    selected_urgencies = _select(urgencies, URGENCY_LEVELS, "urgency levels") if urgencies else ["none"]
    selected_user_availabilities = (
        _select(user_availabilities, USER_AVAILABILITY_LEVELS, "user-availability levels")
        if user_availabilities
        else ["none"]
    )
    selected_scenarios = _select_scenarios(scenario_ids, scenario_set_path)
    selected_seeds = list(seeds or DEFAULT_PHASE2_SEEDS)
    resolved_temperature = DEFAULT_PHASE2_TEMPERATURE if temperature is None else temperature
    workers = max(1, int(concurrency))

    factory = provider_factory or (lambda model_id, is_live: create_phase2_provider(model_id, is_live))
    pool = _ProviderPool(selected_models, factory, live, workers)
    if reasoning_effort:
        for provider in pool.all_instances():
            if hasattr(provider, "reasoning_effort"):
                provider.reasoning_effort = reasoning_effort
    # One gate per run: a 429 on any worker pauses every worker's next attempt
    # until the window passes, instead of N workers hammering in lockstep.
    rate_limit_gate = RateLimitGate()
    for provider in pool.all_instances():
        if hasattr(provider, "rate_limit_gate"):
            provider.rate_limit_gate = rate_limit_gate
    # Validate every provider up front so a misconfigured one (missing key,
    # wrong model id) aborts before the episode grid runs, instead of being
    # swallowed per-episode by the tool loop and saved as an all-error run.
    # One instance per model is enough — the pool's instances are identical.
    for model_id in selected_models:
        pool.representative(model_id).preflight()

    run_id = run_id or f"run_{uuid4().hex[:12]}"
    cells = list(
        _grid_cells(
            selected_models,
            selected_conditions,
            selected_framings,
            selected_urgencies,
            selected_user_availabilities,
            selected_scenarios,
            selected_seeds,
        )
    )
    total_units = len(cells)
    fingerprint = grid_fingerprint(
        selected_models,
        selected_conditions,
        selected_framings,
        selected_urgencies,
        selected_user_availabilities,
        [scenario.scenario_id for scenario in selected_scenarios],
        selected_seeds,
    )

    results_by_key: Dict[EpisodeKey, EvaluationResult] = {}
    if resume:
        # The grid alone is not enough: resuming a live run with --dry-run
        # would splice fake episodes among the paid ones. The header records
        # how the run was made; a resume must match it.
        loaded = CheckpointStore(run_id, root=checkpoint_root).verify(
            fingerprint,
            settings={
                "live": live,
                "temperature": resolved_temperature,
                "reasoning_effort": reasoning_effort,
            },
        )
        # Errored episodes are re-run rather than restored: resuming after a
        # rate-limit cascade is the main reason to resume at all, and those
        # cells are exactly the ones the cascade poisoned.
        results_by_key = {key: result for key, result in loaded["restored"].items() if not result.error}
        if on_resume is not None:
            # Only after verify() has accepted the checkpoint, so a mismatched
            # grid reports the refusal instead of a restored-episode count it
            # is about to throw away.
            on_resume(len(results_by_key), len(loaded["restored"]) - len(results_by_key))

    pending = [cell for cell in cells if cell.key not in results_by_key]
    completed_units = len(results_by_key)

    store: Optional[CheckpointStore] = None
    if checkpoint:
        store = CheckpointStore(run_id, root=checkpoint_root).open(
            {
                "run_id": run_id,
                "live": live,
                "temperature": resolved_temperature,
                "reasoning_effort": reasoning_effort,
                "grid": fingerprint,
            }
        )

    lock = threading.Lock()
    state = {"completed": completed_units, "consecutive_errors": 0, "aborted": None}
    # Set on Ctrl-C and when the auto-stop trips. Queued episodes check it
    # before starting, so "stop" means "no new spending", not "after the wave".
    stop = threading.Event()

    def _record(cell: GridCell, result: EvaluationResult) -> None:
        """Bank one finished episode. Serialized — the only shared mutation."""
        with lock:
            results_by_key[cell.key] = result
            if store is not None:
                store.append(cell.key, result)
            state["completed"] += 1
            if result.error:
                state["consecutive_errors"] += 1
                if state["consecutive_errors"] >= consecutive_error_limit and state["aborted"] is None:
                    banked = (
                        f" Everything completed so far is checkpointed; resume with --resume {run_id}."
                        if store is not None
                        else ""
                    )
                    state["aborted"] = RunAbortedError(
                        f"{state['consecutive_errors']} episodes in a row failed after retries "
                        f"— stopping at {state['completed']}/{total_units} episodes instead of "
                        f"filling the rest of the grid with errors. Last failure "
                        f"({cell.label}): {result.error}.{banked}",
                        completed_units=state["completed"],
                        total_units=total_units,
                        consecutive_errors=state["consecutive_errors"],
                        last_error=result.error,
                    )
                    stop.set()
            else:
                state["consecutive_errors"] = 0

    def _execute(cell: GridCell) -> None:
        if stop.is_set():
            return  # stopped while queued: skip before any provider call
        provider = pool.lease(cell.model_id)
        try:
            result = run_phase2_episode(
                provider,
                cell.scenario,
                cell.control_condition,
                cell.framing,
                cell.seed,
                resolved_temperature,
                cell.model_id,
                cell.urgency,
                cell.user_availability,
            )
        finally:
            pool.release(cell.model_id, provider)
        _record(cell, result)

    try:
        if workers == 1:
            for cell in pending:
                if progress_cb is not None:
                    progress_cb(state["completed"], total_units, cell.label)
                _execute(cell)
                if state["aborted"] is not None:
                    raise state["aborted"]
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit in bounded waves rather than queueing the whole grid,
                # so an abort stops spending within a wave instead of after
                # 13,560 futures have already been handed to the pool.
                for start in range(0, len(pending), workers * 4):
                    if state["aborted"] is not None or stop.is_set():
                        break
                    wave = pending[start : start + workers * 4]
                    futures = [executor.submit(_execute, cell) for cell in wave]
                    try:
                        for future in futures:
                            future.result()
                            if progress_cb is not None:
                                with lock:
                                    completed_now = state["completed"]
                                progress_cb(completed_now, total_units, f"{completed_now}/{total_units} episodes")
                    except BaseException:
                        # Ctrl-C (or a crashed worker): stop the queue NOW.
                        # In-flight episodes finish and are checkpointed —
                        # a thread's provider call cannot be interrupted —
                        # but nothing queued may start a new paid call.
                        stop.set()
                        for future in futures:
                            future.cancel()
                        raise
            if state["aborted"] is not None:
                raise state["aborted"]
    finally:
        if store is not None:
            store.close()

    if progress_cb is not None:
        progress_cb(state["completed"], total_units, "complete")

    # Canonical grid order, not completion order, so parallel and resumed runs
    # serialize identically to a plain serial one.
    ordered = [cell for cell in cells if cell.key in results_by_key]
    results: List[EvaluationResult] = [results_by_key[cell.key] for cell in ordered]
    events: List[Dict[str, Any]] = []
    for cell in ordered:
        events.extend(_episode_events(run_id, cell, results_by_key[cell.key]))

    # Local import: app.phase2.survey imports this module (PHASE2_SCENARIO_SET),
    # so a module-level import here would close a cycle.
    from .survey import floor_for_phase2

    metrics = compute_metrics(results, floor_fn=floor_for_phase2)
    metrics["phase2"] = phase2_metrics_block(
        results,
        selected_conditions,
        selected_framings,
        selected_urgencies,
        selected_user_availabilities,
    )

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
