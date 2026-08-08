-- Episode store for published benchmark runs.
--
-- A full run serializes to hundreds of MB; publishing it as one `payload`
-- blob in benchmark_runs times out at the gateway, and the site could not
-- download it either. `publish` now uploads one row per episode here in
-- size-capped batches (app/supabase_publish.py), keeps `benchmark_runs.payload`
-- slim (config + metrics, no `results`/`events`), and the dashboard pages
-- episodes back with ordered selects. Runs published before this migration
-- keep their full payload and still render; the site falls back to it.
--
-- `episode_index` is the episode's position in the run's canonical results
-- order, so `order=episode_index.asc` reassembles the run exactly as a local
-- run file would read. Re-publishing a run deletes its rows and re-inserts,
-- so the table never holds a stale mix of two uploads.
--
-- Like benchmark_runs, this table grants public SELECT via RLS; writes use the
-- service-role key, which bypasses RLS. Run once against the project referenced
-- by SUPABASE_URL (Supabase dashboard > SQL editor, or psql). Idempotent.

create table if not exists public.benchmark_run_episodes (
  run_id        text not null,
  episode_index integer not null,
  -- Lifted for direct filtering; the full episode lives in `result`.
  scenario_id   text,
  model_name    text,
  result        jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  primary key (run_id, episode_index)
);

create index if not exists benchmark_run_episodes_scenario_idx
  on public.benchmark_run_episodes (scenario_id);
create index if not exists benchmark_run_episodes_model_idx
  on public.benchmark_run_episodes (model_name);

-- Public read, service-role write (mirrors benchmark_runs).
alter table public.benchmark_run_episodes enable row level security;
drop policy if exists "Public read benchmark run episodes" on public.benchmark_run_episodes;
create policy "Public read benchmark run episodes"
  on public.benchmark_run_episodes
  for select
  using (true);
