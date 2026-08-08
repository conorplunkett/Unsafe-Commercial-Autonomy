-- Phase 2 web survey adds a comfort-with-agent-purchases item.
--
-- "How comfortable would you be letting an AI assistant make purchases for
-- you with your card?" on a four-point scale (see DEMOGRAPHICS in
-- web/public/survey.html). Stored as the option key, one of
-- "very_comfortable", "somewhat_comfortable", "not_very_comfortable",
-- "not_at_all_comfortable".
--
-- Descriptive only: it is not a sampling stratum and no lock rule reads it.
-- It is a breakdown axis, so a permissive answer pattern can be read against
-- the respondent's stated comfort with agent spending.
--
-- Run once against the project referenced by SUPABASE_URL. Idempotent.

alter table public.phase2_survey_responses add column if not exists agent_purchase_comfort text;
