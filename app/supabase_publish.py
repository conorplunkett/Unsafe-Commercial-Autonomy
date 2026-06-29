"""Publish benchmark runs to Supabase for the public "Official run" dashboard.

This is the *upload* half of the results pipeline. The harness runs experiments
locally and stores each run under ``runtime/runs/``; the ``publish`` CLI command
(see ``app/cli.py``) then pushes a chosen run into a Supabase ``benchmark_runs``
table that the static site reads.

Only deliberately published runs land here. The "Run it yourself" flow on the
site stays local to whoever ran it and is never written to Supabase.

Writes use the Supabase *service-role* key, which must be kept server-side and
is read from the environment, never committed. The site reads with the
publishable (anon) key, which is safe to embed because row-level security on the
table only grants public SELECT.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

DEFAULT_TABLE = "benchmark_runs"


class SupabasePublishError(RuntimeError):
    """Raised when a run cannot be published (missing config or API error)."""


def _config() -> tuple[str, str, str]:
    """Resolve (base_url, service_key, table) from the environment."""
    url = os.environ.get("SUPABASE_URL")
    # Accept either name; the service-role key is the secret write credential.
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    table = os.environ.get("SUPABASE_BENCHMARK_TABLE", DEFAULT_TABLE)
    if not url:
        raise SupabasePublishError(
            "SUPABASE_URL is not set. Export it (and SUPABASE_SERVICE_KEY) before publishing."
        )
    if not key:
        raise SupabasePublishError(
            "SUPABASE_SERVICE_KEY is not set. Use the service-role key from "
            "Supabase > Project Settings > API; keep it out of version control."
        )
    return url.rstrip("/"), key, table


def model_names_from_run(run: Dict[str, Any]) -> list:
    """Distinct model names for a run, robust to older payload shapes.

    Prefers the first-class ``model_names`` field; falls back to the per-result
    model names, then to the ``by_model_name`` metric keys, so a run published
    before model identity was first-class still lands a usable value.
    """
    names = run.get("model_names")
    if names:
        return list(names)
    seen: Dict[str, None] = {}
    for result in run.get("results") or []:
        name = result.get("model_name") if isinstance(result, dict) else None
        if name and name not in seen:
            seen[name] = None
    if seen:
        return list(seen)
    by_model_name = (run.get("metrics") or {}).get("by_model_name") or {}
    return list(by_model_name)


def row_from_run(run: Dict[str, Any], label: Optional[str] = None) -> Dict[str, Any]:
    """Shape a stored BenchmarkRun dict into a ``benchmark_runs`` row.

    The full run is kept in ``payload`` so the dashboard can render it exactly as
    a local run; a few fields are lifted out for listing and ordering.
    ``model_ids`` holds the provider/config selectors ("openai"); ``model_names``
    holds the actual models ("gpt-5.4-mini") so the table is queryable per model.
    """
    if not run.get("run_id"):
        raise SupabasePublishError("Run payload is missing a run_id.")
    return {
        "run_id": run["run_id"],
        "created_at": run.get("created_at"),
        "phase": run.get("phase"),
        "label": label,
        "model_ids": run.get("model_ids", []),
        "model_names": model_names_from_run(run),
        "metrics": run.get("metrics", {}),
        "payload": run,
    }


def publish_run(
    run: Dict[str, Any],
    label: Optional[str] = None,
    *,
    client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    """Upsert one run into Supabase, keyed on run_id, and return the row sent.

    Re-publishing the same run_id overwrites the prior row, so fixing and
    re-uploading a run is idempotent.
    """
    base_url, key, table = _config()
    row = row_from_run(run, label)
    endpoint = f"{base_url}/rest/v1/{table}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        # Upsert on the run_id primary key, and skip echoing the row back.
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        response = client.post(endpoint, headers=headers, content=json.dumps(row))
        # The model_names column is new. If this project hasn't run the migration
        # (db/migrations/0001_add_model_names.sql), Postgrest rejects the unknown
        # column; retry once without it so publishing still works — the model
        # names remain inside payload, just not queryable at the top level.
        if response.status_code >= 400 and "model_names" in response.text:
            fallback = {k: v for k, v in row.items() if k != "model_names"}
            response = client.post(endpoint, headers=headers, content=json.dumps(fallback))
    except httpx.HTTPError as exc:  # network/transport failure
        raise SupabasePublishError(f"Supabase request failed: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code >= 400:
        raise SupabasePublishError(
            f"Supabase publish failed ({response.status_code}): {response.text}"
        )
    return row
