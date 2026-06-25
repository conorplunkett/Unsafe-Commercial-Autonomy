# PayBench — website

The public site for **PayBench**, a benchmark for unsafe commercial autonomy in
AI agents with delegated payment authority. Deployed at
[paybench.org](https://paybench.org).

A long-form, explanatory benchmark page (Next.js 16 App Router, Tailwind v4,
Newsreader + IBM Plex Mono) that reads results **live** from Supabase and falls
back to a bundled sample when no run is published.

> **Heads up:** this repo pins Next.js 16, which has breaking changes vs. older
> versions. See `AGENTS.md` — read `node_modules/next/dist/docs/` before editing.

## Develop

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build + type check
npm run lint
```

## Structure

- `app/page.tsx` — the single long-form landing page (hero → abstract →
  motivation → design → categories → taxonomy → control ladder → method →
  live results → leaderboard → dataset teaser → roadmap → limitations →
  citation → authors).
- `app/scenarios/page.tsx` — `/scenarios`, the full Phase-1 dataset browser.
- `components/` — one component per section. `DataProvider` is the single
  source of live/sample data; `Findings`, `StatRow`, `Donut`, `HeroChart`, and
  `Leaderboard` read from it via `useData()`.
- `lib/metrics.ts` — all aggregations (`summarize`, `byCondition`,
  `byCategory`, `confusion`, `byModel`). Everything reuses `summarize`, so the
  leaderboard can never disagree with the headline stats.
- `lib/config.ts` — Supabase + links. Set `NEXT_PUBLIC_PAPER_URL` to wire the
  "Read the paper" button to a public PDF/arXiv; otherwise it links to the
  on-page abstract.
- `lib/scenarios.ts` — **generated** bundle of the locked Phase-1 (v1, 50)
  scenarios for the dataset browser.

## Link previews (OpenGraph / social cards)

Every route ships rich link previews (iMessage, Messenger, Slack, X, etc.).
Keep this working when adding pages:

- Root defaults (title template, description, `openGraph`, `twitter`,
  `metadataBase`) live in `app/layout.tsx`.
- `app/opengraph-image.tsx` renders the shared 1200×630 card at build time
  (`force-static`, since the site is `output: export`).
- Give each new route its own `openGraph`/`twitter` `title`, `description`,
  `url`, and a `canonical`. **Note:** defining `openGraph` on a page drops the
  inherited file-based image, so re-reference it (`images: ["/opengraph-image"]`)
  — see `app/scenarios/page.tsx`.
- `vercel.json` forces `Content-Type: image/png` on the extensionless
  `opengraph-image` static file so scrapers actually render the card.

After deploying, sanity-check a URL at <https://www.opengraph.xyz>.

## Live data

`DataProvider` fetches published runs from Supabase (`benchmark_runs`) using a
read-only publishable key, with a deterministic sample fallback. Override at
build time with `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`,
`NEXT_PUBLIC_BENCHMARK_TABLE`.

## Regenerating the scenario dataset

`lib/scenarios.ts` is generated from the Phase-1 source set. Re-run from the
**repo root** (with the project's Python env) whenever the v1 scenarios change:

```bash
python3 - <<'PY'
import json
from app.data import load_scenarios
from app.models import model_to_dict
keep=('scenario_id','title','category','user_instruction','pair_id','pair_role','stakes','safe_to_act','right_answer','failure_tested','source_situation')
out=[{('situation' if k=='source_situation' else k): model_to_dict(s).get(k) for k in keep} for s in load_scenarios()]
header='''// AUTO-GENERATED from data/scenario_sets/v1_50_scenarios.md. Do not edit by hand.

export interface ScenarioCard {
  scenario_id: string; title: string; category: string; user_instruction: string;
  pair_id: string; pair_role: "trap" | "lookalike"; stakes: "low" | "high";
  safe_to_act: boolean | null; right_answer: string | null;
  failure_tested: string | null; situation: string;
}

export const SCENARIOS: ScenarioCard[] = '''
open('web/lib/scenarios.ts','w').write(header + json.dumps(out, indent=2, ensure_ascii=False) + ';\n')
print('wrote web/lib/scenarios.ts:', len(out))
PY
```

Only the **locked** Phase-1 set is published. The provisional 250-scenario set
stays in the repo to preserve benchmark integrity.
