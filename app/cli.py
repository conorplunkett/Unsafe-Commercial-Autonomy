from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional, TextIO

from .models import ControlCondition
from .providers import ProviderError
from .runner import DEFAULT_CONTROL_CONDITIONS, DEFAULT_SEEDS, DEFAULT_TEMPERATURE, run_phase1_evaluation
from .storage import RunStorage


def _csv(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _csv_int(value: Optional[str]) -> Optional[List[int]]:
    items = _csv(value)
    return [int(item) for item in items] if items is not None else None


def _csv_conditions(value: Optional[str]) -> Optional[List[ControlCondition]]:
    items = _csv(value)
    return items if items is not None else None  # type: ignore[return-value]


class _ProgressBar:
    """Render a determinate, single-line progress bar for a CLI eval run.

    Driven by ``run_phase1_evaluation``'s ``progress_cb`` (completed, total,
    label). Only draws when the stream is a TTY so redirected/piped output and
    the test suite stay clean. Uses ``\\r`` to redraw in place and clears the
    line when the run finishes, leaving the summary table untouched.
    """

    def __init__(self, stream: Optional[TextIO] = None, width: int = 24) -> None:
        self._stream = stream if stream is not None else sys.stderr
        self._width = width
        self._active = bool(getattr(self._stream, "isatty", lambda: False)())

    def update(self, completed: int, total: int, label: str) -> None:
        if not self._active:
            return
        frac = completed / total if total else 1.0
        filled = int(round(self._width * frac))
        bar = "█" * filled + "░" * (self._width - filled)
        verb = "done" if completed >= total else "running"
        line = f"[{bar}] {int(frac * 100):3d}% ({completed}/{total}) {verb} {label}"
        cols = shutil.get_terminal_size((80, 20)).columns
        # Pad to the terminal width so a shorter label can't leave stale text
        # behind from the previous, longer line.
        self._stream.write("\r" + line[: cols - 1].ljust(cols - 1))
        self._stream.flush()

    def finish(self) -> None:
        if not self._active:
            return
        cols = shutil.get_terminal_size((80, 20)).columns
        self._stream.write("\r" + " " * (cols - 1) + "\r")
        self._stream.flush()


def _format_rate(summary: dict, key: str) -> str:
    ci = summary.get(f"{key}_ci", {})
    rate = summary.get(f"{key}_rate", 0.0)
    if ci:
        return f"{rate:.3f} [{ci.get('ci_low', 0.0):.3f}, {ci.get('ci_high', 0.0):.3f}]"
    return f"{rate:.3f}"


# How many per-result rows the detail table prints before collapsing into a
# pointer to the saved JSON, so a 250-scenario sweep doesn't flood the terminal
# while a handful of debug scenarios still print in full.
_DETAIL_ROW_CAP = 60

# Verdicts that mean the run did something other than the safe thing — these are
# the rows worth reading first when debugging.
_PROBLEM_VERDICTS = ("error", "unsafe", "false_refusal", "welfare_loss")


def _format_action(action: Optional[dict]) -> str:
    """One-line description of the action a model took, for the detail table."""
    if not action:
        return "-"
    parts = [str(action.get("action_type") or "?")]
    amount = action.get("amount")
    if amount is not None:
        parts.append(f"${amount:.2f}")
    payment_type = action.get("payment_type")
    if payment_type:
        parts.append(str(payment_type))
    if action.get("approval_requested"):
        parts.append("(approval req)")
    return " ".join(parts)


def _result_notes(result: dict) -> str:
    """Why a result landed where it did: error, failure codes, or a block."""
    if result.get("error"):
        return f"ERROR: {result['error']}"
    failures = result.get("failure_metrics") or []
    if failures:
        return ", ".join(failures)
    blocks = result.get("block_reasons") or []
    if blocks:
        return "blocked: " + ", ".join(blocks)
    return "-"


def _print_verdicts_and_failures(metrics: dict) -> None:
    verdict_counts = metrics.get("verdict_counts") or {}
    if verdict_counts:
        ordered = sorted(verdict_counts.items(), key=lambda item: (-item[1], item[0]))
        print("Verdicts:     " + "  ".join(f"{verdict}={count}" for verdict, count in ordered))
    failure_counts = metrics.get("failure_counts") or {}
    if failure_counts:
        ordered = sorted(failure_counts.items(), key=lambda item: (-item[1], item[0]))
        print("Failure types: " + "  ".join(f"{name}={count}" for name, count in ordered))
    else:
        print("Failure types: (none)")


def _print_result_details(results: List[dict]) -> None:
    if not results:
        return
    # Surface problem verdicts first, then by scenario/seed, so the rows you most
    # want when debugging are at the top regardless of grid iteration order.
    def sort_key(result: dict):
        verdict = result.get("verdict", "")
        problem_rank = _PROBLEM_VERDICTS.index(verdict) if verdict in _PROBLEM_VERDICTS else len(_PROBLEM_VERDICTS)
        return (problem_rank, result.get("scenario_id", ""), result.get("seed") or 0)

    ordered = sorted(results, key=sort_key)
    print("")
    print("Per-result detail (problems first):")
    header = f"{'Scenario':26} {'Condition':16} {'Sd':>2} {'Verdict':13} {'Action':32} Notes"
    print(header)
    print("-" * max(len(header), 96))
    for result in ordered[:_DETAIL_ROW_CAP]:
        print(
            f"{(result.get('scenario_id') or '-')[:26]:26} "
            f"{(result.get('control_condition') or '-')[:16]:16} "
            f"{(str(result.get('seed')) if result.get('seed') is not None else '-'):>2} "
            f"{(result.get('verdict') or '-')[:13]:13} "
            f"{_format_action(result.get('action'))[:32]:32} "
            f"{_result_notes(result)}"
        )
    if len(ordered) > _DETAIL_ROW_CAP:
        print(f"... {len(ordered) - _DETAIL_ROW_CAP} more (see the saved run JSON).")

    # Rationales are the most useful debugging signal for non-safe verdicts, so
    # print them in full(ish) instead of cramming them into the table.
    problems = [result for result in ordered if result.get("verdict") in _PROBLEM_VERDICTS]
    if problems:
        print("")
        print("Rationales for non-safe verdicts:")
        for result in problems[:_DETAIL_ROW_CAP]:
            scenario = result.get("scenario_id") or "-"
            seed = result.get("seed")
            rationale = (result.get("action") or {}).get("rationale") or "(none)"
            rationale = " ".join(rationale.split())
            print(f"  [{result.get('verdict')}] {scenario} seed={seed}: {rationale[:300]}")


def _print_summary(run_payload: dict) -> None:
    metrics = run_payload["metrics"]
    print(f"Run saved: runtime/runs/{run_payload['run_id']}.json")
    print(f"Results: {metrics['total_results']}")
    if metrics.get("error_count"):
        print(f"Errors: {metrics['error_count']}")
    print("")
    _print_verdicts_and_failures(metrics)
    print("")
    print("Model/control                         Results  Unsafe payment CI      False refusal CI")
    print("-" * 88)
    for agent_id, summary in sorted(metrics.get("by_agent", {}).items()):
        print(
            f"{agent_id[:36]:36} "
            f"{summary['total_results']:7}  "
            f"{_format_rate(summary, 'unsafe_payment'):22} "
            f"{_format_rate(summary, 'false_refusal')}"
        )
    _print_result_details(run_payload.get("results") or [])


def eval_command(args: argparse.Namespace) -> int:
    model_ids = _csv(args.models) or ["openai"]
    control_conditions = _csv_conditions(args.conditions) or DEFAULT_CONTROL_CONDITIONS
    scenario_ids = _csv(args.scenario_ids)
    seeds = _csv_int(args.seeds) or DEFAULT_SEEDS
    progress = _ProgressBar()
    try:
        run = run_phase1_evaluation(
            model_ids=model_ids,
            control_conditions=control_conditions,
            scenario_ids=scenario_ids,
            scenario_set_path=Path(args.scenario_set) if args.scenario_set else None,
            seeds=seeds,
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            live=not args.dry_run,
            progress_cb=progress.update,
        )
    except ProviderError as exc:
        # Pre-run validation failed (e.g. bad model id) — abort before saving a
        # junk run, with the actionable message instead of a traceback.
        print(f"Cannot start eval: {exc}")
        return 2
    finally:
        progress.finish()
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


def models_command(args: argparse.Namespace) -> int:
    from .providers import available_openai_models

    if args.provider != "openai":
        print(f"Model listing is only implemented for the openai provider (got {args.provider!r}).")
        return 2
    try:
        model_ids = available_openai_models()
    except ProviderError as exc:
        print(f"Could not list models: {exc}")
        return 1
    for model_id in model_ids:
        print(model_id)
    return 0


def survey_command(args: argparse.Namespace) -> int:
    from .data import load_scenarios
    from .survey import is_synthetic, survey_summary

    summary = survey_summary()
    scenarios = load_scenarios()
    if is_synthetic():
        print("WARNING: survey data is SYNTHETIC placeholder data, not real responses.\n")
    print("Scenario                          Modal answer      Agreement  Source      Key status")
    print("-" * 92)
    for scenario in scenarios:
        votes = summary.get(scenario.scenario_id)
        if votes:
            source = "survey"
            modal = votes["modal_answer"]
            agreement = f"{votes['modal_count']}/{votes['respondents']}"
        else:
            source = "team-keyed"
            modal = "-"
            agreement = "-"
        print(
            f"{scenario.scenario_id[:32]:32}  {modal:16}  {agreement:9}  {source:10}  {scenario.answer_key_status}"
        )
    locked = sum(1 for scenario in scenarios if scenario.answer_key_status == "locked")
    print(f"\nLocked: {locked}/{len(scenarios)} scenarios")
    return 0 if locked == len(scenarios) else 1


def test_command(args: argparse.Namespace) -> int:
    """Quick smoke test: 1 model, 1 condition, 2 scenarios, 2 seeds."""
    model_ids = _csv(args.models) or ["openai"]
    progress = _ProgressBar()
    try:
        run = run_phase1_evaluation(
            model_ids=model_ids,
            control_conditions=["no_policy"],
            scenario_ids=["scn_v1_a1_trap", "scn_v1_a1_lookalike"],
            seeds=[1, 2],
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            live=not args.dry_run,
            progress_cb=progress.update,
        )
    finally:
        progress.finish()
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


def smoketest_openai_command(args: argparse.Namespace) -> int:
    """Minimal OpenAI smoketest: 1 scenario, 1 seed, always gpt-5.4-mini."""
    from .providers import OpenAIResponsesProvider

    def _factory(model_id: str, live: bool):
        return OpenAIResponsesProvider(model_name="gpt-5.4-mini")

    progress = _ProgressBar()
    try:
        run = run_phase1_evaluation(
            model_ids=["openai"],
            control_conditions=["no_policy"],
            scenario_ids=["scn_v1_a1_trap"],
            seeds=[1],
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            live=True,
            provider_factory=_factory,
            progress_cb=progress.update,
        )
    finally:
        progress.finish()
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


def smoketest_openai_5_command(args: argparse.Namespace) -> int:
    """OpenAI smoketest across 5 scenarios, always gpt-5.4-mini."""
    from .providers import OpenAIResponsesProvider

    def _factory(model_id: str, live: bool):
        return OpenAIResponsesProvider(model_name="gpt-5.4-mini")

    progress = _ProgressBar()
    try:
        run = run_phase1_evaluation(
            model_ids=["openai"],
            control_conditions=["no_policy"],
            scenario_ids=[
                "scn_v1_a1_trap",
                "scn_v1_a2_lookalike",
                "scn_v1_b1_trap",
                "scn_v1_b2_lookalike",
                "scn_v1_a5_trap",
            ],
            seeds=[1],
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            live=True,
            provider_factory=_factory,
            progress_cb=progress.update,
        )
    finally:
        progress.finish()
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


# ---------------------------------------------------------------------------
# Phase 2 commands — sandbox benchmark, fully separate from the Phase 1 paths.
# All app.phase2 imports are lazy so Phase 1 commands never load Phase 2 code.
# ---------------------------------------------------------------------------


def phase2_eval_command(args: argparse.Namespace) -> int:
    """Phase 2 six-condition sandbox ablation with framing variation."""
    from .phase2 import run_phase2_evaluation

    if not args.dry_run:
        scenario_count = len(_csv(args.scenario_ids) or []) or 250
        conditions = len(_csv(args.conditions) or []) or 6
        framings = len(_csv(args.framings) or []) or 2
        seeds = len(_csv_int(args.seeds) or []) or 5
        models = len(_csv(args.models) or ["openai"])
        episodes = scenario_count * conditions * framings * seeds * models
        print(
            f"Live run: ~{episodes} multi-turn episodes "
            f"({scenario_count} scenarios x {conditions} conditions x {framings} framings "
            f"x {seeds} seeds x {models} models). Consider subsetting.\n"
        )
    progress = _ProgressBar()
    try:
        run = run_phase2_evaluation(
            model_ids=_csv(args.models),
            control_conditions=_csv(args.conditions),
            framings=_csv(args.framings),
            scenario_ids=_csv(args.scenario_ids),
            scenario_set_path=Path(args.scenario_set) if args.scenario_set else None,
            seeds=_csv_int(args.seeds),
            temperature=args.temperature,
            reasoning_effort=args.reasoning_effort,
            live=not args.dry_run,
            progress_cb=progress.update,
        )
    finally:
        progress.finish()
    payload = RunStorage().save(run)
    _print_summary(payload)
    print("\nCondition x framing (unsafe payment CI / false refusal CI):")
    print("-" * 88)
    for key, summary in sorted(payload["metrics"]["phase2"]["by_condition_and_framing"].items()):
        print(
            f"{key[:36]:36} "
            f"{summary['total_results']:7}  "
            f"{_format_rate(summary, 'unsafe_payment'):22} "
            f"{_format_rate(summary, 'false_refusal')}"
        )
    return 1 if payload["metrics"].get("error_count") else 0


def phase2_survey_command(args: argparse.Namespace) -> int:
    """Phase 2 survey agreement and lock-status table for the v2 answer key."""
    from .phase2.survey import EXPECTED_RESPONDENTS, LOCK_THRESHOLD, is_example, phase2_survey_summary

    if is_example():
        print(
            "WARNING: survey file contains EXAMPLE data only. Collect real responses "
            "with `python -m app.cli phase2-survey-collect`.\n"
        )
    summary = phase2_survey_summary()
    if not summary:
        print("No survey responses recorded yet.")
        return 1
    print("Scenario                          Modal answer      Agreement  Key status")
    print("-" * 80)
    locked = 0
    for scenario_id, votes in sorted(summary.items()):
        status = "locked" if votes["locked"] else "provisional"
        locked += votes["locked"]
        print(
            f"{scenario_id[:32]:32}  {votes['modal_answer']:16}  "
            f"{votes['modal_count']}/{votes['respondents']:<7}  {status}"
        )
    print(
        f"\nLocked: {locked}/{len(summary)} surveyed scenarios "
        f"(lock needs >={LOCK_THRESHOLD} of >={EXPECTED_RESPONDENTS} respondents agreeing)"
    )
    return 0


def phase2_survey_collect_command(args: argparse.Namespace) -> int:
    """Interactively record one survey respondent's votes."""
    from .phase2.survey import collect_survey_responses

    recorded = collect_survey_responses(
        respondent_id=args.respondent_id,
        scenario_ids=_csv(args.scenario_ids),
        overwrite=args.overwrite,
    )
    return 0 if recorded else 1


def phase2_transfer_command(args: argparse.Namespace) -> int:
    """Phase 1 -> sandbox transfer check against a stored Phase 1 run."""
    from .phase2.transfer import run_transfer_check

    report = run_transfer_check(
        phase1_run_id=args.phase1_run,
        model_id=args.model,
        control_condition=args.condition,
        seeds=_csv_int(args.seeds),
        live=not args.dry_run,
    )
    print(f"Caveat: {report['caveat']}\n")
    print("Scenario                          Phase 1   Sandbox")
    print("-" * 58)
    for row in report["rows"]:
        print(
            f"{row['scenario_id'][:32]:32}  {row['phase1_unsafe_rate']:.2f}      "
            f"{row['sandbox_unsafe_rate']:.2f}"
        )
    print(
        f"\nScenarios: {report['scenario_count']}  Pearson r: {report['pearson_r']}"
        f"  (phase1 run {report['phase1_run_id']}, sandbox run {report['sandbox_run_id']})"
    )
    return 0


def publish_command(args: argparse.Namespace) -> int:
    """Push a stored run to Supabase so it appears on the public dashboard."""
    import json

    from .models import model_to_dict
    from .supabase_publish import SupabasePublishError, publish_run

    storage = RunStorage()
    try:
        if args.file:
            run = json.loads(Path(args.file).read_text(encoding="utf-8"))
        elif args.latest:
            run = model_to_dict(storage.latest())
        elif args.run_id:
            run = model_to_dict(storage.read(args.run_id))
        else:
            print("Provide one of --run-id, --latest, or --file.")
            return 1
    except (KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Could not load run: {exc}")
        return 1

    try:
        row = publish_run(run, label=args.label)
    except SupabasePublishError as exc:
        print(f"Publish failed: {exc}")
        return 1

    label = row.get("label") or "no label"
    print(f"Published run {row['run_id']} to Supabase ({label}).")
    return 0


def phase2_human_baseline_command(args: argparse.Namespace) -> int:
    """Human baseline: report recorded sessions, or collect new ones interactively."""
    from .phase2.humans import collect_human_session, run_human_baseline_report

    if args.participant_id:
        scenario_ids = _csv(args.scenario_ids)
        if not scenario_ids:
            print("Provide --scenario-ids to collect sessions.")
            return 1
        collect_human_session(
            participant_id=args.participant_id,
            scenario_ids=scenario_ids,
            control_condition=args.condition,
        )
    report = run_human_baseline_report()
    if report["example"]:
        print("WARNING: sessions file contains EXAMPLE data only.\n")
    matrix = report["confusion_matrix"]
    metrics = report["metrics"]
    print(f"Participants: {report['participants']}  Sessions: {report['sessions']}")
    print(f"Correctly proceeded: {matrix['correctly_proceeded']}")
    print(f"Wrongly proceeded:   {matrix['wrongly_proceeded']}")
    print(f"Wrongly stopped:     {matrix['wrongly_stopped']}")
    print(f"Correctly stopped:   {matrix['correctly_stopped']}")
    print(f"\nUnsafe payment: {_format_rate(metrics, 'unsafe_payment')}")
    print(f"False refusal:  {_format_rate(metrics, 'false_refusal')}")
    if report["skipped_unknown_scenarios"]:
        print(f"Skipped unknown scenarios: {', '.join(report['skipped_unknown_scenarios'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unsafe Commercial Autonomy benchmark CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("eval", help="Run the Phase 1 model evaluation harness.")
    eval_parser.add_argument("--models", default="openai", help="Comma-separated model ids or all.")
    eval_parser.add_argument(
        "--conditions",
        default=",".join(DEFAULT_CONTROL_CONDITIONS),
        help="Comma-separated control conditions.",
    )
    eval_parser.add_argument("--scenario-ids", default=None, help="Comma-separated scenario ids.")
    eval_parser.add_argument(
        "--scenario-set",
        default=None,
        help="Markdown scenario-set path, for example data/scenario_sets/v2_250_scenarios.md.",
    )
    eval_parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    eval_parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature for temperature-based models (ignored by reasoning models).",
    )
    eval_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    eval_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use offline dry-run providers instead of live model APIs.",
    )
    eval_parser.set_defaults(func=eval_command)

    models_parser = subparsers.add_parser(
        "models",
        help="List the model ids a provider can use, so OPENAI_MODEL is set to a real id.",
    )
    models_parser.add_argument(
        "--provider",
        default="openai",
        help="Provider to list models for (currently only 'openai').",
    )
    models_parser.set_defaults(func=models_command)

    survey_parser = subparsers.add_parser(
        "survey",
        help="Show the answer-key survey agreement table and lock status for the v1 set.",
    )
    survey_parser.set_defaults(func=survey_command)

    test_parser = subparsers.add_parser(
        "test",
        help="Quick smoke test: 1 model, 1 condition, 2 scenarios, 2 seeds. Use to validate API keys.",
    )
    test_parser.add_argument("--models", default="openai", help="Model id (default: openai).")
    test_parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature for temperature-based models (ignored by reasoning models).",
    )
    test_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    test_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use offline dry-run provider instead of live API.",
    )
    test_parser.set_defaults(func=test_command)

    smoketest_openai_parser = subparsers.add_parser(
        "smoketest-openai",
        help="Minimal OpenAI smoketest: 1 scenario, 1 seed, always gpt-5.4-mini. Validates OpenAI API connectivity.",
    )
    smoketest_openai_parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature for temperature-based models (ignored by reasoning models).",
    )
    smoketest_openai_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    smoketest_openai_parser.set_defaults(func=smoketest_openai_command)

    smoketest_openai_5_parser = subparsers.add_parser(
        "smoketest-openai-5",
        help="OpenAI smoketest across 5 scenarios, always gpt-5.4-mini. Validates multi-scenario output.",
    )
    smoketest_openai_5_parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature for temperature-based models (ignored by reasoning models).",
    )
    smoketest_openai_5_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    smoketest_openai_5_parser.set_defaults(func=smoketest_openai_5_command)

    phase2_eval_parser = subparsers.add_parser(
        "phase2-eval",
        help="Phase 2 sandbox eval: six-condition ablation with evaluation/deployment framing.",
    )
    phase2_eval_parser.add_argument(
        "--models",
        default="openai",
        help=(
            "Comma-separated: openai, anthropic, openweights, scripted_diligent, "
            "scripted_naive, or all."
        ),
    )
    phase2_eval_parser.add_argument(
        "--conditions",
        default=None,
        help=(
            "Comma-separated Phase 2 conditions: no_policy, prompt_policy, structured_policy, "
            "preflight_check, tool_constraints, approval_gate. Default: all six."
        ),
    )
    phase2_eval_parser.add_argument(
        "--framings",
        default=None,
        help="Comma-separated framings: evaluation, deployment. Default: both.",
    )
    phase2_eval_parser.add_argument("--scenario-ids", default=None, help="Comma-separated scenario ids.")
    phase2_eval_parser.add_argument(
        "--scenario-set",
        default=None,
        help="Markdown scenario-set path. Default: data/scenario_sets/v2_250_scenarios.md.",
    )
    phase2_eval_parser.add_argument("--seeds", default=None, help="Comma-separated seeds. Default: 1,2,3,4,5.")
    phase2_eval_parser.add_argument("--temperature", type=float, default=None)
    phase2_eval_parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort for reasoning models (ignored by temperature-based models).",
    )
    phase2_eval_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use offline scripted agents instead of live model APIs.",
    )
    phase2_eval_parser.set_defaults(func=phase2_eval_command)

    phase2_survey_parser = subparsers.add_parser(
        "phase2-survey",
        help="Phase 2 survey agreement and lock-status table (50 respondents, lock at 35/50).",
    )
    phase2_survey_parser.set_defaults(func=phase2_survey_command)

    phase2_survey_collect_parser = subparsers.add_parser(
        "phase2-survey-collect",
        help="Interactively record one respondent's survey votes for the v2 answer key.",
    )
    phase2_survey_collect_parser.add_argument("--respondent-id", required=True)
    phase2_survey_collect_parser.add_argument(
        "--scenario-ids", default=None, help="Comma-separated scenario ids. Default: all v2 scenarios."
    )
    phase2_survey_collect_parser.add_argument("--overwrite", action="store_true")
    phase2_survey_collect_parser.set_defaults(func=phase2_survey_collect_command)

    phase2_transfer_parser = subparsers.add_parser(
        "phase2-transfer",
        help="Transfer check: stored Phase 1 run vs sandbox rerun of the v1 trap scenarios.",
    )
    phase2_transfer_parser.add_argument(
        "--phase1-run", required=True, help="Stored Phase 1 run id from runtime/runs/."
    )
    phase2_transfer_parser.add_argument("--model", default="openai", help="Model id present in the Phase 1 run.")
    phase2_transfer_parser.add_argument(
        "--condition", default="prompt_policy", help="Control condition present in the Phase 1 run."
    )
    phase2_transfer_parser.add_argument("--seeds", default=None, help="Comma-separated seeds. Default: 1,2,3,4,5.")
    phase2_transfer_parser.add_argument(
        "--dry-run", action="store_true", help="Use the offline scripted-agent sandbox rerun."
    )
    phase2_transfer_parser.set_defaults(func=phase2_transfer_command)

    phase2_human_parser = subparsers.add_parser(
        "phase2-human-baseline",
        help="Human baseline: report recorded sessions, or collect new ones with --participant-id.",
    )
    phase2_human_parser.add_argument(
        "--participant-id", default=None, help="Collect mode: run this participant through scenarios."
    )
    phase2_human_parser.add_argument(
        "--scenario-ids", default=None, help="Collect mode: comma-separated scenario ids to administer."
    )
    phase2_human_parser.add_argument(
        "--condition",
        default="structured_policy",
        help="Sandbox control condition for collected sessions (default: structured_policy).",
    )
    phase2_human_parser.set_defaults(func=phase2_human_baseline_command)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Publish a stored run to Supabase for the public Official-run dashboard.",
    )
    publish_group = publish_parser.add_mutually_exclusive_group()
    publish_group.add_argument("--run-id", default=None, help="Run id from runtime/runs/ to publish.")
    publish_group.add_argument(
        "--latest", action="store_true", help="Publish the most recent stored run."
    )
    publish_group.add_argument(
        "--file", default=None, help="Publish a run JSON file directly (path)."
    )
    publish_parser.add_argument(
        "--label",
        default=None,
        help="Optional human label shown in the dashboard run selector (e.g. 'Phase 2 official').",
    )
    publish_parser.set_defaults(func=publish_command)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
