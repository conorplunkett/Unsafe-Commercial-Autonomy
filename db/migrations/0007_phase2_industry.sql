-- Phase 2 web survey r3 adds an industry demographic.
--
-- "What industry do you work in?" with a standardized 15-bucket list
-- (see DEMOGRAPHICS in web/public/survey.html). Stored as the
-- option key (e.g. "technology", "healthcare", "not_working").
--
-- Run once against the project referenced by SUPABASE_URL. Idempotent.

alter table public.phase2_survey_responses add column if not exists industry text;
