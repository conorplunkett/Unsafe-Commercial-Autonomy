-- Phase 2 web survey r2 records the acceptability sub-question.
--
-- Instrument v2_web_r2 adds the Phase 1-style "also acceptable (select all)"
-- step after each preferred-action pick, so this table gains the same
-- `also_acceptable` jsonb column phase1_survey_responses already has
-- (question id -> array of option keys; empty array = "No, only my choice").
--
-- Run once against the project referenced by SUPABASE_URL. Idempotent.

alter table public.phase2_survey_responses add column if not exists also_acceptable jsonb;
