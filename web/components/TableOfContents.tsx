import { TOC } from "@/lib/sections";

// Numbered anchor list under the hero so readers can jump straight to a
// section. Entries come from lib/sections.ts, the same list the nav uses.
export function TableOfContents() {
  return (
    <nav
      aria-label="Table of contents"
      className="mt-12 border-y border-border py-6"
    >
      <p className="label">Contents</p>
      <ol className="mt-4 grid gap-x-10 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
        {TOC.map((s, i) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className="tap group flex items-baseline gap-3 py-0.5"
            >
              <span className="font-mono text-caption text-muted">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="font-serif text-ui leading-snug transition-colors group-hover:text-accent">
                {s.label}
              </span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
