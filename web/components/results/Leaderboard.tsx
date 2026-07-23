"use client";

import { useData } from "./DataProvider";
import { byModel } from "@/lib/metrics";
import { pct, num } from "@/lib/format";

export function Leaderboard() {
  const { allResults, results } = useData();
  // Rank across every published run so each model is scored on all its episodes,
  // not just the selected run. Fall back to the selected run if the pooled fetch
  // came back empty.
  const pooled = allResults.length ? allResults : results;
  const rows = byModel(pooled);

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
        <table className="w-full border-collapse text-[0.95rem]">
          <thead>
            <tr className="border-b border-ink/25 text-left">
              <th className="py-2 pr-3 font-mono text-xs font-medium uppercase tracking-wider text-muted">
                #
              </th>
              <th className="py-2 pr-3 font-mono text-xs font-medium uppercase tracking-wider text-muted">
                Model
              </th>
              <th className="py-2 px-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
                Unsafe payment
              </th>
              <th className="py-2 px-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
                Refused when safe
              </th>
              <th className="py-2 px-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
                Welfare
              </th>
              <th className="py-2 pl-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
                n
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.modelId} className="border-b border-border">
                <td className="py-2.5 pr-3 font-mono text-muted">{i + 1}</td>
                <td className="py-2.5 pr-3 font-serif text-[1.05rem]">
                  {r.modelName}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-danger">
                  {pct(r.unsafe)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-warn">
                  {pct(r.falseRefusal)}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-accent">
                  {pct(r.welfare)}
                </td>
                <td className="py-2.5 pl-2 text-right font-mono text-muted">
                  {num(r.n)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 max-w-2xl text-sm leading-snug text-muted">
        Per model, pooled across every published run. Ranked on the
        safety–autonomy frontier: lower unsafe-payment rate first, then a lower
        rate of refusing when it was safe to act. Both numbers are shown, so a
        model that only avoids unsafe payments by refusing everything does not
        top the board. The{" "}
        <span className="font-mono">n</span> column shows how many episodes back
        each row, so models with thinner coverage are visible.
      </p>
    </div>
  );
}
