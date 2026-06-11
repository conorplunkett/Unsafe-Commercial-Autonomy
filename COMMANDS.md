# Commands and capabilities

Operational cheat sheet for this repository. For the research plan, benchmark
design, metrics definitions, phased roadmap, and failure taxonomy, see
[README.md](README.md).

## What this repo does today

- Parses scenario sets from Markdown tables into structured `Scenario` objects
- Runs Phase 1 model evaluations (live LLM APIs or offline providers)
- Scores agent actions against policy rules and answer keys (multi-label failures)
- Computes safety-autonomy metrics with Wilson confidence intervals
- Exposes a FastAPI dashboard and JSON API
- Runs deterministic demo agents for control-layer comparisons (legacy path)
- Stores run results as JSON under `runtime/runs/`

Phase 1 scope is a **simulated card-credential benchmark**. Stablecoin wallets,
x402 payments, and paid tool access appear in some legacy demo scenarios but are
future work for the main benchmark unless explicitly called out.

There is **no compile or build step**. Plain Python + static HTML/CSS/JS.

---

## Setup

```bash
cd /path/to/Unsafe-Commercial-Autonomy
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Dependencies (`requirements.txt`): `fastapi`, `uvicorn`, `pydantic`, `pytest`,
`httpx`, `openai`, `anthropic`.

Verify install:

```bash
python -m pytest
python -m app.cli survey
```

---

## CLI (`python -m app.cli`)

Help:

```bash
python -m app.cli --help
python -m app.cli eval --help
```

### `survey` — answer-key lock status (v1)

Shows per-scenario survey agreement and whether the v1 answer key is locked.
No API keys required.

```bash
python -m app.cli survey
```

Data sources:

- `data/survey/phase1_survey_responses.json` — 10-respondent votes (currently
  **synthetic placeholder**; replace before reporting results)
- `data/answer_keys/v1_constraints.json` — structured policy fields for v1

Locking rule: a surveyed v1 scenario locks when ≥7/10 agree; team-keyed
scenarios lock without a survey. v2 scenarios stay `provisional` until their
own survey exists.

### `eval` — Phase 1 model evaluation harness

```bash
python -m app.cli eval [options]
```

| Flag | Default | Description |
| --- | --- | --- |
| `--models` | `openai` | Comma-separated: `openai`, `anthropic`, `openweights`, `baseline_naive`, or `all` |
| `--conditions` | `no_policy,prompt_policy,tool_constraints` | Control layers to test |
| `--scenario-ids` | all in set | Filter, e.g. `scn_v1_a1_trap,scn_v1_a1_lookalike` |
| `--scenario-set` | v1 (50 scenarios) | Path to Markdown set, e.g. `data/scenario_sets/v2_250_scenarios.md` |
| `--seeds` | `1,2,3,4,5` | Seeds per (model, condition, scenario) combo |
| `--temperature` | `0.7` | Model sampling temperature |
| `--dry-run` | off | Offline fake providers — **no real API calls** |

Results save to `runtime/runs/run_<id>.json`. CLI prints unsafe-payment and
false-refusal rates with Wilson CIs per model/control combo.

**Total eval count** = `scenarios × conditions × seeds × models`

Examples:

```bash
# Offline smoke test (fast, no API)
python -m app.cli eval --models openai --scenario-ids scn_v1_a1_trap --seeds 1 --dry-run

# Naive baseline — offline heuristic, calibrates scorer (fast)
python -m app.cli eval --models baseline_naive --seeds 1

# v2 single scenario
python -m app.cli eval \
  --models openai \
  --scenario-set data/scenario_sets/v2_250_scenarios.md \
  --scenario-ids scn_v2_a1_trap \
  --seeds 1 \
  --dry-run

# Live OpenAI — slow, real API calls (no --dry-run)
export OPENAI_API_KEY=...
python -m app.cli eval \
  --models openai \
  --conditions no_policy,prompt_policy,tool_constraints \
  --seeds 1,2,3,4,5

# All providers (each needs env configured)
export ANTHROPIC_API_KEY=... ANTHROPIC_MODEL=...
export OPENWEIGHTS_BASE_URL=http://127.0.0.1:8001 OPENWEIGHTS_MODEL=...
python -m app.cli eval --models all
```

#### Fast vs slow — when to trust results

| Run type | API calls? | Speed | Use for |
| --- | --- | --- | --- |
| `--dry-run` | No | Sub-second to seconds | Pipeline smoke test only |
| `--models baseline_naive` | No | ~0.3s for 750 combos | Scorer calibration |
| Live `openai` / `anthropic` / `openweights` | Yes, one per combo | Hours at full scale | Real model results |

Full v2 live run example: 250 × 3 conditions × 5 seeds = **3,750 API calls**
per model.

---

## Phase 2 mockup commands (`phase2-*`)

**All Phase 2 commands are MOCKUPS.** They exercise the full Phase 2 pipeline
(six-condition ablation, framing test, survey, human baseline, transfer check)
with deterministic hash-seeded mock agents — no live models, no sandbox
payment platform, no API keys. The numbers are illustrative only.

Phase 2 lives in `app/phase2.py` and is fully separate from Phase 1: the
Phase 1 commands (`eval`, `survey`, `test`, `smoketest-*`) never import it,
and the Phase 1 runner still rejects the Phase 2-only control conditions.

### `phase2-eval` — six-condition ablation + evaluation-awareness framing

```bash
python -m app.cli phase2-eval                          # full v2 set, all six conditions, both framings
python -m app.cli phase2-eval \
  --models mock_weak,mock_strong \
  --conditions no_policy,preflight_check,approval_gate \
  --framings deployment \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --seeds 1,2
```

| Flag | Default | Description |
| --- | --- | --- |
| `--models` | `mock_weak,mock_strong` | Mock agents: `mock_weak`, `mock_strong`, `mock_baseline_naive` |
| `--conditions` | all six | `no_policy`, `prompt_policy`, `structured_policy`, `preflight_check`, `tool_constraints`, `approval_gate` |
| `--framings` | `evaluation,deployment` | Evaluation-awareness framing variants |
| `--scenario-set` | v2 (250 scenarios) | Markdown scenario-set path |
| `--scenario-ids` / `--seeds` | all / `1,2,3,4,5` | Same semantics as Phase 1 `eval` |

Runs save to `runtime/runs/` like Phase 1 runs, tagged `"phase": "phase2_mock"`,
with extra `metrics.phase2` blocks (`by_framing`, `by_condition_and_framing`).
Enforcement mocks: `tool_constraints` hard-blocks enforceable trap payments,
`preflight_check` blocks them only when the mock agent remembers to invoke the
check (~70%), and `approval_gate` pauses all trap payments plus some safe
high-stakes ones (raising false refusals — the frontier trade-off).

### `phase2-survey` — synthetic 50-participant answer-key survey (v2)

```bash
python -m app.cli phase2-survey
```

Prints per-scenario modal answers and agreement out of 50 synthetic
respondents; lock threshold is 35/50 (70%). Replace with real survey data
before reporting results.

### `phase2-transfer` — simulated-vs-sandbox transfer check

```bash
python -m app.cli phase2-transfer [--seeds 1,2,3,4,5] [--model mock_weak]
```

Reruns the 25 v1 trap scenarios in two mocked environments and reports
per-scenario unsafe rates plus their Pearson correlation.

### `phase2-human-baseline` — simulated human baseline

```bash
python -m app.cli phase2-human-baseline [--participants 8] [--sample-size 40]
```

Prints the confusion matrix and headline rates for simulated participants on
a sample of v2 tasks.

---

## Web server and dashboard

Start the server (any of these):

```bash
uvicorn app.main:app --reload
python implementation.py
python -m app.main
```

- Dashboard: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

The dashboard lets you pick models, control conditions, category/scenario
filters, and a **Live run** toggle, then POST to `/api/runs`. Default seeds in
the UI are `[1, 2, 3, 4, 5]`.

---

## HTTP API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Dashboard UI (`static/index.html`) |
| `GET` | `/api/agents` | Deterministic demo agent profiles |
| `GET` | `/api/models` | Model provider profiles |
| `GET` | `/api/control-conditions` | Control-layer profiles |
| `GET` | `/api/scenarios` | All scenarios from default scenario set |
| `GET` | `/api/scenarios/{scenario_id}` | One scenario |
| `POST` | `/api/runs` | Start a benchmark run |
| `GET` | `/api/runs` | List run summaries |
| `GET` | `/api/runs/{run_id}` | Full run payload |
| `GET` | `/api/runs/{run_id}/events` | Audit events for a run |
| `GET` | `/api/metrics` | Metrics for latest run |
| `GET` | `/api/metrics?run_id=...` | Metrics for a specific run |
| `GET` | `/search?query=...` | Mock product catalog search |
| `POST` | `/execute-payment` | Legacy compatibility payment eval endpoint |

Static assets: `static/` (`index.html`, `app.js`, `styles.css`).

### `POST /api/runs` body

Supports **two modes** (see `RunRequest` in `app/models.py`):

**Phase 1 model eval** (preferred):

```json
{
  "model_ids": ["openai"],
  "control_conditions": ["no_policy", "prompt_policy", "tool_constraints"],
  "scenario_ids": ["scn_v1_a1_trap"],
  "scenario_set_path": "data/scenario_sets/v2_250_scenarios.md",
  "seeds": [1, 2, 3, 4, 5],
  "temperature": 0.7,
  "live": false
}
```

**Legacy deterministic agents** (no `model_ids` / `control_conditions` / `seeds`):

```json
{
  "agent_ids": ["baseline_surface_agent", "tool_constrained_agent"],
  "scenario_ids": ["scn_v1_a1_trap"]
}
```

If `model_ids`, `control_conditions`, `seeds`, or `live` is set, the Phase 1
path is used. Otherwise `agent_ids` run through scripted deterministic agents.

---

## Model providers (`--models`)

| ID | Live behavior | Required env |
| --- | --- | --- |
| `openai` | OpenAI Responses API | `OPENAI_API_KEY`; optional `OPENAI_MODEL` (default `gpt-5.5`) |
| `anthropic` | Anthropic Messages API | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `openweights` | OpenAI-compatible `/v1/chat/completions` | `OPENWEIGHTS_BASE_URL`, `OPENWEIGHTS_MODEL`; optional `OPENWEIGHTS_API_KEY` (default `local`) |
| `baseline_naive` | Offline heuristic — always cheapest, never ask | None |
| `all` | Runs all four above | All configured keys/URLs |

With `--dry-run`, live model IDs use `DryRunProvider` (offline scripted
actions). `baseline_naive` is always offline regardless of `--dry-run`.

---

## Control conditions (`--conditions`)

| ID | What the model receives |
| --- | --- |
| `no_policy` | Task context only |
| `prompt_policy` | Policy instructions in the system prompt |
| `tool_constraints` | Prompt policy plus simulated payment-tool hard blocks (`apply_tool_constraints` in `app/policies.py`) |

Phase 2 conditions from the research plan (structured policy, preflight check,
human approval gate) are **not implemented** in the current harness.

---

## Deterministic demo agents (legacy API path)

Used when `POST /api/runs` is called with `agent_ids` and no Phase 1 fields.
Defined in `app/agents.py`:

| ID | Behavior summary |
| --- | --- |
| `baseline_surface_agent` | Surface-level task completion; unsafe on traps, safe on lookalikes (v1 Markdown) |
| `prompt_policy_agent` | Follows some prompt policy; still fails on several categories |
| `structured_policy_agent` | Checks structured fields; safe on v1 Markdown set |
| `human_approval_agent` | Escalates ambiguity; can false-refuse lookalikes |
| `tool_constrained_agent` | Hard limits help spend/merchant cases; misses semantic failures |
| `audit_review_agent` | Structured policy + approval + audit; safe on v1 Markdown set |

These are **not** the same as `baseline_naive`. The naive baseline is a
heuristic provider for Phase 1 CLI evals.

---

## Scenario sets and data files

| Path | Role |
| --- | --- |
| `data/scenario_sets/v1_50_scenarios.md` | **Default** — 50 scenarios (25 trap/lookalike pairs) |
| `data/scenario_sets/v2_250_scenarios.md` | Phase 2 expansion — 250 scenarios (125 pairs) |
| `data/answer_keys/v1_constraints.json` | Machine-checkable policy fields for v1 only |
| `data/survey/phase1_survey_responses.json` | Survey votes for preference-dependent v1 scenarios |
| `data/catalog.json` | Mock merchant/product catalog for `/search` |

Scenario IDs are derived at load time, e.g. `scn_v1_a1_trap`, `scn_v2_a1_trap`.
There is intentionally no editable `data/scenarios.json` copy.

### Choosing a scenario set

1. CLI: `--scenario-set data/scenario_sets/v2_250_scenarios.md`
2. Env: `SCENARIO_SET=v2_250_scenarios` or `SCENARIO_SET_PATH=<path>`
3. API: `"scenario_set_path": "data/scenario_sets/v2_250_scenarios.md"`

v2 has **provisional** answer keys (no `v2_constraints.json` yet).

---

## Environment variables

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Live OpenAI evals |
| `OPENAI_MODEL` | OpenAI model name (default `gpt-5.5`) |
| `ANTHROPIC_API_KEY` | Live Anthropic evals |
| `ANTHROPIC_MODEL` | Anthropic model name (required for anthropic provider) |
| `OPENWEIGHTS_BASE_URL` | OpenAI-compatible local server base URL |
| `OPENWEIGHTS_MODEL` | Model name on that server |
| `OPENWEIGHTS_API_KEY` | Auth header for open-weights server (default `local`) |
| `SCENARIO_SET` | Scenario filename stem, e.g. `v2_250_scenarios` |
| `SCENARIO_SET_PATH` | Full path to a scenario Markdown file |
| `RUN_LIVE_OPENAI_EVAL` | Set to `1` to enable `tests/test_live_openai.py` |

---

## Tests

```bash
python -m pytest                         # all tests
python -m pytest tests/test_cli.py       # one file
python -m pytest -k "naive"              # filter by name
```

| Test file | Covers |
| --- | --- |
| `test_cli.py` | CLI eval and survey |
| `test_data.py` | Scenario Markdown parsing |
| `test_policy.py` | Scoring, baseline agent, rule violations |
| `test_providers.py` | Provider parsing, naive baseline, dry-run |
| `test_survey.py` | Survey locking logic |
| `test_metrics.py` | Metric aggregation and CIs |
| `test_phase1_runner.py` | Full Phase 1 eval loop |
| `test_agents.py` | Deterministic agent actions |
| `test_api.py` | FastAPI endpoints |
| `test_live_openai.py` | Live OpenAI smoke (needs `RUN_LIVE_OPENAI_EVAL=1` + `OPENAI_API_KEY`) |

---

## Output and metrics

Runs save to `runtime/runs/run_<id>.json`.

Headline metrics (CLI summary and `metrics.by_agent`):

- **Unsafe payment rate** — wrongly proceeded when safe action was stop/ask
- **False refusal rate** — wrongly stopped when autonomous action was allowed
- Wilson confidence intervals on both (when `safe_to_act` is set on scenarios)

Additional metrics in full payload: `approval_failure_rate`,
`privacy_leakage_rate`, `welfare_loss_rate`, `failure_taxonomy`,
`by_category`, `by_stakes`, `error_count`, etc. See `app/metrics.py`.

Agent actions must be one of: `purchase`, `pay_tool`, `send_stablecoin`,
`ask_approval`, `refuse`, `defer`.

---

## Source code map

| Module | Responsibility |
| --- | --- |
| `app/cli.py` | `survey` and `eval` commands |
| `app/main.py` | FastAPI app and routes |
| `app/runner.py` | Eval loop (`run_phase1_evaluation`, `run_benchmark`) |
| `app/providers.py` | OpenAI, Anthropic, open-weights, naive baseline, dry-run |
| `app/policies.py` | Tool constraints and action scoring |
| `app/data.py` | Markdown scenario parsing, catalog load |
| `app/survey.py` | Survey aggregation and lock status |
| `app/agents.py` | Legacy deterministic agents |
| `app/metrics.py` | Safety-autonomy metrics |
| `app/storage.py` | Run JSON persistence |
| `implementation.py` | Alternate uvicorn entrypoint |

---

## Not implemented yet (see README)

- Phase 2 **real** sandbox infrastructure (the `phase2-*` commands are mockups)
- v2 answer key / constraints JSON and a real powered survey
- Additional payment rails as first-class benchmark scope
- Real human baseline collection workflow
- Live-model runs under the Phase 2 six-condition ablation

For those topics, [README.md](README.md) remains the source of truth.
