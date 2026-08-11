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
import re
import time
from typing import Any, Callable, Dict, Iterator, List, Optional

import httpx

DEFAULT_TABLE = "benchmark_runs"
DEFAULT_EPISODES_TABLE = "benchmark_run_episodes"

# One full run serializes to hundreds of MB; a single POST of that blob times
# out at the gateway. Episodes upload in size-capped batches instead, each a
# few MB, so a 220 MB run is ~100 ordinary requests. Rows per batch is a
# secondary cap for runs with tiny episodes.
EPISODE_BATCH_MAX_BYTES = 2_000_000
EPISODE_BATCH_MAX_ROWS = 500
# Per-request retry for transient faults (timeouts, 5xx): a publish that dies
# at batch 80 of 100 should not have been one request to begin with.
REQUEST_ATTEMPTS = 3
_RETRY_SLEEP = time.sleep  # test seam

_MISSING_COLUMN_RE = re.compile(r"column \"([^\"]+)\"")
# PostgREST's own unknown-column error for insert bodies (PGRST204) uses a
# different shape: Could not find the 'x' column of 'table' in the schema cache.
_PGRST_MISSING_COLUMN_RE = re.compile(r"[Cc]ould not find the '([^']+)' column")

# The public project URL is not a secret (the site embeds it client-side), so we
# default to it. Only the service-role *key* must be supplied via the
# environment. Override SUPABASE_URL to publish to a different project.
DEFAULT_URL = "https://tethtzycfdplyzvrtknh.supabase.co"


class SupabasePublishError(RuntimeError):
    """Raised when a run cannot be published (missing config or API error)."""


def _config(
    table_env: str = "SUPABASE_BENCHMARK_TABLE", default_table: str = DEFAULT_TABLE
) -> tuple[str, str, str]:
    """Resolve (base_url, service_key, table) from the environment."""
    # The URL is public, so fall back to the project default; only the key is
    # secret and must be provided.
    url = os.environ.get("SUPABASE_URL") or DEFAULT_URL
    # Accept either name; the service-role key is the secret write credential.
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    table = os.environ.get(table_env, default_table)
    if not key:
        raise SupabasePublishError(
            "SUPABASE_SERVICE_KEY is not set. Use the service-role key from "
            "Supabase > Project Settings > API; keep it out of version control."
        )
    return url.rstrip("/"), key, table


def _missing_column(response: httpx.Response) -> Optional[str]:
    """Return the column name PostgREST reports as missing, if that's the error."""
    if response.status_code < 400:
        return None
    text = response.text or ""
    match = _MISSING_COLUMN_RE.search(text)
    if match and "does not exist" in text:
        return match.group(1)
    match = _PGRST_MISSING_COLUMN_RE.search(text)
    if match:
        return match.group(1)
    return None


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


def slim_run_payload(run: Dict[str, Any]) -> Dict[str, Any]:
    """The run without its episode bulk.

    ``results`` moves to the episodes table (the reason batched publishing
    exists); ``events`` is derived from the results' own audit trails and the
    site never reads it, so it ships in neither place. ``episode_count`` lets
    a reader know how many episode rows belong to the run without counting.
    """
    payload = {key: value for key, value in run.items() if key not in ("results", "events")}
    payload["episode_count"] = len(run.get("results") or [])
    return payload


def episode_rows_from_run(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One ``benchmark_run_episodes`` row per result, in canonical run order.

    ``episode_index`` is the position in the run's results list — the same
    order a local run file carries — so reassembling the run is an ordered
    select, and re-publishing upserts row-for-row.
    """
    rows = []
    for index, result in enumerate(run.get("results") or []):
        result = result if isinstance(result, dict) else {}
        rows.append(
            {
                "run_id": run["run_id"],
                "episode_index": index,
                "scenario_id": result.get("scenario_id"),
                "model_name": result.get("model_name"),
                "result": result,
            }
        )
    return rows


def row_from_run(run: Dict[str, Any], label: Optional[str] = None) -> Dict[str, Any]:
    """Shape a stored BenchmarkRun dict into a ``benchmark_runs`` row.

    ``payload`` carries the slim run (config + metrics; episodes live in the
    episodes table); a few fields are lifted out for listing and ordering.
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
        "payload": slim_run_payload(run),
    }


def _episode_batches(rows: List[Dict[str, Any]]) -> Iterator[List[Dict[str, Any]]]:
    """Split episode rows into request-sized batches (bytes first, rows second)."""
    batch: List[Dict[str, Any]] = []
    size = 2  # the enclosing JSON array brackets
    for row in rows:
        encoded = len(json.dumps(row, ensure_ascii=False).encode("utf-8")) + 1
        if batch and (size + encoded > EPISODE_BATCH_MAX_BYTES or len(batch) >= EPISODE_BATCH_MAX_ROWS):
            yield batch
            batch, size = [], 2
        batch.append(row)
        size += encoded
    if batch:
        yield batch


def _missing_table(response: httpx.Response) -> bool:
    """PostgREST's unknown-relation error (PGRST205), e.g. before a migration ran."""
    if response.status_code < 400:
        return False
    text = response.text or ""
    return "PGRST205" in text or "Could not find the table" in text


def _request_with_retry(
    send: Callable[[], httpx.Response], what: str
) -> httpx.Response:
    """Issue one request with short retries on transport faults and 5xx.

    4xx responses return immediately — they are deterministic (bad body,
    missing table, missing column) and the callers decide what they mean.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(REQUEST_ATTEMPTS):
        try:
            response = send()
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt == REQUEST_ATTEMPTS - 1:
                raise SupabasePublishError(f"Supabase request failed ({what}): {exc}") from exc
        else:
            if response.status_code >= 500 and attempt < REQUEST_ATTEMPTS - 1:
                _RETRY_SLEEP(2.0 * (attempt + 1))
                continue
            return response
        _RETRY_SLEEP(2.0 * (attempt + 1))
    raise SupabasePublishError(f"Supabase request failed ({what}): {last_exc}")


def publish_run(
    run: Dict[str, Any],
    label: Optional[str] = None,
    *,
    client: Optional[httpx.Client] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Publish one run: episodes in batches, then the run row. Idempotent.

    Order matters for atomicity-in-effect: the site lists runs from the run
    table, so episodes upload first (delete-then-insert, so a re-publish never
    leaves orphans) and the run row lands last as the commit point — a publish
    that dies mid-batch leaves nothing visible, and re-running it heals.
    ``progress`` receives (episodes_sent, episodes_total) after each batch.
    Returns the run row sent, with ``episode_count`` inside its payload.
    """
    base_url, key, table = _config()
    episodes_table = os.environ.get(
        "SUPABASE_BENCHMARK_EPISODES_TABLE", DEFAULT_EPISODES_TABLE
    )
    row = row_from_run(run, label)
    episode_rows = episode_rows_from_run(run)
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        # Upsert on the primary key, and skip echoing rows back.
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    owns_client = client is None
    # Batches are a few MB; 60 s of headroom per request, not per run.
    client = client or httpx.Client(timeout=60.0)
    try:
        if episode_rows:
            run_filter = f"run_id=eq.{run['run_id']}"
            episodes_endpoint = f"{base_url}/rest/v1/{episodes_table}"
            response = _request_with_retry(
                lambda: client.delete(f"{episodes_endpoint}?{run_filter}", headers=headers),
                "episodes delete",
            )
            if _missing_table(response):
                raise SupabasePublishError(
                    f"The {episodes_table!r} table does not exist yet. Run "
                    "db/migrations/0009_add_benchmark_run_episodes.sql against "
                    "the project, then re-run publish."
                )
            if response.status_code >= 400:
                raise SupabasePublishError(
                    f"Supabase episodes delete failed ({response.status_code}): {response.text}"
                )
            sent = 0
            for batch in _episode_batches(episode_rows):
                payload = json.dumps(batch, ensure_ascii=False)
                response = _request_with_retry(
                    lambda body=payload: client.post(
                        episodes_endpoint, headers=headers, content=body
                    ),
                    "episodes insert",
                )
                if response.status_code >= 400:
                    raise SupabasePublishError(
                        f"Supabase episodes insert failed after {sent}/{len(episode_rows)} "
                        f"episodes ({response.status_code}): {response.text}. "
                        "Re-running publish is safe; it restarts this run's episodes."
                    )
                sent += len(batch)
                if progress is not None:
                    progress(sent, len(episode_rows))

        endpoint = f"{base_url}/rest/v1/{table}"
        response = _request_with_retry(
            lambda: client.post(endpoint, headers=headers, content=json.dumps(row)),
            "run row",
        )
        # The model_names column is new. If this project hasn't run the migration
        # (db/migrations/0001_add_model_names.sql), Postgrest rejects the unknown
        # column; retry once without it so publishing still works — the model
        # names remain inside payload, just not queryable at the top level.
        if response.status_code >= 400 and "model_names" in response.text:
            fallback = {k: v for k, v in row.items() if k != "model_names"}
            response = _request_with_retry(
                lambda: client.post(endpoint, headers=headers, content=json.dumps(fallback)),
                "run row",
            )
    finally:
        if owns_client:
            client.close()

    if response.status_code >= 400:
        raise SupabasePublishError(
            f"Supabase publish failed ({response.status_code}): {response.text}"
        )
    return row

