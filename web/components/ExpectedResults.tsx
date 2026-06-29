// Shown in place of live findings while no benchmark run has been published.
// Content mirrors the proposal's hypotheses (Notion §3) and expected results
// (§7). Everything here is a prediction, not a measurement.

const HYPOTHESES = [
  "Choosing a purchase that technically satisfies the instruction while violating the user's implied preference.",
  "Overspending through shipping, taxes, service fees, subscriptions, or add-ons.",
  "Failing to ask for approval when ambiguity is high.",
  "Leaking unnecessary personal or payment context to merchants or tools.",
  "Taking irreversible actions when a reversible draft, hold, or approval flow would be safer.",
  "Optimising for task completion over user welfare.",
];

const EXPECTATIONS: { layer: string; expect: string }[] = [
  {
    layer: "Prompt-only policy",
    expect: "Expected to fail often — a stated rule in the prompt is weak protection under pressure.",
  },
  {
    layer: "Structured policy / preflight",
    expect: "Expected to sit between prompting and hard constraints.",
  },
  {
    layer: "Tool-level hard constraints",
    expect: "Should cut direct overspend, but miss harder-to-detect failures (wrong item, non-refundable option, data leakage, split payments).",
  },
  {
    layer: "Human approval gate",
    expect: "Should cut severe failures while raising the false-stop rate — exactly why the frontier framing matters.",
  },
];

export function ExpectedResults() {
  return (
    <div className="mt-6 grid gap-12 lg:grid-cols-2">
      <div>
        <p className="label mb-3">Hypotheses — the failures we expect</p>
        <p className="mb-4 text-base leading-relaxed text-ink/85">
          We expect current agents to often satisfy the surface-level task while
          violating at least one deeper commercial constraint. The most likely
          failures:
        </p>
        <ul className="space-y-2.5">
          {HYPOTHESES.map((h) => (
            <li key={h} className="flex gap-3 text-[0.98rem] leading-snug text-ink/85">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-danger" />
              {h}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p className="label mb-3">Expected effect of each control layer</p>
        <div className="space-y-3">
          {EXPECTATIONS.map((e) => (
            <div key={e.layer} className="rounded-xl border border-border bg-paper-2/40 p-4">
              <p className="font-serif text-lg leading-snug">{e.layer}</p>
              <p className="mt-1 text-sm leading-snug text-muted">{e.expect}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm leading-snug text-muted">
          The best setup is expected to combine structured payment policy, hard
          tool constraints, merchant/category validation, approval thresholds,
          and audit logs. These are predictions — the live charts below populate
          only once a real run is published.
        </p>
      </div>
    </div>
  );
}
