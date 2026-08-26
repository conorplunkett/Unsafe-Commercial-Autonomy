from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_scenarios_endpoint():
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 50
    assert scenarios[0]["scenario_id"] == "scn_v1_a1_trap"
    assert scenarios[0]["pair_role"] == "trap"


def test_list_model_and_control_condition_endpoints():
    models = client.get("/api/models")
    controls = client.get("/api/control-conditions")

    assert models.status_code == 200
    assert "openai" in models.json()
    assert controls.status_code == 200
    assert set(controls.json()) == {"no_policy", "prompt_policy", "tool_constraints"}


def test_create_run_retrieve_events_and_metrics():
    response = client.post(
        "/api/runs",
        json={
            "agent_ids": ["baseline_surface_agent"],
            "scenario_ids": ["scn_v1_a1_trap"],
        },
    )

    assert response.status_code == 200
    run = response.json()
    assert run["metrics"]["total_results"] == 1
    assert run["metrics"]["unsafe_payment_rate"] == 1.0

    run_id = run["run_id"]
    read_response = client.get(f"/api/runs/{run_id}")
    assert read_response.status_code == 200
    assert read_response.json()["run_id"] == run_id

    events_response = client.get(f"/api/runs/{run_id}/events")
    assert events_response.status_code == 200
    assert len(events_response.json()) >= 2

    metrics_response = client.get(f"/api/metrics?run_id={run_id}")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["unsafe_payment_rate"] == 1.0


def test_create_phase1_model_run_with_new_request_fields():
    response = client.post(
        "/api/runs",
        json={
            "model_ids": ["openai"],
            "control_conditions": ["no_policy", "tool_constraints"],
            "scenario_ids": ["scn_v1_a1_trap"],
            "seeds": [1],
            "temperature": 0.7,
            "live": False,
        },
    )

    assert response.status_code == 200
    run = response.json()
    assert run["model_ids"] == ["openai"]
    assert run["control_conditions"] == ["no_policy", "tool_constraints"]
    assert run["seeds"] == [1]
    assert run["metrics"]["total_results"] == 2
    assert run["metrics"]["by_control_condition"]["tool_constraints"]["unsafe_payment_rate"] == 0.0


def test_legacy_search_endpoint():
    response = client.get("/search?query=coffee")

    assert response.status_code == 200
    assert response.json()["results"]


def _stored_run_id():
    response = client.post(
        "/api/runs",
        json={
            "agent_ids": ["baseline_surface_agent"],
            "scenario_ids": ["scn_v1_a1_trap"],
        },
    )
    assert response.status_code == 200
    return response.json()["run_id"]


def test_read_run_default_is_light_with_episode_index():
    run_id = _stored_run_id()

    light = client.get(f"/api/runs/{run_id}").json()
    assert light["run_id"] == run_id
    assert light["events"] == []
    [result] = light["results"]
    assert result["episode_index"] == 0
    assert result["raw_model_output"] is None
    assert result["raw_reasoning"] is None
    assert result["audit_events"] == []
    # The fields the dashboard reads survive the strip.
    assert result["verdict"]
    assert result["action"]["action_type"]
    assert light["metrics"]["total_results"] == 1


def test_read_run_include_full_returns_heavy_fields():
    run_id = _stored_run_id()

    full = client.get(f"/api/runs/{run_id}?include=full").json()
    [result] = full["results"]
    assert result["episode_index"] == 0
    assert result["audit_events"]
    assert full["events"]


def test_episode_detail_endpoint():
    run_id = _stored_run_id()

    response = client.get(f"/api/runs/{run_id}/results/0")
    assert response.status_code == 200
    episode = response.json()
    assert set(episode) == {
        "episode_index",
        "action",
        "proposed_action",
        "raw_model_output",
        "raw_reasoning",
        "audit_events",
        "turns",
    }
    assert episode["audit_events"]

    assert client.get(f"/api/runs/{run_id}/results/9999").status_code == 404
    assert client.get("/api/runs/run_missing/results/0").status_code == 404


def test_phase2_survey_coverage_endpoint():
    response = client.get("/api/phase2/survey-coverage")

    assert response.status_code == 200
    ids = response.json()["survey_covered"]
    # Frozen with the committed aggregate: the 44 surveyed scenarios, which
    # is NOT the semantic-only trap set (43) — e11_trap was surveyed and then
    # redesigned objective, so it stays survey-covered.
    assert ids == sorted(ids)
    assert len(ids) == 44
    phase2_ids = {s["scenario_id"] for s in client.get("/api/phase2/scenarios").json()}
    assert set(ids) <= phase2_ids
    assert all(scenario_id.endswith("_trap") for scenario_id in ids)
