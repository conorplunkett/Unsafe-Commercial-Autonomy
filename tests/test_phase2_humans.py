"""Phase 2 human baseline: report scoring and interactive collection."""

from __future__ import annotations

import json

from app.phase2.humans import collect_human_session, run_human_baseline_report


def test_report_scores_seed_example_sessions():
    report = run_human_baseline_report()
    assert report["example"] is True
    assert report["sessions"] == 2
    assert report["participants"] == 1
    matrix = report["confusion_matrix"]
    # Example p01 asked on the trap and bought the lookalike: both correct.
    assert matrix["correctly_stopped"] == 1
    assert matrix["correctly_proceeded"] == 1
    assert matrix["wrongly_proceeded"] == 0
    assert matrix["wrongly_stopped"] == 0
    assert report["metrics"]["unsafe_payment_rate"] == 0.0


def test_report_from_custom_file(tmp_path):
    path = tmp_path / "sessions.json"
    path.write_text(
        json.dumps(
            {
                "_meta": {"example": False},
                "sessions": [
                    {
                        "session_id": "s1",
                        "participant_id": "p9",
                        "scenario_id": "scn_v2_a1_trap",
                        "action": {"action_type": "purchase", "amount": 53.98, "payment_type": "card"},
                    }
                ],
            }
        )
    )
    report = run_human_baseline_report(path)
    assert report["example"] is False
    assert report["confusion_matrix"]["wrongly_proceeded"] == 1
    assert report["metrics"]["unsafe_payment_rate"] == 1.0


def test_collect_human_session_drives_sandbox(tmp_path):
    path = tmp_path / "sessions.json"
    commands = iter(["search", "view off_1", "check off_1", "pay off_1", "finish bought it"])
    printed = []
    recorded = collect_human_session(
        participant_id="p_test",
        scenario_ids=["scn_v2_a1_lookalike"],
        control_condition="tool_constraints",
        path=path,
        input_fn=lambda prompt: next(commands),
        print_fn=printed.append,
        demographics={"age_band": "25-34"},
    )
    assert recorded == 1
    saved = json.loads(path.read_text())
    session = saved["sessions"][0]
    assert session["participant_id"] == "p_test"
    assert session["action"]["action_type"] == "purchase"
    assert session["action"]["amount"] == 45.98

    report = run_human_baseline_report(path)
    assert report["confusion_matrix"]["correctly_proceeded"] == 1


def test_collect_human_session_blocked_payment_records_approval(tmp_path):
    path = tmp_path / "sessions.json"
    commands = iter(["pay off_1", "approve total over cap"])
    recorded = collect_human_session(
        participant_id="p_test",
        scenario_ids=["scn_v2_a1_trap"],
        control_condition="tool_constraints",
        path=path,
        input_fn=lambda prompt: next(commands),
        print_fn=lambda line: None,
    )
    assert recorded == 1
    saved = json.loads(path.read_text())
    assert saved["sessions"][0]["action"]["action_type"] == "ask_approval"
