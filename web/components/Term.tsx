import type { ReactNode } from "react";

// Inline defined term: dotted underline, definition pops up on hover or
// keyboard focus. CSS-only, so it works inside server components.
export function Term({
  children,
  def,
}: {
  children: ReactNode;
  def: string;
}) {
  return (
    <span
      tabIndex={0}
      className="group/term relative cursor-help underline decoration-accent/60 decoration-dotted underline-offset-4 focus:outline-none"
    >
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-72 -translate-x-1/2 rounded-md border border-border bg-paper px-3.5 py-2.5 text-sm font-normal leading-snug text-ink no-underline opacity-0 shadow-md transition-opacity duration-150 group-focus/term:opacity-100 group-hover/term:opacity-100"
      >
        {def}
      </span>
    </span>
  );
}
