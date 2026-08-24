# Handoff: how the Survey 1 results report was produced, for reuse on Survey 2

Written 2026-08-11 at the end of the Survey 1 analysis-and-report session, so the
same process can be rerun on the Phase 2 survey data and new patterns compared
against Phase 1. Audience: the next Claude session (or human) doing the Phase 2
analysis, plus Conor. Read this whole file before touching Phase 2 data.

## 1. What was produced, and where it lives

| Artifact | Path | Notes |
| --- | --- | --- |
| Published report (v1.2, n = 35) | `survey1_results_v1.md` (repo root) | Merged to main via PRs #243, #256, #261 |
| Figures (5) | `survey1_figs/*.png` | Dashboard visual language, percentages only |
| Independent recompute, n = 31 | `scripts/survey1_handoff/fable_survey1_analysis.py` | Validates against committed aggregates |
| Pooled recompute, n = 35 | `scripts/survey1_handoff/n35_recompute.py` | The report's numbers source; embeds the 4 post-lock rows |
| Figure generator + screenshotter | `scripts/survey1_handoff/gen_figs.py`, `shoot2.js` | Standalone HTML → Playwright PNG |
| This handoff | `data/survey/SURVEY1_ANALYSIS_HANDOFF.md` | |

Existing project files the analysis leaned on (do not modify): the
pre-registration `PHASE1_WEB_SURVEY.md`, the decision memo
`PHASE1_SURVEY_RESULTS_v1_web_r6.md` (its §8 is the n = 35 validation table),
the committed anonymized data `phase1_survey_responses.json`, the committed
aggregates `phase1_results_v1_web_r6.json`, and the live instrument
`web/public/survey0.html` (source of truth for verbatim wordings).

## 2. Data provenance and the n accounting (the part that will bite again)

Supabase project `uca-benchmark` (id `tethtzycfdplyzvrtknh`), table
`phase1_survey_responses`. Columns used: `created_at`, `answers` (jsonb),
`also_acceptable` (jsonb), `attention` (jsonb: `att_1/att_2 → {answer, passed}`),
`ai_familiarity`, `used_agent_purchases`, `duration_seconds`,
`meta->>'survey_version'`. **Never select `respondent_name` or `email` into
context, files, or commits.** The acknowledgments section uses names Conor
pastes from his admin dashboard; emails never appear anywhere.

The final accounting, which took real work to get right:

- 36 rows total in the table at analysis time.
- 31 clean pre-lock responses (July 7–15) = the pre-registered answer-key set,
  locked 2026-07-16.
- 4 clean post-lock responses (July 17–22, still tagged `v1_web_r6`): pooled
  into the report's descriptives as a disclosed extension. Recomputing every
  scenario at 35 changes no modal answer and no lock verdict (pre-verified in
  memo §8; re-verified independently).
- 1 junk row (Aug 9, tagged `v1_web_r6_postlock`): 1-second duration AND failed
  the instructed-response check. Excluded under two pre-registered rules.
- Conor initially asked for "36 people." The right move was to check the raw
  rows, show him why the 36th fails the survey's own rules, and report 35 with
  the exclusion stated in Method. He accepted immediately. **Do the same on
  Phase 2: verify the requested n against the exclusion rules before using it.**
- Watch for test rows: `respondent_name = "TEST LIVE"`, emails prefixed
  `test-live-`, `meta.test = true` (see `web/public/survey0.html` for the
  conventions; Phase 2's instrument has analogous modes).

## 3. The verification discipline (non-negotiable)

Every number in the published prose survived this chain. Reproduce it:

1. **Recompute from raw per-respondent votes**, never from the memo's prose.
   For n = 31 the committed `phase1_survey_responses.json` is the source; the
   recompute must match the committed `phase1_results_v1_web_r6.json` on every
   scenario (modal, agreement, lock) with **zero mismatches** before anything
   else happens. It did.
2. **Validate the extended sample against an independent record.** The n = 35
   recompute had to reproduce memo §8's per-scenario percentages exactly
   (assertion built into `n35_recompute.py`, tolerance 0.06pp). It did, 12/12.
3. **Audit the final prose against the script output** line by line before
   committing. This pass caught one real miswording: "71–90% wanted the agent
   to stop" was wrong because on the categorical-rule traps the majority-safe
   response includes substitution (a proceed); the supportable claim was "at
   least 80% chose a limit-respecting response." Expect exactly this class of
   error: prose that rounds a safe-action share into a stop-action share.
4. **Figures are computed, not styled guesses**: every bar's width comes from
   the recompute output, and each figure's numbers were re-derived in the same
   session as the screenshot.

Key formulas (all in the scripts, no external deps):

- Wilson 95% interval for every headline proportion.
- **Exact McNemar** for within-pair reversals: binomial two-sided test on the
  discordant pairs only (respondents who proceed on one pair member and stop
  on the other). This is the strongest analysis in the whole report — 25
  stricter vs 0 looser on the contractor pair — and it exists because the
  paired design lets you watch the same person flip. Phase 2's scenario
  structure differs; find its pairs or near-pairs first (see §7).
- **Fisher exact** (hypergeometric) for the camp contrast at respondent level.
- Vote mapping: raw option keys → {buy, buy_compliant_alternative,
  use_free_source, ask, refuse} per the table in `PHASE1_WEB_SURVEY.md`;
  category level {proceed, ask, refuse} for flip tests.

## 4. The analysis inventory (run all of these on Phase 2)

1. Per-item distributions, modal answer, agreement share, lock verdict under
   the phase's own pre-registered rule, Wilson CIs.
2. **Reflexive-ask floor** from the baseline calibration item, with CI; read
   every item's ask-rate against the floor. (Phase 2's r2 instrument added a
   baseline item for exactly this purpose.)
3. **Within-subject flips** on matched or near-matched item pairs + exact
   McNemar. Report flips as counts ("25 of 35, none in reverse"), never only
   as two aggregate percentages.
4. **Camp split** on the baseline item: per-camp consensus tables, per-camp
   modal answers, safe-item ask-rate contrast + Fisher exact, camp × recovery
   choice on blocked purchases. At Phase 1 n = 35: camps were 18/17, ask rates
   53% vs 14%, delegators cleared 70% on 8/12 items vs 5/12 full-sample, and
   the camps were unanimous on opposite halves of the same pair. Also check
   substitution-by-camp: delegators' modal answer on both categorical-rule
   traps was the compliant substitute (59%, 53%) while they still stopped for
   the budget breach (65% ask) — that asymmetry is a Phase 2 question now.
5. **Unsafe-vote counts** per trap + per-respondent histogram, graded by
   violation type (categorical rule vs numeric limit vs coercion). Phase 1:
   13/210 = 6.2%, 25/35 never; categorical 0–6%, numeric 9–20%.
6. **Acceptability lens**: preferred-or-also-acceptable share per option;
   which items reach a ≥70%-acceptable action despite failing preference
   consensus (Phase 1: 10 of 12, and 5 of the 7 deadlocked); the
   "only my choice" strictness rate (46%); and the **cost of asking** (share
   marking a confirmation unacceptable on explicit-instruction items: 40% on
   the explicit $500).
7. Demographics splits, descriptive only, with cell sizes stated. Phase 2 has
   strata (age band, sex, region, purchasing role, industry) so this gets
   richer; keep the same discipline about small cells.
8. Stability check: recompute with/without late responses; date-cutoff
   handling per the phase's pre-registration.

## 5. Report production (layout, voice, figures)

**Layout** (Conor-approved, reuse for Phase 2): title containing the n; one
byline line (Conor Plunkett · PayBench · date · version · repo link); abstract
150–200 words; 4–5 key-findings bullets with the number first in each; body
sections; results-by-scenario table; a small pre-registered-vs-exploratory
table; Method late; **Limitations as its own section** (not folded into
Method); design implications explicitly labeled as hypotheses, each bullet
tracing to a specific number; Acknowledgments (names only, submission order);
Appendix A instrument wordings **verbatim from the instrument code**, not from
memory or the results JSON; Appendix B full per-item distributions; Appendix C
links; BibTeX block.

**Register**: formal research prose, "we", third person for respondents. This
was reached the hard way: a punchy first-person version was rejected as "way
too casual." Do not oscillate back.

**Voice rules that actually bit during editing** (source:
github.com/conorbronsdon/avoid-ai-writing, plus repo `AGENTS.md`):

- No em dashes anywhere. Colons, commas, periods.
- No "It's not X, it's Y" or "X, not Y" contrast headings ("Two camps, not
  confusion" was explicitly called out as an AI tell).
- No self-labeled significance ("the cleanest finding in the survey"): state
  the result, let 25-vs-0 do the work.
- Sentence-case headings, no title case, no cute aphorisms; descriptive
  research headings ("Budget caps operate as hard constraints").
- Thin repeated constructions: "rather than" was cut from 9 uses to 5; hedges
  ("appears to") from 3 to 1; intensifiers ("heavily") deleted where a number
  sits adjacent.
- Replace vague quantities with numbers ("close to uniformly no" → "no in 94%
  of votes").
- No p-value glosses ("one-in-a-million coincidence" misstates what p means;
  a reviewer will catch it). State the test and the p.
- Define jargon inline or avoid it: "trap/lookalike", "recovery", "modal",
  "lock" all got rewritten after Conor flagged them. "Recovery" became "what
  the assistant does when a purchase is blocked", with the three exits named.
- Population claims from a convenience sample are hedged and quarantined in
  the hypotheses section ("if this split persists in deployed populations").
- Methodology detail never appears in headline copy (repo AGENTS.md rule);
  figures get no captions except a one-line legend under the first figure.

**Figures**: five per report, matching the admin/results dashboard visual
language. Palette from `web/app/globals.css`: paper #fbf7ec, paper-2 #f2ead6,
ink #1b1713, muted #7c7163, border #e5dcc7, greens #1a6b59/#2f8f74 for
proceed, amber #bf8a2d for ask, red #b4472b for refuse. Bar idiom from
`web/components/survey/QuestionCard.tsx`: rounded track, solid fill = chose
it, 30%-opacity fill = chose-or-acceptable. Conor's figure rules, learned via
rejection: **percentages only** (no x/31 counts), no LOCKED/PROVISIONAL
badges, no TRAP/LOOKALIKE labels, no eyebrow captions, no modal footers.
Generate as standalone HTML (`gen_figs.py`) and screenshot with
playwright-core + the preinstalled Chromium headless shell
(`/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`),
deviceScaleFactor 2, element screenshot of `.shot`. Don't screenshot the live
site for report figures once the committed page data lags the report's n.
Figure set that worked: 2–3 pair contrasts (the two strongest findings + the
acceptability illustration), the camp ask-rate bars, the unsafe-votes bars.

**Delivery**: commit report + figures on a `claude/...` branch, push; merge to
main only when Conor says merge (repo AGENTS.md: branch → PR → merge PR,
never direct to main). He edits in Google Docs by copying the rendered GitHub
page (that carries the images); raw md paste does not.

## 6. Conor's editorial profile (the accumulated "prompt")

Distilled from every revision request this session; treat as standing
instructions for Phase 2 writing:

- Every question/item must be covered somewhere, but inconclusive ones can be
  lumped into one insight with the per-item numbers in a table.
- He wants insights shaped like product rules: "people let it act when THEY
  said the number; ambiguity, even $25-small, means check."
- He will paste your text into Google Docs and rework it; deliver standalone
  md, simple structure, one table style, portable formatting.
- Ask-before-merge is not required once he has said merge in the session, but
  he flips register/direction fast; keep every version as its own commit so
  rollbacks are one revert.
- He verifies numbers ("56/102 is out of your ass" — it wasn't, but the burden
  of proof is on the analysis): every figure label must be traceable to the
  recompute output, and if he challenges a number, show the derivation, fix
  the presentation, and don't cave on correct data.
- Acknowledgment promises are real: survey volunteers were promised name
  credits; include them, names only.
- He values the "improvements for next time" genre: the report's Limitations +
  a future-work list (pre-register the camp split; reword the contested pair;
  screen on the delegation premise; recruit past his network; explicit
  "none acceptable" option; parametric overshoot/ambiguity gradients). These
  are commitments Phase 2 should either honor or consciously defer.
- Cohort naming: "delegators" is settled; the counterpart candidates he liked
  are "approvers" (paper), "co-signers" (memorable), "ask-first" (social);
  "supervisors" is the current in-report term. Confirm before Phase 2 writes
  one in.

## 7. Phase 2: what is different, and the landmines

Read `PHASE2_WEB_SURVEY.md` in full before running anything. Known deltas as
of this handoff:

- **Instrument**: `v2_web_r3` (r1 and r2 were replaced before any real
  collection; version gate excludes strays). 44 surveyed scenarios in five
  fixed-order parts with context screens, per-item concrete ballot options on
  fixed slot keys, an acceptability sub-question, and a baseline calibration
  item. Wordings live in the Phase 2 instrument page under `web/public/`;
  quote verbatim from there for the appendix.
- **Lock rule differs**: ≥35 of 50 respondents agreeing per scenario, AND the
  crowd's answer must agree with the committed key. Not Phase 1's 70%/n≥15.
  Use the phase's own rule for lock verdicts; keep 70% only for
  cross-phase comparison if explicitly labeled.
- **Vote vocabulary differs**: slot keys per item; the coarse vocabulary is
  {proceed_trap, proceed_fabricate, proceed_safe, ask_approval, refuse} (see
  `phase2_survey_responses.json` `_meta`). Build the mapping from the Phase 2
  doc, not from Phase 1's table.
- **The committed `phase2_survey_responses.json` is EXAMPLE DATA**
  (`_meta.example: true`) at handoff time. Real data: Supabase table
  `phase2_survey_responses` (migration `0003_add_phase2_survey.sql`; columns
  extended by 0005 sex, 0006 also_acceptable, 0007 industry). The referenced
  importer `scripts/analyze_phase2_survey.py` did not exist yet when this was
  written; check before assuming it does.
- **Demographics are stratified** (age band, sex, region, purchasing role,
  industry): plan the descriptive cuts up front, state cell sizes, resist
  inferential claims on small strata.
- **Pairs**: Phase 2 items are not all clean trap/lookalike pairs. Identify
  which items form within-subject contrasts (same task, one changed detail)
  before promising McNemar tests; where no pair exists, the flip analysis is
  simply unavailable, and saying so beats forcing it.
- Same exclusion hygiene: instructed-response check, minimum duration, version
  gate, lock-date cutoff, test rows, team responses, one response per email.

## 8. Kickoff prompt for the Phase 2 session

Paste something like this to start the next session:

> Read `data/survey/SURVEY1_ANALYSIS_HANDOFF.md` and follow it. Then: (1) read
> `data/survey/PHASE2_WEB_SURVEY.md` and the Phase 2 instrument page under
> `web/public/` end to end; (2) pull the real Phase 2 responses from the
> Supabase table `phase2_survey_responses` (project `uca-benchmark`), never
> selecting names or emails; (3) apply the pre-registered exclusion rules and
> report the exact n accounting to me before analyzing; (4) run the full
> analysis inventory from handoff §4, adapting the vote mapping and lock rule
> to Phase 2's pre-registration, and validate any official aggregates against
> an independent recompute with zero mismatches; (5) report back the tiered
> insight list (pre-registered vs exploratory) with Phase 1 comparisons
> before writing anything; (6) then draft the report per handoff §5–6 as
> `survey2_results_v1.md` with figures in `survey2_figs/`, research register,
> avoid-ai-writing rules, on a fresh `claude/...` branch.

## 9. Cross-phase patterns to check first in the new data

The Phase 1 findings, as predictions Phase 2 can confirm, refine, or break:

1. Explicit figure → autonomy; ambiguous figure → confirmation (91/80 split,
   25-vs-0 flips). Does it replicate with business framing and larger sums?
2. Numeric limits are hard lines at trivial overshoots (71/71 at $2.47), and
   silent repair of a budget is near-universally unwanted (1 of 35).
3. Categorical-rule blocks tolerate autonomous substitution far more than
   budget breaches do (51%/43% substitute vs 3% repair), especially among
   delegators.
4. A reflexive-ask floor near half the sample (51%), stable at the person
   level; camps predicted by one baseline item (53% vs 14% ask rates).
5. Unsafe endorsement stays rare (6%) and graded by violation type; coercion
   and named rules near zero.
6. Acceptability consensus exceeds preference consensus (10/12 items ≥70%
   acceptable); asking is broadly tolerated but unacceptable to ~40% on
   explicit instructions.
7. Taste-laden purchases (gifts) resist delegation even when compliant
   (17/17 tie); dominance (free identical document) produces the highest
   autonomy (86%).

Deviation from any of these in Phase 2 is itself a finding; agreement across
two instruments and framings is a much stronger claim than either alone.
