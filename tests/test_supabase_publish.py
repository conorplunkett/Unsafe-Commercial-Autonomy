import copy
import json

import pytest

import app.supabase_publish as supabase_publish
from app.supabase_publish import (
    SupabasePublishError,
    episode_rows_from_run,
    model_names_from_run,
    publish_run,
    row_from_run,
    slim_run_payload,
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


def _episode_run(count=3):
    return {
        **SAMPLE_RUN,
        "results": [
            {"scenario_id": f"scn_{i}", "model_name": "gpt-5.4-mini", "verdict": "safe"}
            for i in range(count)
        ],
        "events": [{"event_id": f"e{i}"} for i in range(count)],
    }


class _StubResponse:
    def __init__(self, status_code=201, text=""):
        self.status_code = status_code
        self.text = text


class _StubClient:
    """Records every request a publish makes, returning canned responses."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def post(self, url, headers=None, content=None):
        self.calls.append({"method": "post", "url": url, "headers": headers, "content": content})
        return self._response

    def delete(self, url, headers=None):
        self.calls.append({"method": "delete", "url": url, "headers": headers})
        return self._response


def test_row_from_run_lifts_listing_fields_and_slims_the_payload():
    row = row_from_run(_episode_run(2), label="Phase 2 official")
    assert row["run_id"] == "run_123"
    assert row["created_at"] == "2026-06-15T12:00:00Z"
    assert row["phase"] == "phase2"
    assert row["label"] == "Phase 2 official"
    assert row["model_ids"] == ["openai"]
    assert row["metrics"] == {"total_results": 10}
    # Episodes live in the episodes table; the run row keeps config + metrics.
    assert "results" not in row["payload"]
    assert "events" not in row["payload"]
    assert row["payload"]["episode_count"] == 2


def test_episode_rows_carry_canonical_order_and_lifted_fields():
    rows = episode_rows_from_run(_episode_run(3))
    assert [row["episode_index"] for row in rows] == [0, 1, 2]
    assert rows[0]["run_id"] == "run_123"
    assert rows[0]["scenario_id"] == "scn_0"
    assert rows[0]["model_name"] == "gpt-5.4-mini"
    assert rows[0]["result"]["verdict"] == "safe"
    assert slim_run_payload(_episode_run(3))["episode_count"] == 3


def test_episode_rows_preserve_navigation_history_for_publication():
    navigation = {
        "entry_url": "https://shop.com/item",
        "redirect_chain": ["https://checkout.com/session/123"],
        "final_url": "https://checkout.com/session/123",
    }
    run = _episode_run(1)
    run["results"][0]["audit_events"] = [
        {
            "event_type": "tool_call",
            "code": "view_offer",
            "detail": {"navigation": navigation},
        }
    ]

    [row] = episode_rows_from_run(run)

    assert row["result"]["audit_events"][0]["detail"]["navigation"] == navigation


def test_episode_rows_publish_outbound_message_events_verbatim():
    event = {
        "event_type": "outbound_message",
        "code": "delivered",
        "detail": {
            "recipient": "billing@example.com",
            "message": "Attached as requested.",
            "shared_fields": ["account_reference"],
            "attachments": ["invoice.pdf"],
            "receipt_id": "delivery_1234",
        },
    }
    run = {
        **SAMPLE_RUN,
        "results": [
            {
                "scenario_id": "scn_v2_d9_trap",
                "model_name": "gpt-5.4-mini",
                "audit_events": [event],
            }
        ],
    }

    rows = episode_rows_from_run(run)

    assert rows[0]["result"]["audit_events"] == [event]


def test_cap_reasoning_truncates_over_cap_text_and_its_audit_mirror():
    cap = supabase_publish.REASONING_PUBLISH_MAX_CHARS
    long_text = "a" * (cap + 500)
    result = {
        "scenario_id": "scn_0",
        "raw_reasoning": long_text,
        "audit_events": [
            {
                "event_type": "model_output",
                "code": "raw_output",
                "detail": {"raw_model_output": "{}", "raw_reasoning": long_text},
            },
            {"event_type": "verdict", "code": "safe", "detail": {}},
        ],
    }
    original = copy.deepcopy(result)

    capped = supabase_publish._cap_reasoning(result)

    assert capped["raw_reasoning"].startswith("a" * cap)
    assert capped["raw_reasoning"] == (
        "a" * cap + "\n… [truncated 500 chars for publish]"
    )
    # The mirrored copy inside the model_output event's detail gets the same
    # truncation; the unrelated verdict event is left alone.
    assert capped["audit_events"][0]["detail"]["raw_reasoning"] == capped["raw_reasoning"]
    assert capped["audit_events"][1] == {"event_type": "verdict", "code": "safe", "detail": {}}
    # The caller's dict — top level and nested audit events — is untouched.
    assert result == original


def test_cap_reasoning_leaves_under_cap_result_unchanged():
    result = {
        "scenario_id": "scn_1",
        "raw_reasoning": "short reasoning",
        "audit_events": [{"event_type": "model_output", "detail": {"raw_reasoning": "short reasoning"}}],
    }
    assert supabase_publish._cap_reasoning(result) is result


def test_cap_reasoning_leaves_result_without_raw_reasoning_untouched():
    result = {"scenario_id": "scn_2", "verdict": "safe"}
    assert supabase_publish._cap_reasoning(result) is result


def test_episode_rows_from_run_caps_oversized_reasoning():
    cap = supabase_publish.REASONING_PUBLISH_MAX_CHARS
    long_text = "b" * (cap + 10)
    run = {
        **SAMPLE_RUN,
        "results": [
            {
                "scenario_id": "scn_0",
                "model_name": "gpt-5.4-mini",
                "raw_reasoning": long_text,
                "audit_events": [
                    {"event_type": "model_output", "detail": {"raw_reasoning": long_text}}
                ],
            }
        ],
    }

    rows = episode_rows_from_run(run)

    capped_text = rows[0]["result"]["raw_reasoning"]
    assert capped_text == "b" * cap + "\n… [truncated 10 chars for publish]"
    assert capped_text != long_text
    assert rows[0]["result"]["audit_events"][0]["detail"]["raw_reasoning"] == capped_text
    # The run passed in is unaffected.
    assert len(run["results"][0]["raw_reasoning"]) == cap + 10


def test_row_from_run_requires_run_id():
    with pytest.raises(SupabasePublishError):
        row_from_run({"created_at": "x"})


def test_row_from_run_surfaces_model_names_for_per_model_queries():
    run = {**SAMPLE_RUN, "model_names": ["gpt-5.4-mini", "gpt-5.5"]}
    row = row_from_run(run)
    assert row["model_ids"] == ["openai"]
    assert row["model_names"] == ["gpt-5.4-mini", "gpt-5.5"]


def test_model_names_from_run_falls_back_to_results_then_metrics():
    # Prefers the first-class field.
    assert model_names_from_run({"model_names": ["a"]}) == ["a"]
    # Falls back to distinct per-result names, in order.
    assert model_names_from_run(
        {"results": [{"model_name": "x"}, {"model_name": "x"}, {"model_name": "y"}]}
    ) == ["x", "y"]
    # Then to the per-model metric keys for legacy payloads.
    assert model_names_from_run(
        {"metrics": {"by_model_name": {"z": {}}}}
    ) == ["z"]
    assert model_names_from_run({}) == []


def test_publish_retries_without_model_names_when_column_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")

    class _TwoStepClient:
        def __init__(self):
            self.calls = []

        def post(self, url, headers=None, content=None):
            self.calls.append(json.loads(content))
            if len(self.calls) == 1:
                return _StubResponse(
                    status_code=400,
                    text="column \"model_names\" of relation \"benchmark_runs\" does not exist",
                )
            return _StubResponse(status_code=201)

    client = _TwoStepClient()
    publish_run({**SAMPLE_RUN, "model_names": ["gpt-5.5"]}, client=client)

    assert len(client.calls) == 2
    assert "model_names" in client.calls[0]
    # The retry drops the unknown column but still writes the run.
    assert "model_names" not in client.calls[1]
    assert client.calls[1]["run_id"] == "run_123"


def test_row_from_run_surfaces_enforcement_scope():
    run = {**SAMPLE_RUN, "enforcement_scope": "rail_reachable"}
    assert row_from_run(run)["enforcement_scope"] == "rail_reachable"
    # Phase 1 runs, and any Phase 2 run stored before the axis existed,
    # publish null rather than omitting the column.
    assert row_from_run(SAMPLE_RUN)["enforcement_scope"] is None


def test_publish_retries_without_enforcement_scope_when_column_missing(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")

    class _TwoStepClient:
        def __init__(self):
            self.calls = []

        def post(self, url, headers=None, content=None):
            self.calls.append(json.loads(content))
            if len(self.calls) == 1:
                return _StubResponse(
                    status_code=400,
                    text=(
                        "Could not find the 'enforcement_scope' column of "
                        "'benchmark_runs' in the schema cache"
                    ),
                )
            return _StubResponse(status_code=201)

    client = _TwoStepClient()
    publish_run({**SAMPLE_RUN, "enforcement_scope": "all"}, client=client)

    assert len(client.calls) == 2
    assert client.calls[0]["enforcement_scope"] == "all"
    assert "enforcement_scope" not in client.calls[1]
    assert client.calls[1]["run_id"] == "run_123"


def test_publish_retries_past_two_missing_columns_at_once(monkeypatch):
    """A project that has run neither migration 0001 nor 0011 still publishes:
    each retry drops whichever column PostgREST names next, not just one."""
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")

    class _ThreeStepClient:
        def __init__(self):
            self.calls = []

        def post(self, url, headers=None, content=None):
            self.calls.append(json.loads(content))
            if "model_names" in self.calls[-1]:
                return _StubResponse(
                    status_code=400,
                    text="column \"model_names\" of relation \"benchmark_runs\" does not exist",
                )
            if "enforcement_scope" in self.calls[-1]:
                return _StubResponse(
                    status_code=400,
                    text=(
                        "Could not find the 'enforcement_scope' column of "
                        "'benchmark_runs' in the schema cache"
                    ),
                )
            return _StubResponse(status_code=201)

    client = _ThreeStepClient()
    publish_run(
        {**SAMPLE_RUN, "model_names": ["gpt-5.5"], "enforcement_scope": "all"},
        client=client,
    )

    assert len(client.calls) == 3
    assert client.calls[2]["run_id"] == "run_123"
    assert "model_names" not in client.calls[2]
    assert "enforcement_scope" not in client.calls[2]


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


def test_publish_run_batches_episodes_then_commits_the_run_row(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    monkeypatch.delenv("SUPABASE_BENCHMARK_EPISODES_TABLE", raising=False)
    client = _StubClient(_StubResponse(status_code=201))

    row = publish_run(_episode_run(3), client=client)

    shapes = [
        (call["method"], call["url"].split("/rest/v1/")[1].split("?")[0])
        for call in client.calls
    ]
    # Delete-then-insert on the episodes table, and the run row LAST: the site
    # lists runs from benchmark_runs, so a publish that dies mid-batch leaves
    # nothing visible.
    assert shapes[0] == ("delete", "benchmark_run_episodes")
    assert shapes[1] == ("post", "benchmark_run_episodes")
    assert shapes[-1] == ("post", "benchmark_runs")
    assert "run_id=eq.run_123" in client.calls[0]["url"]
    batch = json.loads(client.calls[1]["content"])
    assert [entry["episode_index"] for entry in batch] == [0, 1, 2]
    run_row = json.loads(client.calls[-1]["content"])
    assert "results" not in run_row["payload"]
    assert run_row["payload"]["episode_count"] == 3
    assert row["payload"]["episode_count"] == 3


def test_publish_run_splits_episode_batches(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    monkeypatch.setattr(supabase_publish, "EPISODE_BATCH_MAX_ROWS", 2)
    client = _StubClient(_StubResponse(status_code=201))
    seen = []

    publish_run(_episode_run(5), client=client, progress=lambda sent, total: seen.append((sent, total)))

    episode_posts = [
        call for call in client.calls
        if call["method"] == "post" and "benchmark_run_episodes" in call["url"]
    ]
    assert [len(json.loads(call["content"])) for call in episode_posts] == [2, 2, 1]
    assert seen == [(2, 5), (4, 5), (5, 5)]


def test_publish_run_zero_episode_run_skips_the_episodes_table(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    client = _StubClient(_StubResponse(status_code=201))

    publish_run(SAMPLE_RUN, client=client)

    assert [call["method"] for call in client.calls] == ["post"]
    assert client.calls[0]["url"].endswith("/rest/v1/benchmark_runs")


def test_publish_run_names_the_missing_episodes_migration(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    client = _StubClient(
        _StubResponse(
            status_code=404,
            text='{"code":"PGRST205","message":"Could not find the table '
            "'public.benchmark_run_episodes' in the schema cache\"}",
        )
    )

    with pytest.raises(SupabasePublishError) as excinfo:
        publish_run(_episode_run(1), client=client)
    assert "0009_add_benchmark_run_episodes" in str(excinfo.value)


def test_publish_run_retries_transient_5xx_per_request(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-secret")
    monkeypatch.setattr(supabase_publish, "_RETRY_SLEEP", lambda seconds: None)

    class _FlakyClient(_StubClient):
        def __init__(self):
            super().__init__(_StubResponse(status_code=201))
            self.failed_once = False

        def post(self, url, headers=None, content=None):
            if "benchmark_run_episodes" in url and not self.failed_once:
                self.failed_once = True
                self.calls.append({"method": "post", "url": url, "content": content})
                return _StubResponse(status_code=503, text="upstream hiccup")
            return super().post(url, headers=headers, content=content)

    client = _FlakyClient()
    publish_run(_episode_run(2), client=client)

    episode_posts = [
        call for call in client.calls
        if call["method"] == "post" and "benchmark_run_episodes" in call["url"]
    ]
    assert len(episode_posts) == 2  # the 503 was retried, not fatal
