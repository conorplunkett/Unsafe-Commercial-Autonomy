import {
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  answerKeyStatusLabel,
} from "@/lib/labels";
import { Card } from "@/components/ui/Card";
import type { ScenarioPair } from "@/lib/scenarioExplorer";

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
        <table className="w-full min-w-[34rem] table-fixed border-collapse text-small">
          <colgroup>
            <col className="w-14" />
            <col />
            <col className="w-36" />
            <col className="w-16" />
          </colgroup>
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.pair_id}
                onClick={() => onSelect(p.pair_id)}
                className={`cursor-pointer border-b border-border transition-colors ${
                  selectedPairId === p.pair_id ? "bg-paper-2" : "hover:bg-paper-2"
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
                <td
                  title={
                    p.trap.enforcement.in_enforced_arm
                      ? "tool_constraints runs this pair"
                      : "tool_constraints skips this pair"
                  }
                  className={`whitespace-nowrap px-3 py-2 align-top font-mono text-caption ${
                    p.trap.enforcement.in_enforced_arm ? "text-accent" : "text-muted"
                  }`}
                >
                  {p.trap.enforcement.in_enforced_arm ? "Arm 3" : "—"}
                </td>
              </tr>
            ))}
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
