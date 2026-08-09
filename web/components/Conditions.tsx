import { ToggleSection } from "./ToggleSection";
import { Card } from "@/components/ui/Card";
import {
  CONDITION_ORDER,
  CONDITION_LABELS,
  CONDITION_DESCRIPTIONS,
} from "@/lib/labels";

export function Conditions() {
  return (
    <ToggleSection
      id="controls"
      title="Control layers"
      intro={
        <>
          Phase 1 compares no policy, prompt policy, and tool constraints.
          Phase 2 adds structured-policy, preflight, and approval conditions.
          The six conditions are alternatives, not six controls stacked on one
          payment.
        </>
      }
    >
      <Card
        as="ol"
        tone="bare"
        pad="none"
        className="mt-8 space-y-px overflow-hidden"
      >
        {CONDITION_ORDER.map((id, i) => (
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
