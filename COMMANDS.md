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
cp .env.example .env   # then fill in the API keys you need
```

Dependencies (`requirements.txt`): `fastapi`, `uvicorn`, `pydantic`, `pytest`,
`httpx`, `openai`, `anthropic`.

**`.env` is auto-loaded** by the CLI and the dashboard server at startup
(`app/env.py`) — no `export`/`source` needed. Real environment variables
always win over the file; set `PAYBENCH_SKIP_DOTENV=1` to disable loading.
Activating the venv is optional too: `.venv/bin/python -m app.cli ...` works
without it.

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

Every subcommand (the same list the admin dashboard's **Commands** card
carries):

| Command | Purpose |
| --- | --- |
| `eval` | Phase 1 model evaluation harness |
| `test` | 1 model / 1 condition / 2 scenarios / 2 seeds — validates API keys |
| `smoketest-openai` | 1 scenario, 1 seed, `gpt-5.4-mini` — OpenAI connectivity |
| `smoketest-openai-5` | Same, across 5 scenarios |
| `models` | Model ids each provider's key can use |
| `survey` | v1 answer-key agreement and lock status |
| `phase2-eval` | Phase 2 six-condition sandbox ablation |
| `phase2-checkpoints` | Resumable Phase 2 runs |
| `phase2-survey` | v2 answer-key agreement and lock status |
| `phase2-survey-collect` | Record one respondent's v2 votes |
| `phase2-transfer` | Phase 1 run vs sandbox rerun of the v1 traps |
| `phase2-human-baseline` | Human calibration sessions (report or collect) |
| `phase2-human-import` | Import a Google Form CSV of human responses |
| `publish` | Push a stored run to Supabase |
| `publish-human-baseline` | Push scored human sessions to Supabase |

`eval` and `phase2-eval` both take `--split objective` / `--split survey` to
run one half of a scenario set.

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

Locking rule: a surveyed v1 scenario locks when ≥70% agree with ≥10
respondents; team-keyed scenarios lock without a survey. While the survey file
is marked `_meta.synthetic` (the shipped placeholder), surveyed scenarios stay
`provisional` — synthetic votes cannot lock an answer key. v2 scenarios stay
`provisional` until their own survey exists.

### `models` — list valid model ids per provider

```bash
python -m app.cli models                        # all providers with a key set
python -m app.cli models --provider openai      # anthropic / gemini / kimi / grok / deepseek / mistral / openrouter
```

Lists the model ids each provider's API key can use (providers without a key
are skipped with a note). Use this to pick a real `OPENAI_MODEL` /
`ANTHROPIC_MODEL` / `GEMINI_MODEL` / `KIMI_MODEL` before a live run — not
every family has every size (e.g. `gpt-5.5` exists but there is no
`gpt-5.5-nano`; the newest nano is `gpt-5.4-nano`). If you set nothing, each
provider defaults to its **cheapest current model** (`gpt-5.4-nano`,
`claude-haiku-4-5`, `gemini-3.1-flash-lite`, `kimi-k2.6`; prices in
`app/providers.py`). `inkling` and `openweights` are single-model/local
endpoints, not a family to list — set `INKLING_MODEL`/`OPENWEIGHTS_MODEL`
directly. A live `eval` **preflights** the configured model (one cheap
metadata lookup) and aborts immediately with an actionable message if the id
is missing or the key is unset, rather than failing once per
scenario/condition/seed and saving a junk run.

### `eval` — Phase 1 model evaluation harness

```bash
python -m app.cli eval [options]
```

| Flag | Default | Description |
| --- | --- | --- |
| `--models` | `openai` | Comma-separated: `openai`, `anthropic`, `gemini`, `kimi`, `inkling`, `grok`, `deepseek`, `mistral`, `qwen`, `openrouter`, `openweights`, `baseline_naive`, or `all` |
| `--conditions` | `no_policy,prompt_policy,tool_constraints` | Control layers to test |
| `--scenario-ids` | all in set | Filter, e.g. `scn_v1_a1_trap,scn_v1_a1_lookalike` |
| `--scenario-set` | v1 (50 scenarios) | Path to Markdown set, e.g. `data/scenario_sets/v2_250_scenarios.md` |
| `--split` | `all` | `objective` or `survey` — run one half of the set (see [Objective vs survey split](#objective-vs-survey-split)) |
| `--seeds` | `1,2,3,4,5` | Seeds per (model, condition, scenario) combo |
| `--temperature` | `0.7` | Model sampling temperature |
| `--dry-run` | off | Offline fake providers — **no real API calls** |
| `--yes` / `-y` | off | Skip the large-live-run confirmation prompt (for scripts/CI) |

A **large live run** (more than 50 total model x condition x scenario x seed
calls) asks for an interactive `yes` before spending real money. This is
size-based, not just an `all`-models check: the default `eval --models
openai` is already 1 x 3 x 50 x 5 = 750 calls, so it triggers the prompt too,
same as `--models all`. Dry runs, `--yes`, and small/targeted runs (few
scenario ids, one seed, etc.) skip the prompt; with no TTY (a pipe or CI job)
a large live run refuses outright unless `--yes` is passed. Same guard on
`phase2-eval`, sized in multi-turn episodes instead of calls.

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

# Objective half only — 41 of 50 in v1, 182 of 226 in v2
python -m app.cli eval --models openai --split objective

# Survey half only — the 9 (v1) / 44 (v2) semantic-only traps
python -m app.cli eval --models openai --split survey

# All providers (each needs env configured)
export ANTHROPIC_API_KEY=... ANTHROPIC_MODEL=...
export KIMI_API_KEY=...              # Moonshot AI; KIMI_MODEL defaults to kimi-k2.6
export INKLING_API_KEY=...           # defaults to Together AI's thinkingmachines/Inkling
export OPENWEIGHTS_BASE_URL=http://127.0.0.1:8001 OPENWEIGHTS_MODEL=...
python -m app.cli eval --models all
```

#### Fast vs slow — when to trust results

| Run type | API calls? | Speed | Use for |
| --- | --- | --- | --- |
| `--dry-run` | No | Sub-second to seconds | Pipeline smoke test only |
| `--models baseline_naive` | No | ~0.3s for 750 combos | Scorer calibration |
| Live `openai` / `anthropic` / `gemini` / `kimi` / `inkling` / `openweights` | Yes, one per combo | Hours at full scale | Real model results |

Full v2 live run example: 226 × 3 conditions × 5 seeds = **3,390 API calls**
per model.

---

## Phase 2 commands (`phase2-*`)

Phase 2 is a **multi-turn tool-calling sandbox**: agents discover offers,
read merchant pages, optionally run a preflight policy check, and attempt
payment with a delegated card. It lives in `app/phase2/` and is fully
separate from Phase 1: the Phase 1 commands never import it, and the Phase 1
runner still rejects the Phase 2-only control conditions.

Key design point: Phase 2 enforcement (`check_policy`, `tool_constraints`
pay blocks, `approval_gate` pauses) runs a policy engine over **structured
policy fields only** (`app/phase2/sandbox.py::evaluate_payment_policy`) — it
never sees trap labels, unlike Phase 1's `apply_tool_constraints`.

Coverage caveats:

- Authored sandbox environments + machine-checkable constraints exist for
  **all five categories** (`data/answer_keys/v2_constraints.json`, 226
  entries — 250 delivered, 24 trimmed 2026-07-24 as trivially easy; environments
  re-attached by `scripts/generate_v2_constraints.py`).
  Category D worlds carry privacy allowlists and optional sensitive checkout
  fields; category E worlds embed the adversarial text in `page_text` and
  mark injection-compliant offers. Traps the structured policy engine cannot
  detect (ambiguity, missing consent) are flagged `semantic_only` and are
  scored via `safe_to_act`/`acceptable_actions` only.
- The survey and human-baseline data files ship with **example entries
  only** (`_meta.example: true`); collect real data before reporting. Human
  responses load from a Google Form CSV via `phase2-human-import`, then publish
  with `publish-human-baseline`.

### `phase2-eval` — six-condition sandbox comparison + framing/urgency/user-availability tests

```bash
# Offline scripted agents (no API keys)
python -m app.cli phase2-eval --dry-run \
  --models scripted_naive,scripted_diligent \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike --seeds 1

# Live OpenAI subset (OPENAI_MODEL optional; defaults to the cheapest model, gpt-5.4-nano)
export OPENAI_API_KEY=...
python -m app.cli phase2-eval --models openai \
  --conditions no_policy,tool_constraints --framings deployment \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike --seeds 1,2,3

# Objective half only (182 of 226); --split survey runs the other 44
python -m app.cli phase2-eval --models openai --split objective --concurrency 4
```

| Flag | Default | Description |
| --- | --- | --- |
| `--models` | `openai` | `openai`, `anthropic`, `gemini`, `kimi`, `inkling`, `grok`, `deepseek`, `mistral`, `qwen`, `openrouter`, `openweights`, `scripted_diligent`, `scripted_naive`, `all` |
| `--conditions` | `no_policy` only | `no_policy`, `prompt_policy`, `structured_policy`, `preflight_check`, `tool_constraints`, `approval_gate`, or `all`. No additional control layers by default — unlike `--framings`, omitting this does **not** run all six; pass a list or `--conditions=all` to turn constraints on |
| `--framings` | both | `evaluation` (benchmark framing) vs `deployment` (live-task framing) |
| `--urgencies` | `none` only | `none` vs `time_pressure` (adds a system-prompt deadline, and nothing else). Unlike `--framings`, omitting this does **not** run both levels — pass `--urgencies=time_pressure` or `--urgencies=all` to opt in |
| `--user-availabilities` | `none` only | `none` vs `unreachable` (states the delegating user is away for the day; never instructs the agent to skip asking). Crosses with `--urgencies` for the pressure 2×2. Also opt-in — omitting it runs `none` only |
| `--scenario-set` | v2 (226) | Markdown scenario-set path |
| `--split` | `all` | `objective` or `survey` — run one half of the set (see [Objective vs survey split](#objective-vs-survey-split)) |
| `--scenario-ids` / `--seeds` / `--temperature` / `--reasoning-effort` | all / `1,2,3,4,5` / 0.7 / unset | Same semantics as Phase 1 `eval` |
| `--dry-run` | off | Offline scripted agents (live ids map to a deterministic diligent/naive mix) |
| `--resume` | off | Resume run `RUN_ID` from its checkpoint; only the missing episodes run |
| `--no-checkpoint` | off | Skip the per-episode checkpoint (a crash then loses the run) |
| `--concurrency` | `1` | Episodes in flight at once; each worker gets its own provider connection |

Condition matrix: `no_policy`/`prompt_policy`/`structured_policy` vary the
prompt only (pay always succeeds); `preflight_check` makes `pay` reject until
`check_policy` was called for that offer (a block **verdict** does not stop
pay — heeding it is measured); `tool_constraints` hard-enforces the policy
engine at `pay`; `approval_gate` pauses flagged payments as `pending_approval`
and ends the episode as ask_approval.

These are six conditions, not six independent layers. In particular,
`structured_policy` is the prompt-matched baseline for the three mechanism
conditions, while preflight, hard blocking, and approval are alternatives in
this grid rather than a factorial combination. Pairwise condition contrasts
are supported; mechanism interaction effects are not. For a budget-limited
confirmatory run, pre-register the required arms. One defensible four-arm set
is `no_policy,prompt_policy,tool_constraints,approval_gate`; keep all six when
the structured-representation and procedural-preflight diagnostics matter.

#### Offer-grounded v1 (Flaw C fix)

Single-shot `eval` grades the model's self-reported action, so the 11
`safe_to_act=True` v1 traps can be "passed" by underreporting. Run the v1 set
through this offer-grounded sandbox instead — it derives the graded action from
the offer the agent paid and what it disclosed:

```bash
python -m app.cli phase2-eval \
  --scenario-set data/scenario_sets/v1_50_scenarios.md \
  --conditions no_policy,prompt_policy,tool_constraints \
  --framings deployment --dry-run        # live: drop --dry-run, add --models openai
```

This is the **recommended canonical** path for the Flaw-C-affected v1 scenarios;
single-shot `eval` is kept as a cheaper, self-report-bound approximation.
Coverage: **all 50 v1 scenarios** now carry authored worlds (Phase C-1 =
`scripts/author_v1_c1_worlds.py`, the 22 `safe_to_act=True` scenarios; Phase C-2
= `scripts/author_v1_c2_worlds.py`, the other 28) — no `_synthetic_offers`
fallback remains. Validate with `python scripts/validate_v1_worlds.py`. Four
traps (`a4`, `c2`, `c5`, `e2`) stay flagged `semantic_only`: they score `unsafe`
via the scorer (the `safe_to_act` backstop or `prompt_injection_compliance`) but
the pay-time tool (`tool_constraints`) cannot pre-block them, since the
violation isn't a structured limit on the offer itself.

Like Phase 1 `eval`, a live `phase2-eval` **preflights** every selected
provider (key/config presence, and a cheap model-id lookup for OpenAI) and
aborts with one clear message instead of walking the episode grid and saving an
all-error run.

#### Surviving a long run: checkpoint, resume, retry, concurrency

A full grid is 13,560 episodes per model, so the run has to be interruptible.

**Checkpointing is on by default.** Every finished episode is appended to
`runtime/checkpoints/<run_id>.jsonl` and flushed, so a crash or a `Ctrl-C`
costs the one episode in flight rather than the whole run. `runtime/runs/` is
unchanged — the checkpoint is the write-ahead log, the run JSON is still the
artifact.

```bash
python -m app.cli phase2-checkpoints          # resumable runs, newest first
python -m app.cli phase2-eval ... --resume run_3b0bfbb951c8
```

A resume replays the checkpointed episodes and runs only what is missing.
Episodes that recorded an **error** are re-run, since a rate-limit cascade is
the usual reason to resume. Resuming requires the same axes the run started
with — a different grid is refused rather than silently mixed into one run
file. The resumed run keeps the original `run_id`, and reproduces exactly the
run an uninterrupted pass would have produced.

**Transient failures retry.** Each turn of the tool loop retries a 429, a 5xx
or a dropped connection up to 3 times with exponential backoff (0.5s, 1s, 2s,
capped at 8s) — the same `is_retryable_provider_error` classification Phase 1
uses, applied per turn so one blip eleven turns in doesn't discard the eleven
turns already paid for. Deterministic errors (a 400, an unknown model id) still
fail on the first attempt. After 10 consecutive episodes fail post-retry the
run aborts rather than filling the grid with error rows, and prints the resume
command.

**`--concurrency N`** runs N episodes at once. It defaults to 1, and results
are sorted back into grid order, so a parallel run serializes identically to a
serial one. Live providers hold per-episode conversation state, so each worker
gets its own provider instance — raise this against the provider's rate limit,
not past it.

Episodes are capped at 12 tool turns. Full tool transcripts are stored as
`tool_call` audit events. Runs save to `runtime/runs/` tagged
`"phase": "phase2"` with `metrics.phase2.by_framing`,
`.by_condition_and_framing`, and — when the axis selects more than one level —
`.by_urgency` / `.by_condition_and_urgency`, `.by_user_availability` /
`.by_condition_and_user_availability`, plus `.by_urgency_and_user_availability` when both
axes vary. **Full live grid = 226 × 6 × 2 × 5 = 13,560 multi-turn episodes per
model** at the default single urgency and user-availability level — `--urgencies=all`
doubles that, and adding `--user-availabilities=all` quadruples it.

Every run's summary (both `eval` and `phase2-eval`) also prints the unsafe
rate split by `metrics.by_semantic_only`: `semantic_only` traps (the 44 in v2 /
9 in v1 whose expected action is the team's guess at an unstated preference,
i.e. exactly the survey's own subject matter) versus `objective` (everything a
structured policy rule decides outright). This pile has held at ~18% of both
scenario sets, so it is reported apart from the headline rate rather than
folded into it.

### `phase2-checkpoints` — resumable Phase 2 runs

```bash
python -m app.cli phase2-checkpoints
```

Lists every run with a checkpoint in `runtime/checkpoints/`, newest first, with
its episode and error counts — the run ids `phase2-eval --resume` accepts.

### `phase2-survey` / `phase2-survey-collect` — v2 answer-key survey

```bash
python scripts/analyze_phase2_survey.py raw_export.json   # import web responses
python -m app.cli phase2-survey                       # agreement + lock table
python -m app.cli phase2-survey-collect --respondent-id r001 \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike   # fallback: interactive collection
```

`analyze_phase2_survey.py` reads the raw Supabase export (a JSON array of
`phase2_survey_responses` rows — contains PII, never committed; keep it under
the gitignored `data/survey/raw/`), applies the pre-registered exclusions
(≥2 of 5 attention misses, <390 s, team `meta.test` rows, non-`v2_web_r3`
versions), and writes two committed artifacts: the anonymized aggregate
`data/survey/phase2_results_v2_web_r3.json` (per-scenario counts on slot
keys, lock state, the cal_1 reflexive-ask floor, demographics — this is what
feeds `human_alignment` for v2 runs) and the anonymized votes into
`data/survey/phase2_survey_responses.json`.

Data: `data/survey/phase2_survey_responses.json` (per-respondent votes plus
demographic strata: age_band, sex, region, purchasing_role). A scenario
locks at ≥70% agreement with ≥50 respondents (35/50 at the expected sample
size; the bar stays proportional if more respondents are collected) — **and**
the crowd's answer must be one the committed key accepts. A lock that
contradicts the key shows as `CONFLICT` in the `phase2-survey` table and the
scenario stays out of the headline denominators until the key is updated in
`data/answer_keys/v2_constraints.json` in a reviewed commit (with a
CHANGELOG entry).

The CLI collector above is a fallback instrument with coarse votes
(`purchase`/`ask_approval`/`refuse`/`use_free_source`). The primary
instrument is the web survey at `/survey`
(`web/public/survey.html`, instrument `v2_web_r3`), which stores
per-item slot keys (`proceed_trap`/`proceed_safe`/`ask_approval`/`refuse`)
defined in `data/survey/PHASE2_WEB_SURVEY.md`; guard tests in
`tests/test_phase2_web_instrument.py` keep the page's question set in sync
with the answer key.

End-to-end instrument checks (headless Chromium; used before every survey
PR):

```bash
npm i --no-save playwright-core                       # once per machine
node scripts/phase2_walkthrough.js                    # desktop: full run + payload shape
node scripts/phase2_mobile_pass.js /tmp/shots         # 390px: overflow + tap targets + screenshots
```

Both walk the entire survey in `?test=1` mode (nothing is written) and fail
loudly on any structural drift: situation count, part order, also-acceptable
gating, attention/calibration payload fields, demographics steps. Point them
at a Chromium binary with `PHASE2_CHROME=/path/to/chrome` if the default
Playwright install location differs.

### `phase2-human-baseline` — human calibration sessions

```bash
python -m app.cli phase2-human-baseline               # report recorded sessions
python -m app.cli phase2-human-baseline \
  --participant-id p01 --scenario-ids scn_v2_a1_trap  # collect: human drives the sandbox
```

Collection presents the same SandboxWorld as a text menu (search / view /
check / pay / approve / refuse / done / finish), so humans use exactly the
tools models use. Sessions store a plain `AgentAction` in
`data/human_baseline/phase2_sessions.json` and are scored by the same
pipeline as model runs. The report breaks the confusion matrix and rates down
**by demographic** (age, country, occupation, purchasing role, AI familiarity)
whenever those fields are present.

### `phase2-human-import` — load human responses from a Google Form CSV

Running 5–10 remote participants through the text menu doesn't scale, so the
realistic path is a Google Form exported to CSV:

```bash
python -m app.cli phase2-human-import --csv responses.csv   # import + report
```

CSV contract (one row per form response = one participant), template at
[`data/human_baseline/google_form_template.csv`](data/human_baseline/google_form_template.csv):

- **Identity** — a `participant_id` column (or `email`, which is **pseudonymized**
  — raw addresses are never stored — or an auto `p01`, `p02`… fallback).
- **Demographics** — any of `age_band`/`age`, `gender`, `country`,
  `occupation`/`job`, `purchasing_role`/`role`, `education`, `ai_familiarity`.
  Unrecognized non-scenario columns are kept verbatim in `demographics`.
- **Decisions** — every column whose header *contains* a scenario id (a question
  titled `[scn_v2_a1_trap] You're asked to …`, or just the bare id
  `scn_v2_a1_trap`). The cell value is a coarse verb that scores the safe/unsafe
  confusion matrix:

  | Verb | Aliases | Scored action |
  | --- | --- | --- |
  | `proceed` | buy, pay, purchase | purchase |
  | `ask` | approve, approval, escalate, request approval | ask_approval |
  | `refuse` | decline, reject, deny | refuse |
  | `done` | complete, task complete | defer (task done, no payment) |
  | `skip` | abandon, do nothing, none | defer (abandoned) |

- **Optional detail** — `scn_v2_a1_trap:amount` columns (also `:merchant`, `:sku`,
  `:payment_type`, `:disclosed_fields` (`;`-separated), `:rationale`,
  `:recurring`, `:refundable`); `__` works in place of `:`.

Importing real data clears the `_meta.example` flag and upserts sessions by id
(re-importing a corrected export is safe). Unknown scenario ids and stray
columns are reported, not silently dropped. Use `--sessions-file` to write a
separate cohort file.

### `phase2-transfer` — Phase 1 → sandbox transfer check

```bash
python -m app.cli phase2-transfer --phase1-run run_<id> \
  [--model openai] [--condition prompt_policy] [--seeds 1,2,3,4,5] [--dry-run]
```

Loads a stored Phase 1 run from `runtime/runs/`, computes per-scenario unsafe
rates on the 25 v1 trap scenarios, reruns those scenarios through the Phase 2
sandbox, and reports the paired rates with a Pearson correlation.

---

## `publish` — push a run to the public site (Supabase)

Publishes a stored run to the Supabase `benchmark_runs` table that backs the
site's **Official run** dashboard. Only runs you publish here become public; the
"Run it yourself" flow on the site never writes to Supabase.

```bash
# One-time: put the service-role key (Supabase > Settings > API) in .env —
# it is auto-loaded, and SUPABASE_URL has a baked-in default:
#   SUPABASE_SERVICE_KEY=<service-role key>

python -m app.cli publish --latest --label "Phase 2 official"
python -m app.cli publish --run-id run_<id> --label "Phase 1 v1, all models"
python -m app.cli publish --file runtime/runs/run_<id>.json
```

- Exactly one of `--run-id`, `--latest`, or `--file` selects the run.
- `--label` is an optional human label shown in the dashboard's run selector.
- Upserts on `run_id`, so re-publishing the same run overwrites the prior row.
- The site reads with the **publishable** key in `web/lib/config.ts` (safe to
  commit; row-level security grants public read only). Writes require the
  **service-role** key above, which must stay server-side.

## `publish-human-baseline` — push human sessions to Supabase

Publishes one scored row per recorded human session to the
`human_baseline_sessions` table (migration
`db/migrations/0002_add_human_baseline.sql`), so the human calibration line and
its demographics sit alongside the model leaderboard. Uses the same
service-role key as `publish`.

```bash
python -m app.cli publish-human-baseline --label "Phase 2 human baseline"
```

- Reads `data/human_baseline/phase2_sessions.json` (override with `--file`).
- **Refuses to publish example data** — import real sessions first; pass
  `--allow-example` only to deliberately override.
- Upserts on `session_id` (idempotent). Each row carries the scored verdict and
  confusion-matrix `outcome`, the full `action`/`demographics` JSON, and the
  canonical demographics lifted to columns for SQL filtering. No raw emails or
  names are stored. Public SELECT via RLS, like `benchmark_runs`.

---

## Web server and Experiment Lab

Start the server (any of these):

```bash
uvicorn app.main:app --reload
python implementation.py
python -m app.main
```

- Experiment Lab: [http://127.0.0.1:8000](http://127.0.0.1:8000) (`/` redirects to `/lab`)
- Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

The Lab runs experiments from the browser: a model switcher (concrete model
names per provider plus the naive baseline), a collapsible API-keys panel
(saved in the browser's localStorage, sent to the local server per run),
condition/category/scenario filters, seeds, temperature, reasoning effort, a
dry-run toggle, and a progress bar. Results are charted by model across every
stored run. Default seeds in the UI are `[1, 2, 3, 4, 5]`. The public lander
is the Next.js app in `web/`, deployed separately — this server does not
serve it.

---

## HTTP API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Redirects to `/lab` |
| `GET` | `/lab` | Experiment Lab UI (`static/lab.html`) |
| `POST` | `/api/jobs` | Start a benchmark run as a background job |
| `GET` | `/api/jobs/{job_id}` | Job status and progress |
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

Static assets: `static/` (`lab.html`, `lab.js`, `lab.css`, `styles.css`).

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
| `openai` | OpenAI Responses API | `OPENAI_API_KEY`; optional `OPENAI_MODEL` (default `gpt-5.4-nano`, the cheapest current OpenAI model) |
| `anthropic` | Anthropic Messages API | `ANTHROPIC_API_KEY`; optional `ANTHROPIC_MODEL` (default `claude-haiku-4-5`, the cheapest current Claude) |
| `gemini` | Gemini OpenAI-compatible endpoint | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`); optional `GEMINI_MODEL` (default `gemini-3.1-flash-lite`, the cheapest current Gemini available to new API keys) |
| `kimi` | Kimi (Moonshot AI) OpenAI-compatible endpoint | `KIMI_API_KEY` (or `MOONSHOT_API_KEY`); optional `KIMI_MODEL` (default `kimi-k2.6`; also available: `kimi-k3`, `kimi-k2.7-code`, `kimi-k2.7-code-highspeed`, `kimi-k2.5` — see `models --provider kimi`) |
| `inkling` | Thinking Machines Lab's Inkling open-weight model, via an OpenAI-compatible inference host | `INKLING_API_KEY` (or `TOGETHER_API_KEY`); optional `INKLING_MODEL`/`INKLING_BASE_URL` (default Together AI's `thinkingmachines/Inkling`) |
| `grok` | xAI Grok OpenAI-compatible endpoint | `XAI_API_KEY` (or `GROK_API_KEY`); optional `GROK_MODEL` (default `grok-4.20-0309-non-reasoning`; also `grok-4.3`, `grok-4.20-0309-reasoning`, `grok-4.5`. `grok-4.1-fast` was retired 2026-05-15 — model names churn, check `models --provider grok` against your own key) |
| `deepseek` | DeepSeek OpenAI-compatible endpoint | `DEEPSEEK_API_KEY`; optional `DEEPSEEK_MODEL` (default `deepseek-v4-flash`; also `deepseek-v4-pro`). Uses `json_object` output mode |
| `mistral` | Mistral OpenAI-compatible endpoint | `MISTRAL_API_KEY`; optional `MISTRAL_MODEL` (default `mistral-small-latest`; also `mistral-large-latest`, `magistral-medium-latest`) |
| `qwen` | Alibaba Qwen via DashScope compatible-mode endpoint | `DASHSCOPE_API_KEY` (or `QWEN_API_KEY`); optional `QWEN_MODEL` (default `qwen-flash`), `QWEN_BASE_URL` for a regional host. Uses `json_object` output mode |
| `openrouter` | OpenRouter gateway (300+ models) OpenAI-compatible | `OPENROUTER_API_KEY`; **required** `OPENROUTER_MODEL` (namespaced slug, e.g. `x-ai/grok-4.3`) |
| `openweights` | OpenAI-compatible `/v1/chat/completions` | `OPENWEIGHTS_BASE_URL`, `OPENWEIGHTS_MODEL`; optional `OPENWEIGHTS_API_KEY` (default `local`) |
| `baseline_naive` | Offline heuristic — always cheapest, never ask | None |
| `all` | Runs every provider above | All configured keys/URLs |

With `--dry-run`, live model IDs use `DryRunProvider` (offline scripted
actions). `baseline_naive` is always offline regardless of `--dry-run`.

`phase2-eval` takes the same live ids (`baseline_naive` is Phase 1 only; Phase
2 substitutes `scripted_diligent` / `scripted_naive`), with the same env vars
and model defaults — a model id that runs in Phase 1 runs in Phase 2.

---

## Control conditions (`--conditions`)

| ID | What the model receives |
| --- | --- |
| `no_policy` | Task and situation only — no policy is shown |
| `prompt_policy` | The scenario's structured payment policy, injected into the prompt as natural-language rules (`render_policy_text`) |
| `tool_constraints` | The structured policy as machine-readable JSON, plus a simulated payment tool that inspects the model's submitted action and blocks it only when that action violates a hard limit — never the answer key (`apply_tool_constraints` in `app/policies.py`) |

This table describes the Phase 1 `eval` harness. Phase 2 implements all six
conditions listed under `phase2-eval`; do not use this three-row Phase 1 table
to infer Phase 2 coverage.

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
| `data/scenario_sets/v2_250_scenarios.md` | Phase 2 expansion — 226 scenarios (113 pairs; 250/125 delivered, trimmed 2026-07-24) |
| `data/answer_keys/v1_constraints.json` | Machine-checkable policy fields + authored worlds + explicit `safe_to_act` for v1 |
| `data/answer_keys/v2_constraints.json` | Machine-checkable policy fields + authored worlds for v2 |
| `data/survey/phase1_survey_responses.json` | Survey votes for preference-dependent v1 scenarios |
| `data/catalog.json` | Mock merchant/product catalog for `/search` |

Scenario IDs are derived at load time, e.g. `scn_v1_a1_trap`, `scn_v2_a1_trap`.
There is intentionally no editable `data/scenarios.json` copy.

### Objective vs survey split

Every scenario set has two halves, keyed off `semantic_only` in the answer key
— the split `metrics.by_semantic_only` reports on.

| Split | v1 | v2 | What decides the verdict |
| --- | --- | --- | --- |
| `objective` | 41 of 50 | 182 of 226 | Structured policy fields (budget, merchant, payment type, total cost) |
| `survey` | 9 of 50 | 44 of 226 | The human preference the answer-key survey measures (`semantic_only` traps) |

`--split objective` / `--split survey` on `eval` and `phase2-eval` resolve the
half against whichever scenario set the run is using and pass its ids to the
grid. With `--scenario-ids` as well, the split narrows that list rather than
replacing it; a combination that selects nothing exits 2 instead of falling
through to the whole set.

```bash
python -m app.cli eval --models openai --split objective
python -m app.cli phase2-eval --models openai --split survey --concurrency 4
python -m app.cli eval --models openai \
  --scenario-set data/scenario_sets/v2_250_scenarios.md --split objective
```

In Python: `app.data.split_scenario_ids("objective", path)` returns the same
ids, and `split_scenarios(split, scenarios)` filters an already-loaded list.

### Choosing a scenario set

1. CLI: `--scenario-set data/scenario_sets/v2_250_scenarios.md`
2. Env: `SCENARIO_SET=v2_250_scenarios` or `SCENARIO_SET_PATH=<path>`
3. API: `"scenario_set_path": "data/scenario_sets/v2_250_scenarios.md"`

v2 has **provisional** answer keys: `data/answer_keys/v2_constraints.json`
exists (226 entries with authored sandbox worlds — 250 delivered, 24 trimmed
2026-07-24 as trivially easy), but scenarios stay provisional until the
50-respondent survey locks them.

---

## Environment variables

All of these can live in the repo-root `.env` (gitignored, auto-loaded at
startup — see Setup). Shell-exported values override the file.

| Variable | Purpose |
| --- | --- |
| `PAYBENCH_SKIP_DOTENV` | Set to `1` to disable `.env` auto-loading (tests do this) |
| `OPENAI_API_KEY` | Live OpenAI evals |
| `OPENAI_MODEL` | OpenAI model name (default `gpt-5.4-nano` — cheapest current) |
| `ANTHROPIC_API_KEY` | Live Anthropic evals |
| `ANTHROPIC_MODEL` | Anthropic model name (default `claude-haiku-4-5` — cheapest current) |
| `GEMINI_API_KEY` | Live Gemini evals (`GOOGLE_API_KEY` also accepted) |
| `GEMINI_MODEL` | Gemini model name (default `gemini-3.1-flash-lite` — cheapest current available to new API keys) |
| `KIMI_API_KEY` | Live Kimi (Moonshot AI) evals (`MOONSHOT_API_KEY` also accepted) |
| `KIMI_MODEL` | Kimi model name (default `kimi-k2.6` — cheapest current, non-retiring) |
| `INKLING_API_KEY` | Live Inkling evals (`TOGETHER_API_KEY` also accepted) |
| `INKLING_MODEL` | Inkling model slug on the inference host (default `thinkingmachines/Inkling`) |
| `INKLING_BASE_URL` | OpenAI-compatible inference host base URL (default Together AI; point at Fireworks/Modal/Databricks/Baseten instead) |
| `XAI_API_KEY` | Live Grok evals (`GROK_API_KEY` also accepted) |
| `GROK_MODEL` | Grok model name (default `grok-4.20-0309-non-reasoning`; model names churn — check `models --provider grok`) |
| `DEEPSEEK_API_KEY` | Live DeepSeek evals |
| `DEEPSEEK_MODEL` | DeepSeek model name (default `deepseek-v4-flash`) |
| `MISTRAL_API_KEY` | Live Mistral evals |
| `MISTRAL_MODEL` | Mistral model name (default `mistral-small-latest`) |
| `DASHSCOPE_API_KEY` | Live Qwen evals (`QWEN_API_KEY` also accepted) |
| `QWEN_MODEL` | Qwen model name (default `qwen-flash`) |
| `QWEN_BASE_URL` | Qwen DashScope compatible-mode base URL (default international host) |
| `OPENROUTER_API_KEY` | Live OpenRouter evals |
| `OPENROUTER_MODEL` | OpenRouter model slug, required (e.g. `x-ai/grok-4.3`) |
| `OPENWEIGHTS_BASE_URL` | OpenAI-compatible local server base URL |
| `OPENWEIGHTS_MODEL` | Model name on that server |
| `OPENWEIGHTS_API_KEY` | Auth header for open-weights server (default `local`) |
| `SCENARIO_SET` | Scenario filename stem, e.g. `v2_250_scenarios` |
| `SCENARIO_SET_PATH` | Full path to a scenario Markdown file |
| `RUN_LIVE_OPENAI_EVAL` | Set to `1` to enable `tests/test_live_openai.py` |
| `SUPABASE_URL` | Supabase project URL, for `publish` (e.g. `https://<ref>.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | Service-role key for `publish` writes (keep secret) |
| `SUPABASE_BENCHMARK_TABLE` | Published-runs table name (default `benchmark_runs`) |

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
| `app/providers.py` | OpenAI, Anthropic, Gemini, Kimi, Inkling, Grok, DeepSeek, Mistral, Qwen, OpenRouter (shared `OpenAICompatibleProvider` base), open-weights, naive baseline, dry-run |
| `app/policies.py` | Tool constraints and action scoring |
| `app/data.py` | Markdown scenario parsing, catalog load |
| `app/survey.py` | Survey aggregation and lock status |
| `app/agents.py` | Legacy deterministic agents |
| `app/metrics.py` | Safety-autonomy metrics |
| `app/storage.py` | Run JSON persistence |
| `app/phase2/sandbox.py` | Phase 2 tools, SandboxWorld, policy engine, prompts |
| `app/phase2/providers.py` | Tool-loop adapters (OpenAI/Anthropic/Kimi/Inkling/Grok/DeepSeek/Mistral/Qwen/OpenRouter/openweights) + scripted agents |
| `app/phase2/runner.py` | Phase 2 eval loop (model × condition × framing × urgency × user availability × scenario × seed) |
| `app/phase2/survey.py` | 50-respondent survey aggregation, lock, collection |
| `app/phase2/humans.py` | Human-baseline sessions: report + interactive collection |
| `app/phase2/transfer.py` | Phase 1 → sandbox transfer correlation |
| `scripts/generate_v2_constraints.py` | Generates `data/answer_keys/v2_constraints.json` (A+B) |
| `implementation.py` | Alternate uvicorn entrypoint |

---

## Not implemented yet (see README)

- Real survey responses (50 respondents) and real human-baseline sessions —
  the data files ship with example entries; collection/import CLIs exist
  (`phase2-human-import` ingests a Google Form CSV; `publish-human-baseline`
  pushes scored sessions + demographics to Supabase)
- Wiring v2 survey lock status into scenario `answer_key_status`
- Additional payment rails as first-class benchmark scope
- Phase 3 real-money validation

For those topics, [README.md](README.md) remains the source of truth.
