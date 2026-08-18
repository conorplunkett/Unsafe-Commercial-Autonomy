import fcntl
import os
import pty
import struct
import termios

from app.cli import (
    _format_rate,
    _print_human_axes,
    _print_result_details,
    _print_verdicts_and_failures,
    _ProgressBar,
    main,
)


def test_format_rate_reports_na_when_nothing_scored():
    # Regression: an all-unscored group still carries a zeroed (not missing)
    # CI dict, so a truthiness check on the dict alone printed "0.000" next
    # to a real number instead of admitting nothing was scored yet.
    unscored = {
        "unsafe_payment_rate": 0.0,
        "unsafe_payment_ci": {"count": 0, "total": 0, "rate": 0.0, "ci_low": 0.0, "ci_high": 0.0},
    }
    assert _format_rate(unscored, "unsafe_payment") == "n/a"

    scored = {
        "unsafe_payment_rate": 0.25,
        "unsafe_payment_ci": {"count": 1, "total": 4, "rate": 0.25, "ci_low": 0.01, "ci_high": 0.65},
    }
    assert _format_rate(scored, "unsafe_payment") == "0.250 [0.010, 0.650]"


def _floor_metrics(source: str) -> dict:
    return {
        "over_refusal_vs_floor": {
            "floor": {"rate": 0.55, "source": source},
            "refused_clean_rate": 0.6,
            "excess": 0.05,
        }
    }


def test_print_human_axes_flags_a_phase1_fallback_floor(capsys):
    # A Phase 2 run without its own floor yet borrows Phase 1's -- silently
    # doing so is the bug (indistinguishable from Phase 2's own number).
    _print_human_axes(_floor_metrics("phase1_fallback"))
    assert "[Phase 1, provisional]" in capsys.readouterr().out


def test_print_human_axes_does_not_flag_a_runs_own_floor(capsys):
    _print_human_axes(_floor_metrics("phase2"))
    assert "[Phase 1, provisional]" not in capsys.readouterr().out

    _print_human_axes(_floor_metrics("phase1"))
    assert "[Phase 1, provisional]" not in capsys.readouterr().out


def test_print_verdicts_and_failures_splits_keyed_from_unkeyed(capsys):
    # Regression: a run mixing keyed and dropped results used to print one
    # flat "Verdicts: unsafe=2 ..." line, indistinguishable from a run where
    # both unsafe verdicts were actually scored -- the exact overstatement
    # this bug is about.
    metrics = {
        "verdict_counts": {"unsafe": 2},
        "verdict_counts_keyed": {"unsafe": 1},
        "verdict_counts_unkeyed": {"unsafe": 1},
    }
    _print_verdicts_and_failures(metrics)
    output = capsys.readouterr().out
    assert "Verdicts (keyed):     unsafe=1" in output
    assert "Verdicts (dropped, not scored): unsafe=1" in output
    # The old undifferentiated line must not also appear -- that would just
    # restore the double-counted read alongside the new one.
    assert "Verdicts:     unsafe=2" not in output


def test_print_verdicts_and_failures_stays_single_line_when_fully_keyed(capsys):
    # The common case (nothing dropped in this run) keeps the original
    # one-line format -- nothing to split.
    metrics = {
        "verdict_counts": {"unsafe": 2, "safe": 1},
        "verdict_counts_keyed": {"unsafe": 2, "safe": 1},
        "verdict_counts_unkeyed": {},
    }
    _print_verdicts_and_failures(metrics)
    output = capsys.readouterr().out
    assert "Verdicts:     unsafe=2  safe=1" in output
    assert "keyed" not in output


def test_print_verdicts_and_failures_handles_metrics_without_split_fields(capsys):
    # A run's metrics saved before this fix landed carries no
    # verdict_counts_keyed/verdict_counts_unkeyed at all -- must fall back to
    # the flat line instead of crashing.
    metrics = {"verdict_counts": {"safe": 3}}
    _print_verdicts_and_failures(metrics)
    assert "Verdicts:     safe=3" in capsys.readouterr().out


def test_print_result_details_marks_unkeyed_rows(capsys):
    # Regression: the per-row detail table gave no visual signal that a row's
    # verdict rests on a dropped scenario and is excluded from the headline
    # rates -- indistinguishable from a fully-keyed row.
    results = [
        {
            "scenario_id": "scn_v1_a4_lookalike",
            "control_condition": "no_policy",
            "seed": 1,
            "verdict": "unsafe",
            "answer_key_status": "dropped",
        },
        {
            "scenario_id": "scn_v2_a1_trap",
            "control_condition": "no_policy",
            "seed": 1,
            "verdict": "unsafe",
            "answer_key_status": "objective",
        },
    ]
    _print_result_details(results)
    output = capsys.readouterr().out
    row_lines = {
        line.split()[0]: line
        for line in output.splitlines()
        if line.split() and line.split()[0].startswith("scn_")
    }
    assert " * " in row_lines["scn_v1_a4_lookalike"]
    assert " * " not in row_lines["scn_v2_a1_trap"]
    assert "not scored in the headline rates" in output


def test_print_result_details_omits_legend_when_nothing_unkeyed(capsys):
    results = [
        {
            "scenario_id": "scn_v2_a1_trap",
            "control_condition": "no_policy",
            "seed": 1,
            "verdict": "unsafe",
            "answer_key_status": "objective",
        },
    ]
    _print_result_details(results)
    output = capsys.readouterr().out
    assert "*" not in output
    assert "not scored in the headline rates" not in output


def test_print_result_details_does_not_mark_awaiting_survey_rows(capsys):
    # 2026-08-17 policy: awaiting_survey results are scored against the team's
    # provisional key, so they must not carry the unkeyed marker or trigger
    # the "not scored" legend -- only "dropped" does now.
    results = [
        {
            "scenario_id": "scn_v2_a4_trap",
            "control_condition": "no_policy",
            "seed": 1,
            "verdict": "unsafe",
            "answer_key_status": "awaiting_survey",
        },
    ]
    _print_result_details(results)
    output = capsys.readouterr().out
    assert "*" not in output
    assert "not scored in the headline rates" not in output


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


def test_phase1_grid_size_defaults_seeds_to_one():
    # No --seeds passed (None) must price against the real default (one seed,
    # 2026-08-11), not a stale assumption -- this is the number a human
    # approves live spend against, so it can't silently drift from DEFAULT_SEEDS.
    from app.cli import _phase1_grid_size

    total, breakdown = _phase1_grid_size(["openai"], None, ["scn_v1_a1_trap"], None, None)
    assert total == 1 * 3 * 1 * 1  # 1 model x default 3 conditions x 1 scenario x 1 seed
    assert "1 seed(s)" in breakdown


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
    # is already a 150-call grid (50 scenarios x 3 conditions x 1 seed), so it
    # must abort (exit 2) with no TTY, before touching any provider -- this is
    # the "full grid" case, not just an explicit --models all.
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


def test_cli_phase2_eval_checkpoints_and_resumes(capsys, monkeypatch, tmp_path):
    """The whole resume path through the CLI: run, lose the tail, pick it up."""
    import app.cli as cli
    from app.phase2.checkpoint import CheckpointStore

    monkeypatch.setenv("RUN_CHECKPOINT_DIR", str(tmp_path))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    argv = [
        "phase2-eval", "--models", "scripted_naive",
        "--scenario-ids", "scn_v2_a1_trap,scn_v2_a1_lookalike",
        "--conditions", "no_policy", "--framings", "deployment", "--seeds", "1,2",
    ]
    assert main(argv) == 0
    capsys.readouterr()

    run_id = next(path.stem for path in tmp_path.glob("*.jsonl"))
    path = tmp_path / f"{run_id}.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:3]) + "\n")  # header + 2

    assert main(argv + ["--resume", run_id]) == 0
    output = capsys.readouterr().out
    assert f"Resuming {run_id}: 2 episodes restored." in output
    assert f"{run_id}.json" in output  # saved under the original id
    _, restored = CheckpointStore(run_id, root=tmp_path).load()
    assert len(restored) == 4


def test_cli_phase2_eval_resume_without_a_checkpoint_is_refused(capsys, monkeypatch, tmp_path):
    import app.cli as cli

    monkeypatch.setenv("RUN_CHECKPOINT_DIR", str(tmp_path))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    status = main(
        ["phase2-eval", "--models", "scripted_naive", "--scenario-ids", "scn_v2_a1_trap",
         "--seeds", "1", "--resume", "run_nope"]
    )
    output = capsys.readouterr().out
    assert status == 2
    assert "Cannot resume: No checkpoint for run run_nope" in output
    assert "'" not in output.splitlines()[0]  # a sentence, not a KeyError repr


def test_cli_phase2_eval_resume_needs_checkpointing_enabled(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("RUN_CHECKPOINT_DIR", str(tmp_path))
    status = main(
        ["phase2-eval", "--models", "scripted_naive", "--scenario-ids", "scn_v2_a1_trap",
         "--seeds", "1", "--resume", "run_x", "--no-checkpoint"]
    )
    assert status == 2
    assert "--resume needs the checkpoint it resumes from" in capsys.readouterr().out


def test_cli_phase2_checkpoints_lists_resumable_runs(capsys, monkeypatch, tmp_path):
    import app.cli as cli

    monkeypatch.setenv("RUN_CHECKPOINT_DIR", str(tmp_path))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert main(["phase2-checkpoints"]) == 1
    assert "No Phase 2 checkpoints found." in capsys.readouterr().out

    main(["phase2-eval", "--models", "scripted_naive", "--scenario-ids", "scn_v2_a1_trap", "--seeds", "1"])
    capsys.readouterr()
    assert main(["phase2-checkpoints"]) == 0
    output = capsys.readouterr().out
    assert next(path.stem for path in tmp_path.glob("*.jsonl")) in output
    assert "--resume" in output



def _phase2_args(**overrides):
    import argparse

    # Must carry every attribute _phase2_grid_size reads: a missing one raises
    # AttributeError inside its try, which is swallowed into a (0, "") estimate
    # rather than an error — so an out-of-date helper here silently turns a real
    # assertion into "the grid could not be sized".
    defaults = dict(
        models=None, conditions=None, framings=None, urgencies=None,
        user_availabilities=None, scenario_ids=None, scenario_set=None, seeds=None,
        split="all",
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
    # 226 scenarios x 1 condition (no_policy default) x 1 framing (deployment default) x 1 urgency x 1 seed x 1 model.
    assert episodes == 226 * 1 * 1
    assert "226 scenario(s)" in breakdown
    assert "250" not in breakdown

    # An explicit scenario list wins over the set size, deduped.
    episodes, _ = _phase2_grid_size(
        _phase2_args(
            models="anthropic", seeds="1", conditions="no_policy",
            framings="deployment", scenario_ids="scn_v2_a1_trap,scn_v2_a1_trap",
        )
    )
    assert episodes == 1


def test_phase2_grid_size_defaults_seeds_to_one():
    # Regression guard for the same class of bug as the 250-vs-226 fix above:
    # the seed count used to be a bare `or 5` literal instead of deriving from
    # DEFAULT_PHASE2_SEEDS, so it silently kept quoting a 5-seed cost estimate
    # after the real default (2026-08-11) dropped to one seed -- a confirmation
    # prompt overstating spend by 5x.
    from app.cli import _phase2_grid_size

    episodes, breakdown = _phase2_grid_size(_phase2_args(models="anthropic", scenario_ids="scn_v2_a1_trap"))
    assert episodes == 1
    assert "1 seed(s)" in breakdown


def test_phase2_grid_size_expands_all_flags_to_their_real_count():
    # Regression (F4): "--conditions all" (and the other *-all axes) counted as
    # a single CSV item instead of resolving to the real condition/level count,
    # so the confirmation prompt quoted a run at 1/4 (or 1/2) of what it would
    # actually spend. A run quoted as 2,260 episodes was really 9,040.
    from app.cli import _phase2_grid_size

    episodes, breakdown = _phase2_grid_size(_phase2_args(models="anthropic", conditions="all", seeds="1,2,3,4,5"))
    # 226 scenarios x 3 conditions x 1 framing (deployment only) x 5 seeds x 1 model.
    assert episodes == 3390
    assert "3 condition(s)" in breakdown

    episodes, _ = _phase2_grid_size(
        _phase2_args(models="anthropic", seeds="1", scenario_ids="scn_v2_a1_trap", framings="all")
    )
    assert episodes == 1  # framing has a single level (deployment) since 2026-08-17

    episodes, _ = _phase2_grid_size(
        _phase2_args(models="anthropic", seeds="1", scenario_ids="scn_v2_a1_trap", urgencies="all")
    )
    assert episodes == 1 * 2  # 1 framing (deployment default) x 2 urgency levels

    episodes, _ = _phase2_grid_size(
        _phase2_args(models="anthropic", seeds="1", scenario_ids="scn_v2_a1_trap", user_availabilities="all")
    )
    assert episodes == 1 * 2  # 1 framing (deployment default) x 2 user-availability levels


def test_phase2_grid_size_defers_on_an_unknown_condition():
    # A typo'd condition must not silently price as "1 condition" (previously
    # it did, since the old code counted CSV items instead of resolving them) --
    # defer to the "no estimate" sentinel so the real run raises the real error.
    from app.cli import _phase2_grid_size

    assert _phase2_grid_size(_phase2_args(models="anthropic", conditions="not_a_real_condition")) == (0, "")


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


def test_cli_eval_split_objective_runs_only_the_objective_half(capsys):
    # --split is the only thing that selects a half: "objective" is a reporting
    # split (metrics.by_semantic_only), not a property of the grid, so without
    # this flag running it means pasting 41 (v1) or 182 (v2) ids by hand.
    status = main(
        ["eval", "--conditions", "no_policy", "--seeds", "1", "--split", "objective", "--dry-run"]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Split: objective — 41 scenario(s)." in output
    assert "Results: 41" in output


def test_cli_eval_split_survey_runs_only_the_surveyed_half(capsys):
    status = main(
        ["eval", "--conditions", "no_policy", "--seeds", "1", "--split", "survey", "--dry-run"]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Split: survey — 9 scenario(s)." in output
    assert "Results: 9" in output


def test_cli_eval_split_follows_the_scenario_set(capsys):
    status = main(
        [
            "eval",
            "--conditions", "no_policy",
            "--seeds", "1",
            "--scenario-set", "data/scenario_sets/v2_250_scenarios.md",
            "--split", "survey",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Split: survey — 44 scenario(s)." in output
    assert "Results: 44" in output


def test_cli_eval_split_narrows_explicit_scenario_ids(capsys):
    status = main(
        [
            "eval",
            "--conditions", "no_policy",
            "--seeds", "1",
            "--scenario-ids", "scn_v1_a4_trap,scn_v1_a2_lookalike",
            "--split", "objective",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    # a4_trap is semantic_only (survey half); a2_lookalike is objective.
    assert "Split: objective — 1 scenario(s)." in output
    assert "Results: 1" in output


def test_cli_eval_split_that_selects_nothing_refuses_to_run(capsys):
    # Empty ids would otherwise fall through to the runner's "no ids means
    # everything" default and silently run the whole set.
    status = main(
        [
            "eval",
            "--scenario-ids", "scn_v1_a2_lookalike",
            "--split", "survey",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 2
    assert "--split survey selected no scenarios" in output
    assert "Run saved:" not in output


def test_cli_phase2_eval_split_runs_one_half(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    status = main(
        [
            "phase2-eval",
            "--models", "scripted_diligent",
            "--conditions", "no_policy",
            "--framings", "deployment",
            "--seeds", "1",
            "--split", "survey",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Split: survey — 44 scenario(s)." in output
    assert "Results: 44" in output


def test_phase2_grid_size_counts_the_split_not_the_whole_set():
    # The confirmation prompt has to quote what --split will actually spend.
    from app.cli import _phase2_grid_size, _resolve_split
    from app.phase2.runner import PHASE2_SCENARIO_SET

    args = _phase2_args(models="anthropic", seeds="1", split="objective")
    scenario_ids = _resolve_split("objective", None, PHASE2_SCENARIO_SET)
    episodes, breakdown = _phase2_grid_size(args, scenario_ids)
    # 182 scenarios x 1 condition (no_policy default) x 1 framing (deployment default).
    assert episodes == 182 * 1 * 1
    assert "182 scenario(s)" in breakdown


def test_phase2_resume_command_line_carries_the_split():
    # A 182-id --scenario-ids list would be unusable; the resume line keeps the
    # flag that produced it instead.
    from app.cli import _resume_command_line

    args = _phase2_args(
        models="anthropic", seeds="1", split="objective",
        temperature=None, reasoning_effort=None, concurrency=1, dry_run=False,
    )
    line = _resume_command_line(args, "run_abc123")
    assert "--split objective" in line

    args.split = "all"
    assert "--split" not in _resume_command_line(args, "run_abc123")


def test_cli_publish_refuses_a_degraded_run_without_the_flag(tmp_path, capsys, monkeypatch):
    import json as _json

    published = {}

    def _fake_publish(run, label=None, progress=None):
        published["run_id"] = run["run_id"]
        return {"run_id": run["run_id"], "label": label, "payload": {"episode_count": 0}}

    monkeypatch.setattr("app.supabase_publish.publish_run", _fake_publish)
    run = {
        "run_id": "run_degraded",
        "metrics": {
            "quality": {"status": "degraded", "reasons": ["52/750 calls failed (6.9%)"]}
        },
        "results": [],
    }
    path = tmp_path / "run.json"
    path.write_text(_json.dumps(run), encoding="utf-8")

    status = main(["publish", "--file", str(path)])
    output = capsys.readouterr().out
    assert status == 1
    assert "degraded" in output
    assert "52/750" in output
    assert not published  # the refusal happened before any network path

    # The explicit override publishes, and says how many episodes went up.
    status = main(["publish", "--file", str(path), "--allow-degraded"])
    output = capsys.readouterr().out
    assert status == 0
    assert published["run_id"] == "run_degraded"
    assert "0 episodes" in output


def test_cli_publish_passes_ok_and_unstamped_runs(tmp_path, capsys, monkeypatch):
    import json as _json

    monkeypatch.setattr(
        "app.supabase_publish.publish_run",
        lambda run, label=None, progress=None: {
            "run_id": run["run_id"],
            "label": label,
            "payload": {"episode_count": len(run.get("results") or [])},
        },
    )
    ok_run = {"run_id": "run_ok", "metrics": {"quality": {"status": "ok"}}, "results": []}
    legacy_run = {"run_id": "run_legacy", "metrics": {}, "results": []}
    for run in (ok_run, legacy_run):
        path = tmp_path / f"{run['run_id']}.json"
        path.write_text(_json.dumps(run), encoding="utf-8")
        assert main(["publish", "--file", str(path)]) == 0
    out = capsys.readouterr().out
    assert "run_ok" in out and "run_legacy" in out


def _legacy_phase2_run(scenario_ids):
    """A real scripted Phase 2 run, rewound to its pre-pair_role stored shape."""
    from app.metrics import compute_metrics
    from app.models import BenchmarkRun, model_to_dict, parse_model
    from app.phase2.runner import run_phase2_evaluation
    from app.phase2.survey import floor_for_phase2

    run = run_phase2_evaluation(
        model_ids=["scripted_naive"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=scenario_ids,
        seeds=[1],
        checkpoint=False,
    )
    payload = model_to_dict(run)
    for result in payload["results"]:
        result.pop("pair_role", None)
    legacy = parse_model(BenchmarkRun, payload)
    legacy.metrics = compute_metrics(legacy.results, floor_fn=floor_for_phase2)
    assert legacy.metrics["unsafe_denominator"] == "all_keyed_legacy"
    return legacy


def test_cli_recompute_backfills_pair_role_and_flips_denominator(tmp_path, monkeypatch, capsys):
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    legacy = _legacy_phase2_run(
        ["scn_v2_a1_trap", "scn_v2_a1_lookalike", "scn_v2_b1_trap", "scn_v2_c6_trap"]
    )
    RunStorage().save(legacy)

    assert main(["recompute", "--all"]) == 0
    out = capsys.readouterr().out
    assert "pair_role backfilled on 4 episode(s)" in out

    stored = RunStorage().read(legacy.run_id)
    # scripted_naive falls for all three traps -- including c6_trap, whose
    # awaiting_survey status scores it under its provisional key exactly like
    # the other two (2026-08-17 policy) -- and the lookalike leaves the
    # headline denominator.
    assert stored.metrics["unsafe_denominator"] == "keyed_traps"
    assert stored.metrics["unsafe_payment_ci"]["total"] == 3
    assert stored.metrics["unsafe_payment_ci"]["count"] == 3
    assert stored.metrics["unsafe_outside_traps_ci"]["total"] == 1
    assert stored.metrics["awaiting_survey_count"] == 1
    assert all(result.pair_role in ("trap", "lookalike") for result in stored.results)
    # The phase2 breakdown block is rebuilt from the stored run's own axes.
    assert list(stored.metrics["phase2"]["by_framing"]) == ["deployment"]


def test_cli_recompute_publish_flag_republishes_with_label(tmp_path, monkeypatch, capsys):
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    published = []
    monkeypatch.setattr(
        "app.supabase_publish.publish_run",
        lambda run, label=None, progress=None: (
            published.append((run["run_id"], label))
            or {
                "run_id": run["run_id"],
                "label": label,
                "payload": {"episode_count": len(run.get("results") or [])},
            }
        ),
    )
    legacy = _legacy_phase2_run(["scn_v2_a1_trap", "scn_v2_a1_lookalike"])
    RunStorage().save(legacy)

    assert main(["recompute", "--run-id", legacy.run_id, "--publish", "--label", "rekeyed"]) == 0
    assert published == [(legacy.run_id, "rekeyed")]
    # What was published is the recomputed shape, not the stored legacy one.
    republished = RunStorage().read(legacy.run_id)
    assert republished.metrics["unsafe_denominator"] == "keyed_traps"


def test_cli_recompute_parses_six_condition_era_runs(tmp_path, monkeypatch, capsys):
    # Runs recorded before the 2026-08-05 condition cut carry approval_gate
    # episodes. The condition can no longer run, but stored runs containing it
    # must still parse, recompute, and republish (read-compat entry in
    # models.ControlCondition).
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    legacy = _legacy_phase2_run(["scn_v2_a1_trap", "scn_v2_a1_lookalike"])
    legacy.results.append(
        legacy.results[0].model_copy(update={"control_condition": "approval_gate"})
    )
    legacy.control_conditions = list(legacy.control_conditions) + ["approval_gate"]
    RunStorage().save(legacy)

    assert main(["recompute", "--all"]) == 0
    stored = RunStorage().read(legacy.run_id)
    assert stored.metrics["unsafe_denominator"] == "keyed_traps"
    assert "approval_gate" in stored.metrics["by_control_condition"]


def test_cli_recompute_all_skips_unparseable_run_and_continues(tmp_path, monkeypatch, capsys):
    import json as _json

    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    good = _legacy_phase2_run(["scn_v2_a1_trap", "scn_v2_a1_lookalike"])
    RunStorage().save(good)
    # A stored run in a shape the current models reject: valid listing fields,
    # invalid episode. It must skip with a message, not kill the sweep.
    (tmp_path / "run_zzz_broken.json").write_text(
        _json.dumps(
            {
                "run_id": "run_zzz_broken",
                "created_at": "2026-01-01T00:00:00+00:00",
                "agent_ids": ["x"],
                "scenario_ids": ["scn_v1_a1_trap"],
                "results": [{"scenario_id": "scn_v1_a1_trap", "verdict": "bogus"}],
                "events": [],
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )

    assert main(["recompute", "--all"]) == 1
    out = capsys.readouterr().out
    assert "Could not load run run_zzz_broken" in out
    assert f"{good.run_id}: pair_role backfilled" in out


def _merge_source_runs(tmp_path):
    """Two stored Phase 1 runs of one gauntlet, differing only by condition."""
    from app.storage import RunStorage
    from tests.test_merge import _run

    storage = RunStorage()
    runs = [
        _run("run_a", "no_policy", created_at="2026-07-01T10:00:00+00:00"),
        _run("run_b", "structured_policy", created_at="2026-07-20T10:00:00+00:00"),
    ]
    for run in runs:
        storage.save(run)
    return runs


def test_cli_merge_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    _merge_source_runs(tmp_path)

    assert main(["merge", "--run-ids", "run_a,run_b", "--out-run-id", "merged_1", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "4 episodes" in out
    assert "Dry run" in out
    assert not RunStorage().exists("merged_1")


def test_cli_merge_writes_a_pooled_run_and_keeps_the_sources(tmp_path, monkeypatch, capsys):
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    _merge_source_runs(tmp_path)

    assert (
        main(["merge", "--run-ids", "run_a,run_b", "--out-run-id", "merged_1", "--yes"]) == 0
    )
    storage = RunStorage()
    merged = storage.read("merged_1")
    assert len(merged.results) == 4
    assert [source.run_id for source in merged.merged_from] == ["run_a", "run_b"]
    assert set(merged.metrics["by_control_condition"]) == {"no_policy", "structured_policy"}
    # Sources are a record, not scratch space.
    assert storage.exists("run_a") and storage.exists("run_b")


def test_cli_merge_refuses_incompatible_runs_before_asking(tmp_path, monkeypatch, capsys):
    from app.storage import RunStorage

    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    runs = _merge_source_runs(tmp_path)
    runs[1].scenario_ids = runs[1].scenario_ids[:1]
    RunStorage().save(runs[1])

    assert main(["merge", "--run-ids", "run_a,run_b", "--out-run-id", "merged_1", "--yes"]) == 1
    out = capsys.readouterr().out
    assert "not one experiment" in out
    assert "different scenario sets" in out
    assert not RunStorage().exists("merged_1")


def test_cli_merge_will_not_overwrite_an_existing_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    _merge_source_runs(tmp_path)

    assert main(["merge", "--run-ids", "run_a,run_b", "--out-run-id", "run_a", "--yes"]) == 1
    assert "already exists" in capsys.readouterr().out


def test_cli_merge_publish_marks_the_sources_superseded(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    _merge_source_runs(tmp_path)
    marked = {}
    monkeypatch.setattr(
        "app.supabase_publish.publish_run",
        lambda run, label=None, progress=None: {
            "run_id": run["run_id"],
            "label": label,
            "payload": {"episode_count": len(run.get("results") or [])},
        },
    )
    monkeypatch.setattr(
        "app.supabase_publish.mark_superseded",
        lambda run_ids, superseded_by=None: marked.update(
            {"ids": list(run_ids), "by": superseded_by}
        )
        or list(run_ids),
    )

    assert (
        main(
            [
                "merge",
                "--run-ids",
                "run_a,run_b",
                "--out-run-id",
                "merged_1",
                "--yes",
                "--publish",
                "--label",
                "stitched",
            ]
        )
        == 0
    )
    assert marked == {"ids": ["run_a", "run_b"], "by": "merged_1"}
    assert "Marked 2 source run(s) superseded" in capsys.readouterr().out


def test_cli_merge_publish_can_leave_the_sources_alone(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    _merge_source_runs(tmp_path)
    calls = []
    monkeypatch.setattr(
        "app.supabase_publish.publish_run",
        lambda run, label=None, progress=None: {
            "run_id": run["run_id"],
            "label": label,
            "payload": {"episode_count": 0},
        },
    )
    monkeypatch.setattr(
        "app.supabase_publish.mark_superseded",
        lambda run_ids, superseded_by=None: calls.append(run_ids) or list(run_ids),
    )

    assert (
        main(
            [
                "merge",
                "--run-ids",
                "run_a,run_b",
                "--out-run-id",
                "merged_1",
                "--yes",
                "--publish",
                "--no-supersede",
            ]
        )
        == 0
    )
    assert calls == []


def test_cli_publish_of_an_unmerged_run_never_supersedes(tmp_path, monkeypatch, capsys):
    import json as _json

    calls = []
    monkeypatch.setattr(
        "app.supabase_publish.publish_run",
        lambda run, label=None, progress=None: {
            "run_id": run["run_id"],
            "label": label,
            "payload": {"episode_count": 0},
        },
    )
    monkeypatch.setattr(
        "app.supabase_publish.mark_superseded",
        lambda run_ids, superseded_by=None: calls.append(run_ids) or list(run_ids),
    )
    path = tmp_path / "run.json"
    path.write_text(_json.dumps({"run_id": "run_plain", "metrics": {}, "results": []}), encoding="utf-8")

    assert main(["publish", "--file", str(path)]) == 0
    assert calls == []
