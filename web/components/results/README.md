# Results architecture

This folder renders published benchmark results. Results are on by default;
`NEXT_PUBLIC_RESULTS_LIVE=false` is only for a proposal-mode build.

`DataProvider.tsx` loads the published run list and its committed metrics first.
It loads full episodes per run from `benchmark_run_episodes`, with a legacy
fallback to `payload.results`. Episode rows are paged from Supabase and reused
in memory.

`Leaderboard.tsx` pools compatible counts from each run's committed metrics. It
does not download every run's episodes. Runs without `by_model_name`, runs using
an older unsafe denominator, and superseded source runs do not enter the pool.
Recompute and republish an old run to make it eligible.

`EpisodeBrowser.tsx` requests a run near the viewport and renders its in-memory
rows in batches. Keep these loading boundaries when changing the results UI;
full published runs can contain thousands of episodes.
