import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { ScenarioBrowser } from "@/components/ScenarioBrowser";

export const metadata: Metadata = {
  title: "Dataset",
  description:
    "Browse the locked Phase-1 PayBench dataset: 50 trap-and-lookalike commercial scenarios across five categories of delegated-payment failure.",
};

export default function ScenariosPage() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-16 sm:px-8">
        <header className="scroll-mt-20 pt-14 sm:pt-20">
          <p className="label">Phase-1 dataset · 50 scenarios</p>
          <h1 className="mt-4 font-serif text-4xl tracking-tight sm:text-5xl">
            The scenario set
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink/85">
            Fifty hand-built commercial scenarios — twenty-five matched
            trap-and-lookalike pairs, ten per category, with a survey-locked
            answer key. Traps are unsafe to act on; lookalikes should simply
            proceed. Filter below; the full set and the expanded 250-scenario
            version live in the repository.
          </p>
        </header>
        <ScenarioBrowser />
      </main>
      <Footer />
    </div>
  );
}
