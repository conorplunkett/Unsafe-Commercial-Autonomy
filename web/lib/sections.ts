// Single source of truth for the in-page anchors used by the top nav and the
// scrollspy. Order matches the visual order down the page. Keep ids in sync with
// the `id` props on Hero / SectionDivider in app/page.tsx.
export interface SectionLink {
  id: string;
  label: string;
}

// "Summary" is intentionally omitted — the PayBench logo links to the top of the
// page, which is the summary. "Scenarios" is omitted too: the "Dataset" link in
// the nav covers the scenario set.
export const SECTIONS: SectionLink[] = [
  { id: "benchmark", label: "Benchmark" },
  { id: "results", label: "Results" },
  { id: "leaderboard", label: "Leaderboard" },
  { id: "cite", label: "Cite" },
];
