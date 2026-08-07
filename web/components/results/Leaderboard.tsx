"use client";

import { useData } from "./DataProvider";
import { byModel, poolModelMetrics } from "@/lib/metrics";
import { modelDisplayName } from "@/lib/labels";
import { CONFIG } from "@/lib/config";
import { pct, num } from "@/lib/format";

export function Leaderboard() {
  const { runs, results } = useData();
  // Rank across every published run so each model is scored on all its episodes,
  // not just the selected run — pooled from the runs' committed metrics, which
  // ship with the run list. Falls back to the selected run's episodes when a run
  // predates the by_model_name breakdown (and for the bundled sample).
  const pooledRows = poolModelMetrics(runs);
  const rows = pooledRows.length ? pooledRows : byModel(results);

  if (!rows.length) {
    return (
      <p className="mt-6 text-muted">
        No per-model results yet — the leaderboard populates from the published
        data.
      </p>
    );
  }

  return (
    <div className="mt-6">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-small">
          <thead>
            <tr className="border-b border-ink/25 text-left">
              <th className="py-2 pr-3 font-mono text-caption font-medium uppercase tracking-wider text-muted">
                #
              </th>
              <th className="py-2 pr-3 font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Model
              </th>
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Unsafe payment
              </th>
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Refused when safe
              </th>
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                User welfare
              </th>
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Missed recovery
              </th>
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Human alignment
              </th>
              <th className="py-2 pl-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                n
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.modelId} className="border-b border-border">
                <td className="py-2.5 pr-3 font-mono text-muted">{i + 1}</td>
                <td className="py-2.5 pr-3 font-serif text-ui">
                  {modelDisplayName(r.modelName)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-danger">
                  {pct(r.unsafe)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-warn">
                  {pct(r.refusedWhenSafe)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-accent">
                  {pct(r.welfare)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-danger">
                  {pct(r.missedRecovery)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-ink">
                  {r.humanAlignment == null ? "—" : r.humanAlignment.toFixed(2)}
                </td>
                <td className="py-2.5 pl-2 text-right font-mono text-muted">
                  {num(r.n)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <a
        href={CONFIG.dataUrl}
        target="_blank"
        rel="noreferrer"
        className="tap-link mt-6 rounded-full border border-accent px-4 py-2 font-mono text-caption uppercase tracking-wider text-accent transition-colors hover:bg-accent/10"
      >
        View the data →
      </a>
      <p className="mt-4 max-w-2xl text-small leading-snug text-muted">
        Per model, pooled across every published run. Ranked on the
        safety–autonomy frontier: lower unsafe-payment rate first, then a lower
        rate of refusing when it was safe to act. Both numbers are shown, so a
        model that only avoids unsafe payments by refusing everything does not
        top the board. The{" "}
        <span className="font-mono">n</span> column shows how many episodes back
        each row, so models with thinner coverage are visible. Both binary rates
        saturate, so two survey-grounded axes sit beside them: missed recovery,
        the share of gradeable stops that took a different stop than the answer
        key names, and human alignment, the mean share of surveyed respondents
        who preferred the action taken. Human alignment breaks ties the frontier
        cannot; it never reorders a ranking the frontier already decides. Ask
        calibration is a correlation and cannot be pooled across runs, so it is
        reported per run in the axes section above.
      </p>
    </div>
  );
}
