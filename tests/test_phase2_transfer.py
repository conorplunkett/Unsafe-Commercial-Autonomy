"""Transfer check: stored Phase 1 run vs sandbox rerun of v1 traps."""

from __future__ import annotations

import pytest

from app.phase2.transfer import pearson, run_transfer_check
from app.runner import run_phase1_evaluation
from app.storage import RunStorage


def test_pearson():
    assert pearson([0, 1, 2], [0, 1, 2]) == 1.0
    assert pearson([0, 1, 2], [2, 1, 0]) == -1.0
    assert pearson([1, 1, 1], [0, 1, 2]) is None
    assert pearson([1.0], [1.0]) is None


def test_transfer_check_against_stored_phase1_run(tmp_path):
    storage = RunStorage(root=tmp_path)
    phase1_run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["prompt_policy"],
        seeds=[1],
        live=False,
    )
    storage.save(phase1_run)

    report = run_transfer_check(
        phase1_run_id=phase1_run.run_id,
        model_id="openai",
        control_condition="prompt_policy",
        seeds=[1],
        live=False,
        storage=storage,
    )
    assert report["scenario_count"] == 25
    assert len(report["rows"]) == 25
    for row in report["rows"]:
        assert row["scenario_id"].endswith("_trap")
        assert 0.0 <= row["phase1_unsafe_rate"] <= 1.0
        assert 0.0 <= row["sandbox_unsafe_rate"] <= 1.0
    if report["pearson_r"] is not None:
        assert -1.0 <= report["pearson_r"] <= 1.0
    assert "caveat" in report


def test_transfer_check_errors_clearly_on_missing_model(tmp_path):
    storage = RunStorage(root=tmp_path)
    phase1_run = run_phase1_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        scenario_ids=["scn_v1_a1_trap"],
        seeds=[1],
        live=False,
    )
    storage.save(phase1_run)
    with pytest.raises(KeyError):
        run_transfer_check(
            phase1_run_id=phase1_run.run_id,
            model_id="anthropic",
            control_condition="no_policy",
            storage=storage,
        )
