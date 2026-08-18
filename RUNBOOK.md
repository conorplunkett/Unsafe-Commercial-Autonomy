# PayBench runbook

This file covers operational workflows that are not obvious from CLI help.
Commands, flags, and defaults are canonical in:

```bash
python -m app.cli --help
python -m app.cli <command> --help
```

Secrets and environment variables are documented in `.env.example`. The CLI
and local server load `.env` automatically.

## Paid Phase 2 runs

Start with one pair, one seed, and one model before launching a full grid:

```bash
python -m app.cli phase2-eval --models openai \
  --scenario-ids scn_v2_a1_trap,scn_v2_a1_lookalike \
  --conditions all --seeds 1
```

The current design has three conditions; framing is no longer a runnable axis. Pressure
axes are opt-in. Large live runs print their episode count and require explicit
confirmation; use `--yes` only in a script or CI job whose scope was reviewed.

Every current condition exposes `search_offers`, `view_offer`, `pay`,
`request_approval`, and `finish`. Only `tool_constraints` enforces the structured
policy, internally when `pay` runs. `structured_policy` leaves `pay` unenforced,
and direct `check_policy` calls are rejected. Historical
`required_check`/`preflight_check` runs and stored `check_policy` transcript
events remain readable and recomputable.

Each completed episode is appended to a checkpoint. Keep checkpointing enabled
for paid runs.

```bash
python -m app.cli phase2-checkpoints
python -m app.cli phase2-eval --resume <run_id> [the original axes]
```

Resume rejects a different grid and reruns errored episodes. `--concurrency N`
runs independent episodes in parallel; choose `N` against the provider's rate
limit.

Local run JSON is stored under `runtime/runs/`; checkpoints live under
`runtime/checkpoints/`. Both directories are gitignored.

## Phase 2 survey import

Raw exports contain personal information. Store them only under the gitignored
`data/survey/raw/` directory.

```bash
python scripts/analyze_phase2_survey.py data/survey/raw/export.json
python -m app.cli phase2-survey
```

The analyzer applies the pre-registered exclusions and writes anonymized
aggregates and answer-key votes. Never commit the raw export.

For the fallback interactive collector, use
`python -m app.cli phase2-survey-collect --help`.

The Phase 1 survey is closed. Its committed aggregate and locked key require no
further collection or regeneration.

## Publishing

Apply the SQL files under `db/migrations/` in numeric order to the target
Supabase project. Current run publishing depends on the episode table created by
`0009_add_benchmark_run_episodes.sql`; merged-run supersession uses
`0010_add_superseded_by.sql`.

Set `SUPABASE_SERVICE_KEY` in `.env`, then publish a stored run:

```bash
python -m app.cli publish --latest --label "Phase 2 official"
```

Publishing is deliberate: local Experiment Lab runs never upload themselves.
The publisher rejects incomplete or degraded runs unless `--allow-degraded` is
passed. Re-publishing the same `run_id` replaces its published representation.

## Recomputing metrics

Metric definitions can change without changing episode actions. Recompute old
runs before pooling them with current results:

```bash
python -m app.cli recompute --latest
python -m app.cli recompute --all
python -m app.cli recompute --run-id <run_id> --publish
```

Recompute updates stored metrics in place and leaves episode verdicts intact.
It also rebuilds the two primary Phase 2 paired contrasts:
`structured_policy - no_policy` and
`tool_constraints - structured_policy`. These use exact scenario/seed matches
within each model, urgency, and user-availability cell, then report a paired
scenario-level risk difference and 95% Student-t interval. The CLI summary also
shows missing, errored, and unpaired cell counts. Wilson intervals remain
episode-level descriptives.

## Combining fragmented runs

Use `merge` when one experiment was completed across several sittings or files.
First inspect compatibility without writing anything:

```bash
python -m app.cli merge --run-ids run_a,run_b,run_c --dry-run
```

Then create and optionally publish the pooled artifact:

```bash
python -m app.cli merge --run-ids run_a,run_b,run_c \
  --publish --label "Phase 2 complete grid"
```

Sources must use the same model, scenario set, and sampling configuration.
Overlapping episodes fail by default. Published source runs are marked
superseded so the leaderboard does not count their episodes twice; avoid
`--no-supersede` unless double-counting is intentional.

## Local services

```bash
uvicorn app.main:app --reload
```

- Experiment Lab: `http://127.0.0.1:8000/lab`
- API schema: `http://127.0.0.1:8000/docs`
- Stored-run API: `http://127.0.0.1:8000/api/runs`

The public site is a separate static Next.js application under `web/`; see
`web/README.md` for its local commands.

The launch video is a standalone Remotion project. Run `npm run dev` under
`video/` and open [http://localhost:3000](http://localhost:3000); its file
structure and render commands are in `video/README.md`.
