import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { StatRow } from "@/components/StatRow";
import { SectionDivider } from "@/components/SectionDivider";
import { Donut } from "@/components/Donut";
import { Findings } from "@/components/Findings";
import { TaxonomyGrid } from "@/components/TaxonomyGrid";
import { Method } from "@/components/Method";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <Hero />
        <StatRow />

        <SectionDivider id="findings" eyebrow="Results" title="Findings">
          {
            "Read live from the published benchmark runs. Each setup is summarised by a confusion matrix over matched trap-and-lookalike pairs."
          }
        </SectionDivider>
        <div className="mt-10">
          <Donut />
        </div>
        <Findings />

        <SectionDivider eyebrow="Taxonomy" title="What the benchmark measures">
          {
            "Twelve ways an agent holding delegated payment authority can fail a commercial task while still completing it."
          }
        </SectionDivider>
        <TaxonomyGrid />

        <SectionDivider id="method" eyebrow="Method" title="How it is scored" />
        <Method />
      </main>
      <Footer />
    </div>
  );
}
