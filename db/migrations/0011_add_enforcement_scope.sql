-- Add a queryable enforcement-scope column to benchmark_runs.
--
-- Phase 2's tool_constraints arm runs on a subset of scenarios -- the ones
-- whose pay rail can refuse a payment their world offers, plus their pair
-- partners (app/phase2/scope.py) -- rather than every scenario, unless the run
-- passed --enforcement-scope all. Which one a published run used was only
-- readable inside `payload.enforcement_scope`; this lifts it to a top-level
-- column so runs can be filtered or grouped by scope without downloading the
-- payload. Phase 1 runs, and any run predating this axis, publish null.
--
-- Run once against the project referenced by SUPABASE_URL (Supabase dashboard >
-- SQL editor, or psql). Idempotent: safe to re-run. Publishing tolerates this
-- column being absent (it falls back to writing enforcement_scope inside
-- payload only, the same fallback db/migrations/0001 gave model_names), but
-- top-level filtering needs it.

alter table public.benchmark_runs
  add column if not exists enforcement_scope text;

comment on column public.benchmark_runs.enforcement_scope is
  'Phase 2 tool_constraints scenario scope this run used ("rail_reachable" or '
  '"all"); null for Phase 1 runs and any run published before this axis existed.';

create index if not exists benchmark_runs_enforcement_scope_idx
  on public.benchmark_runs (enforcement_scope);
