from __future__ import annotations

from app.metrics import phase2_paired_contrasts, recompute_run_metrics
from app.models import AgentAction, EvaluationResult
from app.phase2.runner import run_phase2_evaluation


def _result(
    scenario_id: str,
    condition: str,
    seed: int,
    *,
    unsafe: bool = False,
    refused: bool = False,
    model: str = "model-a",
    urgency: str = "none",
    user_availability: str = "none",
    pair_role: str = "trap",
    over_refusal_scoring_enabled: bool = True,
    answer_key_status: str = "survey_locked_70",
    outcome_eligible: bool = True,
    error: str | None = None,
) -> EvaluationResult:
    verdict = "error" if error else "unsafe" if unsafe else "refused_when_safe" if refused else "safe"
    action = AgentAction(action_type="defer", rationale="synthetic")
    return EvaluationResult(
        scenario_id=scenario_id,
        scenario_title=scenario_id,
        category="synthetic",
        agent_id=f"provider:{condition}",
        agent_name=f"{model} / {condition}",
        model_id="provider",
        model_name=model,
        provider_id="provider",
        control_condition=condition,
        framing="deployment",
        urgency=urgency,
        user_availability=user_availability,
        seed=seed,
        action=action,
        proposed_action=action,
        verdict=verdict,
        refused_when_safe=refused,
        pair_role=pair_role,
        over_refusal_scoring_enabled=over_refusal_scoring_enabled,
        answer_key_status=answer_key_status,
        outcome_eligible=outcome_eligible,
        error=error,
    )


def _comparison(results, contrast, outcome):
    matches = [
        row
        for row in phase2_paired_contrasts(results)["comparisons"]
        if row["contrast"] == contrast and row["outcome"] == outcome
    ]
    assert len(matches) == 1
    return matches[0]


def test_repeated_seeds_are_averaged_within_scenario_and_direction_is_b_minus_a():
    results = []
    for seed in (1, 2):
        results.extend(
            [
                _result("scenario_1", "no_policy", seed, unsafe=True),
                _result("scenario_1", "structured_policy", seed, unsafe=False),
                _result("scenario_2", "no_policy", seed, unsafe=False),
                _result("scenario_2", "structured_policy", seed, unsafe=False),
            ]
        )

    row = _comparison(
        results, "structured_policy_minus_no_policy", "unsafe_verdict"
    )
    assert row["paired_seed_count"] == 4
    assert row["scenario_count"] == 2
    assert row["condition_a_rate"] == 0.5
    assert row["condition_b_rate"] == 0.0
    assert row["risk_difference"] == -0.5


def test_exact_seed_pairing_reports_missing_errors_and_unpaired_cells():
    results = [
        _result("scenario_1", "no_policy", 1),
        _result("scenario_1", "structured_policy", 2),
        _result("scenario_1", "no_policy", 3),
        _result("scenario_1", "structured_policy", 3, error="provider error"),
    ]
    row = _comparison(
        results, "structured_policy_minus_no_policy", "unsafe_verdict"
    )
    assert row["paired_seed_count"] == 0
    assert row["scenario_count"] == 0
    assert row["missing_count"] == 2
    assert row["error_count"] == 1
    assert row["unpaired_count"] == 3
    assert row["risk_difference"] is None


def test_outcome_filters_exclude_unkeyed_and_wrong_denominator_rows():
    results = [
        _result("keyed_trap", "no_policy", 1, unsafe=True),
        _result("keyed_trap", "structured_policy", 1),
        _result("lookalike", "no_policy", 1, pair_role="lookalike"),
        _result("lookalike", "structured_policy", 1, pair_role="lookalike"),
        _result(
            "excluded_trap",
            "no_policy",
            1,
            answer_key_status="excluded",
        ),
        _result(
            "excluded_trap",
            "structured_policy",
            1,
            answer_key_status="excluded",
        ),
    ]
    unsafe = _comparison(
        results, "structured_policy_minus_no_policy", "unsafe_verdict"
    )
    refused = _comparison(
        results, "structured_policy_minus_no_policy", "refused_when_safe"
    )
    assert unsafe["paired_seed_count"] == 1
    assert unsafe["excluded_count"] == 4
    # The scoring-enabled lookalike remains in the refused-when-safe denominator;
    # the excluded pair leaves both outcomes.
    assert refused["paired_seed_count"] == 2
    assert refused["excluded_count"] == 2


def test_behaviorally_unobservable_rows_leave_both_paired_outcomes():
    results = [
        _result(
            "e11_trap",
            condition,
            1,
            outcome_eligible=False,
        )
        for condition in ("no_policy", "structured_policy")
    ]
    for outcome in ("unsafe_verdict", "refused_when_safe"):
        row = _comparison(
            results,
            "structured_policy_minus_no_policy",
            outcome,
        )
        assert row["paired_seed_count"] == 0
        assert row["excluded_count"] == 2


def test_models_and_pressure_cells_are_never_pooled():
    results = []
    for model in ("model-a", "model-b"):
        for urgency in ("none", "time_pressure"):
            results.extend(
                [
                    _result("scenario_1", "no_policy", 1, model=model, urgency=urgency),
                    _result(
                        "scenario_1",
                        "structured_policy",
                        1,
                        model=model,
                        urgency=urgency,
                    ),
                ]
            )
    rows = [
        row
        for row in phase2_paired_contrasts(results)["comparisons"]
        if row["contrast"] == "structured_policy_minus_no_policy"
        and row["outcome"] == "unsafe_verdict"
    ]
    assert len(rows) == 4
    assert {(row["model"], row["urgency"]) for row in rows} == {
        ("model-a", "none"),
        ("model-a", "time_pressure"),
        ("model-b", "none"),
        ("model-b", "time_pressure"),
    }
    assert all(row["scenario_count"] == 1 for row in rows)


def test_zero_variance_difference_has_zero_width_t_interval():
    results = []
    for scenario_id in ("scenario_1", "scenario_2", "scenario_3"):
        results.extend(
            [
                _result(scenario_id, "structured_policy", 1, refused=True),
                _result(scenario_id, "tool_constraints", 1, refused=False),
            ]
        )
    row = _comparison(
        results, "tool_constraints_minus_structured_policy", "refused_when_safe"
    )
    assert row["scenario_count"] == 3
    assert row["risk_difference"] == -1.0
    assert row["ci_low"] == -1.0
    assert row["ci_high"] == -1.0


def test_recompute_rebuilds_the_same_paired_metrics():
    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy", "structured_policy", "tool_constraints"],
        scenario_ids=["scn_v2_a1_trap", "scn_v2_a1_lookalike"],
        seeds=[1, 2],
        checkpoint=False,
    )
    before = run.metrics["phase2"]["paired_contrasts"]
    run.metrics = {}
    recompute_run_metrics(run)
    assert run.metrics["phase2"]["paired_contrasts"] == before
    assert run.metrics["phase2"]["episode_descriptives"] == {
        "unit": "episode",
        "confidence_interval": "Wilson score, 95%",
    }


def test_recompute_backfills_outcome_exclusions(monkeypatch):
    import app.metrics as metrics_module

    run = run_phase2_evaluation(
        model_ids=["scripted_diligent"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v2_e11_trap", "scn_v2_e11_lookalike"],
        seeds=[1],
        checkpoint=False,
    )
    for result in run.results:
        result.outcome_eligible = True
        result.outcome_exclusion_reason = None
    run.metrics = {}

    # No committed v2 scenario carries an outcome exclusion any more
    # (scn_v2_e11_trap left it 2026-08-23 -- its injected instruction now
    # points at a distinguishable second offer -- see CHANGELOG), so this
    # monkeypatches the engine's exclusion metadata to simulate one for both
    # arms, as if a future scenario were flagged reasoning_only_unobservable,
    # to keep recompute_run_metrics's backfill path itself covered.
    monkeypatch.setattr(
        metrics_module,
        "_scenario_outcome_eligibility",
        lambda: {
            "scn_v2_e11_trap": (False, "reasoning_only_unobservable"),
            "scn_v2_e11_lookalike": (False, "reasoning_only_unobservable"),
        },
    )

    recompute_run_metrics(run)

    assert all(result.outcome_eligible is False for result in run.results)
    assert run.metrics["outcome_excluded_count"] == 2
    assert run.metrics["outcome_exclusion_reasons"] == {
        "reasoning_only_unobservable": 2
    }
    assert run.metrics["unsafe_payment_ci"]["total"] == 0
    assert run.metrics["refused_when_safe_ci"]["total"] == 0
    assert run.metrics["payment_effectiveness_ci"]["pairs"] == 0
