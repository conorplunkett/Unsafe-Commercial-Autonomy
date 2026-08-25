import { ToggleSection } from "./ToggleSection";

export function Limitations() {
  return (
    <ToggleSection id="limitations" title="Caveats">
      <div className="mt-6 max-w-3xl space-y-5 font-serif text-prose leading-relaxed text-ink/85">
        <p>
          Ground truth comes from validation surveys — 31 respondents in Phase
          1, a first batch of 52 in Phase 2 — not powered studies, and seed
          counts per scenario are still small, so confidence intervals are
          wide. Read these first findings as preliminary.
        </p>
        <p>
          Results are produced in a simulated environment. Whether simulated
          failure rates transfer to real payment infrastructure stays untested
          until the limited real-money validation in Phase 3.
        </p>
        <p className="text-ui text-muted">
          To keep the benchmark honest, only the locked Phase-1 set (50
          scenarios) is published here; the 226-scenario Phase-2 set stays
          unpublished, with a private holdout planned so future models cannot
          simply train on the questions.
        </p>
      </div>
    </ToggleSection>
  );
}
