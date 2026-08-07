import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Runner } from "@/components/Runner";
import { CONFIG } from "@/lib/config";

export const metadata: Metadata = {
  title: "Run it yourself",
  description:
    "Run a PayBench scenario against an OpenAI, Anthropic, Gemini, Kimi, Inkling, Grok, DeepSeek, Mistral, Qwen, or OpenRouter model with your own API key. Each run is scored by the same harness as the published results.",
};

export default function RunPage() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl px-5 pb-10 sm:px-8">
        <header className="scroll-mt-20 pt-14 sm:pt-20">
          <p className="label">Run it yourself</p>
          <h1 className="mt-4 font-serif text-h1 tracking-tight">
            Run the benchmark
          </h1>
          <p className="mt-4 max-w-2xl text-prose leading-relaxed text-ink/85">
            Drop a model from any major provider — OpenAI, Anthropic, Gemini,
            Kimi, Inkling, Grok, DeepSeek, Mistral, Qwen, or OpenRouter — into a
            real PayBench scenario with your own API key.
          </p>
          <p className="mt-3 max-w-2xl text-ui leading-relaxed text-muted">
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
