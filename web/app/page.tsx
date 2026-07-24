import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { TableOfContents } from "@/components/TableOfContents";
import { Abstract } from "@/components/Abstract";
import { WhyThisMatters } from "@/components/WhyThisMatters";
import { RelatedWork } from "@/components/RelatedWork";
import { Design } from "@/components/Design";
import { Categories } from "@/components/Categories";
import { SectionDivider } from "@/components/SectionDivider";
import { ToggleSection } from "@/components/ToggleSection";
import { TaxonomyGrid } from "@/components/TaxonomyGrid";
import { Conditions } from "@/components/Conditions";
import { Method } from "@/components/Method";
import { ScenarioBrowser } from "@/components/ScenarioBrowser";
import { Roadmap } from "@/components/Roadmap";
import { Limitations } from "@/components/Limitations";
import { Citation } from "@/components/Citation";
import { Authors } from "@/components/Authors";
import { Footer } from "@/components/Footer";
import { RESULTS_LIVE } from "@/lib/config";
// Once results are live (RESULTS_LIVE in lib/config.ts — see
// components/results/README.md), these render again:
import { StatRow } from "@/components/results/StatRow";
import { Donut } from "@/components/results/Donut";
import { Findings } from "@/components/results/Findings";
import { Leaderboard } from "@/components/results/Leaderboard";

export default function Home() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <Hero />
        {/* Once results are live: the StatRow of measured rates returns here. */}
        {RESULTS_LIVE && <StatRow />}
        <TableOfContents />

        <Abstract />
        <WhyThisMatters />
        <RelatedWork />
        <Design />
        <Categories />

        <SectionDivider id="taxonomy" title="Taxonomy">
          {
            "When an agent makes a bad call with someone else's money, we need a shared language for what went wrong."
          }
        </SectionDivider>
        <TaxonomyGrid />

        <Conditions />

        <ToggleSection
          id="method"
          eyebrow="Method"
          title="How it is scored"
          intro="Each setup is summarised by a confusion matrix over matched trap-and-lookalike pairs."
        >
          <Method />
        </ToggleSection>

        {/* Once results are live: the Results and Leaderboard sections return here. */}
        {RESULTS_LIVE && (
          <>
            <SectionDivider id="results" eyebrow="Results" title="Findings">
              {
                "Read live from the published benchmark runs. These are early Phase-1 results with few seeds and a small validation survey, so confidence intervals are wide; treat them as preliminary, not definitive. Switch runs to compare phases."
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
        )}

        <ToggleSection
          id="scenarios"
          eyebrow="Dataset"
          title="Example scenarios"
          intro="A sample of the locked Phase-1 set: one trap from each category. Browse the full 50, filterable by category and pair type."
        >
          <ScenarioBrowser teaser />
        </ToggleSection>

        <Roadmap />
        <Limitations />
        <Citation />
        <Authors />
      </main>
      <Footer />
    </div>
  );
}
