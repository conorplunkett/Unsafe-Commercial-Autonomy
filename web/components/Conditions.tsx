import { ToggleSection } from "./ToggleSection";
import { Term } from "./Term";
import {
  CONDITION_ORDER,
  CONDITION_LABELS,
  CONDITION_DESCRIPTIONS,
} from "@/lib/labels";

export function Conditions() {
  return (
    <ToggleSection
      id="controls"
      eyebrow="Control layers"
      title="The control ladder"
      intro={
        <>
          The benchmark varies one control layer at a time, from no policy at
          all up to a human approval gate, to see which actually moves the
          frontier. Phase 1 runs three of the rungs (no policy, prompt policy,
          and tool constraints); the full six-condition{" "}
          <Term def="An ablation removes or varies one component at a time while holding everything else fixed, to measure how much that component contributes to the result.">
            ablation
          </Term>{" "}
          below is Phase 2.
        </>
      }
    >
      <ol className="mt-8 space-y-px overflow-hidden rounded-xl border border-border">
        {CONDITION_ORDER.map((id, i) => (
          <li
            key={id}
            className="flex items-baseline gap-4 bg-paper-2/40 px-5 py-4"
          >
            <span className="font-mono text-sm text-accent">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <p className="font-serif text-lg">{CONDITION_LABELS[id]}</p>
              <p className="mt-0.5 text-sm leading-snug text-muted">
                {CONDITION_DESCRIPTIONS[id]}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </ToggleSection>
  );
}
