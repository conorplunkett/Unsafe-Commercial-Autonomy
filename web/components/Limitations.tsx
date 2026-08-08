import { ToggleSection } from "./ToggleSection";

export function Limitations() {
  return (
    <ToggleSection id="limitations" eyebrow="Caveats" title="Limitations">
      <div className="mt-6 max-w-3xl space-y-5 font-serif text-prose leading-relaxed text-ink/85">
        <p>
          Phase-1 ground truth comes from a 31-respondent validation survey, not
          a powered study, and published runs currently cover one seed per
          scenario, so confidence intervals are wide. Read these first findings
          as preliminary.
        </p>
        <p>
          Results are produced in a simulated environment. Whether simulated
          failure rates transfer to real payment infrastructure stays untested
          until the Phase 2 sandbox transfer check, and ultimately the limited
          real-money validation in Phase 3.
        </p>
        <p className="text-ui text-muted">
          To keep the benchmark honest, only the locked Phase-1 set (50
          scenarios) is published here. The expanded 250-scenario set is
          provisional, and a private holdout is planned so future models cannot
          simply train on the questions.
        </p>
      </div>
    </ToggleSection>
  );
}
