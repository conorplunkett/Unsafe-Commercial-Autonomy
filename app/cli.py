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
        temperature=0.7,
        live=not args.dry_run,
    )
    payload = RunStorage().save(run)
    _print_summary(payload)
    return 1 if payload["metrics"].get("error_count") else 0


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
    eval_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
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
        "--dry-run",
        action="store_true",
        help="Use offline dry-run provider instead of live API.",
    )
    test_parser.set_defaults(func=test_command)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
