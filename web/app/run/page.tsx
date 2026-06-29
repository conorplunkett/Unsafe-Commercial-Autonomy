import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Runner } from "@/components/Runner";

export const metadata: Metadata = {
  title: "Run it yourself",
  description:
    "Run a PayBench scenario against any OpenAI or Anthropic model with your own API key. Each run is scored by the same harness as the published results.",
};

export default function RunPage() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <header className="scroll-mt-20 pt-14 sm:pt-20">
          <p className="label">Run it yourself · bring your own key</p>
          <h1 className="mt-4 font-serif text-5xl leading-[1.0] tracking-tight sm:text-6xl">
            Run the benchmark
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink/85">
            Drop any OpenAI or Anthropic model into a real PayBench scenario with
            your own API key, and watch how it handles delegated payment
            authority. Each run is scored by the same harness behind the
            published results — so you see exactly what the leaderboard measures.
          </p>
        </header>
        <Runner />
      </main>
      <Footer />
    </div>
  );
}
