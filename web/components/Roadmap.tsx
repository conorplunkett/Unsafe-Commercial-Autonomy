import { ToggleSection } from "./ToggleSection";
import { Card } from "@/components/ui/Card";

const PHASES = [
  {
    tag: "Phase 1",
    status: "Complete",
    title: "Simulated benchmark · 50 scenarios",
    body: "Fully mocked payment tools, merchants, and checkout pages. The scenario set and the 31-respondent answer-key survey are locked, and the first runs are published: four models plus a naive always-cheapest baseline, across the no-policy / prompt-policy / tool-constraints conditions.",
  },
  {
    tag: "Phase 2",
    status: "In progress",
    title: "Offer-grounded sandbox · 226 scenarios",
    body: "113 trap/lookalike pairs with richer merchants and adversarial pressure. The agent searches offers, reads merchant pages, and pays through a real checkout loop; the scorer grades the offer it actually selected. Runs through the no-policy / structured-policy / tool-constraints ladder, keyed where needed by a 52-respondent preference survey.",
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
    <ToggleSection id="roadmap" title="Roadmap">
      <div className="mt-8 grid gap-6 md:grid-cols-3">
        {PHASES.map((p) => (
          <Card tone="bare" key={p.tag}>
            <div className="flex items-center justify-between">
              <p className="label">{p.tag}</p>
              <span
                className={`rounded-full px-2.5 py-0.5 font-mono text-caption uppercase tracking-wider ${
                  p.status === "Results live" || p.status === "In progress"
                    ? "bg-accent/15 text-accent"
                    : "bg-paper-2 text-muted"
                }`}
              >
                {p.status}
              </span>
            </div>
            <p className="mt-2 text-prose leading-snug">{p.title}</p>
            <p className="mt-2 text-small leading-snug text-muted">{p.body}</p>
          </Card>
        ))}
      </div>
    </ToggleSection>
  );
}
