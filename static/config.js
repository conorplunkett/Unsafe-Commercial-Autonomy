// Public configuration for reading published benchmark results from Supabase.
//
// Safe to commit: the publishable key is designed to ship in client code, and
// row-level security on this project only grants public SELECT on the
// benchmark_runs table. It cannot write, and there are no other tables.
//
// The "Official run" dashboard reads from here. The "Run it yourself" flow does
// NOT use Supabase — it talks to the local backend and stays on the visitor's
// machine. If Supabase is unreachable or empty, the official dashboard falls
// back to the local /api/runs results so the page still works when run locally.
window.UCA_CONFIG = {
  supabaseUrl: "https://tethtzycfdplyzvrtknh.supabase.co",
  supabasePublishableKey: "sb_publishable_eWFeJOuV_jq9eZ8wNhlanQ_29XMuY2j",
  benchmarkTable: "benchmark_runs",
};
