from app.cli import main


def test_cli_eval_dry_run_prints_saved_summary(capsys):
    status = main(
        [
            "eval",
            "--models",
            "openai",
            "--conditions",
            "no_policy",
            "--scenario-ids",
            "scn_v1_a1_trap",
            "--seeds",
            "1",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Run saved:" in output
    assert "openai:no_policy" in output


def test_cli_eval_live_without_openai_key_aborts_before_running(capsys, monkeypatch):
    # Missing key is caught by preflight, so the run aborts up front with an
    # actionable message instead of saving a junk run full of errored combos.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = main(
        [
            "eval",
            "--models",
            "openai",
            "--conditions",
            "no_policy",
            "--scenario-ids",
            "scn_v1_a1_trap",
            "--seeds",
            "1",
        ]
    )

    output = capsys.readouterr().out
    assert status == 2
    assert "Cannot start eval" in output
    assert "Run saved:" not in output


def test_cli_eval_accepts_v2_scenario_set(capsys):
    status = main(
        [
            "eval",
            "--models",
            "openai",
            "--conditions",
            "no_policy",
            "--scenario-set",
            "data/scenario_sets/v2_250_scenarios.md",
            "--scenario-ids",
            "scn_v2_a1_trap",
            "--seeds",
            "1",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Run saved:" in output
    assert "openai:no_policy" in output


def test_cli_survey_reports_all_locked(capsys):
    status = main(["survey"])

    output = capsys.readouterr().out
    assert status == 0
    assert "SYNTHETIC" in output
    assert "Locked: 50/50 scenarios" in output


def test_cli_test_command_dry_run(capsys):
    status = main(["test", "--dry-run", "--reasoning-effort", "low"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Run saved:" in output
