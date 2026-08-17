from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data import ROOT_DIR
from .models import BenchmarkRun, model_to_dict, parse_model


def _default_root() -> Path:
    override = os.environ.get("RUN_STORAGE_DIR")
    if override:
        return Path(override)
    return ROOT_DIR / "runtime" / "runs"


# Summary sidecars live in a subdirectory so list_runs()'s glob("*.json") over
# the storage root never mistakes one for a run file (the same reason the
# phase2 checkpoints subdirectory can live under the storage root).
SUMMARY_DIRNAME = "_summaries"

# The per-result fields that dominate a stored run's size: joined model
# transcripts and the tool-call audit trail. The Lab dashboard reads them only
# in the single-episode detail panel, so the light serve path strips them and
# /api/runs/{run_id}/results/{episode_index} serves them per episode instead.
HEAVY_RESULT_FIELDS = ("raw_model_output", "raw_reasoning", "audit_events")

_SUMMARY_KEYS = ("run_id", "created_at", "agent_ids", "scenario_ids", "metrics")


class RunStorage:
    def __init__(self, root: Path | None = None):
        self.root = root or _default_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def _summary_path(self, run_id: str) -> Path:
        return self.root / SUMMARY_DIRNAME / f"{run_id}.json"

    @staticmethod
    def _pluck_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "run_id": payload["run_id"],
            "created_at": payload["created_at"],
            "agent_ids": payload["agent_ids"],
            "scenario_ids": payload["scenario_ids"],
            "metrics": payload["metrics"],
        }

    def _write_summary_sidecar(self, run_id: str, summary: Dict[str, Any]) -> None:
        # Best-effort on purpose: the sidecar is a cache, so a read-only or
        # full disk must never turn a successful save or listing into an error.
        try:
            path = self._summary_path(run_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        except OSError:
            pass

    def _fresh_summary(self, run_path: Path) -> Optional[Dict[str, Any]]:
        """The sidecar summary for a run file, or None when it can't be trusted."""
        sidecar = self.root / SUMMARY_DIRNAME / run_path.name
        try:
            # >= rather than >: save() writes the run file first and the
            # sidecar second, so an untouched pair always passes. A run file
            # rewritten without going through save() (recompute --file) lands
            # newer than its sidecar and falls through to the full parse.
            if sidecar.stat().st_mtime_ns < run_path.stat().st_mtime_ns:
                return None
            with sidecar.open("r", encoding="utf-8") as handle:
                summary = json.load(handle)
        except (OSError, ValueError):
            # Missing, unreadable, or torn sidecar — treat as stale.
            return None
        if not isinstance(summary, dict) or any(key not in summary for key in _SUMMARY_KEYS):
            return None
        return {key: summary[key] for key in _SUMMARY_KEYS}

    def save(self, run: BenchmarkRun) -> Dict[str, Any]:
        payload = model_to_dict(run)
        with self._path(run.run_id).open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        # Run file first, sidecar second, so the sidecar's mtime is >= the run
        # file's — exactly the freshness rule _fresh_summary checks.
        self._write_summary_sidecar(run.run_id, self._pluck_summary(payload))
        return payload

    def exists(self, run_id: str) -> bool:
        return self._path(run_id).exists()

    def read(self, run_id: str) -> BenchmarkRun:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Run {run_id} not found")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return parse_model(BenchmarkRun, payload)

    def read_raw(self, run_id: str) -> Dict[str, Any]:
        """The stored payload as plain JSON, skipping Pydantic entirely.

        Serve-path helper: no validation also means none of the legacy field
        aliasing read() applies, so these dicts must not be handed to code
        expecting normalized field names.
        """
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Run {run_id} not found")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _stamp_episode_indices(payload: Dict[str, Any]) -> Dict[str, Any]:
        # Position in the stored results list is the canonical episode address
        # (the same one supabase_publish uses for episode rows). Stamped on
        # served copies only — never persisted, so run files stay byte-stable.
        for index, result in enumerate(payload.get("results") or []):
            result["episode_index"] = index
        return payload

    def read_light(self, run_id: str) -> Dict[str, Any]:
        """The run as served to the Lab: transcripts and event stream stripped.

        The slimmed payload still goes through Pydantic so the legacy aliases
        (false_refusal -> refused_when_safe, renamed verdicts and conditions)
        apply to the fields the Lab reads — validation is cheap once the heavy
        fields never reach it.
        """
        payload = self.read_raw(run_id)
        # events duplicates the results' own audit trails and the Lab never
        # reads it. [] rather than del: BenchmarkRun requires the key.
        payload["events"] = []
        for result in payload.get("results") or []:
            if isinstance(result, dict):
                for field in HEAVY_RESULT_FIELDS:
                    result.pop(field, None)
        run = parse_model(BenchmarkRun, payload)
        return self._stamp_episode_indices(model_to_dict(run))

    def read_full_dict(self, run_id: str) -> Dict[str, Any]:
        return self._stamp_episode_indices(model_to_dict(self.read(run_id)))

    def read_episode(self, run_id: str, index: int) -> Dict[str, Any]:
        """The deferred fields of one stored episode, verbatim from disk.

        No Pydantic pass, so action/proposed_action may carry legacy tokens on
        old runs — clients should merge only the transcript fields and keep
        the aliased copies from the light payload for everything else.
        """
        results = self.read_raw(run_id).get("results")
        if not isinstance(results, list) or not 0 <= index < len(results):
            raise IndexError(f"Episode {index} not found in run {run_id}")
        result = results[index]
        return {
            "episode_index": index,
            "action": result.get("action"),
            "proposed_action": result.get("proposed_action"),
            "raw_model_output": result.get("raw_model_output"),
            "raw_reasoning": result.get("raw_reasoning"),
            "audit_events": result.get("audit_events") or [],
        }

    def delete(self, run_id: str) -> None:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Run {run_id} not found")
        path.unlink()
        self._summary_path(run_id).unlink(missing_ok=True)

    def list_runs(self) -> List[Dict[str, Any]]:
        summaries: List[Dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            summary = self._fresh_summary(path)
            if summary is None:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                summary = self._pluck_summary(payload)
                # Self-heal: pre-sidecar runs and direct rewrites (recompute
                # --file) get their sidecar (re)built on the next listing.
                self._write_summary_sidecar(path.stem, summary)
            summaries.append(summary)
        return sorted(summaries, key=lambda item: item["created_at"], reverse=True)

    def latest(self) -> BenchmarkRun:
        runs = self.list_runs()
        if not runs:
            raise KeyError("No benchmark runs found")
        return self.read(runs[0]["run_id"])
