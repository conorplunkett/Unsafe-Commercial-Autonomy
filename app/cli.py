from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

from .models import ControlCondition
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


def _format_rate(summary: dict, key: str) -> str:
    ci = summary.get(f"{key}_ci", {})
    rate = summary.get(f"{key}_rate", 0.0)
    if ci:
        return f"{rate:.3f} [{ci.get('ci_low', 0.0):.3f}, {ci.get('ci_high', 0.0):.3f}]"
    return f"{rate:.3f}"


def _print_summary(run_payload: dict) -> None:
    print(f"Run saved: runtime/runs/{run_payload['run_id']}.json")
    print(f"Results: {run_payload['metrics']['total_results']}")
    if run_payload["metrics"].get("error_count"):
        print(f"Errors: {run_payload['metrics']['error_count']}")
    print("")
    print("Model/control                         Results  Unsafe payment CI      False refusal CI")
    print("-" * 88)
    for agent_id, summary in sorted(run_payload["metrics"].get("by_agent", {}).items()):
        print(
            f"{agent_id[:36]:36} "
            f"{summary['total_results']:7}  "
            f"{_format_rate(summary, 'unsafe_payment'):22} "
            f"{_format_rate(summary, 'false_refusal')}"
        )


def eval_command(args: argparse.Namespace) -> int:
    model_ids = _csv(args.models) or ["openai"]
    control_conditions = _csv_conditions(args.conditions) or DEFAULT_CONTROL_CONDITIONS
    scenario_ids = _csv(args.scenario_ids)
    seeds = _csv_int(args.seeds) or DEFAULT_SEEDS
    run = run_phase1_evaluation(
        model_ids=model_ids,
        control_conditions=control_conditions,
        scenario_ids=scenario_ids,
        scenario_set_path=Path(args.scenario_set) if args.scenario_set else None,
        seeds=seeds,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
        live=not args.dry_run,
    )
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


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
    run = run_phase1_evaluation(
        model_ids=model_ids,
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap", "scn_v1_a1_lookalike"],
        seeds=[1, 2],
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
        live=not args.dry_run,
    )
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


def smoketest_openai_command(args: argparse.Namespace) -> int:
    """Minimal OpenAI smoketest: 1 scenario, 1 seed, always gpt-5.4-mini."""
    from .providers import OpenAIResponsesProvider

    def _factory(model_id: str, live: bool):
        return OpenAIResponsesProvider(model_name="gpt-5.4-mini")

    run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
        live=True,
        provider_factory=_factory,
    )
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


def smoketest_openai_5_command(args: argparse.Namespace) -> int:
    """OpenAI smoketest across 5 scenarios, always gpt-5.4-mini."""
    from .providers import OpenAIResponsesProvider

    def _factory(model_id: str, live: bool):
        return OpenAIResponsesProvider(model_name="gpt-5.4-mini")

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
    )
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


# ---------------------------------------------------------------------------
# Phase 2 (mockup) commands — fully separate from the Phase 1 paths above.
# All app.phase2 imports are lazy so Phase 1 commands never load Phase 2 code.
# ---------------------------------------------------------------------------


def phase2_eval_command(args: argparse.Namespace) -> int:
    """Mocked Phase 2 six-condition ablation with framing variation. Offline only."""
    from .phase2 import run_phase2_evaluation

    run = run_phase2_evaluation(
        model_ids=_csv(args.models),
        control_conditions=_csv(args.conditions),
        framings=_csv(args.framings),
        scenario_ids=_csv(args.scenario_ids),
        scenario_set_path=Path(args.scenario_set) if args.scenario_set else None,
        seeds=_csv_int(args.seeds),
    )
    payload = RunStorage().save(run)
    print("PHASE 2 MOCKUP: offline hash-seeded mock agents, no live models or sandbox.\n")
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
    return 0


def phase2_survey_command(args: argparse.Namespace) -> int:
    """Synthetic 50-participant survey table for the v2 answer key."""
    from .data import load_scenarios
    from .phase2 import PHASE2_SCENARIO_SET, PHASE2_SURVEY_LOCK_THRESHOLD, phase2_survey_summary

    print("PHASE 2 MOCKUP: survey votes are SYNTHETIC placeholder data.\n")
    summary = phase2_survey_summary()
    scenarios = load_scenarios(PHASE2_SCENARIO_SET)
    print("Scenario                          Modal answer  Agreement  Key status")
    print("-" * 76)
    locked = 0
    for scenario in scenarios:
        votes = summary[scenario.scenario_id]
        status = "locked" if votes["locked"] else "provisional"
        locked += votes["locked"]
        print(
            f"{scenario.scenario_id[:32]:32}  {votes['modal_answer']:12}  "
            f"{votes['modal_count']}/{votes['respondents']:<6}  {status}"
        )
    print(
        f"\nLocked: {locked}/{len(scenarios)} scenarios "
        f"(threshold {PHASE2_SURVEY_LOCK_THRESHOLD}/50 agreement)"
    )
    return 0


def phase2_transfer_command(args: argparse.Namespace) -> int:
    """Mocked Phase 1 -> sandbox transfer check on the 25 v1 trap scenarios."""
    from .phase2 import run_phase2_transfer_check

    print("PHASE 2 MOCKUP: both environments are mocked; correlation is illustrative.\n")
    report = run_phase2_transfer_check(seeds=_csv_int(args.seeds), model_id=args.model)
    print("Scenario                          Simulated  Sandbox")
    print("-" * 58)
    for row in report["rows"]:
        print(
            f"{row['scenario_id'][:32]:32}  {row['simulated_unsafe_rate']:.2f}       "
            f"{row['sandbox_unsafe_rate']:.2f}"
        )
    print(f"\nScenarios: {report['scenario_count']}  Pearson r: {report['pearson_r']}")
    return 0


def phase2_human_baseline_command(args: argparse.Namespace) -> int:
    """Mocked human-baseline run on a sample of v2 tasks."""
    from .phase2 import run_phase2_human_baseline

    print("PHASE 2 MOCKUP: simulated participants, not real human data.\n")
    report = run_phase2_human_baseline(
        participants=args.participants,
        sample_size=args.sample_size,
    )
    matrix = report["confusion_matrix"]
    print(f"Participants: {report['participants']}  Sample: {report['sample_size']} scenarios")
    print(f"Correctly proceeded: {matrix['correctly_proceeded']}")
    print(f"Wrongly proceeded:   {matrix['wrongly_proceeded']}")
    print(f"Wrongly stopped:     {matrix['wrongly_stopped']}")
    print(f"Correctly stopped:   {matrix['correctly_stopped']}")
    print(f"\nUnsafe payment rate: {report['unsafe_payment_rate']:.3f}")
    print(f"False refusal rate:  {report['false_refusal_rate']:.3f}")
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
        choices=["minimal", "low", "medium", "high"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    eval_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use offline dry-run providers instead of live model APIs.",
    )
    eval_parser.set_defaults(func=eval_command)

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
        choices=["minimal", "low", "medium", "high"],
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
        choices=["minimal", "low", "medium", "high"],
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
        choices=["minimal", "low", "medium", "high"],
        default=None,
        help="Reasoning effort for reasoning models such as gpt-5.x (ignored by temperature-based models).",
    )
    smoketest_openai_5_parser.set_defaults(func=smoketest_openai_5_command)

    phase2_eval_parser = subparsers.add_parser(
        "phase2-eval",
        help="MOCKUP: Phase 2 six-condition ablation with framing test. Offline, no API keys.",
    )
    phase2_eval_parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated mock model ids: mock_weak, mock_strong, mock_baseline_naive.",
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
    phase2_eval_parser.set_defaults(func=phase2_eval_command)

    phase2_survey_parser = subparsers.add_parser(
        "phase2-survey",
        help="MOCKUP: synthetic 50-participant survey agreement table for the v2 answer key.",
    )
    phase2_survey_parser.set_defaults(func=phase2_survey_command)

    phase2_transfer_parser = subparsers.add_parser(
        "phase2-transfer",
        help="MOCKUP: Phase 1 simulated vs sandbox transfer check on the 25 v1 trap scenarios.",
    )
    phase2_transfer_parser.add_argument("--seeds", default=None, help="Comma-separated seeds. Default: 1,2,3,4,5.")
    phase2_transfer_parser.add_argument(
        "--model",
        default="mock_weak",
        help="Mock model id to simulate (default: mock_weak).",
    )
    phase2_transfer_parser.set_defaults(func=phase2_transfer_command)

    phase2_human_parser = subparsers.add_parser(
        "phase2-human-baseline",
        help="MOCKUP: simulated human-baseline run on a sample of v2 tasks.",
    )
    phase2_human_parser.add_argument("--participants", type=int, default=8, help="Simulated participants (5-10).")
    phase2_human_parser.add_argument("--sample-size", type=int, default=40, help="Number of v2 scenarios sampled.")
    phase2_human_parser.set_defaults(func=phase2_human_baseline_command)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
