"""Per-episode checkpointing for Phase 2 runs, so a crash costs one episode.

The full grid under the default --pressure-scope headline_only is 6,480
episodes per model (226 scenarios each under no_policy and structured_policy,
166 under tool_constraints, x 5 seeds; only structured_policy crosses the 2
urgencies x 2 user availabilities, the rest run pressure-axis baseline — see
app/phase2/scope.py). --pressure-scope all restores the pre-2026-08-26 full
cross-product, 12,360. Each episode is a tool loop of up to MAX_TURNS provider
calls. Without this the whole run lives in memory until the CLI saves it at
the end, so a Ctrl-C or a rate-limit cascade late in the grid throws away
every dollar already spent. Each finished episode is appended here as one
JSON line and flushed, and `--resume` replays them instead of paying for them
twice.

Deliberately not the run JSON format: RunStorage writes one whole BenchmarkRun
after metrics are computed, which is exactly the thing that cannot happen
mid-run. These two are complementary — the checkpoint is the write-ahead log,
runtime/runs/<run_id>.json is still the artifact.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import ValidationError

from ..data import ROOT_DIR
from ..models import EvaluationResult, model_to_dict, parse_model
from .sandbox import PHASE2_CONTROL_CONDITIONS
from .scope import DEFAULT_ENFORCEMENT_SCOPE, DEFAULT_PRESSURE_SCOPE


# Same shape as the (model, condition, framing, urgency, user_availability,
# scenario, seed) tuple the run's event ids already concatenate, so a
# checkpoint line and an audit event name the same episode.
EpisodeKey = Tuple[str, str, str, str, str, str, int]


def _default_root() -> Path:
    """Where checkpoints live.

    Honors RUN_CHECKPOINT_DIR, then falls back to a sibling of whatever run
    storage is configured — so the test suite's RUN_STORAGE_DIR tmpdir
    (tests/conftest.py) keeps checkpoints hermetic too, and a normal run writes
    to the gitignored runtime/ tree.
    """
    override = os.environ.get("RUN_CHECKPOINT_DIR")
    if override:
        return Path(override)
    run_storage = os.environ.get("RUN_STORAGE_DIR")
    if run_storage:
        return Path(run_storage) / "checkpoints"
    return ROOT_DIR / "runtime" / "checkpoints"


def episode_key(
    model_id: str,
    control_condition: str,
    framing: str,
    urgency: str,
    user_availability: str,
    scenario_id: str,
    seed: int,
) -> EpisodeKey:
    return (model_id, control_condition, framing, urgency, user_availability, scenario_id, int(seed))


def grid_fingerprint(
    model_ids: Iterable[str],
    control_conditions: Iterable[str],
    framings: Iterable[str],
    urgencies: Iterable[str],
    user_availabilities: Iterable[str],
    scenario_ids: Iterable[str],
    seeds: Iterable[int],
    enforcement_scope: str = DEFAULT_ENFORCEMENT_SCOPE,
    pressure_scope: str = DEFAULT_PRESSURE_SCOPE,
) -> Dict[str, Any]:
    """The axes a resume must agree with.

    Sorted, so the fingerprint is about grid *membership* rather than the order
    the axes were typed on the command line. Resuming into a different grid
    would silently mix two experiments in one run file.

    ``enforcement_scope`` and ``pressure_scope`` are axes like the rest: each
    decides which cells a condition actually runs (app/phase2/scope.py), so a
    checkpoint started under one scope cannot be resumed under the other.
    Checkpoints written before a given key existed carry the full
    cross-product and mismatch every current grid, which is the same answer
    any grid change gets — start a fresh run.
    """
    return {
        "model_ids": sorted(model_ids),
        "control_conditions": sorted(control_conditions),
        "framings": sorted(framings),
        "urgencies": sorted(urgencies),
        "user_availabilities": sorted(user_availabilities),
        "scenario_ids": sorted(scenario_ids),
        "seeds": sorted(int(seed) for seed in seeds),
        "enforcement_scope": enforcement_scope,
        "pressure_scope": pressure_scope,
    }


class CheckpointMismatch(Exception):
    """A resume was asked for against a checkpoint of a different grid."""


class CheckpointMissing(KeyError):
    """No checkpoint exists for the run id a resume named.

    Subclasses KeyError so existing `except KeyError` callers still catch it,
    but stringifies as a plain sentence — KeyError's repr would wrap the
    message in quotes on the way to the terminal.
    """

    def __str__(self) -> str:
        return self.args[0] if self.args else ""


class CheckpointStore:
    """Append-only JSONL log of finished episodes for one run."""

    def __init__(self, run_id: str, root: Optional[Path] = None):
        self.run_id = run_id
        self.root = root or _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self._handle = None

    @property
    def path(self) -> Path:
        return self.root / f"{self.run_id}.jsonl"

    def exists(self) -> bool:
        return self.path.exists()

    # -- writing ----------------------------------------------------------

    def open(self, header: Dict[str, Any]) -> "CheckpointStore":
        """Open for append, writing the header if the file is new.

        A run killed mid-flush can leave a final line with no newline. Appending
        straight onto it would glue the next record to the fragment and lose
        that episode too, so terminate the fragment first — load() already skips
        it, and this keeps it to the one episode that was actually in flight.
        """
        is_new = not self.path.exists()
        if not is_new and self._ends_mid_line():
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
        self._handle = self.path.open("a", encoding="utf-8")
        if is_new:
            self._write({"record": "header", "created_at": _now(), **header})
        return self

    def _ends_mid_line(self) -> bool:
        try:
            if self.path.stat().st_size == 0:
                return False
            with self.path.open("rb") as handle:
                handle.seek(-1, os.SEEK_END)
                return handle.read(1) != b"\n"
        except OSError:
            return False

    def append(self, key: EpisodeKey, result: EvaluationResult) -> None:
        self._write({"record": "episode", "key": list(key), "result": model_to_dict(result)})

    def _write(self, payload: Dict[str, Any]) -> None:
        if self._handle is None:
            raise RuntimeError("CheckpointStore.open() must be called before writing")
        self._handle.write(json.dumps(payload) + "\n")
        # Flush and fsync per episode: the whole point is surviving a kill -9,
        # and an episode costs far more than the write does.
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "CheckpointStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- reading ----------------------------------------------------------

    def load(self) -> Tuple[Dict[str, Any], Dict[EpisodeKey, EvaluationResult]]:
        """Return (header, {key: result}) for an existing checkpoint.

        Tolerates a truncated final line: a run killed mid-write leaves a
        partial record, and refusing to resume because of it would defeat the
        purpose. Later records for the same key win, so a re-run episode
        replaces its earlier errored attempt.

        Also tolerates an episode row naming a control condition outside the
        current Phase 2 grid — one removed outright (e.g. "approval_gate",
        cut 2026-08-08, or "required_check", cut 2026-08-17; the
        preflight_check -> required_check *rename* is different and is mapped
        for stored results by models._LEGACY_CONDITION_ALIASES).
        Such a row can no longer be resumed under any current grid, so it is
        dropped like a truncated line instead of crashing the whole read. The
        check is an explicit PHASE2_CONTROL_CONDITIONS membership test on the
        key: it used to fall out of the result failing to parse, which broke
        when "approval_gate" became a read-compat ControlCondition so stored
        *runs* containing it could recompute and republish.
        """
        if not self.path.exists():
            raise CheckpointMissing(f"No checkpoint for run {self.run_id} at {self.path}")
        header: Dict[str, Any] = {}
        restored: Dict[EpisodeKey, EvaluationResult] = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue  # truncated tail from an interrupted write
                if payload.get("record") == "header":
                    header = payload
                elif payload.get("record") == "episode":
                    key = payload["key"]
                    if len(key) > 1 and key[1] not in PHASE2_CONTROL_CONDITIONS:
                        continue  # pre-cutover episode; not resumable in any current grid
                    try:
                        restored[episode_key(*key)] = parse_model(EvaluationResult, payload["result"])
                    except ValidationError:
                        continue  # row in a shape the current models reject
        return header, restored

    def verify(
        self, fingerprint: Dict[str, Any], settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Load, and refuse to resume into a grid — or a run mode — the
        checkpoint isn't from.

        The grid says *what* is being run; ``settings`` says *how* — the
        header fields ``live``, ``temperature`` and ``reasoning_effort``.
        Resuming a live run with --dry-run would splice free fake episodes
        among the paid real ones, indistinguishable in the finished run file,
        and a changed temperature or reasoning effort would silently mix two
        sampling regimes. Any mismatch on a field the header records refuses
        the resume; fields an older checkpoint never recorded are skipped.
        """
        header, restored = self.load()
        if "grid" not in header:
            raise CheckpointMismatch(
                f"Checkpoint {self.path} predates grid fingerprinting (no "
                f"'grid' in its header) and can't be safety-checked against "
                f"the current run. Start a fresh run instead of resuming "
                f"this one."
            )
        stored = header["grid"]
        if stored != fingerprint:
            differing = sorted(
                axis for axis in set(stored) | set(fingerprint)
                if stored.get(axis) != fingerprint.get(axis)
            )
            raise CheckpointMismatch(
                f"Checkpoint {self.path} was written for a different grid "
                f"(differs on: {', '.join(differing)}). Resume with the same "
                f"axes it was started with, or start a fresh run."
            )
        for field, asked in (settings or {}).items():
            if field not in header:
                continue
            recorded = header.get(field)
            if recorded != asked:
                raise CheckpointMismatch(
                    f"Checkpoint {self.path} was written by a run with "
                    f"{field}={recorded!r}; this resume asked for {asked!r}. "
                    f"Resume with the settings the run was started with, or "
                    f"start a fresh run."
                )
        return {"header": header, "restored": restored}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_checkpoints(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Resumable runs, newest first — what `--resume` can be pointed at."""
    root = root or _default_root()
    if not root.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for path in root.glob("*.jsonl"):
        store = CheckpointStore(path.stem, root=root)
        try:
            header, restored = store.load()
        except (CheckpointMissing, OSError):
            continue
        entries.append(
            {
                "run_id": path.stem,
                "created_at": header.get("created_at", ""),
                "episodes": len(restored),
                "errored": sum(1 for result in restored.values() if result.error),
                "path": str(path),
            }
        )
    return sorted(entries, key=lambda entry: entry["created_at"], reverse=True)
