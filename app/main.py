from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .env import load_env_file

# Auto-load repo-root .env (existing env vars win) before anything reads
# provider or Supabase configuration. See app/env.py.
load_env_file()

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
async def root():
    # This server is the local experiment console; the public lander lives in
    # web/ and is deployed separately. The legacy static dashboard is gone.
    return RedirectResponse(url="/lab")


@app.get("/lab")
async def lab():
    return FileResponse(STATIC_DIR / "lab.html")


@app.get("/lab")
async def lab():
    # Local-only experiment console. Separate page on purpose: the lander at /
    # mirrors the live site and is not edited for lab workflows.
    return FileResponse(STATIC_DIR / "lab.html")


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


@app.get("/api/phase2/scenarios")
async def list_phase2_scenarios():
    # The v2 250-scenario set backs Phase 2 runs. Imported lazily so the Phase 1
    # API path never pulls in Phase 2 modules at startup.
    from .phase2 import PHASE2_SCENARIO_SET

    return [model_to_dict(scenario) for scenario in load_scenarios(PHASE2_SCENARIO_SET)]


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
            reasoning_effort=request.reasoning_effort,
            live=request.live,
            api_key=request.api_key,
            model_name=request.byok_model_name,
        )
        return storage.save(run)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# In-memory registry of background benchmark jobs, so the dashboard can start a
# run and poll a progress bar instead of holding one long request open. Jobs are
# process-local (lost on restart); the finished run itself is persisted through
# RunStorage exactly like a synchronous /api/runs run.
JOBS: Dict[str, Dict[str, Any]] = {}


@app.post("/api/jobs")
async def create_job(request: RunRequest):
    job_id = f"job_{uuid4().hex[:12]}"
    job: Dict[str, Any] = {
        "job_id": job_id,
        "status": "running",
        "completed": 0,
        "total": 0,
        "unit": "",
        "run_id": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    JOBS[job_id] = job

    def progress(completed: int, total: int, unit: str) -> None:
        job["completed"] = completed
        job["total"] = total
        job["unit"] = unit

    def work() -> None:
        try:
            run = run_benchmark(
                agent_ids=request.agent_ids,
                model_ids=request.model_ids,
                control_conditions=request.control_conditions,
                scenario_ids=request.scenario_ids,
                scenario_set_path=Path(request.scenario_set_path) if request.scenario_set_path else None,
                seeds=request.seeds,
                temperature=request.temperature,
                reasoning_effort=request.reasoning_effort,
                live=request.live,
                api_key=request.api_key,
                model_name=request.byok_model_name,
                progress_cb=progress,
            )
            storage.save(run)
            job["run_id"] = run.run_id
            job["status"] = "done"
        except Exception as exc:  # surfaced to the polling client, not raised
            job["error"] = str(exc)
            job["status"] = "error"

    threading.Thread(target=work, daemon=True).start()
    return job


@app.get("/api/jobs/{job_id}")
async def read_job(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


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
