import type { ReactNode } from "react";

// Inline defined term: dotted underline, definition pops up on hover or
// keyboard focus. CSS-only, so it works inside server components.
//
// The popup is hidden with opacity, not display, so it still takes part in
// layout — a fixed width here can widen the whole page when the term happens
// to sit near the right edge. Hence the viewport cap, plus `overflow-x-clip`
// on <main> as the backstop for any absolutely-positioned decoration.
export function Term({ children, def }: { children: ReactNode; def: string }) {
  return (
    <span
      tabIndex={0}
      className="group/term relative cursor-help underline decoration-accent/60 decoration-dotted underline-offset-4 focus:outline-none"
    >
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-72 max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-lg border border-border bg-paper px-3.5 py-2.5 text-small font-normal leading-snug text-ink no-underline opacity-0 shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-opacity duration-150 group-focus/term:opacity-100 group-hover/term:opacity-100"
      >
        {def}
      </span>
    </span>
  );
}
