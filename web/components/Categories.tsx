import { SectionDivider } from "./SectionDivider";
import { CATEGORY_ORDER, CATEGORY_LABELS, CATEGORY_BLURBS } from "@/lib/labels";

export function Categories() {
  return (
    <>
      <SectionDivider eyebrow="Coverage" title="Five categories">
        Scenarios are balanced across five families of commercial constraint,
        with matched trap-and-lookalike pairs in each.
      </SectionDivider>
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {CATEGORY_ORDER.map((id, i) => (
          <div
            key={id}
            className="rounded-xl border border-border bg-paper-2/40 p-5"
          >
            <p className="label">
              {String(i + 1).padStart(2, "0")}
            </p>
            <p className="mt-1.5 font-serif text-xl">{CATEGORY_LABELS[id]}</p>
            <p className="mt-2 text-sm leading-snug text-muted">
              {CATEGORY_BLURBS[id]}
            </p>
          </div>
        ))}
      </div>
    </>
  );
}
