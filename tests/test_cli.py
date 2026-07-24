import fcntl
import os
import pty
import struct
import termios

from app.cli import _ProgressBar, main


def test_progress_bar_uses_real_tty_width_over_stale_columns_env(monkeypatch):
    # Regression: a shell that exported COLUMNS before splitting into a
    # narrower pane leaves that env var stale. If the progress bar trusted
    # it, lines would overflow the real pane width, autowrap, and each
    # redraw's "\r" would land on a blank wrapped row instead of the row
    # with real text -- leaving old status lines stuck on screen forever.
    monkeypatch.setenv("COLUMNS", "200")
    master_fd, slave_fd = pty.openpty()
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 40, 0, 0))
    stream = os.fdopen(slave_fd, "w")
    try:
        bar = _ProgressBar(stream=stream, width=24)
        assert bar._columns() == 40

        bar.update(10, 750, "running openai / no_policy / scn_v1_d3_lookalike / seed 3")
        stream.flush()
        os.set_blocking(master_fd, False)
        written = b""
        try:
            while True:
                written += os.read(master_fd, 4096)
        except BlockingIOError:
            pass
        line = written.decode()
        # Every rendered line, including the leading "\r", must fit the real
        # 40-column pane -- not the stale 200-column env value.
        assert len(line.split("\r")[-1]) <= 39
    finally:
        stream.close()
        os.close(master_fd)


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
        "XAI_API_KEY",
        "GROK_API_KEY",
        "DEEPSEEK_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    status = main(["models"])

    output = capsys.readouterr().out
    assert status == 1
    assert "== openai ==" in output
    assert "== anthropic ==" in output
    assert "== gemini ==" in output
    assert "== kimi ==" in output
    assert "== grok ==" in output
    assert "== deepseek ==" in output
    assert "== mistral ==" in output
    assert "== openrouter ==" in output
    # openai, anthropic, gemini, kimi, grok, deepseek, mistral, openrouter.
    assert output.count("skipped:") == 8


def test_cli_models_rejects_unknown_provider(capsys):
    status = main(["models", "--provider", "not-a-provider"])

    output = capsys.readouterr().out
    assert status == 2
    assert "Unknown provider" in output
