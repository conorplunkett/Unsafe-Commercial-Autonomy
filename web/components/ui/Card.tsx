import type { ElementType, ReactNode } from "react";

// The panel shell used across the site: a rounded, bordered box with an
// optional tint. Before this existed there were fifteen hand-written variants
// whose fill opacity and padding had drifted apart; keep new panels going
// through here so restyling stays a one-file change. See DESIGN.md.

const TONES = {
  // Default: the tinted panel that carries most content sections.
  tint: "border-border bg-paper-2/40",
  // Sits on top of a tinted parent, or needs to read as the front-most layer.
  raised: "border-border bg-paper",
  // Outline only — for panels wrapping their own striped rows or a table.
  bare: "border-border",
  accent: "border-accent/30 bg-accent/[0.05]",
  // Louder than `danger` — for an error the user has to act on, not a labelled panel.
  alert: "border-danger/40 bg-danger/10",
  danger: "border-danger/30 bg-danger/[0.04]",
} as const;

const PADS = {
  none: "", // wrapping a table, list, or anything that owns its own padding
  sm: "p-4",
  md: "p-5",
} as const;

export function Card({
  as: Tag = "div",
  tone = "tint",
  pad = "md",
  className = "",
  children,
  ...rest
}: {
  as?: ElementType;
  tone?: keyof typeof TONES;
  pad?: keyof typeof PADS;
  className?: string;
  children?: ReactNode;
} & Record<string, unknown>) {
  return (
    <Tag
      className={`rounded-xl border ${TONES[tone]} ${PADS[pad]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </Tag>
  );
}
