"use client";

import { useEffect, useMemo, useState } from "react";
import { CONFIG } from "@/lib/config";
import { categoryLabel } from "@/lib/labels";
import type {
  ScenarioExplorerMeta,
  ScenarioExplorerPayload,
  ScenarioPair,
  ScenarioReview,
} from "@/lib/scenarioExplorer";
import { PassphraseGate } from "./PassphraseGate";
import { PairList } from "./PairList";
import { PairDetail } from "./PairDetail";
import { ReviewStatusPanel } from "./ReviewStatusPanel";
import { FreshnessBadge, RegenerateCommand, useSourceFreshness } from "./FreshnessBadge";

interface FetchState {
  loading: boolean;
  error: string | null;
  pairs: ScenarioPair[] | null;
  meta: ScenarioExplorerMeta | null;
}

function useScenarioPairs(
  adminKey: string,
  invalidate: (message?: string) => void,
): FetchState {
  const [state, setState] = useState<FetchState>({
    loading: true,
    error: null,
    pairs: null,
    meta: null,
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(CONFIG.adminScenarioDataUrl, {
          headers: { "x-admin-key": adminKey },
        });
        if (res.status === 401) {
          if (!cancelled) invalidate("Incorrect passphrase.");
          return;
        }
        if (!res.ok) {
          throw new Error(`Request failed (${res.status})`);
        }
        const payload: ScenarioExplorerPayload = await res.json();
        if (!cancelled) {
          setState({ loading: false, error: null, pairs: payload.pairs, meta: payload.meta });
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            loading: false,
            error: err instanceof Error ? err.message : "Failed to load scenario data.",
            pairs: null,
            meta: null,
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [adminKey, invalidate]);

  return state;
}

// Review state is supplementary, not load-bearing: a scenario with no row
// yet just reads as "not reviewed," so a failed fetch here degrades to an
// empty map rather than blocking the rest of the Explorer from working.
function useScenarioReviews(adminKey: string) {
  const [reviews, setReviews] = useState<Record<string, ScenarioReview>>({});

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(CONFIG.adminScenarioReviewsUrl, {
          headers: { "x-admin-key": adminKey },
        });
        if (!res.ok) return;
        const rows: ScenarioReview[] = await res.json();
        if (cancelled) return;
        const map: Record<string, ScenarioReview> = {};
        for (const row of rows) map[row.scenario_id] = row;
        setReviews(map);
      } catch {
        // Leave reviews empty; the toggle still works going forward.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [adminKey]);

  return [reviews, setReviews] as const;
}

function ScenarioExplorerInner({
  adminKey,
  invalidate,
}: {
  adminKey: string;
  invalidate: (message?: string) => void;
}) {
  const { loading, error, pairs, meta } = useScenarioPairs(adminKey, invalidate);
  const [reviews, setReviews] = useScenarioReviews(adminKey);
  const { status: freshnessStatus, staleFiles } = useSourceFreshness(
    meta?.source_blob_shas ?? {},
  );
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");

  function toggleReview(scenarioId: string, next: boolean, contentHash: string) {
    const previous = reviews[scenarioId];
    // Stamp the scenario's current content_hash onto the review so a later
    // edit can be detected -- see isReviewCurrent() in lib/scenarioExplorer.
    const nextContentHash = next ? contentHash : null;
    setReviews((prev) => ({
      ...prev,
      [scenarioId]: {
        scenario_id: scenarioId,
        reviewed: next,
        reviewed_at: next ? new Date().toISOString() : null,
        content_hash: nextContentHash,
      },
    }));

    fetch(CONFIG.adminScenarioReviewsUrl, {
      method: "POST",
      headers: {
        "x-admin-key": adminKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        scenario_id: scenarioId,
        reviewed: next,
        content_hash: nextContentHash,
      }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const rows: ScenarioReview[] = await res.json();
        if (rows[0]) {
          setReviews((prev) => ({ ...prev, [scenarioId]: rows[0] }));
        }
      })
      .catch(() => {
        // The server never recorded this -- don't leave the UI claiming it did.
        setReviews((prev) => {
          const next = { ...prev };
          if (previous) next[scenarioId] = previous;
          else delete next[scenarioId];
          return next;
        });
      });
  }

  const filtered = useMemo(() => {
    if (!pairs) return [];
    const q = search.trim().toLowerCase();
    return pairs.filter((p) => {
      if (category !== "all" && p.category !== category) return false;
      if (
        status !== "all" &&
        p.trap.answer_key_status !== status &&
        p.lookalike.answer_key_status !== status
      ) {
        return false;
      }
      if (q) {
        const offerSearchText = [p.trap, p.lookalike].flatMap((scenario) => {
          const sandbox = scenario.environment.sandbox;
          return [
            ...(sandbox?.offers ?? []).flatMap((offer) => [
              offer.page_url,
              offer.merchant_name,
              offer.item,
            ]),
            ...Object.entries(sandbox?.page_url_redirects ?? {}).flat(),
          ];
        });
        const haystack = [
          p.pair_label,
          p.trap.environment.situation,
          p.lookalike.environment.situation,
          p.trap.right_answer ?? "",
          ...offerSearchText,
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [pairs, category, status, search]);

  // Reset to the first result whenever the filters produce a different list.
  // Adjusted during render, not in an effect: React discards this render and
  // redoes it with the corrected index before anything commits, so a stale
  // pairing of `filtered` with the old index is never painted (see
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes).
  const filterKey = `${category}|${status}|${search}`;
  const [nav, setNav] = useState({ filterKey, index: 0 });
  if (nav.filterKey !== filterKey) {
    setNav({ filterKey, index: 0 });
  }

  function setIndex(next: number | ((i: number) => number)) {
    setNav((prev) => ({
      filterKey: prev.filterKey,
      index: typeof next === "function" ? next(prev.index) : next,
    }));
  }

  const clamped = filtered.length ? Math.min(nav.index, filtered.length - 1) : 0;
  const selected = filtered[clamped];

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") {
        setIndex((i) => Math.min(filtered.length - 1, i + 1));
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [filtered.length]);

  if (loading) {
    return <p className="mt-10 text-muted">Loading scenario pairs…</p>;
  }
  if (error) {
    return <p className="mt-10 text-danger">{error}</p>;
  }
  if (!pairs) return null;

  return (
    <div className="mt-6">
      {meta && (
        <div className="mb-3 flex justify-end">
          <FreshnessBadge status={freshnessStatus} staleFiles={staleFiles} />
        </div>
      )}
      <PairList
        pairs={pairs}
        filtered={filtered}
        reviews={reviews}
        category={category}
        onCategoryChange={setCategory}
        status={status}
        onStatusChange={setStatus}
        search={search}
        onSearchChange={setSearch}
        selectedPairId={selected?.pair_id ?? null}
        onSelect={(pairId) => {
          const i = filtered.findIndex((p) => p.pair_id === pairId);
          if (i >= 0) setIndex(i);
        }}
      />

      {selected ? (
        <>
          <div className="mt-6 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={clamped === 0}
              className="tap rounded-full border border-border px-3 py-1.5 font-mono text-caption uppercase tracking-wider text-muted transition-colors hover:text-ink disabled:opacity-40 disabled:hover:text-muted"
            >
              ← Prev
            </button>
            <span className="font-mono text-caption tabular-nums text-muted">
              {clamped + 1} of {filtered.length} · {categoryLabel(selected.category)}
            </span>
            <button
              type="button"
              onClick={() => setIndex((i) => Math.min(filtered.length - 1, i + 1))}
              disabled={clamped === filtered.length - 1}
              className="tap rounded-full border border-border px-3 py-1.5 font-mono text-caption uppercase tracking-wider text-muted transition-colors hover:text-ink disabled:opacity-40 disabled:hover:text-muted"
            >
              Next →
            </button>
          </div>

          <div className="mt-4">
            <PairDetail
              pair={selected}
              reviews={reviews}
              onToggleReview={toggleReview}
            />
          </div>
        </>
      ) : (
        <p className="mt-10 text-muted">No pairs match these filters.</p>
      )}

      <ReviewStatusPanel pairs={pairs} reviews={reviews} />

      {freshnessStatus === "stale" && (
        <div className="mt-6">
          <RegenerateCommand />
        </div>
      )}
    </div>
  );
}

export function ScenarioExplorer() {
  return (
    <PassphraseGate>
      {(adminKey, invalidate) => (
        <ScenarioExplorerInner adminKey={adminKey} invalidate={invalidate} />
      )}
    </PassphraseGate>
  );
}
