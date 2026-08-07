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


def test_confirm_live_run_passes_through_safe_cases():
    from app.cli import _confirm_live_run

    # Dry runs are offline/free; small grids don't need a prompt; --yes is
    # explicit; a 0-estimate (grid size couldn't be computed) defers to the
    # real run's own error instead of blocking here.
    assert _confirm_live_run(1000, "big", live=False, assume_yes=False, label="x") is True
    assert _confirm_live_run(10, "small", live=True, assume_yes=False, label="x") is True
    assert _confirm_live_run(1000, "big", live=True, assume_yes=True, label="x") is True
    assert _confirm_live_run(0, "", live=True, assume_yes=False, label="x") is True


def test_confirm_live_run_refuses_large_run_without_tty(monkeypatch, capsys):
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    result = cli._confirm_live_run(1000, "1 model x 1000 calls", live=True, assume_yes=False, label="Phase 1 eval")

    assert result is False
    assert "Refusing to run this live Phase 1 eval without confirmation" in capsys.readouterr().out


def test_confirm_live_run_interactive_yes_and_abort(monkeypatch):
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def _confirm(answer):
        monkeypatch.setattr("builtins.input", lambda _prompt: answer)
        return cli._confirm_live_run(1000, "big grid", live=True, assume_yes=False, label="Phase 1 eval")

    assert _confirm("yes") is True
    assert _confirm("") is False
    assert _confirm("no") is False


def test_phase1_grid_size_computes_breakdown():
    from app.cli import _phase1_grid_size

    total, breakdown = _phase1_grid_size(["openai"], None, ["scn_v1_a1_trap"], None, [1, 2])
    assert total == 1 * 3 * 1 * 2  # 1 model x default 3 conditions x 1 scenario x 2 seeds
    assert "2 seed(s)" in breakdown

    # Unknown model id can't be resolved -- returns the "defer to real error" 0.
    assert _phase1_grid_size(["not-a-real-provider"], None, None, None, None) == (0, "")


def test_phase1_grid_size_excludes_offline_models():
    # Offline providers (baseline_naive) make no API calls, so they never count
    # toward the live-cost confirmation grid.
    from app.cli import _phase1_grid_size

    assert _phase1_grid_size(["baseline_naive"], None, None, None, [1]) == (0, "")
    # A mixed run counts only the live model(s).
    total, breakdown = _phase1_grid_size(
        ["openai", "baseline_naive"], ["no_policy"], ["scn_v1_a1_trap"], None, [1]
    )
    assert total == 1  # 1 live model x 1 condition x 1 scenario x 1 seed
    assert "1 model(s)" in breakdown


def test_cli_eval_offline_baseline_skips_confirmation(capsys, monkeypatch):
    # The documented offline baseline command must run in non-interactive
    # contexts (CI, pipes) without tripping the live-cost guard.
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(["eval", "--models", "baseline_naive", "--seeds", "1"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Refusing to run" not in output
    assert "Run saved:" in output


def test_cli_phase2_eval_offline_scripted_skips_confirmation(capsys, monkeypatch):
    # Scripted Phase 2 agents run offline, so a scripted-only grid never trips
    # the episode-cost confirmation.
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(
        ["phase2-eval", "--models", "scripted_naive", "--scenario-ids", "scn_v2_a1_trap", "--seeds", "1"]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Refusing to run" not in output
    assert "Run saved:" in output


def test_cli_eval_large_grid_aborts_without_confirmation(capsys, monkeypatch):
    # The full command path: a live default eval (single model x full v1 set)
    # is already a 750-call grid, so it must abort (exit 2) with no TTY,
    # before touching any provider -- this is the "full grid" case, not just
    # an explicit --models all.
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(["eval", "--models", "openai"])

    output = capsys.readouterr().out
    assert status == 2
    assert "Refusing to run this live Phase 1 eval without confirmation" in output
    assert "Run saved:" not in output


def test_cli_eval_small_live_grid_skips_confirmation(capsys, monkeypatch):
    # A small, explicitly-scoped live run (well under the threshold) proceeds
    # straight to the real provider call without any prompt.
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(
        ["eval", "--models", "openai", "--scenario-ids", "scn_v1_a1_trap", "--seeds", "1"]
    )

    output = capsys.readouterr().out
    assert status == 2  # fails on the missing API key, not the confirmation gate
    assert "Refusing to run" not in output
    assert "Cannot start eval: Provide an OpenAI API key" in output


def test_cli_eval_dry_run_all_skips_confirmation(capsys):
    # --dry-run is offline and free, so even '--models all' runs unprompted.
    status = main(["eval", "--models", "all", "--dry-run", "--scenario-ids", "scn_v1_a1_trap", "--seeds", "1"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Refusing to run" not in output
    assert "Run saved:" in output


def test_cli_phase2_eval_large_grid_aborts_without_confirmation(capsys, monkeypatch):
    import app.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(["phase2-eval", "--models", "openai"])

    output = capsys.readouterr().out
    assert status == 2
    assert "Refusing to run this live Phase 2 eval without confirmation" in output


def _phase2_args(**overrides):
    import argparse

    # Must carry every attribute _phase2_grid_size reads: a missing one raises
    # AttributeError inside its try, which is swallowed into a (0, "") estimate
    # rather than an error — so an out-of-date helper here silently turns a real
    # assertion into "the grid could not be sized".
    defaults = dict(
        models=None, conditions=None, framings=None, urgencies=None,
        user_availabilities=None, scenario_ids=None, scenario_set=None, seeds=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_phase2_grid_size_counts_the_real_scenario_set():
    # Regression: this defaulted to a hardcoded 250 while the v2 set has held
    # 226 since the 2026-07-24 trim, so the confirmation prompt quoted a run
    # ~10.6% larger than the one being approved -- and quoted 250 no matter
    # which --scenario-set was passed.
    from app.cli import _phase2_grid_size

    episodes, breakdown = _phase2_grid_size(_phase2_args(models="anthropic", seeds="1"))
    # 226 scenarios x 6 conditions x 2 framings x 1 urgency x 1 seed x 1 model.
    assert episodes == 226 * 6 * 2
    assert "226 scenario(s)" in breakdown
    assert "250" not in breakdown

    # An explicit scenario list wins over the set size, deduped.
    episodes, _ = _phase2_grid_size(
        _phase2_args(
            models="anthropic", seeds="1", conditions="no_policy",
            framings="evaluation", scenario_ids="scn_v2_a1_trap,scn_v2_a1_trap",
        )
    )
    assert episodes == 1


def test_phase2_grid_size_defers_on_an_unreadable_scenario_set():
    # A bad --scenario-set must not produce a confident wrong estimate; return
    # the "no estimate" sentinel so the run itself raises the real error.
    from app.cli import _phase2_grid_size

    assert _phase2_grid_size(_phase2_args(models="anthropic", scenario_set="no/such/set.md")) == (0, "")
    assert _phase2_grid_size(_phase2_args(models="not-a-real-provider")) == (0, "")


def test_phase2_grid_size_excludes_scripted_agents():
    # Scripted agents run offline, so an all-scripted run costs nothing live.
    from app.cli import _phase2_grid_size

    assert _phase2_grid_size(_phase2_args(models="scripted_diligent", seeds="1")) == (0, "")
