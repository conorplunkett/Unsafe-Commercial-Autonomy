import type { ReactNode } from "react";

export function SectionDivider({
  id,
  title,
  children,
  noBorder,
}: {
  id?: string;
  title: string;
  children?: ReactNode;
  // Skip the top rule + margin: for a section that immediately follows
  // another element already ending in its own border (e.g. the ToC).
  noBorder?: boolean;
}) {
  return (
    <div
      id={id}
      className={
        noBorder
          ? "scroll-mt-20 pt-8"
          : "mt-20 scroll-mt-20 border-t border-border pt-8"
      }
    >
      <h2 className="text-h2 tracking-tight">{title}</h2>
      {children && (
        <p className="mt-3 max-w-2xl font-serif text-prose leading-relaxed text-ink/80">
          {children}
        </p>
      )}
    </div>
  );
}
