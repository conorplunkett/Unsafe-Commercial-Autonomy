import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { ScenarioBrowser } from "@/components/ScenarioBrowser";

const DATASET_DESCRIPTION =
  "Browse the locked Phase-1 PayBench dataset: 50 trap-and-lookalike commercial scenarios across five categories of delegated-payment failure.";

export const metadata: Metadata = {
  title: "Dataset",
  description: DATASET_DESCRIPTION,
  alternates: { canonical: "/scenarios" },
  openGraph: {
    title: "PayBench Dataset: 50 commercial scenarios",
    description: DATASET_DESCRIPTION,
    url: "/scenarios",
    siteName: "PayBench",
    type: "website",
    // Defining openGraph here replaces the file-based opengraph-image that
    // would otherwise be inherited, so reference the shared card explicitly.
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        type: "image/png",
        alt: "PayBench: A Benchmark for Unsafe Commercial Autonomy in AI Agents with Delegated Payment Authority",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "PayBench Dataset: 50 commercial scenarios",
    description: DATASET_DESCRIPTION,
    images: ["/opengraph-image"],
  },
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
            Fifty hand-built commercial scenarios: twenty-five matched
            trap-and-lookalike pairs, ten per category, with a survey-locked
            answer key. Traps are unsafe to act on; lookalikes should simply
            proceed. Filter below; the full set and the expanded 226-scenario
            version live in the repository.
          </p>
        </header>
        <ScenarioBrowser />
      </main>
      <Footer />
    </div>
  );
}
