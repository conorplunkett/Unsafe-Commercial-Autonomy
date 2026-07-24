"use client";

import { useData } from "./DataProvider";
import { byCondition, byCategory } from "@/lib/metrics";
import { CONDITION_LABELS, categoryLabel } from "@/lib/labels";
import { pct, compactDate } from "@/lib/format";

function RunControls() {
  const { runs, runId, setRunId, run, isSample } = useData();
  return (
    <div className="flex flex-wrap items-center gap-3">
      {runs.length > 1 ? (
        <select
          value={runId ?? ""}
          onChange={(e) => setRunId(e.target.value)}
          className="rounded-md border border-border bg-paper px-3 py-1.5 font-mono text-sm"
        >
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>
              {r.label ?? r.phase ?? r.run_id} · {compactDate(r.published_at ?? r.created_at)}
            </option>
          ))}
        </select>
      ) : (
        <span className="font-mono text-xs text-muted">
          {run?.label ?? "Latest run"} · {compactDate(run?.created_at)}
        </span>
      )}
      {isSample && (
        <span className="rounded-full border border-warn/40 bg-warn/10 px-2.5 py-1 font-mono text-[0.65rem] uppercase tracking-wider text-warn">
          Sample data — live results unavailable right now
        </span>
      )}
    </div>
  );
}

function ConditionTable() {
  const { results } = useData();
  const rows = byCondition(results);
  if (!rows.length) {
    return <p className="text-muted">No control-condition breakdown in this run.</p>;
  }
  return (
    <table className="w-full border-collapse text-[0.95rem]">
      <thead>
        <tr className="border-b border-ink/25 text-left">
          <th className="py-2 pr-3 font-mono text-xs font-medium uppercase tracking-wider text-muted">
            Control condition
          </th>
          <th className="py-2 px-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
            Unsafe
          </th>
          <th className="py-2 px-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
            Refused
          </th>
          <th className="py-2 pl-2 text-right font-mono text-xs font-medium uppercase tracking-wider text-muted">
            User welfare
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.condition} className="border-b border-border">
            <td className="py-2.5 pr-3">{CONDITION_LABELS[r.condition] ?? r.condition}</td>
            <td className="py-2.5 px-2 text-right font-mono text-danger">{pct(r.unsafe)}</td>
            <td className="py-2.5 px-2 text-right font-mono text-warn">{pct(r.refusedWhenSafe)}</td>
            <td className="py-2.5 pl-2 text-right font-mono text-accent">{pct(r.welfare)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CategoryBars() {
  const { results } = useData();
  const rows = byCategory(results);
  if (!rows.length) {
    return <p className="text-muted">No category breakdown in this run.</p>;
  }
  return (
    <div className="space-y-4">
      {rows.map((r) => (
        <div key={r.category}>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="text-[0.95rem]">{categoryLabel(r.category)}</span>
            <span className="font-mono text-sm text-muted">{pct(r.unsafe)}</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-paper-2">
            <div
              className="h-full rounded-full bg-danger"
              style={{ width: `${Math.round((r.unsafe ?? 0) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Findings() {
  return (
    <div className="mt-6">
      <RunControls />
      <div className="mt-8 grid gap-12 lg:grid-cols-2">
        <div>
          <p className="label mb-3">Unsafe payment by control condition</p>
          <ConditionTable />
        </div>
        <div>
          <p className="label mb-3">Unsafe payment by category</p>
          <CategoryBars />
        </div>
      </div>
    </div>
  );
}
