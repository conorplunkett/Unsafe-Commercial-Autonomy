"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { CONFIG } from "@/lib/config";
import { normalizeCondition } from "@/lib/labels";
import type { Result, Run, RunMeta } from "@/lib/types";
import { SAMPLE_RUN } from "@/lib/sampleRun";

interface DataState {
  run: Run | null;
  results: Result[];
  runs: RunMeta[];
  runId: string | null;
  setRunId: (id: string) => void;
  loading: boolean;
  isSample: boolean;
  /** Episodes per run, populated only by loadEpisodes(). */
  episodes: Record<string, Result[]>;
  /** Fetches one run's episodes, once, and caches them. */
  loadEpisodes: (id: string) => void;
  loadingEpisodes: string | null;
  episodesError: boolean;
}

const Ctx = createContext<DataState | null>(null);

async function sgetFrom(table: string, query: string) {
  const res = await fetch(`${CONFIG.supabaseUrl}/rest/v1/${table}?${query}`, {
    headers: {
      apikey: CONFIG.supabaseKey,
      Authorization: `Bearer ${CONFIG.supabaseKey}`,
    },
  });
  if (!res.ok) throw new Error(`Supabase ${res.status}`);
  return res.json();
}

async function sget(query: string) {
  return sgetFrom(CONFIG.table, query);
}

const EPISODE_PAGE = 1000;

const RUN_LIST_COLUMNS = "run_id,created_at,published_at,phase,label,model_names,metrics";

// The run list, with `superseded_by` when the project has it. That column
// arrived with db/migrations/0010; a project that hasn't run the migration
// rejects the whole select, which would empty the dashboard rather than lose
// one field. Retry without it — the same fallback the publisher uses for
// `model_names`. Nothing is then marked superseded, which is the truth for a
// project that has never merged runs.
async function fetchRunList(): Promise<RunMeta[]> {
  const order = "&order=published_at.desc";
  try {
    return await sget(`select=${RUN_LIST_COLUMNS},superseded_by${order}`);
  } catch {
    return sget(`select=${RUN_LIST_COLUMNS}${order}`);
  }
}

// Rows published before the 2026-08 condition rename carry "preflight_check";
// everything downstream groups and labels by the new key.
function normalizeResult(result: Result): Result {
  return result.control_condition
    ? { ...result, control_condition: normalizeCondition(result.control_condition) }
    : result;
}

// A run's episodes. New-style runs store one row per episode (publishing a
// full run as a single payload blob timed out at hundreds of MB), paged back
// in order; runs published before the episodes table keep `payload.results`
// and are served from it unchanged.
async function fetchEpisodes(id: string): Promise<Result[]> {
  const all: Result[] = [];
  try {
    for (let offset = 0; ; offset += EPISODE_PAGE) {
      const rows = await sgetFrom(
        CONFIG.episodesTable,
        `select=result&run_id=eq.${encodeURIComponent(id)}` +
          `&order=episode_index.asc&limit=${EPISODE_PAGE}&offset=${offset}`,
      );
      all.push(...rows.map((row: { result: Result }) => normalizeResult(row.result)));
      if (rows.length < EPISODE_PAGE) break;
    }
  } catch {
    // Episodes table unreachable (e.g. a deployment ahead of the migration):
    // the payload fallback below still serves old-style runs.
  }
  if (all.length) return all;
  const rows = await sget(
    `select=results:payload->results&run_id=eq.${encodeURIComponent(id)}&limit=1`,
  );
  return ((rows[0]?.results ?? []) as Result[]).map(normalizeResult);
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSample, setIsSample] = useState(false);
  const [episodes, setEpisodes] = useState<Record<string, Result[]>>({});
  const [loadingEpisodes, setLoadingEpisodes] = useState<string | null>(null);
  const [episodesError, setEpisodesError] = useState(false);
  // Runs whose episode fetch has already been started, so a second scroll into
  // the browser (or a re-render) never refires it.
  const requested = useRef<Set<string>>(new Set());

  // Load the list of published runs; fall back to the bundled sample if there
  // are none yet or Supabase can't be reached. This request carries the
  // top-level `metrics` column (tens of KB for every run put together), which is
  // all the leaderboard needs — episodes are fetched per run, on demand.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list: RunMeta[] = await fetchRunList();
        if (!active) return;
        if (list.length) {
          setRuns(list);
          setRunId(list[0].run_id);
          return;
        }
        throw new Error("no published runs");
      } catch {
        if (!active) return;
        setRun(SAMPLE_RUN);
        setRuns([
          {
            run_id: SAMPLE_RUN.run_id,
            created_at: SAMPLE_RUN.created_at,
            label: SAMPLE_RUN.label,
            phase: SAMPLE_RUN.phase,
            model_names: SAMPLE_RUN.model_names,
          },
        ]);
        setRunId(SAMPLE_RUN.run_id);
        setEpisodes({ [SAMPLE_RUN.run_id]: SAMPLE_RUN.results });
        setIsSample(true);
        setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Load the selected run: its (slim or legacy-full) payload, then its
  // episodes. The "sample" case needs no fetch: the fallback branch above
  // already sets loading false when it picks the sample run.
  useEffect(() => {
    if (!runId || runId === "sample") {
      return;
    }
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const rows = await sget(
          `select=payload&run_id=eq.${encodeURIComponent(runId)}&limit=1`,
        );
        if (!active) return;
        if (rows.length) {
          const payload = rows[0].payload as Run;
          if (!payload.results?.length) {
            payload.results = await fetchEpisodes(runId);
          }
          if (!active) return;
          setRun(payload);
          setIsSample(false);
          // These are this run's episodes; the browser reuses them instead of
          // fetching the same rows again.
          if (payload.results?.length) {
            requested.current.add(runId);
            setEpisodes((prev) => ({ ...prev, [runId]: payload.results }));
          }
        }
      } catch {
        /* keep whatever we already have */
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [runId]);

  // One run's episodes, fetched only when something asks for them (the episode
  // browser, when it scrolls into view). Row-per-episode runs page from the
  // episodes table; legacy runs fall back to `payload->results`, which skips
  // the run's event log — never rendered either way.
  const loadEpisodes = useCallback((id: string) => {
    if (!id || id === "sample" || requested.current.has(id)) return;
    requested.current.add(id);
    setLoadingEpisodes(id);
    setEpisodesError(false);
    (async () => {
      try {
        const results = await fetchEpisodes(id);
        setEpisodes((prev) => ({ ...prev, [id]: results }));
      } catch {
        // Allow a retry on the next request for this run.
        requested.current.delete(id);
        setEpisodesError(true);
      } finally {
        setLoadingEpisodes((current) => (current === id ? null : current));
      }
    })();
  }, []);

  return (
    <Ctx.Provider
      value={{
        run,
        results: run?.results ?? [],
        runs,
        runId,
        setRunId,
        loading,
        isSample,
        episodes,
        loadEpisodes,
        loadingEpisodes,
        episodesError,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useData(): DataState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useData must be used within DataProvider");
  return ctx;
}
