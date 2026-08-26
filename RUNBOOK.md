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

Every current condition exposes `search_offers`, `view_offer`, `update_checkout`,
`complete_checkout`, `request_approval`, and `finish`. Only `tool_constraints` enforces the structured
policy, internally when `complete_checkout` runs. `structured_policy` leaves `complete_checkout` unenforced,
and direct `check_policy` calls are rejected. Historical
`required_check`/`preflight_check` runs and stored `check_policy` transcript
events remain readable and recomputable.

`tool_constraints` runs on 166 of the 226 scenarios: the ones whose checkout rail can
refuse something their world offers, plus their pair partners. In the other 60
the policy engine never fires, so an enforced episode costs a full tool loop to
reproduce `structured_policy`. `--enforcement-scope all` runs the full
cross-product instead. The scope is a grid axis — a run started under one cannot
be resumed under the other, and merge refuses to pool sources that disagree on
it. Runs record which scenarios each arm covered in `condition_scenario_ids`;
paired contrasts count the difference as `out_of_scope_count`, never as missing
episodes.

To see the per-scenario picture — can the rail fire, what does the agent have to
do first, which reason would it give:

```bash
python -m app.cli phase2-scope
```

`data/answer_keys/phase2_enforcement_scope.json` is the committed copy of that
table. It is derived, so a scenario edit that changes which structured field a
world can trip is *supposed* to move it: when the drift test fails, read the
diff, confirm the scope change was the one you intended, and commit the
regenerated file with the scenario change.

```bash
python scripts/generate_phase2_enforcement_scope.py
```

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

If a reviewed import changes lock status or adopts a survey key, refresh the
frozen effective-key projection and review its diff:

```bash
python scripts/freeze_phase2_research_contract.py
git diff -- data/answer_keys/phase2_research_contract.json
```

Do not refresh the projection for sandbox-only changes. It protects the survey
instrument and authored/effective keys, not merchant worlds or checkout tools.

For the fallback interactive collector, use
`python -m app.cli phase2-survey-collect --help`.

The Phase 1 survey is closed. Its committed aggregate and locked key require no
further collection or regeneration.

## Publishing

Apply the SQL files under `db/migrations/` in numeric order to the target
Supabase project. Current run publishing depends on the episode table created by
`0009_add_benchmark_run_episodes.sql`; merged-run supersession uses
`0010_add_superseded_by.sql`; filtering by Phase 2's tool_constraints scenario
scope uses `0011_add_enforcement_scope.sql`. Publishing and the site's run
list both tolerate any of these being unapplied — they retry without the
missing column rather than failing outright — but the column stays queryable
only once the migration runs.

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

## Scenario Explorer data

The admin Scenario Explorer reads a generated snapshot of the 113 Phase 2 pairs
committed under `supabase/functions/admin-scenario-data/`. Each scenario record
carries an `enforcement` block (`rail_reachable`, `in_enforced_arm`, `fires_on`,
`reasons`) copied from `data/answer_keys/phase2_enforcement_scope.json`, not
recomputed. After any change to `data/scenario_sets/v2_250_scenarios.md` or
`data/answer_keys/v2_constraints.json` — regenerate that file first if the
change could move the scope (see the Phase 2 grid section above), merge it to
`main`, then:

```bash
git checkout main && git pull origin main
./scripts/deploy_scenario_explorer.sh
```

`deploy_scenario_explorer.sh` refuses to run unless you're on `main`, `main`
is exactly even with `origin/main`, the working tree is clean, and
regenerating produces no diff — so a checkout that hasn't pulled the merged
change (what shipped the stale b25 key on 2026-08-26) fails loudly instead of
deploying. Only run the raw `supabase functions deploy` command by hand if
you have a specific reason to bypass the guard.

**`--no-verify-jwt` is required, every time.** This function checks its own
passphrase (`x-admin-key`, compared against the `ADMIN_SURVEY_KEY` secret) --
it does not use Supabase's own JWT auth at all. Deploy without the flag and
Supabase's platform-level JWT check switches back on and rejects every
request before the function's own code ever runs, so *every* passphrase
looks wrong -- this already happened once (2026-08-26). If logins to the
Explorer stop working right after a deploy, check `verify_jwt` on
`admin-scenario-data` first, before suspecting the passphrase itself.

`tests/test_scenario_explorer_data_drift.py` fails when the committed snapshot
no longer matches the generator, so a stale checkout is caught in CI and names
the chunk files to refresh. It cannot see the deployed function: a green suite
means the repo agrees with itself, not that Supabase is serving the current
scenarios. The deploy stays manual — run it after merging anything that changes
those files.

Each scenario record also carries a `content_hash` (sha256 of the whole
record, computed by `generate_scenario_explorer_data.py`). The Explorer stores
that hash on `scenario_reviews` alongside `reviewed`/`reviewed_at` whenever a
scenario is marked reviewed, and treats a review as stale — showing the
scenario as not reviewed again — the moment its current `content_hash` no
longer matches the stored one, i.e. anything about the scenario changed since
it was last reviewed. `scenario_reviews.content_hash` is `null` for reviews
recorded before this shipped; those are trusted as-is until next touched, they
are not retroactively marked stale. `supabase/migrations/` has the one-time
`content_hash text` column migration this needs.

## Local services

```bash
python -m app.main
```

`python -m app.main` scopes hot-reload to `app/` only. Do not use a bare
`uvicorn app.main:app --reload` for Lab work: its default watch covers the whole
tree, so every run write/delete under `runtime/runs/` restarts the server
mid-request (blanks the Runs tab, thrashes the terminal). The CLI equivalent is
`uvicorn app.main:app --reload --reload-dir app`.

- Experiment Lab: `http://127.0.0.1:8000/lab`
- API schema: `http://127.0.0.1:8000/docs`
- Stored-run API: `http://127.0.0.1:8000/api/runs`

The public site is a separate static Next.js application under `web/`; see
`web/README.md` for its local commands.

The launch video is a standalone Remotion project. Run `npm run dev` under
`video/` and open [http://localhost:3000](http://localhost:3000); its file
structure and render commands are in `video/README.md`.
