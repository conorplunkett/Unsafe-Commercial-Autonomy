-- Phase 2 answer-key survey responses (the /phase2-survey web instrument).
--
-- Mirrors the ad-hoc phase1_survey_responses table, but for the v2 answer key:
-- respondents vote on the preference-dependent (semantic_only) v2 scenarios,
-- and each response carries the four demographic strata the Phase 2 lock design
-- stratifies on (age_band, gender, region, purchasing_role). Votes use the
-- Phase 2 vocabulary from app/phase2/survey.py (purchase / ask_approval /
-- refuse / use_free_source); the page maps each on-screen choice to one of
-- these before insert.
--
-- Writes come from the public (anon) key via PostgREST, so RLS grants
-- insert-only to anon and no select — exactly like phase1_survey_responses.
-- One response per email is enforced by a unique index on lower(email); the
-- web page surfaces the resulting 409 as "you're already counted". Run once
-- against the project referenced by SUPABASE_URL. Idempotent: safe to re-run.

create table if not exists public.phase2_survey_responses (
  id               uuid primary key default gen_random_uuid(),
  created_at       timestamptz not null default now(),
  respondent_name  text not null,
  email            text not null,
  -- scenario_id -> vote (purchase | ask_approval | refuse | use_free_source)
  votes            jsonb not null,
  -- randomized per-respondent presentation order (incl. the attention check)
  question_order   jsonb not null,
  -- att_2 instructed-response check: { answer, passed }
  attention        jsonb not null,
  -- Phase 2 demographic strata, lifted to columns for direct filtering.
  age_band         text,
  gender           text,
  region           text,
  purchasing_role  text,
  duration_seconds integer,
  meta             jsonb
);

-- One response per email (case-insensitive).
create unique index if not exists phase2_survey_responses_email_key
  on public.phase2_survey_responses (lower(email));

-- Insert-only for the public key; no anon select (mirrors phase1 survey).
alter table public.phase2_survey_responses enable row level security;
drop policy if exists anon_insert_only on public.phase2_survey_responses;
create policy anon_insert_only
  on public.phase2_survey_responses
  for insert
  to anon
  with check (true);
