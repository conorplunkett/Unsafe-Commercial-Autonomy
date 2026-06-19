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
  repoUrl: "https://github.com/conorplunkett/Unsafe-Commercial-Autonomy",
  // Public link to the paper/writeup. Leave empty until a public PDF/arXiv/Notion
  // is available — the UI falls back to the on-page abstract. Override at build
  // time with NEXT_PUBLIC_PAPER_URL.
  paperUrl: process.env.NEXT_PUBLIC_PAPER_URL ?? "",
  contactEmail: "hello@paybench.org",
  siteUrl: "https://paybench.org",
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
