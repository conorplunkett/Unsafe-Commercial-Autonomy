"""Checkpoint, resume, retry and concurrency for the Phase 2 episode grid.

The paid Phase 2 grid is 12,400 episodes per model, so the failure these guard
against is losing a part-finished run — or burning a cell on a transient 429.
"""

from __future__ import annotations

import json

import pytest

from app.models import parse_model, BenchmarkRun, EvaluationResult
from app.phase2.checkpoint import CheckpointMismatch, CheckpointStore, episode_key, list_checkpoints
from app.phase2.providers import BaseEpisodeProvider, EpisodeResult, ToolLoopProvider
from app.phase2.runner import run_phase2_evaluation
from app.providers import ProviderError, RunAbortedError

PAIR_IDS = ["scn_v2_a1_trap", "scn_v2_a1_lookalike"]
GRID = dict(
    model_ids=["scripted_naive"],
    control_conditions=["no_policy", "tool_constraints"],
    framings=["deployment"],
    scenario_ids=PAIR_IDS,
    seeds=[1, 2],
)  # 8 episodes


def _checkpoint_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_every_episode_is_checkpointed_as_it_finishes(tmp_path):
    run = run_phase2_evaluation(run_id="run_ck1", checkpoint_root=tmp_path, **GRID)
    lines = _checkpoint_lines(tmp_path / "run_ck1.jsonl")
    assert lines[0]["record"] == "header"
    assert len(lines) == 1 + len(run.results) == 9
    assert {tuple(line["key"][:2]) for line in lines[1:]} == {
        ("scripted_naive", "no_policy"),
        ("scripted_naive", "tool_constraints"),
    }


def test_checkpoint_survives_a_crash_partway_through(tmp_path):
    """A provider that dies mid-grid still leaves everything before it banked."""

    class DyingProvider(BaseEpisodeProvider):
        provider_id = "dying"
        model_name = "dying"

        def __init__(self):
            self.calls = 0

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            self.calls += 1
            if self.calls > 3:
                raise RuntimeError("process died")
            return EpisodeResult(raw_outputs=["ok"])

    with pytest.raises(RuntimeError):
        run_phase2_evaluation(
            run_id="run_ck2",
            checkpoint_root=tmp_path,
            provider_factory=lambda model_id, live: DyingProvider(),
            **GRID,
        )
    lines = _checkpoint_lines(tmp_path / "run_ck2.jsonl")
    assert len(lines) == 1 + 3  # header + the three episodes that finished


def test_resume_only_runs_the_missing_cells(tmp_path):
    calls = {"n": 0}

    class CountingProvider(BaseEpisodeProvider):
        provider_id = "counting"
        model_name = "counting"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            calls["n"] += 1
            if calls["n"] > 5:
                raise RuntimeError("stop")
            return EpisodeResult(raw_outputs=["ok"])

    factory = lambda model_id, live: CountingProvider()  # noqa: E731
    with pytest.raises(RuntimeError):
        run_phase2_evaluation(
            run_id="run_ck3", checkpoint_root=tmp_path, provider_factory=factory, **GRID
        )
    assert calls["n"] == 6  # five banked, the sixth raised

    calls["n"] = 0
    run = run_phase2_evaluation(
        run_id="run_ck3", checkpoint_root=tmp_path, resume=True, provider_factory=factory, **GRID
    )
    assert calls["n"] == 3  # only the three that never finished
    assert len(run.results) == 8


def test_resume_reruns_errored_cells_but_not_clean_ones(tmp_path):
    """A rate-limit cascade is the main reason to resume, so its casualties
    must not be restored as permanent errors."""
    attempts = {"n": 0}

    class FlakyProvider(BaseEpisodeProvider):
        provider_id = "flaky"
        model_name = "flaky"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            attempts["n"] += 1
            if attempts["n"] > 4:
                return EpisodeResult(error="429 rate limited")
            return EpisodeResult(raw_outputs=["ok"])

    factory = lambda model_id, live: FlakyProvider()  # noqa: E731
    first = run_phase2_evaluation(
        run_id="run_ck4", checkpoint_root=tmp_path, provider_factory=factory, **GRID
    )
    assert sum(1 for result in first.results if result.error) == 4

    attempts["n"] = 0  # the link came back
    resumed = run_phase2_evaluation(
        run_id="run_ck4", checkpoint_root=tmp_path, resume=True, provider_factory=factory, **GRID
    )
    assert len(resumed.results) == 8
    assert not any(result.error for result in resumed.results)


def test_resume_refuses_a_different_grid(tmp_path):
    run_phase2_evaluation(run_id="run_ck5", checkpoint_root=tmp_path, **GRID)
    narrower = dict(GRID, scenario_ids=[PAIR_IDS[0]])
    with pytest.raises(CheckpointMismatch):
        run_phase2_evaluation(
            run_id="run_ck5", checkpoint_root=tmp_path, resume=True, **narrower
        )


def test_resume_refuses_a_different_enforcement_scope(tmp_path):
    """The scope decides which scenarios the enforced arm runs, so it is a grid
    axis like the rest: resuming across it would mix two designs in one run."""
    run_phase2_evaluation(run_id="run_ck5b", checkpoint_root=tmp_path, **GRID)
    header, _ = CheckpointStore("run_ck5b", root=tmp_path).load()
    assert header["grid"]["enforcement_scope"] == "rail_reachable"

    with pytest.raises(CheckpointMismatch) as excinfo:
        run_phase2_evaluation(
            run_id="run_ck5b",
            checkpoint_root=tmp_path,
            resume=True,
            **dict(GRID, enforcement_scope="all"),
        )
    assert "enforcement_scope" in str(excinfo.value)


def test_resume_tolerates_a_torn_final_write(tmp_path):
    """kill -9 mid-flush leaves a partial line; it must cost one episode, not
    the resume, and must not corrupt the record appended after it."""
    run_phase2_evaluation(run_id="run_ck6", checkpoint_root=tmp_path, **GRID)
    path = tmp_path / "run_ck6.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:5]) + '\n{"record": "episode", "key": ["scr')

    run = run_phase2_evaluation(run_id="run_ck6", checkpoint_root=tmp_path, resume=True, **GRID)
    assert len(run.results) == 8
    _, restored = CheckpointStore("run_ck6", root=tmp_path).load()
    assert len(restored) == 8


def test_resume_reproduces_the_uninterrupted_run(tmp_path):
    full = run_phase2_evaluation(run_id="run_ck7", checkpoint_root=tmp_path, **GRID)
    path = tmp_path / "run_ck7.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:4]) + "\n")
    resumed = run_phase2_evaluation(run_id="run_ck7", checkpoint_root=tmp_path, resume=True, **GRID)

    assert [result.model_dump(mode="json") for result in resumed.results] == [
        result.model_dump(mode="json") for result in full.results
    ]
    assert resumed.events == full.events


def test_no_checkpoint_writes_nothing(tmp_path):
    run_phase2_evaluation(run_id="run_ck8", checkpoint_root=tmp_path, checkpoint=False, **GRID)
    assert not (tmp_path / "run_ck8.jsonl").exists()


def test_list_checkpoints_reports_resumable_runs(tmp_path):
    run_phase2_evaluation(run_id="run_ck9", checkpoint_root=tmp_path, **GRID)
    entries = list_checkpoints(root=tmp_path)
    assert [entry["run_id"] for entry in entries] == ["run_ck9"]
    assert entries[0]["episodes"] == 8
    assert entries[0]["errored"] == 0


def test_load_drops_an_episode_row_naming_a_removed_condition(tmp_path):
    """approval_gate was cut outright on 2026-08-08 (unlike preflight_check,
    which was renamed to required_check with a read-time alias), so a
    checkpoint written before the cut can still have a row naming it. Loading
    one must drop that row instead of crashing on the whole file."""
    store = CheckpointStore("run_ck_removed_condition", root=tmp_path)
    store.open(
        {
            "run_id": "run_ck_removed_condition",
            "live": True,
            "temperature": 0.7,
            "reasoning_effort": None,
            "grid": {},
        }
    )
    store.append(
        episode_key("openai", "no_policy", "deployment", "none", "none", PAIR_IDS[0], 1),
        parse_model(
            EvaluationResult,
            dict(
                scenario_id=PAIR_IDS[0],
                scenario_title="A1 trap",
                category="spend_limits",
                agent_id="openai:no_policy",
                agent_name="gpt / no policy",
                action={"action_type": "refuse", "rationale": "n/a"},
                verdict="safe",
                control_condition="no_policy",
            ),
        ),
    )
    store.close()
    legacy_row = {
        "record": "episode",
        "key": list(episode_key("openai", "approval_gate", "deployment", "none", "none", PAIR_IDS[0], 2)),
        "result": {
            "scenario_id": PAIR_IDS[0],
            "scenario_title": "A1 trap",
            "category": "spend_limits",
            "agent_id": "openai:approval_gate",
            "agent_name": "gpt / approval gate",
            "action": {"action_type": "ask_approval", "approval_requested": True, "rationale": "n/a"},
            "verdict": "safe",
            "control_condition": "approval_gate",
        },
    }
    path = tmp_path / "run_ck_removed_condition.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(legacy_row) + "\n")

    header, restored = CheckpointStore("run_ck_removed_condition", root=tmp_path).load()
    assert len(restored) == 1  # only the no_policy row survives

    entries = list_checkpoints(root=tmp_path)
    assert entries[0]["run_id"] == "run_ck_removed_condition"
    assert entries[0]["episodes"] == 1


def test_load_tolerates_a_result_payload_missing_raw_reasoning(tmp_path):
    """raw_reasoning (app/models.py) postdates plenty of on-disk checkpoints.
    It is Optional with a None default precisely so a pre-cutover row like
    this one -- the key absent from "result" entirely, not merely null --
    still loads instead of tripping the ValidationError guard in
    CheckpointStore.load()."""
    store = CheckpointStore("run_ck_no_raw_reasoning", root=tmp_path)
    store.open(
        {
            "run_id": "run_ck_no_raw_reasoning",
            "live": True,
            "temperature": 0.7,
            "reasoning_effort": None,
            "grid": {},
        }
    )
    store.close()
    legacy_row = {
        "record": "episode",
        "key": list(episode_key("openai", "no_policy", "deployment", "none", "none", PAIR_IDS[0], 1)),
        "result": {
            "scenario_id": PAIR_IDS[0],
            "scenario_title": "A1 trap",
            "category": "spend_limits",
            "agent_id": "openai:no_policy",
            "agent_name": "gpt / no policy",
            "action": {"action_type": "refuse", "rationale": "n/a"},
            "verdict": "safe",
            "control_condition": "no_policy",
            # No "raw_reasoning" key at all -- the pre-cutover shape.
        },
    }
    path = tmp_path / "run_ck_no_raw_reasoning.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(legacy_row) + "\n")

    _, restored = CheckpointStore("run_ck_no_raw_reasoning", root=tmp_path).load()
    assert len(restored) == 1
    result = next(iter(restored.values()))
    assert result.raw_reasoning is None


def test_consecutive_errors_abort_the_run_but_keep_the_checkpoint(tmp_path):
    class DeadProvider(BaseEpisodeProvider):
        provider_id = "dead"
        model_name = "dead"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            return EpisodeResult(error="503 upstream down")

    with pytest.raises(RunAbortedError) as excinfo:
        run_phase2_evaluation(
            run_id="run_ck10",
            checkpoint_root=tmp_path,
            consecutive_error_limit=3,
            provider_factory=lambda model_id, live: DeadProvider(),
            **GRID,
        )
    assert excinfo.value.consecutive_errors == 3
    assert "--resume run_ck10" in str(excinfo.value)
    # The point of aborting with a checkpoint: nothing already paid for is lost.
    assert len(_checkpoint_lines(tmp_path / "run_ck10.jsonl")) == 1 + 3


def test_scattered_errors_do_not_trip_the_breaker(tmp_path):
    """An outage is contiguous; a blip is not. Mirrors the Phase 1 rule."""

    class BlipProvider(BaseEpisodeProvider):
        provider_id = "blip"
        model_name = "blip"

        def __init__(self):
            self.calls = 0

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            self.calls += 1
            if self.calls % 2:
                return EpisodeResult(error="503 upstream down")
            return EpisodeResult(raw_outputs=["ok"])

    run = run_phase2_evaluation(
        run_id="run_ck11",
        checkpoint_root=tmp_path,
        consecutive_error_limit=3,
        provider_factory=lambda model_id, live: BlipProvider(),
        **GRID,
    )
    assert len(run.results) == 8


def test_concurrent_run_matches_the_serial_one(tmp_path):
    serial = run_phase2_evaluation(run_id="run_ck12", checkpoint_root=tmp_path, **GRID)
    parallel = run_phase2_evaluation(
        run_id="run_ck12", checkpoint_root=tmp_path, concurrency=4, **GRID
    )
    assert [result.model_dump(mode="json") for result in parallel.results] == [
        result.model_dump(mode="json") for result in serial.results
    ]
    assert parallel.events == serial.events


def test_concurrency_gives_each_worker_its_own_provider(tmp_path):
    """Live providers hold per-episode conversation state on the instance, so
    two threads sharing one would interleave into the same conversation."""
    built = []

    class TrackingProvider(BaseEpisodeProvider):
        provider_id = "tracking"
        model_name = "tracking"

        def __init__(self):
            built.append(self)

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            return EpisodeResult(raw_outputs=["ok"])

    run_phase2_evaluation(
        run_id="run_ck13",
        checkpoint_root=tmp_path,
        concurrency=4,
        provider_factory=lambda model_id, live: TrackingProvider(),
        **GRID,
    )
    assert len(built) == 4
    assert len({id(provider) for provider in built}) == 4


def test_checkpointed_run_round_trips_through_storage(tmp_path):
    run = run_phase2_evaluation(run_id="run_ck14", checkpoint_root=tmp_path, **GRID)
    reloaded = parse_model(BenchmarkRun, json.loads(json.dumps(run.model_dump(mode="json"))))
    assert isinstance(reloaded, BenchmarkRun)
    assert len(reloaded.results) == len(run.results)


# ---------------------------------------------------------------------------
# Turn-level retry (the Phase 1 policy applied inside the multi-turn tool loop)
# ---------------------------------------------------------------------------


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


def _wrapped(status):
    """A ProviderError shaped like the ones the real transports raise.

    is_retryable_provider_error reads the HTTP status off the `raise ... from`
    chain, not the wrapper, so the cause has to carry the response.
    """
    cause = RuntimeError("boom")
    cause.response = _Response(status)  # type: ignore[attr-defined]
    error = ProviderError("request failed")
    error.__cause__ = cause
    return error


class _RetryStub(ToolLoopProvider):
    provider_id = "stub"
    model_name = "stub"

    def __init__(self, failures, status=429):
        self.failures = failures
        self.status = status
        self.calls = []
        self.delays = []
        self._sleep = self.delays.append
        self.turn = 0

    def start_conversation(self, system_prompt, user_prompt, tools, temperature):
        pass

    def step(self, tool_results):
        self.calls.append(tool_results)
        if self.failures:
            self.failures -= 1
            raise _wrapped(self.status)
        self.turn += 1
        if self.turn == 1:
            return "", [{"id": "c1", "name": "search_offers", "arguments": {}}]
        return "", [
            {"id": "c2", "name": "finish", "arguments": {"summary": "done", "action_taken": "refused"}}
        ]


def test_transient_failure_is_retried_with_backoff():
    # 5xx-class transients keep the classic short schedule; 429s ride the
    # separate wall-clock budget (tested below).
    provider = _RetryStub(failures=2, status=503)
    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        live=True,
        checkpoint=False,
        provider_factory=lambda model_id, live: provider,
    )
    assert run.results[0].error is None
    assert provider.delays == [0.5, 1.0]  # the shared exponential schedule


def test_retry_does_not_resend_the_pending_turn():
    """Every transport stages tool results into its own conversation state
    before the request, so a retry must re-issue rather than re-append."""
    provider = _RetryStub(failures=0)
    run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        live=True,
        checkpoint=False,
        provider_factory=lambda model_id, live: provider,
    )
    provider.failures = 2
    provider.turn = 0
    provider.calls.clear()
    provider._step_with_retry([{"id": "c1", "content": {"ok": True}}])
    assert provider.calls[0] == [{"id": "c1", "content": {"ok": True}}]
    assert provider.calls[1:] == [None, None]


def test_retry_budget_is_finite():
    provider = _RetryStub(failures=99, status=503)
    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        live=True,
        checkpoint=False,
        provider_factory=lambda model_id, live: provider,
    )
    assert run.results[0].error is not None
    assert len(provider.delays) == 3  # DEFAULT_TRANSIENT_RETRIES


def test_rate_limited_turn_rides_the_minutes_budget():
    # A 429 no longer burns the three short attempts (3.5 s total): the turn
    # keeps retrying on the wall-clock budget with growing waits, and only
    # after minutes of budget does the episode record an error. Waits arrive
    # via the run's shared gate, chunked, so only their sum is asserted.
    provider = _RetryStub(failures=99, status=429)
    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        live=True,
        checkpoint=False,
        provider_factory=lambda model_id, live: provider,
    )
    assert run.results[0].error is not None
    assert len(provider.delays) > 3
    assert sum(provider.delays) >= 300.0


def test_deterministic_errors_are_not_retried():
    """A 400 is a config bug; retrying it three times only burns wall-clock."""
    provider = _RetryStub(failures=99, status=400)
    run = run_phase2_evaluation(
        model_ids=["openai"],
        control_conditions=["no_policy"],
        framings=["deployment"],
        scenario_ids=["scn_v2_a1_trap"],
        seeds=[1],
        live=True,
        checkpoint=False,
        provider_factory=lambda model_id, live: provider,
    )
    assert run.results[0].error is not None
    assert provider.delays == []


def test_missing_checkpoint_reads_as_a_sentence(tmp_path):
    """`Cannot resume: {exc}` goes straight to a terminal, and a bare KeyError
    would render the message wrapped in quotes."""
    from app.phase2.checkpoint import CheckpointMissing

    with pytest.raises(CheckpointMissing) as excinfo:
        CheckpointStore("run_absent", root=tmp_path).load()
    assert str(excinfo.value).startswith("No checkpoint for run run_absent")
    assert isinstance(excinfo.value, KeyError)  # existing handlers still catch it


def test_resume_refuses_a_changed_run_mode(tmp_path):
    # The grid matching is not enough: resuming a checkpoint with different
    # sampling settings would mix two runs in one file. temperature stands in
    # for all header-recorded settings here; live has its own test below.
    run_phase2_evaluation(run_id="run_ck20", checkpoint_root=tmp_path, **GRID)
    with pytest.raises(CheckpointMismatch) as excinfo:
        run_phase2_evaluation(
            run_id="run_ck20", checkpoint_root=tmp_path, resume=True, temperature=0.9, **GRID
        )
    assert "temperature" in str(excinfo.value)


def test_verify_refuses_a_live_dry_mismatch_and_tolerates_legacy_headers(tmp_path):
    # A --dry-run resume of a live checkpoint would splice free fake episodes
    # among the paid real ones, indistinguishable in the finished run file.
    store = CheckpointStore("run_ck21", root=tmp_path)
    store.open(
        {"run_id": "run_ck21", "live": True, "temperature": 0.7, "reasoning_effort": None, "grid": {}}
    )
    store.close()
    with pytest.raises(CheckpointMismatch) as excinfo:
        CheckpointStore("run_ck21", root=tmp_path).verify(
            {}, settings={"live": False, "temperature": 0.7, "reasoning_effort": None}
        )
    assert "live" in str(excinfo.value)
    # Matching settings resume; a field the header never recorded is skipped
    # rather than refused, so pre-settings checkpoints stay resumable.
    CheckpointStore("run_ck21", root=tmp_path).verify(
        {},
        settings={"live": True, "temperature": 0.7, "reasoning_effort": None, "later_field": 1},
    )


def test_verify_refuses_a_checkpoint_with_no_grid_header_at_all(tmp_path):
    # A checkpoint written before grid fingerprinting existed has no "grid"
    # key in its header -- not an empty dict. header.get("grid") or {} used to
    # treat that absence the same as an intentionally-empty (matches-anything)
    # grid, so a legacy checkpoint would silently "verify" against ANY current
    # grid, risking a stale-result key collision on resume instead of the
    # refusal every other mismatch in this function raises.
    store = CheckpointStore("run_ck_legacy", root=tmp_path)
    store.open({"run_id": "run_ck_legacy", "live": True, "temperature": 0.7, "reasoning_effort": None})
    store.close()

    with pytest.raises(CheckpointMismatch) as excinfo:
        CheckpointStore("run_ck_legacy", root=tmp_path).verify(
            {"model_ids": ["openai"]},
            settings={"live": True, "temperature": 0.7, "reasoning_effort": None},
        )
    assert "predates grid fingerprinting" in str(excinfo.value)


def test_auto_stop_halts_queued_episodes_in_the_same_wave(tmp_path):
    # The 8-cell grid is one wave at concurrency 2. When the breaker trips at
    # 2 consecutive errors, episodes already queued in the wave must not start:
    # at most the 2 recorded errors plus one in-flight episode per worker.
    started = []

    class DeadProvider(BaseEpisodeProvider):
        provider_id = "dead"
        model_name = "dead"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            started.append(1)
            return EpisodeResult(error="503 upstream down")

    with pytest.raises(RunAbortedError):
        run_phase2_evaluation(
            run_id="run_ck22",
            checkpoint_root=tmp_path,
            concurrency=2,
            consecutive_error_limit=2,
            provider_factory=lambda model_id, live: DeadProvider(),
            **GRID,
        )
    assert len(started) <= 4  # without the stop signal the whole wave (8) ran


def test_worker_crash_cancels_the_queued_remainder_of_the_wave(tmp_path):
    # A hard crash in one worker (Ctrl-C takes the same path out of the wave
    # loop) must cancel queued futures. The first grid cell crashes instantly,
    # so the main thread cancels while the other worker is still in flight: at
    # most the crasher plus one blocked episode per worker ever start; the
    # queued remainder of the 8-cell wave never does.
    import threading

    started = []
    release = threading.Event()

    class CrashingProvider(BaseEpisodeProvider):
        provider_id = "crashing"
        model_name = "crashing"

        def run_episode(self, world, system_prompt, user_prompt, seed, temperature):
            started.append(1)
            if (
                world.scenario.scenario_id == PAIR_IDS[0]
                and world.control_condition == "no_policy"
                and seed == 1
            ):
                raise RuntimeError("process died")
            release.wait(timeout=5)
            return EpisodeResult(raw_outputs=["ok"])

    # The in-flight survivors unblock shortly after the crash propagates, so
    # executor shutdown can finish.
    threading.Timer(0.3, release.set).start()
    with pytest.raises(RuntimeError):
        run_phase2_evaluation(
            run_id="run_ck23",
            checkpoint_root=tmp_path,
            concurrency=2,
            provider_factory=lambda model_id, live: CrashingProvider(),
            **GRID,
        )
    release.set()
    assert 2 <= len(started) <= 3  # without cancellation all 8 cells ran
