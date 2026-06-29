// Single source of truth for the in-page anchors used by the top nav and the
// scrollspy. Order matches the visual order down the page. Keep ids in sync with
// the `id` props on Hero / SectionDivider in app/page.tsx.
export interface SectionLink {
  id: string;
  label: string;
}

export const SECTIONS: SectionLink[] = [
  { id: "summary", label: "Summary" },
  { id: "benchmark", label: "Benchmark" },
  { id: "method", label: "Method" },
  { id: "results", label: "Expected" },
  { id: "scenarios", label: "Scenarios" },
  { id: "cite", label: "Cite" },
];
