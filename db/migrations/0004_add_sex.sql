-- Add a `sex` demographic column to both survey response tables.
--
-- The Phase 1 and Phase 2 web surveys now ask a required sex question
-- (male / female), stored as a top-level column alongside the other
-- demographics so it is directly filterable/groupable in SQL. This is distinct
-- from the Phase 2 `gender` column (gender identity), which is unchanged.
--
-- Run once against the project referenced by SUPABASE_URL. Idempotent.

alter table public.phase1_survey_responses add column if not exists sex text;
alter table public.phase2_survey_responses add column if not exists sex text;
