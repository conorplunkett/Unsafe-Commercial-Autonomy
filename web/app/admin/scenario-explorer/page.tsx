import type { Metadata } from "next";
import { ScenarioExplorer } from "@/components/scenario-explorer/ScenarioExplorer";

export const metadata: Metadata = {
  title: "Scenario Explorer",
  robots: { index: false, follow: false },
};

export default function ScenarioExplorerPage() {
  return (
    <div className="min-h-full">
      <main className="mx-auto w-full max-w-5xl overflow-x-clip px-4 pb-16 sm:px-8">
        <header className="pt-14 sm:pt-20">
          <h1 className="text-h1 tracking-tight">Scenario Explorer</h1>
        </header>
        <ScenarioExplorer />
      </main>
    </div>
  );
}
