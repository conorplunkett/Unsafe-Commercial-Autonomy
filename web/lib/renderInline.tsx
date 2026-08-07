import type { ReactNode } from "react";

// Inline `code`, **bold**, and *em* within an already-plain-text markdown
// string. Order matters: code spans are pulled out first so their contents
// are never re-parsed as bold/em.
const INLINE = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;

export function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  INLINE.lastIndex = 0;
  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const [, code, bold, em] = match;
    if (code !== undefined) {
      nodes.push(
        <code
          key={key++}
          className="rounded bg-paper-2 px-1 py-0.5 font-mono text-[0.85em] text-ink/90"
        >
          {code}
        </code>,
      );
    } else if (bold !== undefined) {
      nodes.push(<strong key={key++}>{bold}</strong>);
    } else if (em !== undefined) {
      nodes.push(<em key={key++}>{em}</em>);
    }
    last = INLINE.lastIndex;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}
