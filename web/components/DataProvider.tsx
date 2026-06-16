"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { CONFIG } from "@/lib/config";
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
}

const Ctx = createContext<DataState | null>(null);

async function sget(query: string) {
  const res = await fetch(`${CONFIG.supabaseUrl}/rest/v1/${CONFIG.table}?${query}`, {
    headers: {
      apikey: CONFIG.supabaseKey,
      Authorization: `Bearer ${CONFIG.supabaseKey}`,
    },
  });
  if (!res.ok) throw new Error(`Supabase ${res.status}`);
  return res.json();
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSample, setIsSample] = useState(false);

  // Load the list of published runs; fall back to the bundled sample if there
  // are none yet or Supabase can't be reached.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list: RunMeta[] = await sget(
          "select=run_id,created_at,published_at,phase,label&order=published_at.desc",
        );
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
          },
        ]);
        setRunId(SAMPLE_RUN.run_id);
        setIsSample(true);
        setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Load the selected run's full payload.
  useEffect(() => {
    if (!runId || runId === "sample") {
      if (runId === "sample") setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    (async () => {
      try {
        const rows = await sget(
          `select=payload&run_id=eq.${encodeURIComponent(runId)}&limit=1`,
        );
        if (!active) return;
        if (rows.length) {
          setRun(rows[0].payload as Run);
          setIsSample(false);
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
