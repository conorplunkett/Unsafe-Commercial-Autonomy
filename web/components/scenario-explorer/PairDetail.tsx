import { categoryLabel } from "@/lib/labels";
import type { ScenarioPair } from "@/lib/scenarioExplorer";
import { ScenarioSide } from "./ScenarioSide";

export function PairDetail({ pair }: { pair: ScenarioPair }) {
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-border pb-3">
        <span className="font-mono text-caption uppercase tracking-wider text-muted">
          {pair.pair_label} · {categoryLabel(pair.category)} · {pair.trap.stakes} stakes
        </span>
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
        <ScenarioSide scenario={pair.trap} />
        <ScenarioSide scenario={pair.lookalike} />
      </div>
    </div>
  );
}
