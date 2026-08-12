-- Mark a published run as pooled into a later merged run.
--
-- `python -m app.cli merge` stitches several sittings of one gauntlet (same
-- model, same scenarios, different control conditions or different days) into
-- a single run whose metrics are recomputed from the pooled episodes. The
-- leaderboard sums each published run's `by_model_name` counts, so once the
-- merged run is published its sources would count their episodes a second
-- time. `publish` stamps this column on the sources; the site excludes stamped
-- rows from the pooled leaderboard while still listing and rendering them, so
-- any single sitting stays inspectable and nothing is deleted.
--
-- Null = the run stands on its own (every run published before this migration).
-- Run once against the project referenced by SUPABASE_URL (Supabase dashboard >
-- SQL editor, or psql). Idempotent.

alter table public.benchmark_runs
  add column if not exists superseded_by text;

comment on column public.benchmark_runs.superseded_by is
  'run_id of the merged run that pooled this run''s episodes; null if the run stands alone.';

create index if not exists benchmark_runs_superseded_by_idx
  on public.benchmark_runs (superseded_by);
