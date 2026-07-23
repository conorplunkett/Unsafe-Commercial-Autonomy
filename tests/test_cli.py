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


def test_cli_survey_reports_real_lock_state(capsys):
    status = main(["survey"])

    output = capsys.readouterr().out
    # The shipped survey file holds the real v1_web_r6 responses: 46 scenarios
    # lock (38 team-keyed + 5 survey-locked + 3 objective-verdict traps) and
    # the 4 failed lookalikes are dropped from the key, so the key is ready
    # (exit 0) and the synthetic warning is gone.
    assert status == 0
    assert "SYNTHETIC" not in output
    assert "Locked: 46/50 scenarios" in output
    assert "4 dropped from key" in output
    assert "Reflexive-ask floor (att_1): 17/31" in output


def test_cli_test_command_dry_run(capsys):
    status = main(["test", "--dry-run", "--reasoning-effort", "low"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Run saved:" in output


def test_cli_phase2_human_import_reports(tmp_path, capsys):
    csv_path = tmp_path / "form.csv"
    csv_path.write_text(
        "participant_id,Job,scn_v2_a1_trap,scn_v2_a1_lookalike\n"
        "p01,Accountant,ask,proceed\n"
    )
    sessions = tmp_path / "sessions.json"

    status = main(
        ["phase2-human-import", "--csv", str(csv_path), "--sessions-file", str(sessions)]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Imported 2 session(s)" in output
    assert "By demographic" in output
    assert sessions.exists()


def test_cli_publish_human_baseline_refuses_example(capsys):
    # The shipped sessions file is example-only; publishing it must be blocked.
    status = main(["publish-human-baseline"])

    output = capsys.readouterr().out
    assert status == 1
    assert "EXAMPLE" in output


def test_cli_models_lists_all_providers_and_skips_missing_keys(capsys, monkeypatch):
    # With no keys set, every provider is skipped with an actionable message
    # instead of crashing or making network calls.
    for var in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "KIMI_API_KEY",
        "MOONSHOT_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    status = main(["models"])

    output = capsys.readouterr().out
    assert status == 1
    assert "== openai ==" in output
    assert "== anthropic ==" in output
    assert "== gemini ==" in output
    assert "== kimi ==" in output
    assert output.count("skipped:") == 4


def test_cli_models_rejects_unknown_provider(capsys):
    status = main(["models", "--provider", "grok"])

    output = capsys.readouterr().out
    assert status == 2
    assert "Unknown provider" in output
