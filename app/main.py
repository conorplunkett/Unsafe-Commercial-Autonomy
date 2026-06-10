from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agents import AGENT_PROFILES
from .data import ROOT_DIR, get_scenario, load_catalog, load_scenarios, search_catalog
from .models import AgentAction, RunRequest, model_to_dict
from .policies import evaluate_action
from .runner import run_benchmark
from .storage import RunStorage


STATIC_DIR = ROOT_DIR / "static"
storage = RunStorage()

MODEL_PROFILES = {
    "openai": {
        "name": "OpenAI",
        "description": "Runs the configured OpenAI model through the Responses API.",
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Runs the configured Anthropic model through the Messages API.",
    },
    "openweights": {
        "name": "Open-weights",
        "description": "Runs an OpenAI-compatible local open-weights endpoint.",
    },
    "baseline_naive": {
        "name": "Naive baseline",
        "description": "Always-cheapest, never-ask heuristic baseline. Runs offline.",
    },
}

CONTROL_CONDITION_PROFILES = {
    "no_policy": {
        "name": "No policy",
        "description": "Model receives only the task context.",
    },
    "prompt_policy": {
        "name": "Prompt policy",
        "description": "Model receives policy instructions in the prompt.",
    },
    "tool_constraints": {
        "name": "Tool constraints",
        "description": "The simulated payment tool blocks enforceable unsafe attempts.",
    },
}

app = FastAPI(title="Unsafe Commercial Autonomy Benchmark", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/agents")
async def list_agents():
    return AGENT_PROFILES


@app.get("/api/models")
async def list_models():
    return MODEL_PROFILES


@app.get("/api/control-conditions")
async def list_control_conditions():
    return CONTROL_CONDITION_PROFILES


@app.get("/api/scenarios")
async def list_scenarios():
    return [model_to_dict(scenario) for scenario in load_scenarios()]


@app.get("/api/scenarios/{scenario_id}")
async def read_scenario(scenario_id: str):
    try:
        return model_to_dict(get_scenario(scenario_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs")
async def create_run(request: RunRequest):
    try:
        run = run_benchmark(
            agent_ids=request.agent_ids,
            model_ids=request.model_ids,
            control_conditions=request.control_conditions,
            scenario_ids=request.scenario_ids,
            scenario_set_path=Path(request.scenario_set_path) if request.scenario_set_path else None,
            seeds=request.seeds,
            temperature=request.temperature,
            live=request.live,
        )
        return storage.save(run)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/runs")
async def list_runs():
    return storage.list_runs()


@app.get("/api/runs/{run_id}")
async def read_run(run_id: str):
    try:
        return model_to_dict(storage.read(run_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/runs/{run_id}/events")
async def read_run_events(run_id: str):
    try:
        return storage.read(run_id).events
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/metrics")
async def read_metrics(run_id: Optional[str] = Query(default=None)):
    try:
        run = storage.read(run_id) if run_id else storage.latest()
        return run.metrics
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/search")
async def search_products(query: str):
    return {"query": query, "results": search_catalog(query, load_catalog())}


@app.post("/execute-payment")
async def execute_payment_endpoint(
    total_amount: float,
    sku: str,
    merchant_id: str,
    scenario_id: str,
    payment_type: str = "card",
):
    try:
        scenario = get_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    action = AgentAction(
        action_type="purchase",
        amount=total_amount,
        sku=sku,
        merchant_id=merchant_id,
        payment_type=payment_type,
        rationale="Compatibility endpoint payment attempt.",
    )
    result = evaluate_action(scenario, "compatibility_endpoint", "Compatibility Endpoint", action)
    return {
        "scenario_id": scenario_id,
        "status": "failed" if result.failure_metrics else "success",
        "failure_metric": result.failure_metrics[0] if result.failure_metrics else None,
        "agent_action": {
            "total_amount": total_amount,
            "sku": sku,
            "merchant_id": merchant_id,
            "payment_type": payment_type,
        },
        "policy_constraint": scenario.payment_policy,
        "evaluation": model_to_dict(result),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
