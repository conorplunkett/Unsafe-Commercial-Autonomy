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
import { ExperimentChangelog } from "@/components/ExperimentChangelog";
import { Footer } from "@/components/Footer";
import { RESULTS_LIVE } from "@/lib/config";
// These sections render when RESULTS_LIVE is enabled in lib/config.ts.
import { Donut } from "@/components/results/Donut";
import { Findings } from "@/components/results/Findings";
import { SurveyAxes } from "@/components/results/SurveyAxes";
import { Leaderboard } from "@/components/results/Leaderboard";
import { EpisodeBrowser } from "@/components/results/EpisodeBrowser";

export default function Home() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl overflow-x-clip px-4 pb-10 sm:px-8">
        <Hero />
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
          title="Scoring method"
          intro="Each setup is summarised by a confusion matrix over matched trap-and-lookalike pairs."
        >
          <Method />
        </ToggleSection>

        {/* Once results are live: the Results and Leaderboard sections return here. */}
        {RESULTS_LIVE && (
          <>
            <SectionDivider id="results" title="Results" />
            <div className="mt-10">
              <Donut />
            </div>
            <Findings />
            <SurveyAxes />

            <SectionDivider id="leaderboard" title="Leaderboard" />
            <Leaderboard />

            <SectionDivider id="episodes" title="Experiment runs" />
            <EpisodeBrowser />
          </>
        )}

        <ToggleSection
          id="scenarios"
          title="Datasets"
          intro="A sample of the locked Phase-1 set: one trap from each category. Browse the full 50, filterable by category and pair type."
        >
          <ScenarioBrowser teaser />
        </ToggleSection>

        <Roadmap />
        <Limitations />
        <Citation />
        <Authors />
        <ExperimentChangelog />
      </main>
      <Footer />
    </div>
  );
}
