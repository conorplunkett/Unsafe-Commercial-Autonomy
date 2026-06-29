// At-a-glance facts about the *design* of the benchmark — not results. The page
// reports no measured rates until a run is published; these are the fixed
// parameters of the Phase-1 proposal (Notion §4–§6).
const STATS: { label: string; value: string }[] = [
  { label: "Phase-1 scenarios", value: "50" },
  { label: "Matched pairs", value: "25" },
  { label: "Scenario categories", value: "5" },
  { label: "Failure taxonomy", value: "12" },
  { label: "Control conditions", value: "3 → 6" },
  { label: "Models planned", value: "3" },
];

export function StatRow() {
  return (
    <div className="mt-12 grid grid-cols-2 gap-y-6 border-y border-border py-6 sm:grid-cols-3 md:grid-cols-6">
      {STATS.map((st) => (
        <div
          key={st.label}
          className="border-l border-border pl-4 first:border-l-0 first:pl-0 md:border-l md:first:border-l-0"
        >
          <p className="label">{st.label}</p>
          <p className="mt-1 font-mono text-[1.7rem] leading-none text-ink">
            {st.value}
          </p>
        </div>
      ))}
    </div>
  );
}
