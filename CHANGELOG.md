# Changelog

Durable project changes, grouped by date. Intermediate implementations that
were later reversed are omitted. Current behavior belongs in `README.md`, CLI
help, and the code; this file records how the project arrived there.

The full pre-consolidation changelog remains available in git:

```bash
git show 218d0f2:CHANGELOG.md
```

## 2026-08-18

- Added a persistent survey progress indicator.

## 2026-08-17

- Reduced the Phase 2 design to three conditions: `no_policy`,
  `structured_policy`, and `tool_constraints`.
- Removed evaluation framing from the runnable grid. Phase 2 now uses one plain
  deployment prompt.
- Removed the advisory `required_check` arm because it measured neither
  enforcement nor compliance with the check result.
- Began scoring the 44 `awaiting_survey` scenarios under disclosed provisional
  keys. Survey results replace those keys when they lock.
- Hardened survey re-keying and aligned disclosure vocabularies across survey,
  scenario, sandbox, and scorer data.
- Corrected the b13 category token, c25 disclosure key, and b25 quantity.
- Made the Experiment Lab lighter and easier to navigate: deferred transcript
  loading, paginated stored results, readable episode detail, condition pills,
  section navigation, pricing, cost, and run-combination panels.
- Made reasoning output visible by default while preserving empty reasoning
  blocks explicitly.

## 2026-08-14

- Reworked Experiment Lab episode detail for readable instructions, actions,
  failures, tool blocks, and reasoning.

## 2026-08-12

- Added `merge` for combining compatible run fragments into one artifact.
- Added published-run supersession so merged and source runs are not pooled
  twice on the leaderboard.

## 2026-08-11

- Changed the headline unsafe-payment denominator to keyed traps. Unsafe actions
  outside the trap pile remain separately reported.
- Added `recompute` for rebuilding stored metrics under current definitions.
- Changed default evaluation seeds from five to one; full five-seed runs are
  explicit.
- Re-keyed compare-offer scenarios whose compliant purchases were previously
  misgraded.
- Fixed repeated tool-call loops, Gemini thought-signature handling, and
  completed-action grounding.
- Added load-time and test-time invariants for scenario worlds and answer keys.

## 2026-08-09

- Graded every completed payment in an episode, rather than only the final one.
- Distinguished blocked harm followed by abandonment from a successful stop.
- Added exposure metrics: acted rate and unsafe-when-acted.
- Distinguished policy blocks from actions that require approval.
- Made survey re-keying lock only when imported votes and the authored key agree.
- Hardened checkpoint resume and live-run cost estimates.
- Removed the human baseline and Phase 1-to-Phase 2 transfer claim from scope.
  The two phases are reported separately.

## 2026-08-08

- Connected Phase 2 web-survey exports to anonymized aggregates and answer-key
  votes, with conflict detection and PII guards.
- Added runnable objective/survey dataset splits.
- Added the Phase 2 Gemini adapter.
- Added batched episode publishing, quality gates, retry handling, resumable
  checkpoints, and concurrent episode execution.
- Kept sustained multi-turn pressure outside the current design.

## 2026-08-07

- Authored policy-silent merchant copy for Phase 2 offers so `no_policy` no
  longer exposed the answer through page text.
- Hid scorer-only fields from model-visible tools.
- Split time pressure and absent-user pressure into independent axes.
- Added robust interruption, resume, retry, and concurrency behavior for paid
  Phase 2 runs.
- Connected the survey analyzer, instrument, answer key, and sandbox through
  guard tests.

## 2026-07-25

- Removed scorer category tokens from model-visible offer data and scrubbed
  author annotations from listing names.

## 2026-07-24

- Trimmed the Phase 2 dataset from 250 to 226 scenarios after two difficulty
  reviews removed 12 trivial pairs. The filename stayed
  `v2_250_scenarios.md` as a stable identifier.
- Completed the `v2_web_r3` survey instrument: 44 preference scenarios, one
  calibration item, five attention checks, fixed action slots, acceptability
  questions, and five context sections.
- Added survey-grounded recovery, alignment, ask-calibration, and top-choice
  metrics.
- Grounded survey quantities and answer options in executable sandbox worlds,
  with tests preventing future drift.
- Added authored trap markers for failures structured policy fields cannot
  express.
- Excluded unlocked survey keys from scoring at the time; the later
  August 17 policy superseded this by scoring disclosed provisional keys.

## 2026-07-22–23

- Replaced the first generic Phase 2 survey with concrete decision points and
  per-item actions.
- Rewrote the instrument for clear tense, explicit agency, non-overlapping
  ask/refuse choices, grounded prices, and five fixed context parts.
- Added demographic fields, attention rules, and pre-registered analysis.

## 2026-06-29

- Offer-grounded all 50 Phase 1 scenarios so the sandbox grades the selected
  offer and disclosures rather than the model's self-report.
- Added structured constraints, multi-label failure scoring, survey locks,
  deterministic baselines, provider adapters, metrics, CLI workflows, and
  publication support.
