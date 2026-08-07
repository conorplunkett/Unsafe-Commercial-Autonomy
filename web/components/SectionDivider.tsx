import type { ReactNode } from "react";

export function SectionDivider({
  id,
  eyebrow,
  title,
  children,
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div id={id} className="mt-20 scroll-mt-20 border-t border-border pt-8">
      {eyebrow && <p className="label">{eyebrow}</p>}
      <h2 className="mt-2 text-h2 tracking-tight">{title}</h2>
      {children && (
        <p className="mt-3 max-w-2xl font-serif text-prose leading-relaxed text-ink/80">
          {children}
        </p>
      )}
    </div>
  );
}
