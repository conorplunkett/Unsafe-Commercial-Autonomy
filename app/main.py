from __future__ import annotations

import os
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
from .providers import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROK_MODEL,
    DEFAULT_INKLING_MODEL,
    DEFAULT_KIMI_MODEL,
    DEFAULT_MISTRAL_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_OPENWEIGHTS_MODEL,
    DEFAULT_QWEN_MODEL,
)
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
    "gemini": {
        "name": "Gemini",
        "description": "Runs the configured Gemini model through its OpenAI-compatible endpoint.",
    },
    "kimi": {
        "name": "Kimi",
        "description": "Runs the configured Kimi (Moonshot AI) model through its OpenAI-compatible endpoint.",
    },
    "inkling": {
        "name": "Inkling",
        "description": "Runs Thinking Machines Lab's Inkling open-weight model through an OpenAI-compatible inference host.",
    },
    "grok": {
        "name": "Grok",
        "description": "Runs the configured xAI Grok model through its OpenAI-compatible endpoint.",
    },
    "deepseek": {
        "name": "DeepSeek",
        "description": "Runs the configured DeepSeek model through its OpenAI-compatible endpoint.",
    },
    "mistral": {
        "name": "Mistral",
        "description": "Runs the configured Mistral model through its OpenAI-compatible endpoint.",
    },
    "qwen": {
        "name": "Qwen",
        "description": "Runs the configured Alibaba Qwen model through the DashScope OpenAI-compatible endpoint.",
    },
    "openrouter": {
        "name": "OpenRouter",
        "description": "Routes to any of OpenRouter's 300+ models via its OpenAI-compatible gateway.",
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

# Every place a provider needs an env var, a default model, or a "does this
# provider need a pasted key" answer reads from here — one place to update
# when a provider is added, instead of hunting through main.py and lab.js
# separately (which is exactly how the Gemini key field went missing).
PROVIDER_ENV_KEYS: Dict[str, list[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "kimi": ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
    "inkling": ["INKLING_API_KEY", "TOGETHER_API_KEY"],
    "grok": ["XAI_API_KEY", "GROK_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "qwen": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "openweights": [],
    "baseline_naive": [],
}

PROVIDER_DEFAULT_MODEL: Dict[str, str] = {
    "openai": DEFAULT_OPENAI_MODEL,
    "anthropic": DEFAULT_ANTHROPIC_MODEL,
    "gemini": DEFAULT_GEMINI_MODEL,
    "kimi": DEFAULT_KIMI_MODEL,
    "inkling": DEFAULT_INKLING_MODEL,
    "grok": DEFAULT_GROK_MODEL,
    "deepseek": DEFAULT_DEEPSEEK_MODEL,
    "mistral": DEFAULT_MISTRAL_MODEL,
    "qwen": DEFAULT_QWEN_MODEL,
    "openrouter": DEFAULT_OPENROUTER_MODEL,
    "openweights": DEFAULT_OPENWEIGHTS_MODEL,
    "baseline_naive": "",
}


def _provider_configured(provider_id: str) -> bool:
    """Whether this server process already has what it needs for this
    provider (an env-loaded API key, or no key requirement at all)."""
    if provider_id == "baseline_naive":
        return True
    if provider_id == "openweights":
        return bool(os.environ.get("OPENWEIGHTS_BASE_URL"))
    return any(os.environ.get(name) for name in PROVIDER_ENV_KEYS.get(provider_id, []))

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


@app.get("/favicon.ico")
async def favicon():
    # Browsers request this path directly, unprefixed by /static.
    return FileResponse(STATIC_DIR / "favicon.ico")


@app.get("/")
async def root():
    # This server is the local experiment console; the public lander lives in
    # web/ and is deployed separately. The legacy static dashboard is gone.
    return RedirectResponse(url="/lab")


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
    # The Lab renders its provider chips and API-key fields from this response
    # instead of a hardcoded list, so a new provider only needs to be added
    # here (and to PROVIDER_ENV_KEYS/PROVIDER_DEFAULT_MODEL above) to show up
    # everywhere. `configured` reflects this process's already-loaded .env, so
    # the Lab can skip demanding a browser-pasted key when one exists there.
    return {
        provider_id: {
            **profile,
            "default_model": PROVIDER_DEFAULT_MODEL.get(provider_id, ""),
            "needs_key": bool(PROVIDER_ENV_KEYS.get(provider_id)),
            "configured": _provider_configured(provider_id),
        }
        for provider_id, profile in MODEL_PROFILES.items()
    }


@app.get("/api/control-conditions")
async def list_control_conditions():
    return CONTROL_CONDITION_PROFILES


# Endpoints below that hit the filesystem (scenario sets, stored runs) or run
# a benchmark are plain `def` on purpose: FastAPI moves sync endpoints to its
# threadpool, so a multi-MB run parse or a long benchmark can't camp on the
# event loop and stall everything else — most visibly the Lab's 800ms
# /api/jobs progress polls.
@app.get("/api/scenarios")
def list_scenarios():
    return [model_to_dict(scenario) for scenario in load_scenarios()]


@app.get("/api/phase2/scenarios")
def list_phase2_scenarios():
    # The v2 250-scenario set backs Phase 2 runs. Imported lazily so the Phase 1
    # API path never pulls in Phase 2 modules at startup.
    from .phase2 import PHASE2_SCENARIO_SET

    return [model_to_dict(scenario) for scenario in load_scenarios(PHASE2_SCENARIO_SET)]


@app.get("/api/scenarios/{scenario_id}")
def read_scenario(scenario_id: str):
    try:
        return model_to_dict(get_scenario(scenario_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/runs")
def create_run(request: RunRequest):
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
            gemini_thinking_level=request.gemini_thinking_level,
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
                gemini_thinking_level=request.gemini_thinking_level,
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
def list_runs():
    return storage.list_runs()


@app.get("/api/runs/{run_id}")
def read_run(run_id: str, include: Optional[str] = Query(default=None)):
    # Light by default: the Lab pulls every stored run on each refresh, and
    # the dashboard reads transcripts only in the one-episode detail panel,
    # served on demand by /api/runs/{run_id}/results/{episode_index} below.
    try:
        if include == "full":
            return storage.read_full_dict(run_id)
        return storage.read_light(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/runs/{run_id}/results/{episode_index}")
def read_run_episode(run_id: str, episode_index: int):
    try:
        return storage.read_episode(run_id, episode_index)
    except (KeyError, IndexError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    # Deletes the stored run file. Local-only console action — the Lab uses it
    # to drop dry-run or mistaken runs from the dashboard. Published runs live
    # in Supabase and are unaffected.
    try:
        storage.delete(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": run_id}


@app.get("/api/runs/{run_id}/events")
def read_run_events(run_id: str):
    try:
        return storage.read(run_id).events
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/metrics")
def read_metrics(run_id: Optional[str] = Query(default=None)):
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
