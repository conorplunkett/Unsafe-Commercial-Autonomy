"""Tests for the Phase 2 mockup harness (app/phase2.py)."""

from __future__ import annotations

from app.cli import main
from app.phase2 import (
    FRAMINGS,
    PHASE2_CONTROL_CONDITIONS,
    phase2_survey_summary,
    run_phase2_evaluation,
    run_phase2_human_baseline,
    run_phase2_transfer_check,
)


def test_phase2_eval_covers_six_conditions_and_both_framings():
    run = run_phase2_evaluation(
        scenario_ids=["scn_v2_a1_trap", "scn_v2_a1_lookalike"],
        seeds=[1, 2],
    )
    assert run.phase == "phase2_mock"
    assert run.control_conditions == PHASE2_CONTROL_CONDITIONS
    assert run.framings == FRAMINGS
    # 2 models x 6 conditions x 2 framings x 2 scenarios x 2 seeds
    assert len(run.results) == 96
    assert {result.framing for result in run.results} == set(FRAMINGS)
    assert "phase2" in run.metrics
    assert run.metrics["phase2"]["mock"] is True
    assert set(run.metrics["phase2"]["by_framing"]) == set(FRAMINGS)


def test_phase2_eval_is_deterministic():
    kwargs = dict(
        model_ids=["mock_weak"],
        control_conditions=["no_policy", "approval_gate"],
        scenario_ids=["scn_v2_a1_trap", "scn_v2_a1_lookalike"],
        seeds=[1, 2, 3],
    )
    first = run_phase2_evaluation(**kwargs)
    second = run_phase2_evaluation(**kwargs)
    actions_first = [result.action.action_type for result in first.results]
    actions_second = [result.action.action_type for result in second.results]
    assert actions_first == actions_second


def test_approval_gate_blocks_trap_payments():
    run = run_phase2_evaluation(
        model_ids=["mock_baseline_naive"],
        control_conditions=["approval_gate"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1, 2, 3],
    )
    assert all(result.action.action_type == "ask_approval" for result in run.results)
    assert all(not result.unsafe_payment for result in run.results)


def test_no_policy_naive_baseline_is_unsafe_on_traps():
    run = run_phase2_evaluation(
        model_ids=["mock_baseline_naive"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1, 2, 3],
    )
    assert all(result.unsafe_payment for result in run.results)


def test_phase2_rejects_unknown_inputs():
    import pytest

    with pytest.raises(KeyError):
        run_phase2_evaluation(model_ids=["gpt-5.5"])
    with pytest.raises(KeyError):
        run_phase2_evaluation(control_conditions=["super_policy"])
    with pytest.raises(KeyError):
        run_phase2_evaluation(framings=["covert"])


def test_phase2_survey_summary_covers_v2_and_is_synthetic():
    summary = phase2_survey_summary()
    assert len(summary) == 250
    assert all(votes["synthetic"] for votes in summary.values())
    assert all(votes["respondents"] == 50 for votes in summary.values())


def test_transfer_check_reports_correlation_over_v1_traps():
    report = run_phase2_transfer_check(seeds=[1, 2, 3])
    assert report["mock"] is True
    assert report["scenario_count"] == 25
    assert report["pearson_r"] is not None
    assert -1.0 <= report["pearson_r"] <= 1.0


def test_human_baseline_confusion_matrix_adds_up():
    report = run_phase2_human_baseline(participants=6, sample_size=20)
    matrix = report["confusion_matrix"]
    assert sum(matrix.values()) == 6 * 20
    assert 0.0 <= report["unsafe_payment_rate"] <= 1.0
    assert 0.0 <= report["false_refusal_rate"] <= 1.0


def test_phase2_cli_commands_run(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.RunStorage.__init__", lambda self, root=None: setattr(self, "root", tmp_path) or tmp_path.mkdir(exist_ok=True) or None)
    assert main(["phase2-eval", "--scenario-ids", "scn_v2_a1_trap,scn_v2_a1_lookalike", "--seeds", "1"]) == 0
    assert "PHASE 2 MOCKUP" in capsys.readouterr().out
    assert main(["phase2-survey"]) == 0
    assert "SYNTHETIC" in capsys.readouterr().out
    assert main(["phase2-transfer", "--seeds", "1,2"]) == 0
    assert "Pearson r" in capsys.readouterr().out
    assert main(["phase2-human-baseline", "--participants", "5", "--sample-size", "10"]) == 0
    assert "Unsafe payment rate" in capsys.readouterr().out


def test_phase1_eval_still_rejects_phase2_conditions():
    """Phase 1 must stay untouched: its runner only accepts its own 3 conditions."""
    import pytest

    from app.runner import run_phase1_evaluation

    with pytest.raises(KeyError):
        run_phase1_evaluation(
            model_ids=["openai"],
            control_conditions=["approval_gate"],
            scenario_ids=["scn_v1_a1_trap"],
            seeds=[1],
        )
