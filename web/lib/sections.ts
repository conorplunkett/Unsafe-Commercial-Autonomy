import { RESULTS_LIVE } from "./config";

// Single source of truth for the page's sections, in visual order. Drives the
// table of contents under the hero (every entry) and the top nav + scrollspy
// (entries with a `short` label). Keep ids in sync with the `id` props on the
// SectionDivider / ToggleSection components in app/page.tsx.
export interface SectionLink {
  id: string;
  label: string;
  // Compact nav label; omitted = ToC only.
  short?: string;
}

// "Summary" is intentionally omitted: the PayBench logo links to the top of
// the page, which is the summary. The Results and Leaderboard anchors only
// exist once results are live (see components/results/README.md).
export const TOC: SectionLink[] = [
  { id: "abstract", label: "Abstract", short: "Abstract" },
  { id: "why", label: "Why this matters" },
  { id: "related", label: "Related work" },
  { id: "benchmark", label: "Experiment design", short: "Design" },
  { id: "coverage", label: "Experiment coverage" },
  { id: "taxonomy", label: "Taxonomy" },
  { id: "controls", label: "The control ladder" },
  { id: "method", label: "How it is scored", short: "Method" },
  ...(RESULTS_LIVE
    ? [
        { id: "results", label: "Findings", short: "Results" },
        { id: "axes", label: "Survey-grounded axes" },
        { id: "leaderboard", label: "Leaderboard", short: "Leaderboard" },
        // ToC only: a seventh nav link overflows the nav row at tablet widths.
        { id: "episodes", label: "Every episode" },
      ]
    : []),
  { id: "scenarios", label: "Example scenarios" },
  { id: "roadmap", label: "Three experiment phases", short: "Roadmap" },
  { id: "limitations", label: "Limitations" },
  { id: "cite", label: "Cite PayBench", short: "Cite" },
  { id: "authors", label: "Authors" },
];

export const SECTIONS: SectionLink[] = TOC.filter((s) => s.short);
