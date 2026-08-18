// Results are live: the first runs are published to Supabase. This controls
// the stat row under the hero, the Results section (donut + findings tables),
// the leaderboard, the Results/Leaderboard nav links, and the Supabase
// DataProvider fetch. The components live in components/results/. Set
// NEXT_PUBLIC_RESULTS_LIVE=false at build time to fall back to proposal mode.
export const RESULTS_LIVE =
  process.env.NEXT_PUBLIC_RESULTS_LIVE !== "false";

// Read-only Supabase config for the public results dashboard. The publishable
// key is safe in client code — row-level security grants public read only. Env
// vars override the baked-in defaults if set at build time on Vercel.
export const CONFIG = {
  supabaseUrl:
    process.env.NEXT_PUBLIC_SUPABASE_URL ??
    "https://tethtzycfdplyzvrtknh.supabase.co",
  supabaseKey:
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
    "sb_publishable_eWFeJOuV_jq9eZ8wNhlanQ_29XMuY2j",
  table: process.env.NEXT_PUBLIC_BENCHMARK_TABLE ?? "benchmark_runs",
  // Row-per-episode store for runs published in batches; older runs keep
  // their episodes inside `payload` and the DataProvider falls back to it.
  episodesTable:
    process.env.NEXT_PUBLIC_BENCHMARK_EPISODES_TABLE ?? "benchmark_run_episodes",
  repoUrl: "https://github.com/conorplunkett/Unsafe-Commercial-Autonomy",
  // Where the published runs come from and how they are written out — the
  // repo's results-publishing section. Target of the leaderboard's
  // "View the data" link.
  dataUrl:
    "https://github.com/conorplunkett/Unsafe-Commercial-Autonomy#publishing-results-to-the-public-site",
  // Public link to the paper/writeup. Leave empty until a public PDF/arXiv/Notion
  // is available — the UI falls back to the on-page abstract. Override at build
  // time with NEXT_PUBLIC_PAPER_URL.
  paperUrl: process.env.NEXT_PUBLIC_PAPER_URL ?? "",
  // Bundled PDF served from /public. Currently a placeholder until the final
  // paper is dropped in at this path.
  paperPdf: process.env.NEXT_PUBLIC_PAPER_PDF ?? "/paybench.pdf",
  contactEmail: "hello@conorplunkett.com",
  siteUrl: "https://paybench.org",
  // Passphrase-gated function serving the Phase 2 scenario/answer-key
  // snapshot for the Scenario Explorer. Not secret itself -- the admin
  // passphrase sent as the x-admin-key header is what protects the data.
  adminScenarioDataUrl:
    process.env.NEXT_PUBLIC_ADMIN_SCENARIO_DATA_URL ??
    "https://tethtzycfdplyzvrtknh.supabase.co/functions/v1/admin-scenario-data",
} as const;

// Whether an external paper link is configured.
export const HAS_PAPER = CONFIG.paperUrl.length > 0;

// Copy-able BibTeX citation shown in the Cite section.
export const CITATION = `@misc{plunkett2026paybench,
  title  = {PayBench: A Benchmark for Unsafe Commercial Autonomy in AI Agents
            with Delegated Payment Authority},
  author = {Plunkett, Conor},
  year   = {2026},
  url    = {https://paybench.org}
}`;
