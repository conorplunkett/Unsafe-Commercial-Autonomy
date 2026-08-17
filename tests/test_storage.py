"""RunStorage serve-path behavior: summary sidecars, light reads, episode reads.

The Lab's loading fix rests on three storage properties — stored run files stay
byte-identical, listings come from sidecar summaries, and served payloads defer
transcripts to a per-episode read — so each is pinned here.
"""

import json
import os

import pytest

from app.storage import SUMMARY_DIRNAME, RunStorage
from tests.test_merge import _run

CREATED_AT = "2026-07-01T10:00:00+00:00"


def _stored_run(tmp_path, monkeypatch, run_id="run_storage_a"):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    storage = RunStorage()
    run = _run(run_id, "no_policy", created_at=CREATED_AT)
    # Give a transcript field real content so stripping is observable
    # (evaluate_phase1_action already fills raw_model_output and audit_events).
    run.results[0].raw_reasoning = "step-by-step thoughts"
    payload = storage.save(run)
    return storage, run, payload


def _paths(tmp_path, run_id):
    return tmp_path / f"{run_id}.json", tmp_path / SUMMARY_DIRNAME / f"{run_id}.json"


def _touch_newer(path, other):
    stat = other.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))


def test_save_writes_sidecar_and_run_file_unchanged(tmp_path, monkeypatch):
    storage, run, payload = _stored_run(tmp_path, monkeypatch)
    run_file, sidecar = _paths(tmp_path, run.run_id)

    # The run file is exactly what save() always wrote — the sidecar is the
    # only new artifact.
    assert run_file.read_text(encoding="utf-8") == json.dumps(payload, indent=2)
    summary = json.loads(sidecar.read_text(encoding="utf-8"))
    assert summary == {
        "run_id": payload["run_id"],
        "created_at": payload["created_at"],
        "agent_ids": payload["agent_ids"],
        "scenario_ids": payload["scenario_ids"],
        "metrics": payload["metrics"],
    }


def test_list_runs_reads_sidecar_not_the_run_file(tmp_path, monkeypatch):
    storage, run, _ = _stored_run(tmp_path, monkeypatch)
    run_file, sidecar = _paths(tmp_path, run.run_id)

    # Garbage the run file; keep the sidecar looking fresh. A listing that
    # parsed run files would blow up here.
    run_file.write_text("{not json", encoding="utf-8")
    _touch_newer(sidecar, run_file)

    [summary] = storage.list_runs()
    assert summary["run_id"] == run.run_id
    assert summary["created_at"] == CREATED_AT


def test_list_runs_backfills_missing_sidecar(tmp_path, monkeypatch):
    storage, run, payload = _stored_run(tmp_path, monkeypatch)
    _, sidecar = _paths(tmp_path, run.run_id)
    sidecar.unlink()

    [summary] = storage.list_runs()
    assert summary["metrics"] == payload["metrics"]
    # Self-healed for pre-sidecar runs.
    assert json.loads(sidecar.read_text(encoding="utf-8"))["run_id"] == run.run_id


def test_list_runs_detects_stale_sidecar(tmp_path, monkeypatch):
    storage, run, payload = _stored_run(tmp_path, monkeypatch)
    run_file, sidecar = _paths(tmp_path, run.run_id)

    # Rewrite the run file without going through save() — the recompute
    # --file path. The mtime rule must route around the stale sidecar.
    changed = dict(payload, created_at="2027-01-01T00:00:00+00:00")
    run_file.write_text(json.dumps(changed, indent=2), encoding="utf-8")
    _touch_newer(run_file, sidecar)

    [summary] = storage.list_runs()
    assert summary["created_at"] == "2027-01-01T00:00:00+00:00"
    assert (
        json.loads(sidecar.read_text(encoding="utf-8"))["created_at"]
        == "2027-01-01T00:00:00+00:00"
    )


def test_list_runs_tolerates_torn_sidecar(tmp_path, monkeypatch):
    storage, run, _ = _stored_run(tmp_path, monkeypatch)
    run_file, sidecar = _paths(tmp_path, run.run_id)
    sidecar.write_text("{torn", encoding="utf-8")
    _touch_newer(sidecar, run_file)

    [summary] = storage.list_runs()
    assert summary["run_id"] == run.run_id
    # Repaired on the way through.
    assert json.loads(sidecar.read_text(encoding="utf-8"))["run_id"] == run.run_id


def test_list_runs_missing_summary_key_still_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    storage = RunStorage()
    (tmp_path / "run_no_metrics.json").write_text(
        json.dumps(
            {
                "run_id": "run_no_metrics",
                "created_at": CREATED_AT,
                "agent_ids": [],
                "scenario_ids": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError):
        storage.list_runs()


def test_delete_removes_sidecar_and_tolerates_missing_one(tmp_path, monkeypatch):
    storage, run, _ = _stored_run(tmp_path, monkeypatch)
    run_file, sidecar = _paths(tmp_path, run.run_id)

    storage.delete(run.run_id)
    assert not run_file.exists()
    assert not sidecar.exists()

    storage.save(run)
    sidecar.unlink()
    storage.delete(run.run_id)
    assert not run_file.exists()


def test_read_light_strips_heavy_fields_and_stamps_episode_index(tmp_path, monkeypatch):
    storage, run, payload = _stored_run(tmp_path, monkeypatch)

    light = storage.read_light(run.run_id)
    assert light["events"] == []
    for index, result in enumerate(light["results"]):
        assert result["episode_index"] == index
        assert result["raw_model_output"] is None
        assert result["raw_reasoning"] is None
        assert result["audit_events"] == []
        assert result["action"]["action_type"]
    assert light["metrics"] == payload["metrics"]

    # Serving light never touches the stored file.
    raw = storage.read_raw(run.run_id)
    assert raw["results"][0]["raw_reasoning"] == "step-by-step thoughts"
    assert raw["results"][0]["audit_events"]
    assert raw["events"]


def test_read_light_applies_legacy_aliases(tmp_path, monkeypatch):
    monkeypatch.setenv("RUN_STORAGE_DIR", str(tmp_path))
    storage = RunStorage()
    # A pre-rename stored run: legacy verdict/condition tokens and the old
    # false_refusal field name, written straight to disk.
    (tmp_path / "run_legacy.json").write_text(
        json.dumps(
            {
                "run_id": "run_legacy",
                "created_at": CREATED_AT,
                "agent_ids": ["openai:preflight_check"],
                "scenario_ids": ["scn_v1_a1_lookalike"],
                "control_conditions": ["preflight_check"],
                "results": [
                    {
                        "scenario_id": "scn_v1_a1_lookalike",
                        "scenario_title": "Lookalike",
                        "category": "authorization",
                        "agent_id": "openai",
                        "agent_name": "OpenAI",
                        "action": {"action_type": "ask_approval", "rationale": "Ask."},
                        "verdict": "false_refusal",
                        "false_refusal": True,
                        "control_condition": "preflight_check",
                        "raw_model_output": "legacy transcript",
                    }
                ],
                "events": [{"event_type": "episode"}],
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )

    light = storage.read_light("run_legacy")
    assert light["control_conditions"] == ["required_check"]
    [result] = light["results"]
    assert result["verdict"] == "refused_when_safe"
    assert result["refused_when_safe"] is True
    assert result["control_condition"] == "required_check"
    assert result["raw_model_output"] is None


def test_read_episode_returns_stored_heavy_fields_verbatim(tmp_path, monkeypatch):
    storage, run, payload = _stored_run(tmp_path, monkeypatch)

    episode = storage.read_episode(run.run_id, 0)
    assert episode["episode_index"] == 0
    assert episode["raw_reasoning"] == "step-by-step thoughts"
    assert episode["raw_model_output"] == payload["results"][0]["raw_model_output"]
    assert episode["audit_events"] == payload["results"][0]["audit_events"]
    assert episode["action"] == payload["results"][0]["action"]

    with pytest.raises(IndexError):
        storage.read_episode(run.run_id, len(payload["results"]))
    with pytest.raises(KeyError):
        storage.read_episode("run_missing", 0)
