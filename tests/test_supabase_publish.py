import json

import pytest

from app.supabase_publish import (
    SupabasePublishError,
    publish_run,
    row_from_run,
)


SAMPLE_RUN = {
    "run_id": "run_123",
    "created_at": "2026-06-15T12:00:00Z",
    "phase": "phase2",
    "model_ids": ["openai"],
    "metrics": {"total_results": 10},
    "results": [],
    "events": [],
}


class _StubResponse:
    def __init__(self, status_code=201, text=""):
        self.status_code = status_code
        self.text = text


class _StubClient:
    """Records the single POST a publish makes, returning a canned response."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, headers=None, content=None):
        self.calls.append({"url": url, "headers": headers, "content": content})
        return self._response


def test_row_from_run_lifts_listing_fields_and_keeps_full_payload():
    row = row_from_run(SAMPLE_RUN, label="Phase 2 official")
    assert row["run_id"] == "run_123"
    assert row["created_at"] == "2026-06-15T12:00:00Z"
    assert row["phase"] == "phase2"
    assert row["label"] == "Phase 2 official"
    assert row["model_ids"] == ["openai"]
    assert row["metrics"] == {"total_results": 10}
    # The whole run is preserved so the dashboard renders it like a local run.
    assert row["payload"] == SAMPLE_RUN


def test_row_from_run_requires_run_id():
    with pytest.raises(SupabasePublishError):
        row_from_run({"created_at": "x"})


def test_publish_run_posts_upsert_with_service_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co/")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    monkeypatch.delenv("SUPABASE_BENCHMARK_TABLE", raising=False)
    client = _StubClient(_StubResponse(status_code=201))

    publish_run(SAMPLE_RUN, label="Official", client=client)

    assert len(client.calls) == 1
    call = client.calls[0]
    # Trailing slash on the URL is normalized, default table name used.
    assert call["url"] == "https://proj.supabase.co/rest/v1/benchmark_runs"
    assert call["headers"]["apikey"] == "service-secret"
    assert call["headers"]["Authorization"] == "Bearer service-secret"
    assert "resolution=merge-duplicates" in call["headers"]["Prefer"]
    body = json.loads(call["content"])
    assert body["run_id"] == "run_123"
    assert body["label"] == "Official"


def test_publish_run_honors_custom_table(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    monkeypatch.setenv("SUPABASE_BENCHMARK_TABLE", "custom_runs")
    client = _StubClient(_StubResponse(status_code=201))

    publish_run(SAMPLE_RUN, client=client)

    assert client.calls[0]["url"].endswith("/rest/v1/custom_runs")


def test_publish_run_raises_on_api_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    client = _StubClient(_StubResponse(status_code=403, text="forbidden"))

    with pytest.raises(SupabasePublishError) as exc:
        publish_run(SAMPLE_RUN, client=client)
    assert "403" in str(exc.value)


def test_publish_run_requires_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(SupabasePublishError):
        publish_run(SAMPLE_RUN, client=_StubClient(_StubResponse()))
