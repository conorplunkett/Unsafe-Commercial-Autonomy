import {
  CATEGORY_ORDER,
  CATEGORY_LABELS,
  answerKeyStatusLabel,
} from "@/lib/labels";
import type { ScenarioPair } from "@/lib/scenarioExplorer";

const STATUS_OPTIONS = [
  "all",
  "objective",
  "awaiting_survey",
  "locked",
  "provisional",
  "dropped",
];

const chip =
  "tap rounded-full border px-3 py-1 font-mono text-caption transition-colors";
const on = "border-accent bg-accent/10 text-accent";
const off = "border-border text-muted hover:text-ink";

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
      <div className="flex flex-wrap items-center gap-2">
        <button
          className={`${chip} ${category === "all" ? on : off}`}
          onClick={() => onCategoryChange("all")}
        >
          All categories
        </button>
        {CATEGORY_ORDER.map((c) => (
          <button
            key={c}
            className={`${chip} ${category === c ? on : off}`}
            onClick={() => onCategoryChange(c)}
          >
            {CATEGORY_LABELS[c]}
          </button>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            className={`${chip} ${status === s ? on : off}`}
            onClick={() => onStatusChange(s)}
          >
            {s === "all" ? "Any status" : answerKeyStatusLabel(s)}
          </button>
        ))}
      </div>

      <input
        type="search"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search situation text or pair"
        className="tap mt-3 w-full rounded-lg border border-border bg-paper px-3 py-1.5 text-small"
      />

      <p className="mt-3 font-mono text-caption text-muted">
        {filtered.length} of {pairs.length} pairs
      </p>

      <div className="mt-2 max-h-72 overflow-auto rounded-lg border border-border">
        <table className="w-full min-w-[26rem] border-collapse text-small">
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.pair_id}
                onClick={() => onSelect(p.pair_id)}
                className={`cursor-pointer border-b border-border transition-colors ${
                  selectedPairId === p.pair_id ? "bg-paper-2" : "hover:bg-paper-2"
                }`}
              >
                <td className="whitespace-nowrap px-3 py-2 align-top font-mono text-caption text-muted">
                  {p.pair_label}
                </td>
                <td className="px-2 py-2 align-top leading-snug">
                  {p.trap.environment.situation}
                </td>
                <td className="whitespace-nowrap px-3 py-2 align-top font-mono text-caption text-muted">
                  {answerKeyStatusLabel(p.trap.answer_key_status)}
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={3} className="px-3 py-6 text-muted">
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
