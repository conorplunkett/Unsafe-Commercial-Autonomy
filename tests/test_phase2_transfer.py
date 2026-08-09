"""Transfer check: stored Phase 1 run vs sandbox rerun of v1 traps."""

from __future__ import annotations

import pytest

from app.phase2.transfer import _per_scenario_unsafe_rates, pearson, run_transfer_check
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
        control_conditions=["tool_constraints"],
        seeds=[1],
        live=False,
    )
    storage.save(phase1_run)

    report = run_transfer_check(
        phase1_run_id=phase1_run.run_id,
        model_id="openai",
        control_condition="tool_constraints",
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
    assert report["skipped_scenario_ids"] == []


def test_per_scenario_rates_exclude_errored_results():
    results = [
        {"scenario_id": "scn_a", "unsafe_payment": True, "error": None},
        {"scenario_id": "scn_a", "unsafe_payment": False, "error": "provider timeout"},
        {"scenario_id": "scn_b", "unsafe_payment": False, "error": "provider timeout"},
    ]
    rates = _per_scenario_unsafe_rates(results, ["scn_a", "scn_b"])
    # The errored scn_a episode must not deflate the rate, and scn_b (all
    # errors) must drop out rather than score as 0% unsafe.
    assert rates == {"scn_a": 1.0}


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
