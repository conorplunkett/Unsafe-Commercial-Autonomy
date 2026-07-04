import { ToggleSection } from "./ToggleSection";

export function Limitations() {
  return (
    <ToggleSection id="limitations" eyebrow="Caveats" title="Limitations">
      {/* Once results are live: reword from proposal tense to reported-results tense. */}
      <div className="mt-6 max-w-3xl space-y-5 text-lg leading-relaxed text-ink/85">
        <p>
          No results are published yet; this page describes a proposal. Phase-1
          ground truth will come from the project team plus a ten-person
          validation survey, not a powered study, and with five seeds per
          scenario the confidence intervals will be wide. The first findings
          should be read as preliminary.
        </p>
        <p>
          Results will be produced in a simulated environment. Whether simulated
          failure rates transfer to real payment infrastructure stays untested
          until the Phase 2 sandbox transfer check, and ultimately the limited
          real-money validation in Phase 3.
        </p>
        <p className="text-base text-muted">
          To keep the benchmark honest, only the locked Phase-1 set (50
          scenarios) is published here. The expanded 250-scenario set is
          provisional, and a private holdout is planned so future models cannot
          simply train on the questions.
        </p>
      </div>
    </ToggleSection>
  );
}
