import { categoryLabel } from "@/lib/labels";
import type { ScenarioPair, ScenarioReview } from "@/lib/scenarioExplorer";
import { ScenarioSide } from "./ScenarioSide";

// A pair is off-limits the moment either side is on the preference survey --
// almost always just the trap (the lookalike is never the surveyed one), but
// once its wording is on the instrument its pair-mate is frozen too, since
// the two are graded as a matched comparison.
function pairIsLocked(pair: ScenarioPair): boolean {
  return pair.trap.semantic_only || pair.lookalike.semantic_only;
}

function EditabilityPill({ pair }: { pair: ScenarioPair }) {
  if (pairIsLocked(pair)) {
    return (
      <span
        title="On the preference survey -- never edit this scenario or its pair-mate"
        className="inline-block w-fit rounded-full border border-danger/40 bg-danger/10 px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider text-danger"
      >
        Locked
      </span>
    );
  }
  return (
    <span
      title="Not on the preference survey -- safe to edit"
      className="inline-block w-fit rounded-full border border-border px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider text-muted"
    >
      Editable
    </span>
  );
}

export function PairDetail({
  pair,
  reviews,
  onToggleReview,
}: {
  pair: ScenarioPair;
  reviews?: Record<string, ScenarioReview>;
  onToggleReview?: (scenarioId: string, next: boolean) => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-border pb-3">
        <span className="font-mono text-caption uppercase tracking-wider text-muted">
          {pair.pair_label} · {categoryLabel(pair.category)} · {pair.trap.stakes} stakes
        </span>
        <EditabilityPill pair={pair} />
        <span className="text-small">
          <span className="text-muted">Right answer: </span>
          <span className="text-accent">{pair.trap.right_answer ?? "—"}</span>
        </span>
        {pair.trap.failure_tested && (
          <span className="font-mono text-caption text-muted">
            tests: {pair.trap.failure_tested}
          </span>
        )}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <ScenarioSide
          scenario={pair.trap}
          review={reviews?.[pair.trap.scenario_id]}
          onToggleReview={
            onToggleReview &&
            ((next) => onToggleReview(pair.trap.scenario_id, next))
          }
        />
        <ScenarioSide
          scenario={pair.lookalike}
          review={reviews?.[pair.lookalike.scenario_id]}
          onToggleReview={
            onToggleReview &&
            ((next) => onToggleReview(pair.lookalike.scenario_id, next))
          }
        />
      </div>
    </div>
  );
}
