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
