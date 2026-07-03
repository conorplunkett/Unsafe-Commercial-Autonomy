# Once results are live

Everything in this folder renders **published benchmark results** and is hidden
while the site is a proposal (no runs published yet). It is all gated behind one
flag: `RESULTS_LIVE` in `web/lib/config.ts`.

## To re-enable when the first real run is published

1. Publish the run to Supabase (`app/supabase_publish.py`) and confirm it shows
   up: `GET {supabaseUrl}/rest/v1/benchmark_runs?select=run_id` must return rows.
2. Flip the flag: set `NEXT_PUBLIC_RESULTS_LIVE=true` in the Vercel build env
   (or change the default in `web/lib/config.ts`).
3. That flag automatically restores:
   - `StatRow` — headline rates under the hero (`app/page.tsx`)
   - the **Results** section — `Donut` + `Findings` (`app/page.tsx`)
   - the **Leaderboard** section (`app/page.tsx`)
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

## Known issues to fix before/when re-enabling (from the frontend review)

- The sample fallback (`lib/sampleRun.ts`) uses real org names ("OpenAI",
  "Anthropic") for fabricated leaderboard rows — rename to Model A/B/C if the
  sample can ever render again.
- `StatRow`'s headline "unsafe payment" pools across all control conditions —
  prefer the no-policy → best-control delta (e.g. "77% → 13%").
- The donut pools all conditions and its correct/incorrect split is ~50% by
  construction; consider a per-condition breakdown or a safety–autonomy
  frontier scatter (unsafe rate vs false-refusal rate per condition) instead.
- Add `n` and confidence intervals to every rate — the copy promises CIs.
- Leaderboard pools across runs with different condition mixes; rank within
  comparable conditions or footnote coverage.
