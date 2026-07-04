import type { ReactNode } from "react";

// A SectionDivider that collapses its body. Same eyebrow/title/intro styling,
// but the whole header is a <summary>, so the section is closed by default and
// pops open on click. Pure HTML details/summary; no client JS.
export function ToggleSection({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id?: string;
  eyebrow?: string;
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
        {eyebrow && <p className="label">{eyebrow}</p>}
        <h2 className="mt-2 flex items-baseline gap-3 font-serif text-3xl tracking-tight sm:text-4xl">
          <span
            aria-hidden
            className="inline-block text-2xl text-accent transition-transform duration-150 group-open:rotate-90"
          >
            ▸
          </span>
          {title}
        </h2>
        {intro && (
          <p className="mt-3 max-w-2xl pl-7 text-lg leading-relaxed text-ink/80">
            {intro}
          </p>
        )}
      </summary>
      <div className="pl-7">{children}</div>
    </details>
  );
}
