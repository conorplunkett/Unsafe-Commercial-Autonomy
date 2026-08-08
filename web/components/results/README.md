# Once results are live

**Status: live.** `RESULTS_LIVE` defaults to `true` as of the first published
runs (2026-07-24). Set `NEXT_PUBLIC_RESULTS_LIVE=false` at build time to fall
back to proposal mode.

Everything in this folder renders **published benchmark results** and is hidden
while the site is a proposal (no runs published yet). It is all gated behind one
flag: `RESULTS_LIVE` in `web/lib/config.ts`.

## To re-enable when the first real run is published

1. Publish the run to Supabase (`app/supabase_publish.py`) and confirm it shows
   up: `GET {supabaseUrl}/rest/v1/benchmark_runs?select=run_id` must return rows.
2. Flip the flag: set `NEXT_PUBLIC_RESULTS_LIVE=true` in the Vercel build env
   (or change the default in `web/lib/config.ts`).
3. That flag automatically restores:
   - the **Results** section — `Donut` + `Findings` (`app/page.tsx`)
   - the **Survey-grounded axes** section — `SurveyAxes` (`app/page.tsx`)
   - the **Leaderboard** section (`app/page.tsx`)
   - the **Episodes** section — `EpisodeBrowser` (`app/page.tsx`)
   - the `Results` / `Leaderboard` nav links (`lib/sections.ts`)
   - the `DataProvider` Supabase fetch (`app/layout.tsx`)
4. Sweep the proposal-tense copy back to results-tense (search the components
   for `RESULTS_LIVE` and `proposal`):
   - `Hero.tsx` — remove the "research proposal / no results yet" status line
   - `Method.tsx` + the Method divider in `app/page.tsx` — "will be scored" →
     "is scored"
   - `Design.tsx` — the validation survey is described as upcoming
   - `Roadmap.tsx` — Phase 1 status/body
   - `Limitations.tsx` — written for a proposal with no published results
   - `Footer.tsx` — "results will be published" → "results are published live"

## What a page view costs

A run row is over a megabyte, so requests are rationed:

| Request | When |
| --- | --- |
| run list + each run's `metrics` column (~50 KB) | on load |
| the newest run's `payload` | on load, for `Donut` / `Findings` |
| one run's `payload->results` | when `EpisodeBrowser` scrolls into view, and per run switch after that |

`Leaderboard` therefore ranks models from the runs' committed `metrics`
(`poolModelMetrics` in `lib/metrics.ts` sums the `unsafe_payment_ci` /
`refused_when_safe_ci` counts) rather than downloading every run's episodes. A
run published before the `by_model_name` breakdown existed contributes nothing to
the pool, and the board falls back to the selected run's episodes if no run
carries it.

`EpisodeBrowser` renders 10 rows and appends 10 more per scroll to the end of its
own scroll container. All of them come from the one already-fetched array, so
paging costs no requests. It opens on the `gpt-5.4-nano` run with unsafe verdicts
sorted to the top (`DEFAULT_RUN_MODEL` / `VERDICT_ORDER`).

## Known issues to fix before/when re-enabling (from the frontend review)

- The sample fallback (`lib/sampleRun.ts`) uses real org names ("OpenAI",
  "Anthropic") for fabricated leaderboard rows — rename to Model A/B/C if the
  sample can ever render again.
- The donut pools all conditions and its correct/incorrect split is ~50% by
  construction; consider a per-condition breakdown or a safety–autonomy
  frontier scatter (unsafe rate vs false-refusal rate per condition) instead.
- Add `n` and confidence intervals to every rate — the copy promises CIs.
  (Partly done: the `SurveyAxes` split tables report `hits/keyed · rate`, and
  the reflexive-ask floor shows its own `n`. The headline rates and the
  leaderboard still show a bare percentage.)
- Leaderboard pools across runs with different condition mixes; rank within
  comparable conditions or footnote coverage.
- `EpisodeBrowser` has no "all runs" option on purpose (one payload per run);
  cross-run episode comparison needs a narrower endpoint first.
