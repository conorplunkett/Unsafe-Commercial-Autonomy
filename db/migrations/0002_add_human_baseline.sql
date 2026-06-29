-- Per-session store for the Phase 2 human baseline.
--
-- The benchmark scores recorded human sessions with the exact model pipeline
-- (app/phase2/humans.py); `publish-human-baseline` pushes one scored row per
-- session here so the public dashboard can show the human calibration line next
-- to the model leaderboard, and so demographics are queryable directly in SQL.
--
-- The canonical demographic fields (age_band, country, occupation, ...) are
-- lifted to top-level columns for filtering/grouping; the full set (including
-- any extra fields a survey captured) is also kept in the `demographics` jsonb.
-- No raw emails or names are stored: the importer pseudonymizes participant ids.
--
-- Like benchmark_runs, this table grants public SELECT via RLS; writes use the
-- service-role key, which bypasses RLS. Run once against the project referenced
-- by SUPABASE_URL (Supabase dashboard > SQL editor, or psql). Idempotent.

create table if not exists public.human_baseline_sessions (
  session_id        text primary key,
  run_label         text,
  participant_id    text not null,
  scenario_id       text not null,
  control_condition text,
  -- Raw survey timestamp kept as text: Google Forms emits locale-dependent,
  -- non-ISO stamps, so storing them verbatim avoids parse failures on insert.
  started_at        text,
  duration_seconds  numeric,
  -- Lifted demographics for direct filtering/grouping.
  age_band          text,
  gender            text,
  country           text,
  occupation        text,
  purchasing_role   text,
  education          text,
  ai_familiarity    text,
  -- Full demographics (canonical + any extra survey fields) and the scored action.
  demographics      jsonb not null default '{}'::jsonb,
  action            jsonb not null default '{}'::jsonb,
  -- Scored outcome (same pipeline as models).
  verdict           text,
  safe_to_act       boolean,
  proceeded         boolean,
  outcome           text,   -- confusion cell: correctly_proceeded | wrongly_proceeded | wrongly_stopped | correctly_stopped
  measured_failure  text,
  failure_metrics   text[] not null default '{}',
  source            text,
  created_at        timestamptz not null default now()
);

-- Common stratification/filter axes.
create index if not exists human_baseline_sessions_scenario_idx
  on public.human_baseline_sessions (scenario_id);
create index if not exists human_baseline_sessions_participant_idx
  on public.human_baseline_sessions (participant_id);
create index if not exists human_baseline_sessions_outcome_idx
  on public.human_baseline_sessions (outcome);
create index if not exists human_baseline_sessions_run_label_idx
  on public.human_baseline_sessions (run_label);

-- Public read, service-role write (mirrors benchmark_runs).
alter table public.human_baseline_sessions enable row level security;
drop policy if exists "Public read human baseline" on public.human_baseline_sessions;
create policy "Public read human baseline"
  on public.human_baseline_sessions
  for select
  using (true);
