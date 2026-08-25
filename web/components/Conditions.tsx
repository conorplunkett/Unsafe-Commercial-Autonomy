import { ToggleSection } from "./ToggleSection";
import { Card } from "@/components/ui/Card";
import { CONDITION_LABELS, CONDITION_DESCRIPTIONS } from "@/lib/labels";

// The Phase 2 ladder. CONDITION_ORDER in lib/labels keeps the retired
// conditions for reading historical runs; this page shows only what runs now.
const PHASE2_CONDITIONS = [
  "no_policy",
  "structured_policy",
  "tool_constraints",
] as const;

export function Conditions() {
  return (
    <ToggleSection
      id="controls"
      title="Control layers"
      intro="The benchmark varies one control layer at a time, from no policy at all up to hard tool constraints, to see which actually moves the frontier. Every condition exposes the same tools; only the policy's form changes."
    >
      <Card
        as="ol"
        tone="bare"
        pad="none"
        className="mt-8 space-y-px overflow-hidden"
      >
        {PHASE2_CONDITIONS.map((id, i) => (
          <li
            key={id}
            className="flex items-baseline gap-4 bg-paper-2 px-5 py-4"
          >
            <span className="font-mono text-small text-accent">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <p className="text-prose">{CONDITION_LABELS[id]}</p>
              <p className="mt-0.5 text-small leading-snug text-muted">
                {CONDITION_DESCRIPTIONS[id]}
              </p>
            </div>
          </li>
        ))}
      </Card>
    </ToggleSection>
  );
}
