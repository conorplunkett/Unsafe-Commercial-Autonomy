-- scenario_reviews itself predates this migrations directory -- it was
-- created directly against the project, not from a tracked file. This is
-- the first migration for that table.
--
-- Adds the column admin-scenario-reviews/index.ts now reads and writes:
-- the scenario's content_hash (from admin-scenario-data) at the moment it
-- was marked reviewed, or null when reviewed is false or the row predates
-- this column. web/lib/scenarioExplorer.ts's isReviewCurrent() compares it
-- against the scenario's current content_hash to decide whether a review
-- still describes the scenario as it exists today.
alter table public.scenario_reviews
  add column if not exists content_hash text;
