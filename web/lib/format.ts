export function pct(v: number | null | undefined, digits = 0): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

// Percentage that keeps its sign, for a value read against a baseline rather
// than against zero (refusal above or below the human ask floor). A rounded-away
// difference prints as a bare "0%" so it never implies a direction it has not
// measured.
export function signedPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const points = Math.round(v * 100);
  if (points === 0) return "0%";
  return `${points > 0 ? "+" : "−"}${Math.abs(points)}%`;
}

// Correlations get two decimals: r=0.41 and r=0.44 are different answers, and
// rounding to a whole percent would erase the difference.
export function corr(v: number | null | undefined): string {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(2);
}

export function num(v: number | null | undefined): string {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US").format(v);
}

export function compactDate(iso?: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(iso));
}

export function titleCase(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
