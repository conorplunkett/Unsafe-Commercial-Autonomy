import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Runner } from "@/components/Runner";
import { CONFIG } from "@/lib/config";

export const metadata: Metadata = {
  title: "Run it yourself",
  description:
    "Run a PayBench scenario against an OpenAI, Anthropic, Gemini, Kimi, or Inkling model with your own API key. Each run is scored by the same harness as the published results.",
};

export default function RunPage() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <header className="scroll-mt-20 pt-14 sm:pt-20">
          <p className="label">Run it yourself</p>
          <h1 className="mt-4 font-serif text-5xl leading-[1.0] tracking-tight sm:text-6xl">
            Run the benchmark
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink/85">
            Drop an OpenAI, Anthropic, Gemini, Kimi, or Inkling model into a
            real PayBench scenario with your own API key.
          </p>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted">
            Prefer to run the full benchmark locally?{" "}
            <a
              href={CONFIG.repoUrl}
              target="_blank"
              rel="noreferrer"
              className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
            >
              Clone it from GitHub
            </a>
            .
          </p>
        </header>
        <Runner />
      </main>
      <Footer />
    </div>
  );
}
