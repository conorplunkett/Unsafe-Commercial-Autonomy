import type { ReactNode } from "react";

// A SectionDivider that collapses its body. Same title/intro styling, but the
// whole header is a <summary>, so the section is closed by default and pops
// open on click. Pure HTML details/summary; no client JS.
export function ToggleSection({
  id,
  title,
  intro,
  children,
}: {
  id?: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}) {
  return (
    <details
      id={id}
      className="group mt-20 scroll-mt-20 border-t border-border pt-8"
    >
      <summary className="cursor-pointer list-none marker:content-none [&::-webkit-details-marker]:hidden">
        <h2 className="flex items-baseline gap-3 text-h2 tracking-tight">
          <span
            aria-hidden
            className="inline-block text-h3 text-accent transition-transform duration-150 group-open:rotate-90"
          >
            ▸
          </span>
          {title}
        </h2>
      </summary>
      {/* Everything below the heading, intro included, is hidden until opened. */}
      {intro && (
        <p className="mt-3 max-w-2xl pl-7 font-serif text-prose leading-relaxed text-ink/80">
          {intro}
        </p>
      )}
      <div className="pl-7">{children}</div>
    </details>
  );
}
