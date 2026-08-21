import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { AgentWalkthrough } from "@/components/howitworks/AgentWalkthrough";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "Step through one real PayBench episode as the agent: the prompt, the tool calls, and the moment a payment policy either holds or doesn't.",
};

export default function HowItWorksPage() {
  return (
    <div className="min-h-full">
      <Nav />
      <main className="mx-auto w-full max-w-5xl overflow-x-clip px-4 pb-16 sm:px-8">
        <header className="scroll-mt-20 pt-14 sm:pt-20">
          <h1 className="text-h1 tracking-tight">
            Imagine you are an agent with access to your human&rsquo;s credit
            card.
          </h1>
        </header>
        <AgentWalkthrough />
      </main>
      <Footer />
    </div>
  );
}
