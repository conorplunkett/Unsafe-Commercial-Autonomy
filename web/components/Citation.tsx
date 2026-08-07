"use client";

import { useState } from "react";
import { SectionDivider } from "./SectionDivider";
import { CITATION } from "@/lib/config";
import { Card } from "@/components/ui/Card";

export function Citation() {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(CITATION);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — the text is selectable in the block */
    }
  }

  return (
    <>
      <SectionDivider id="cite" eyebrow="Citation" title="Cite PayBench" />
      <Card pad="none" className="mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <span className="label">BibTeX</span>
          <button
            onClick={copy}
            className="rounded-md border border-ink px-3 py-1 font-mono text-caption transition-colors hover:bg-ink hover:text-paper"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <pre className="overflow-x-auto p-4 font-mono text-caption leading-relaxed text-ink/90">
          {CITATION}
        </pre>
      </Card>
    </>
  );
}
