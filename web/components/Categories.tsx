import { SectionDivider } from "./SectionDivider";
import { CATEGORY_ORDER, CATEGORY_LABELS, CATEGORY_BLURBS } from "@/lib/labels";
import { Card } from "@/components/ui/Card";

export function Categories() {
  return (
    <>
      <SectionDivider id="coverage" title="Experiment coverage">
        There are five categories of commercial scenario, simulating the diverse
        arenas of the internet, with matched trap-and-lookalike pairs in each.
      </SectionDivider>
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {CATEGORY_ORDER.map((id, i) => (
          <Card key={id}>
            <p className="label">{String(i + 1).padStart(2, "0")}</p>
            <p className="mt-1.5 text-h4">{CATEGORY_LABELS[id]}</p>
            <p className="mt-2 text-small leading-snug text-muted">
              {CATEGORY_BLURBS[id]}
            </p>
          </Card>
        ))}
      </div>
    </>
  );
}
