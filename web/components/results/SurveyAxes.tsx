"use client";

import { useData } from "./DataProvider";
import {
  bySemanticOnly,
  byStakes,
  humanAxes,
  reflexiveAskFloor,
  summarize,
  type SplitPoint,
} from "@/lib/metrics";
import { corr, pct, signedPct } from "@/lib/format";

// The four survey-grounded axes, plus both binary rates split by stakes and by
// whether the answer key rests on a preference the survey validated. Additive
// to the headline rates, which keep their definitions — this section exists
// because those two rates saturate, not because they changed.

function Axis({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  // A node, not a string: the notes carry hyphenated terms ("would-accept")
  // that must not break across lines in a column this narrow.
  note: React.ReactNode;
  tone: string;
}) {
  return (
    <div className="border-l border-border pl-4 first:border-l-0 first:pl-0 sm:border-l sm:first:border-l-0">
      <p className="label">{label}</p>
      <p className={`mt-1 font-mono text-stat leading-none ${tone}`}>{value}</p>
      <p className="mt-1.5 font-mono text-caption leading-snug text-muted">
        {note}
      </p>
    </div>
  );
}

function SplitTable({ title, rows }: { title: string; rows: SplitPoint[] }) {
  if (!rows.length) return null;
  const cell = (rate: number | null, count: number, total: number) =>
    total ? `${count}/${total} · ${pct(rate)}` : "—";
  return (
    <div className="min-w-0">
      <p className="label mb-3">{title}</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-small">
          <thead>
            <tr className="border-b border-ink/25 text-left">
              <th className="py-2 pr-3 font-mono text-caption font-medium uppercase tracking-wider text-muted" />
              <th className="py-2 px-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Unsafe payment
              </th>
              <th className="py-2 pl-2 text-right font-mono text-caption font-medium uppercase tracking-wider text-muted">
                Refused when safe
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.bucket} className="border-b border-border">
                <td className="py-2.5 pr-3">
                  {BUCKET_LABELS[r.bucket] ?? r.bucket}
                </td>
                <td className="py-2.5 px-2 text-right font-mono text-danger">
                  {cell(r.unsafe, r.unsafeCount, r.unsafeTotal)}
                </td>
                <td className="py-2.5 pl-2 text-right font-mono text-warn">
                  {cell(r.refusedWhenSafe, r.refusedCount, r.refusedTotal)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const BUCKET_LABELS: Record<string, string> = {
  high: "High stakes",
  low: "Low stakes",
  semantic_only: "Ambiguous",
  objective: "Objective",
};

export function SurveyAxes() {
  const { results, run, loading } = useData();
  const axes = humanAxes(results);
  const floor = reflexiveAskFloor(run?.metrics);
  const refused = summarize(results).refusedWhenSafeRate;
  const excess = floor && refused != null ? refused - floor.rate : null;

  // "No run here yet" and "this run predates the axes" are different claims, and
  // only the second one is about the data. The page is a static export, so the
  // pre-hydration render and the first paint of every visit both land here with
  // no run loaded — asserting the run predates the axes in that window states
  // something false about whichever run is about to arrive.
  if (loading || !run) {
    return <p className="mt-6 text-muted">Loading the selected run…</p>;
  }

  // A run scored before these axes existed carries none of their inputs. Four
  // em-dashes would read as four measured zeroes, so render nothing instead.
  if (
    !axes.missedRecovery &&
    !axes.humanAlignment &&
    !axes.askCalibration &&
    !floor
  ) {
    return null;
  }

  return (
    <div className="mt-10">
      <p className="label mb-3">Survey-grounded axes</p>
      <div className="grid grid-cols-2 gap-y-6 border-y border-border py-6 md:grid-cols-4">
        <Axis
          label="Incorrect stoppage"
          value={axes.missedRecovery ? pct(axes.missedRecovery.rate) : "—"}
          note={
            axes.missedRecovery
              ? `${axes.missedRecovery.count}/${axes.missedRecovery.total} graded stops`
              : "no gradeable stop"
          }
          tone="text-danger"
        />
        <Axis
          label="Human acceptance"
          value={
            axes.humanAlignment
              ? axes.humanAlignment.preferredMean.toFixed(2)
              : "—"
          }
          note={
            axes.humanAlignment ? (
              <>
                <span className="whitespace-nowrap">
                  {axes.humanAlignment.scenarios} surveyed scenarios
                </span>
                {axes.humanAlignment.acceptableMean != null && (
                  <>
                    {" · "}
                    <span className="whitespace-nowrap">
                      would-accept{" "}
                      {axes.humanAlignment.acceptableMean.toFixed(2)}
                    </span>
                  </>
                )}
              </>
            ) : (
              "no surveyed scenario"
            )
          }
          tone="text-accent"
        />
        <Axis
          label="Asks when supposed to"
          value={corr(axes.askCalibration?.r)}
          note={
            axes.askCalibration
              ? `agent ${pct(axes.askCalibration.agentAskRate)} vs human ${pct(
                  axes.askCalibration.humanAskRate,
                )}`
              : "too few surveyed scenarios"
          }
          tone="text-ink"
        />
        <Axis
          label="Vs reflexive floor"
          value={signedPct(excess)}
          note={
            floor
              ? `${pct(floor.rate)} floor · n=${floor.total}${
                  floor.source === "phase1_fallback" ? " · Phase 1, provisional" : ""
                }`
              : "no survey floor"
          }
          tone={excess != null && excess > 0 ? "text-danger" : "text-accent"}
        />
      </div>

      <div className="mt-8 grid gap-12 lg:grid-cols-2">
        <SplitTable title="By stakes" rows={byStakes(results)} />
        <SplitTable title="By answer key" rows={bySemanticOnly(results)} />
      </div>
    </div>
  );
}
