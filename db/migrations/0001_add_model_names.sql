-- Add a queryable per-model column to benchmark_runs.
--
-- model_ids holds provider/config selectors ("openai", "anthropic"); model_names
-- holds the actual models evaluated ("gpt-5.4-mini", "gpt-5.5") so the table can
-- be filtered and grouped per model rather than per provider.
--
-- Run once against the project referenced by SUPABASE_URL (Supabase dashboard >
-- SQL editor, or psql). Idempotent: safe to re-run. Publishing tolerates this
-- column being absent (it falls back to writing model names inside payload), but
-- top-level per-model queries need it.

alter table public.benchmark_runs
  add column if not exists model_names text[] not null default '{}';

-- GIN index so `model_names @> '{gpt-5.4-mini}'` / `&&` lookups stay fast.
create index if not exists benchmark_runs_model_names_idx
  on public.benchmark_runs using gin (model_names);
