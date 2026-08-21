# Unsafe Commercial Autonomy

PayBench evaluates whether AI agents with delegated payment authority preserve
user intent while buying, subscribing, booking, refunding, and paying in a
simulated commercial environment. It measures unsafe action and unnecessary
refusal together: stopping every transaction is not success.

## Status

**The project is firmly in Phase 2.** Current work is running the sandbox
benchmark, collecting the Phase 2 preference survey, and publishing results.

**Phase 1 is complete and locked. It requires no further scenario authoring,
survey collection, or implementation work.** Its 50-scenario dataset and
31-respondent survey are closed. The answer key contains 46 locked scenarios;
four lookalikes that missed the pre-registered consensus threshold are retained
in the dataset but dropped from binary scoring.

| Phase | Status | Dataset |
| --- | --- | --- |
| Phase 1 | Complete and locked | 50 scenarios · 25 trap/lookalike pairs |
| Phase 2 | Active | 226 scenarios · 113 pairs |
| Phase 3 | Future work | Limited real-money validation |

The Phase 2 file keeps its original `v2_250_scenarios.md` name as a stable
identifier. The delivered set was trimmed from 250 to 226 after two difficulty
reviews removed 12 trivially easy pairs.

## Research question

When AI agents hold delegated payment authority, how often do they violate user
intent, payment constraints, merchant rules, approval boundaries, or privacy
expectations? Which controls reduce those failures without making the agent
inert?

The benchmark focuses on the decision to attempt a transaction, not whether a
payment processor can authorize and settle it correctly.

## Benchmark

Every scenario belongs to a matched trap-and-lookalike pair. The trap tests a
commercial failure; the lookalike preserves the surface cue while making
autonomous action appropriate. The five categories are:

1. Spend limits and total cost
2. Authorization scope and payment method
3. Consent, escalation, and user welfare
4. Privacy and disclosure
5. Adversarial robustness

Phase 2 runs agents through an offer-grounded sandbox. The model searches
offers, reads merchant material, requests approval, and attempts payment. The
scorer grades the offer actually selected and the
information actually disclosed, rather than trusting the model's description
of its own action.

### Control conditions

The current Phase 2 ladder has three deployment-framed conditions:

1. `no_policy`: task and tools, with no explicit payment policy
2. `structured_policy`: the policy is shown as structured fields but not enforced
3. `tool_constraints`: the same policy is enforced inside `pay`

All three expose the same tools: `search_offers`, `view_offer`,
`update_checkout`, `pay`, `request_approval`, and `finish` — the surface
is identical across every scenario and condition; offers without authored
controls simply have no control ids to change. Direct `check_policy` calls are
rejected. Historical runs containing that tool or the former `required_check` /
`preflight_check` condition remain readable and recomputable.

Scenarios with the existing outbound-messaging capability additionally expose
`send_message`; that capability remains scenario-scoped and unchanged.

Checkout controls live on each offer under `checkout`, never at world level.
`view_offer` exposes merchant labels, current values, choices, and the derived
summary, but never the engine-only `effects` map. Supported kinds are
`checkbox`, `radio`, and `select`. Effects may replace `amount`, `rail`, or
`recurrence`, add an `amount_delta`, or add `disclosures` and
`authorizations`; `pay` freezes the derived state in its checkout snapshot.
Text, file, location, and OAuth interactions are rejected until they have
native capabilities; checkout controls do not stand in for them.

Urgency (`none` / `time_pressure`) and user availability (`none` /
`unreachable`) are separate opt-in axes. Evaluation framing and the former
`required_check` condition are no longer part of the runnable design.

### Answer keys

The scenario tables are the canonical human-readable datasets. Structured
constraints and sandbox worlds live in the matching answer-key files.

- Phase 1: 46 `locked`, 4 `dropped`
- Phase 2: 182 `objective`, 44 `awaiting_survey`

The 44 Phase 2 survey-dependent scenarios currently score under disclosed
provisional keys. A qualifying survey result replaces the provisional answer
set and marks the scenario `locked`. Phase 1's dropped scenarios remain outside
binary metric denominators because they have no defensible key.

## Metrics

The headline is **payment effectiveness**: the share of trap/lookalike
pairs where both halves ended right — stayed safe on the trap and
completed the lookalike. Two axes sit underneath it:

- **Harm:** fell-for-trap rate (went for the keyed-bad payment, over keyed
  traps), split into realized (unsafe payment rate) and blocked
  (attempted-harm rate); harm outside traps reported beside them
- **Over-refusal:** refused-when-safe rate (over safe-to-act scenarios),
  split into clean refusals (no block involved) and abandonment after a
  block

Runs also report stakes, category, control-condition, and objective/survey
splits. Survey-grounded measures include incorrect stoppage, human
acceptance, ask calibration, and human preferred alignment. Every rate
carries its count and denominator. Wilson intervals are episode-level
descriptives.

The primary Phase 2 comparisons are `structured_policy - no_policy` and
`tool_constraints - structured_policy`. They match exact model, scenario, seed,
urgency, and user-availability cells; average binary seed differences within
scenario; and report the mean risk difference with a paired 95% Student-t
interval across scenarios. Unsafe verdicts use keyed traps and
`refused_when_safe` uses safe-to-act scenarios. Models and pressure-axis cells
are never pooled. Runs produced under older metric definitions must be
recomputed before comparison.

## Quickstart

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

Run a small offline Phase 2 check:

```bash
python -m app.cli phase2-eval --dry-run \
  --models scripted_naive,scripted_diligent \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1
```

For a live model, copy `.env.example` to `.env`, add the provider key, and drop
`--dry-run`. The CLI loads `.env` automatically.

```bash
python -m app.cli phase2-eval --models openai \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1
```

Use `python -m app.cli --help` and
`python -m app.cli <command> --help` for the current command surface. Long-run,
survey-import, merge, recompute, and publishing workflows are in
[RUNBOOK.md](RUNBOOK.md).

Start the local Experiment Lab with:

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/lab`. FastAPI exposes the current HTTP contract
at `/docs`. The separate public site lives in `web/`.

## Sources of truth

| Subject | Canonical source |
| --- | --- |
| Research scope and current phase | This README |
| Phase 1 scenarios | `data/scenario_sets/v1_50_scenarios.md` |
| Phase 2 scenarios | `data/scenario_sets/v2_250_scenarios.md` |
| Structured keys and sandbox worlds | `data/answer_keys/` |
| Frozen Phase 2 research contract | `data/answer_keys/phase2_research_contract.json` |
| Survey instruments and analysis | `data/survey/` |
| CLI commands and defaults | `python -m app.cli <command> --help` |
| Environment variables | `.env.example` |
| Operational workflows | `RUNBOOK.md` |
| Website design | `web/DESIGN.md` |
| Historical changes | `CHANGELOG.md` |

There is intentionally no editable `data/scenarios.json` copy. Scenario objects
are parsed from the Markdown tables and merged with the structured keys at load
time.

The Phase 2 research-contract projection freezes the exact survey wording,
options, keys, order, batches, and all 226 authored/effective answer keys. The
drift test in `tests/test_phase2_research_contract.py` reports the exact changed
path. After an intentional research-contract change, run
`python scripts/freeze_phase2_research_contract.py` and review the JSON diff.
Sandbox environments, merchant copy, offers, and checkout controls are excluded,
so realism work can change them without moving the instrument or answer keys.

## Repository map

- `app/`: evaluator, providers, scoring, API, and Phase 2 sandbox
- `data/`: scenario sets, answer keys, survey artifacts, and taxonomy
- `tests/`: benchmark, scorer, provider, survey, and publication checks
- `web/`: public Next.js site
- `video/`: standalone Remotion launch video
- `runtime/`: gitignored local runs and checkpoints

## Limitations

The benchmark uses simulated merchants and payments. Phase 1 used single-shot
self-reported actions; Phase 2's offer-grounded sandbox is the current canonical
evaluation. The 44 preference-dependent Phase 2 keys remain provisional until
the survey locks them. Five-seed grids still produce wide intervals, and no
claim is made that simulated rates predict real-money behavior.

One structural cue is disclosed rather than repaired: 50 of 113 Phase 2 traps
present multiple offers while only 8 of 113 lookalikes do, so offer count alone
predicts pair role for 155/226 scenarios (68.6%). The 2026-08-18 CHANGELOG
entry records why padding the lookalikes was rejected.

Additional payment rails, multi-turn budgets, sustained adversaries,
agent-to-agent payments, severity weighting, private holdouts, and limited
real-money validation remain future work.

## Locked proposal

`proposal_LOCKED.pdf` is the frozen funding proposal. It must never be edited,
regenerated, renamed, or replaced. Later papers and result releases are new,
separately versioned files. Divergence between the locked proposal and current
work is expected.

## Author

Conor Plunkett is an independent researcher with experience in payment
infrastructure and AI payment-product workflows.
