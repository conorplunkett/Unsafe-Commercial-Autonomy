// Palette lifted from the product site (static/styles.css) so the launch
// video reads as the same brand: warm "paper" background, ink text, teal
// accent, with danger / ok signal colors for the trap-vs-safe beats.
export const theme = {
  paper: "#f7f2e7",
  paperDeep: "#efe7d6",
  surface: "#fffdf8",
  surfaceStrong: "#f1ead9",
  ink: "#2a241c",
  muted: "#7d7163",
  border: "#e3d9c6",
  rule: "#ddd0b8",
  accent: "#146c5c",
  accentStrong: "#0d4f44",
  danger: "#b13a32",
  dangerBg: "#fbe8e5",
  warn: "#9a6817",
  warnBg: "#fff1d6",
  ok: "#237a4a",
  okBg: "#e4f4ea",
  info: "#2f5d9a",
  infoBg: "#e7eef9",
  serif:
    '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, "Times New Roman", serif',
  sans: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  mono: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
} as const;

// Video-wide timing constants.
export const FPS = 30;
