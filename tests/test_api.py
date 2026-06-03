from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_scenarios_endpoint():
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 10
    assert scenarios[0]["scenario_id"]


def test_create_run_retrieve_events_and_metrics():
    response = client.post(
        "/api/runs",
        json={
            "agent_ids": ["baseline_surface_agent"],
            "scenario_ids": ["scn_shipping_over_budget"],
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
    assert metrics_response.json()["approval_failure_rate"] == 1.0


def test_legacy_search_endpoint():
    response = client.get("/search?query=coffee")

    assert response.status_code == 200
    assert response.json()["results"]

