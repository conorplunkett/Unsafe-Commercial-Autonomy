"use client";

import { useEffect, useState } from "react";
import { CONFIG } from "@/lib/config";
import type { ScenarioExplorerMeta } from "@/lib/scenarioExplorer";

const REPO_PATH = CONFIG.repoUrl.replace(/^https?:\/\/github\.com\//, "");

type FreshnessStatus = "checking" | "current" | "stale" | "unknown";

// Compares the git blob sha the Explorer's data was generated from (baked in
// at generate_scenario_explorer_data.py time) against the live blob sha
// GitHub reports for the same path on `main` -- a public, unauthenticated
// Contents API call, so a failure here (offline, rate-limited, GitHub down)
// reads as "unknown," never as a false "stale."
function useSourceFreshness(sourceBlobShas: Record<string, string>): {
  status: FreshnessStatus;
  staleFiles: string[];
} {
  const [status, setStatus] = useState<FreshnessStatus>("checking");
  const [staleFiles, setStaleFiles] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    const paths = Object.keys(sourceBlobShas);

    (async () => {
      try {
        const results = await Promise.all(
          paths.map(async (path) => {
            const res = await fetch(
              `https://api.github.com/repos/${REPO_PATH}/contents/${path}?ref=main`,
              { headers: { Accept: "application/vnd.github+json" } },
            );
            if (!res.ok) throw new Error(`GitHub API ${res.status} for ${path}`);
            const body: { sha?: string } = await res.json();
            return { path, current: body.sha === sourceBlobShas[path] };
          }),
        );
        if (cancelled) return;
        const stale = results.filter((r) => !r.current).map((r) => r.path);
        setStaleFiles(stale);
        setStatus(stale.length ? "stale" : "current");
      } catch {
        if (!cancelled) setStatus("unknown");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sourceBlobShas]);

  return { status, staleFiles };
}

const BADGE_BASE =
  "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 font-mono text-caption uppercase tracking-wider";

export function FreshnessBadge({ meta }: { meta: ScenarioExplorerMeta }) {
  const { status, staleFiles } = useSourceFreshness(meta.source_blob_shas);

  if (status === "checking") {
    return <span className={`${BADGE_BASE} border-border text-muted`}>Checking freshness…</span>;
  }
  if (status === "unknown") {
    return (
      <span
        title="Couldn't reach GitHub to check for source changes"
        className={`${BADGE_BASE} border-border text-muted`}
      >
        Freshness unknown
      </span>
    );
  }
  if (status === "stale") {
    return (
      <span
        title={`Changed since the last generate: ${staleFiles.join(", ")}`}
        className={`${BADGE_BASE} border-warn/40 bg-warn/10 text-warn`}
      >
        Data stale — regenerate &amp; redeploy
      </span>
    );
  }
  return (
    <span className={`${BADGE_BASE} border-accent/40 bg-accent/10 text-accent`}>
      Data current
    </span>
  );
}
