import { SectionDivider } from "./SectionDivider";

export function Limitations() {
  return (
    <>
      <SectionDivider eyebrow="Caveats" title="Limitations" />
      <div className="mt-6 max-w-3xl space-y-5 text-lg leading-relaxed text-ink/85">
        <p>
          Phase 1 ground truth will come from the project team plus a ten-person
          survey, not a powered study. With five seeds per scenario, confidence
          intervals will be wide and the first findings should be treated as
          preliminary.
        </p>
        <p>
          Phase 1 runs in a simulated environment. Whether simulated failure
          rates transfer to real payment infrastructure is untested — and stays
          untested until the Phase 2 sandbox transfer check and, ultimately, the
          limited real-money validation in Phase 3.
        </p>
        <p className="text-base text-muted">
          To keep the benchmark honest, only the locked Phase-1 set (50
          scenarios) is published here. The expanded 250-scenario set is
          provisional, and a private holdout is planned so future models cannot
          simply train on the questions.
        </p>
      </div>
    </>
  );
}
