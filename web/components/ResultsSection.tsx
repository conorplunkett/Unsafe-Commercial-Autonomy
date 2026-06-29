"use client";

import { useData } from "./DataProvider";
import { SectionDivider } from "./SectionDivider";
import { ExpectedResults } from "./ExpectedResults";
import { Donut } from "./Donut";
import { Findings } from "./Findings";
import { Leaderboard } from "./Leaderboard";

// Single results region that stays honest. Until a *real* run is published to
// Supabase (isSample is true while the bundled illustrative sample is the only
// fallback), this shows the proposal's expected results and hypotheses. Once a
// genuine run lands, it swaps to the live, data-driven charts automatically.
export function ResultsSection() {
  const { isSample, run } = useData();
  const live = !isSample && !!run;

  if (!live) {
    return (
      <>
        <SectionDivider id="results" eyebrow="Expected results" title="What we expect to find">
          {
            "No benchmark run has been published yet. These are the proposal's predictions; the live charts populate automatically once a real run is uploaded."
          }
        </SectionDivider>
        <ExpectedResults />
      </>
    );
  }

  return (
    <>
      <SectionDivider id="results" eyebrow="Results" title="Live findings">
        {
          "Read live from the published benchmark runs. Switch runs to compare phases."
        }
      </SectionDivider>
      <div className="mt-10">
        <Donut />
      </div>
      <Findings />

      <SectionDivider
        id="leaderboard"
        eyebrow="Leaderboard"
        title="Models on the frontier"
      >
        {
          "Every model that appears in the selected run, ranked by the safety–autonomy frontier."
        }
      </SectionDivider>
      <Leaderboard />
    </>
  );
}
