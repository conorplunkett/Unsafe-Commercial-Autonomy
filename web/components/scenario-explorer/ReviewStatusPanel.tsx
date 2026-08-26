import { Card } from "@/components/ui/Card";
import { isReviewCurrent } from "@/lib/scenarioExplorer";
import type { ScenarioExplorerRecord, ScenarioPair, ScenarioReview } from "@/lib/scenarioExplorer";

interface Row {
  scenarioId: string;
  label: string;
  scenario: ScenarioExplorerRecord;
}

function ChipList({ rows, tone }: { rows: Row[]; tone: "reviewed" | "pending" }) {
  if (!rows.length) {
    return (
      <p className="text-small text-muted">
        {tone === "reviewed" ? "None yet." : "All reviewed."}
      </p>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {rows.map((row) => (
        <span
          key={row.scenarioId}
          title={row.scenarioId}
          className={`rounded-lg border px-2 py-0.5 font-mono text-caption ${
            tone === "reviewed"
              ? "border-accent/30 bg-accent/[0.06] text-accent"
              : "border-border text-muted"
          }`}
        >
          {row.label}
        </span>
      ))}
    </div>
  );
}

// Reviewed-vs-not across *every* pair regardless of the current category/
// status/search filters -- this is a standing checklist, not a view of the
// filtered results above it.
export function ReviewStatusPanel({
  pairs,
  reviews,
}: {
  pairs: ScenarioPair[];
  reviews: Record<string, ScenarioReview>;
}) {
  const rows: Row[] = pairs.flatMap((p) => [
    { scenarioId: p.trap.scenario_id, label: `${p.pair_label} trap`, scenario: p.trap },
    {
      scenarioId: p.lookalike.scenario_id,
      label: `${p.pair_label} lookalike`,
      scenario: p.lookalike,
    },
  ]);
  const reviewed = rows.filter((r) => isReviewCurrent(reviews[r.scenarioId], r.scenario));
  const pending = rows.filter((r) => !isReviewCurrent(reviews[r.scenarioId], r.scenario));

  return (
    <Card as="details" tone="bare" pad="sm" className="mt-8">
      <summary className="tap cursor-pointer font-mono text-caption uppercase tracking-wider text-muted">
        Review status · {reviewed.length} of {rows.length} reviewed
      </summary>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="label">Reviewed ({reviewed.length})</p>
          <div className="mt-2">
            <ChipList rows={reviewed} tone="reviewed" />
          </div>
        </div>
        <div>
          <p className="label">Not reviewed ({pending.length})</p>
          <div className="mt-2">
            <ChipList rows={pending} tone="pending" />
          </div>
        </div>
      </div>
    </Card>
  );
}
