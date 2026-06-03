from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .data import ROOT_DIR
from .models import BenchmarkRun, model_to_dict, parse_model


class RunStorage:
    def __init__(self, root: Path | None = None):
        self.root = root or ROOT_DIR / "runtime" / "runs"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def save(self, run: BenchmarkRun) -> Dict[str, Any]:
        payload = model_to_dict(run)
        with self._path(run.run_id).open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return payload

    def read(self, run_id: str) -> BenchmarkRun:
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Run {run_id} not found")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return parse_model(BenchmarkRun, payload)

    def list_runs(self) -> List[Dict[str, Any]]:
        summaries: List[Dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            summaries.append(
                {
                    "run_id": payload["run_id"],
                    "created_at": payload["created_at"],
                    "agent_ids": payload["agent_ids"],
                    "scenario_ids": payload["scenario_ids"],
                    "metrics": payload["metrics"],
                }
            )
        return sorted(summaries, key=lambda item: item["created_at"], reverse=True)

    def latest(self) -> BenchmarkRun:
        runs = self.list_runs()
        if not runs:
            raise KeyError("No benchmark runs found")
        return self.read(runs[0]["run_id"])

