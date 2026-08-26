import {
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  answerKeyStatusLabel,
} from "@/lib/labels";
import { Card } from "@/components/ui/Card";
import type { ScenarioPair, ScenarioReview } from "@/lib/scenarioExplorer";

// A pair counts as reviewed only once both of its scenarios are; until then it
// reads as still needing review and is flagged in the list.
function pairReviewed(
  pair: ScenarioPair,
  reviews: Record<string, ScenarioReview>,
): boolean {
  return Boolean(
    reviews[pair.trap.scenario_id]?.reviewed &&
      reviews[pair.lookalike.scenario_id]?.reviewed,
  );
}

// Real values of ScenarioExplorerRecord["answer_key_status"] -- the filter
// compares against these directly (see ScenarioExplorer.tsx), so an option
// here has to be a real status or it silently matches nothing.
const STATUS_OPTIONS = [
  "all",
  "objective",
  "awaiting_survey",
  "survey_locked_70",
  "provisional_answer",
  "unsafe_clear_safe_unclear",
  "excluded",
];

// Matches the Episode Browser's filter controls (components/results/
// EpisodeBrowser.tsx) so the admin surfaces read as one product.
const selectClass =
  "tap w-full rounded-lg border border-border bg-paper px-3 py-1.5 font-mono text-small";

export function PairList({
  pairs,
  filtered,
  reviews,
  category,
  onCategoryChange,
  status,
  onStatusChange,
  search,
  onSearchChange,
  selectedPairId,
  onSelect,
}: {
  pairs: ScenarioPair[];
  filtered: ScenarioPair[];
  reviews: Record<string, ScenarioReview>;
  category: string;
  onCategoryChange: (value: string) => void;
  status: string;
  onStatusChange: (value: string) => void;
  search: string;
  onSearchChange: (value: string) => void;
  selectedPairId: string | null;
  onSelect: (pairId: string) => void;
}) {
  return (
    <div>
      <Card>
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <p className="label">Filters</p>
          <p className="font-mono text-caption tabular-nums text-muted">
            {filtered.length} of {pairs.length} pairs
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.5fr)] sm:items-end">
          <div>
            <label className="label" htmlFor="se-category">
              Category
            </label>
            <select
              id="se-category"
              className={`mt-1 ${selectClass}`}
              value={category}
              onChange={(e) => onCategoryChange(e.target.value)}
            >
              <option value="all">All categories</option>
              {CATEGORY_ORDER.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="se-status">
              Status
            </label>
            <select
              id="se-status"
              className={`mt-1 ${selectClass}`}
              value={status}
              onChange={(e) => onStatusChange(e.target.value)}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === "all" ? "Any status" : answerKeyStatusLabel(s)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="se-search">
              Search
            </label>
            <input
              id="se-search"
              type="search"
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Situation text or pair"
              className="tap mt-1 w-full rounded-lg border border-border bg-paper px-3 py-1.5 text-small"
            />
          </div>
        </div>
      </Card>

      <div className="mt-3 max-h-72 overflow-auto rounded-2xl border border-border">
        <table className="w-full min-w-[36rem] table-fixed border-collapse text-small">
          <colgroup>
            <col className="w-14" />
            <col />
            <col className="w-36" />
            <col className="w-32" />
          </colgroup>
          <tbody>
            {filtered.map((p) => {
              const reviewed = pairReviewed(p, reviews);
              const selected = selectedPairId === p.pair_id;
              return (
                <tr
                  key={p.pair_id}
                  onClick={() => onSelect(p.pair_id)}
                  className={`cursor-pointer border-b border-border transition-colors ${
                    selected
                      ? "bg-paper-2"
                      : reviewed
                        ? "hover:bg-paper-2"
                        : "bg-flag/[0.06] hover:bg-flag/10"
                  }`}
                >
                  <td className="px-3 py-2 align-top font-mono text-caption text-muted">
                    {p.pair_label}
                  </td>
                  <td className="px-2 py-2 align-top leading-snug">
                    {p.trap.environment.situation}
                  </td>
                  <td
                    title={answerKeyStatusLabel(p.trap.answer_key_status)}
                    className="overflow-hidden text-ellipsis whitespace-nowrap px-3 py-2 align-top font-mono text-caption text-muted"
                  >
                    {answerKeyStatusLabel(p.trap.answer_key_status)}
                  </td>
                  <td className="px-3 py-2 align-top">
                    <span
                      title={
                        reviewed
                          ? "Both sides reviewed"
                          : "Still needs review"
                      }
                      className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-caption font-semibold ${
                        reviewed
                          ? "bg-accent/10 text-accent"
                          : "bg-flag/10 text-flag"
                      }`}
                    >
                      {reviewed ? "Reviewed" : "Not reviewed"}
                    </span>
                  </td>
                </tr>
              );
            })}
            {!filtered.length && (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-muted">
                  No matching pairs.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
