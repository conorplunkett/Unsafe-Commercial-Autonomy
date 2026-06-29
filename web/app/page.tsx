import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { StatRow } from "@/components/StatRow";
import { Abstract } from "@/components/Abstract";
import { WhyThisMatters } from "@/components/WhyThisMatters";
import { RelatedWork } from "@/components/RelatedWork";
import { Design } from "@/components/Design";
import { Categories } from "@/components/Categories";
import { SectionDivider } from "@/components/SectionDivider";
import { TaxonomyGrid } from "@/components/TaxonomyGrid";
import { Conditions } from "@/components/Conditions";
import { Method } from "@/components/Method";
import { ResultsSection } from "@/components/ResultsSection";
import { ScenarioBrowser } from "@/components/ScenarioBrowser";
import { Roadmap } from "@/components/Roadmap";
import { Limitations } from "@/components/Limitations";
import { Citation } from "@/components/Citation";
import { Authors } from "@/components/Authors";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <Hero />
        <StatRow />

        <Abstract />
        <WhyThisMatters />
        <RelatedWork />
        <Design />
        <Categories />

        <SectionDivider eyebrow="Taxonomy" title="What the benchmark measures">
          {
            "Twelve ways an agent holding delegated payment authority can fail a commercial task while still completing it."
          }
        </SectionDivider>
        <TaxonomyGrid />

        <Conditions />

        <SectionDivider id="method" eyebrow="Method" title="How it is scored">
          {
            "Each setup is summarised by a confusion matrix over matched trap-and-lookalike pairs."
          }
        </SectionDivider>
        <Method />

        <ResultsSection />

        <SectionDivider
          id="scenarios"
          eyebrow="Dataset"
          title="Example scenarios"
        >
          {
            "A sample of the draft Phase-1 set — one trap from each category. Browse the full 50, filterable by category and pair type."
          }
        </SectionDivider>
        <ScenarioBrowser teaser />

        <Roadmap />
        <Limitations />
        <Citation />
        <Authors />
      </main>
      <Footer />
    </div>
  );
}
