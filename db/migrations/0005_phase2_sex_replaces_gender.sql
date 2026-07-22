-- Phase 2 collects sex, not gender identity.
--
-- Supersedes the phase2 half of 0004: the Phase 2 survey no longer asks a
-- gender-identity question, so drop the separately-added `sex` column and
-- rename the original `gender` column to `sex` (the Phase 1 `sex` column from
-- 0004 is unchanged). Phase 2 had no responses when this ran, so no data moves.
--
-- The human_baseline_sessions table keeps its own `gender` column — that is a
-- separate instrument and is out of scope here.
--
-- Run once against the project referenced by SUPABASE_URL. Idempotent enough to
-- re-run: the drop is guarded; the rename is a no-op once `sex` already exists.

alter table public.phase2_survey_responses drop column if exists sex;
alter table public.phase2_survey_responses rename column gender to sex;
