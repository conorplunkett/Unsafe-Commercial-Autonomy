import { SectionDivider } from "./SectionDivider";

const PHASES = [
  {
    tag: "Phase 1",
    status: "Proposed",
    title: "Simulated benchmark · 50 scenarios",
    body: "Fully mocked payment tools, merchants, and checkout pages. A locked answer key (10-person survey), three models, the no-policy / prompt-policy / tool-constraints conditions, five seeds per scenario with confidence intervals, and a naive always-cheapest baseline.",
  },
  {
    tag: "Phase 2",
    status: "Next",
    title: "Sandbox expansion · 250 scenarios",
    body: "Fifty scenarios per category with richer merchants and adversarial pressure, the full six-condition ablation with interaction effects, an evaluation-awareness test, a human baseline, and a transfer check against Phase 1.",
  },
  {
    tag: "Phase 3",
    status: "Planned",
    title: "Limited real-money validation",
    body: "Very small amounts on prepaid cards with strict caps and prior review, to test whether simulated failure rates predict real-world behaviour.",
  },
];

export function Roadmap() {
  return (
    <>
      <SectionDivider eyebrow="Roadmap" title="Three phases" />
      <div className="mt-8 grid gap-6 md:grid-cols-3">
        {PHASES.map((p) => (
          <div key={p.tag} className="rounded-xl border border-border p-5">
            <div className="flex items-center justify-between">
              <p className="label">{p.tag}</p>
              <span
                className={`rounded-full px-2.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider ${
                  p.status === "Proposed"
                    ? "bg-accent/15 text-accent"
                    : "bg-paper-2 text-muted"
                }`}
              >
                {p.status}
              </span>
            </div>
            <p className="mt-2 font-serif text-lg leading-snug">{p.title}</p>
            <p className="mt-2 text-sm leading-snug text-muted">{p.body}</p>
          </div>
        ))}
      </div>
    </>
  );
}
