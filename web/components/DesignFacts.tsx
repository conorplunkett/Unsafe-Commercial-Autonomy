import { SCENARIOS } from "@/lib/scenarios";
import { CATEGORY_ORDER, CONDITION_ORDER, TAXONOMY } from "@/lib/labels";
import { num } from "@/lib/format";

// Proposal-mode stand-in for the results StatRow: the same visual rhythm under
// the hero, but only facts about the benchmark design — no measured rates.
// Once results are live, page.tsx swaps this back for components/results/StatRow.
export function DesignFacts() {
  const facts = [
    { label: "Locked scenarios", value: num(SCENARIOS.length) },
    { label: "Categories", value: num(CATEGORY_ORDER.length) },
    { label: "Failure modes", value: num(TAXONOMY.length) },
    { label: "Control layers", value: num(CONDITION_ORDER.length) },
    { label: "Seeds / scenario", value: "5" },
    { label: "Phases", value: "3" },
  ];
  return (
    <div className="mt-12 grid grid-cols-2 gap-y-6 border-y border-border py-6 sm:grid-cols-3 md:grid-cols-6">
      {facts.map((f) => (
        <div
          key={f.label}
          className="border-l border-border pl-4 first:border-l-0 first:pl-0 md:border-l md:first:border-l-0"
        >
          <p className="label">{f.label}</p>
          <p className="mt-1 font-mono text-[1.7rem] leading-none text-ink">
            {f.value}
          </p>
        </div>
      ))}
    </div>
  );
}
