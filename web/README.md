# PayBench website

The static public site for [paybench.org](https://paybench.org). It uses
Next.js 16, Tailwind v4, and client-side Supabase reads.

Read `AGENTS.md` and `DESIGN.md` before changing the site.

## Develop

```bash
cd web
npm install
npm run dev
npm run lint
npm run build
```

The local site runs at `http://localhost:3000`. `npm run build` produces the
static export under `web/out/`.

## Data

Published run metadata lives in `benchmark_runs`; episodes live in
`benchmark_run_episodes`. The browser reads both with the public Supabase key
from `lib/config.ts`. Build-time overrides use:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_BENCHMARK_TABLE`
- `NEXT_PUBLIC_BENCHMARK_EPISODES_TABLE`

The results UI is enabled by default. Set `NEXT_PUBLIC_RESULTS_LIVE=false` only
for a proposal-mode build. If no published run is reachable, the site uses the
bundled deterministic sample.

Runs are published from the repository root; see `../RUNBOOK.md`. Database
changes live under `../db/migrations/`.

`lib/scenarios.ts` is the generated browser bundle for the locked Phase 1
dataset. `lib/surveyResults.ts` is the generated Phase 1 survey aggregate.
Phase 1 is closed, so neither file needs routine regeneration.

## Deploy

The repository-root `vercel.json` installs and builds this directory, serves
`web/out/`, configures clean URLs, and sets the OpenGraph image content type.
