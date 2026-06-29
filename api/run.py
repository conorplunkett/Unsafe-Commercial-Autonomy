"""Vercel serverless function: run a single (scenario x control-condition) cell
of the PayBench benchmark using a visitor-supplied API key.

The public site is a static export; this is its only live backend. It reuses the
exact scoring path as the local harness (``app.runner.run_phase1_evaluation``),
so a "run it yourself" result is scored identically to the published runs. The
visitor's key is used for this one request and is never stored or logged.

The frontend drives one cell per request (one scenario, one condition, one seed)
so each invocation is ~a single model call — fast and safely under the
function's time limit — while showing live progress across a small matrix.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# The bundled `app` package and `data/` directory live at the repo root, one
# level above this file (api/). Make them importable regardless of the CWD the
# function happens to run with.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ALLOWED_PROVIDERS = {"openai", "anthropic"}
ALLOWED_CONDITIONS = {"no_policy", "prompt_policy", "tool_constraints"}
ALLOWED_EFFORT = {"minimal", "low", "medium", "high"}


def run_cell(payload: dict) -> dict:
    """Validate the request and score one scenario/condition cell.

    Raises ValueError for bad input (→ 400). Provider/runtime failures from a
    bad key or model are caught inside the harness and surfaced on the result's
    ``error`` field rather than raising, so the frontend can show them inline.
    """
    provider = str(payload.get("provider") or "").strip()
    model = str(payload.get("model") or "").strip()
    api_key = str(payload.get("apiKey") or "").strip()
    scenario_id = str(payload.get("scenarioId") or "").strip()
    condition = str(payload.get("condition") or "").strip()
    reasoning_effort = str(payload.get("reasoningEffort") or "").strip() or None
    raw_temperature = payload.get("temperature")

    if provider not in ALLOWED_PROVIDERS:
        raise ValueError("provider must be 'openai' or 'anthropic'.")
    if not model:
        raise ValueError("A model name is required.")
    if not api_key:
        raise ValueError("An API key is required.")
    if not scenario_id:
        raise ValueError("A scenario is required.")
    if condition not in ALLOWED_CONDITIONS:
        raise ValueError("Unknown control condition.")
    if reasoning_effort and reasoning_effort not in ALLOWED_EFFORT:
        raise ValueError("Unknown reasoning effort.")
    try:
        temperature = float(raw_temperature) if raw_temperature is not None else None
    except (TypeError, ValueError) as exc:
        raise ValueError("temperature must be a number.") from exc

    # Imported lazily so a malformed request returns 400 without paying the
    # cost of loading the harness + provider SDKs.
    from app.models import model_to_dict
    from app.runner import run_phase1_evaluation

    run = run_phase1_evaluation(
        model_ids=[provider],
        control_conditions=[condition],
        scenario_ids=[scenario_id],
        seeds=[1],
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        live=True,
        api_key=api_key,
        model_name=model,
    )
    results = model_to_dict(run).get("results", [])
    if not results:
        raise ValueError("No result was produced for that scenario.")
    return results[0]


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        try:
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "Invalid JSON body."})
            return

        try:
            result = run_cell(payload)
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 - surface unexpected failures
            self._send(502, {"error": f"Run failed: {exc}"})
            return

        self._send(200, {"result": result})

    def do_GET(self) -> None:  # noqa: N802 - health check + offline self-test
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        if not query.get("selftest"):
            self._send(200, {"ok": True, "endpoint": "POST /api/run"})
            return

        # Offline dry run (no key, no network) that still exercises the full
        # bundling path: importing the harness, reading the data/ files, and
        # scoring. Lets the deploy be verified with a plain GET.
        try:
            from app.models import model_to_dict
            from app.runner import run_phase1_evaluation

            run = run_phase1_evaluation(
                model_ids=["openai"],
                control_conditions=["no_policy"],
                scenario_ids=["scn_v1_a1_trap"],
                seeds=[1],
                live=False,
            )
            result = model_to_dict(run).get("results", [{}])[0]
            self._send(
                200,
                {
                    "ok": True,
                    "selftest": {
                        "scenario_id": result.get("scenario_id"),
                        "verdict": result.get("verdict"),
                        "model_name": result.get("model_name"),
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001 - report bundling/runtime issues
            self._send(500, {"ok": False, "error": f"selftest failed: {exc}"})
