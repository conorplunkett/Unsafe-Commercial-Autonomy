"use client";

import { useData } from "./DataProvider";
import { confusion } from "@/lib/metrics";
import { num } from "@/lib/format";

const SIZE = 230;
const C = SIZE / 2;
const R_OUTER = 100;
const R_INNER = 64;

const SEGMENTS = [
  { key: "correctlyProceeded", label: "Correctly proceeded", color: "var(--color-accent)" },
  { key: "correctlyStopped", label: "Correctly stopped", color: "var(--color-block)" },
  { key: "wronglyProceeded", label: "Wrongly proceeded", color: "var(--color-danger)" },
  { key: "wronglyStopped", label: "Wrongly stopped", color: "var(--color-warn)" },
] as const;

function polar(r: number, a: number): [number, number] {
  return [C + r * Math.cos(a), C + r * Math.sin(a)];
}

function arc(a0: number, a1: number): string {
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const [x0, y0] = polar(R_OUTER, a0);
  const [x1, y1] = polar(R_OUTER, a1);
  const [x2, y2] = polar(R_INNER, a1);
  const [x3, y3] = polar(R_INNER, a0);
  return `M ${x0} ${y0} A ${R_OUTER} ${R_OUTER} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${R_INNER} ${R_INNER} 0 ${large} 0 ${x3} ${y3} Z`;
}

export function Donut() {
  const { results } = useData();
  const c = confusion(results);
  const total =
    c.correctlyProceeded + c.correctlyStopped + c.wronglyProceeded + c.wronglyStopped;

  type Arc = (typeof SEGMENTS)[number] & {
    value: number;
    frac: number;
    a0: number;
    a1: number;
  };
  const arcs = SEGMENTS.reduce<Arc[]>((acc, seg) => {
    const value = c[seg.key];
    const frac = total ? value / total : 0;
    const a0 = acc.length ? acc[acc.length - 1].a1 : -Math.PI / 2;
    const a1 = a0 + frac * Math.PI * 2;
    return [...acc, { ...seg, value, frac, a0, a1 }];
  }, []);

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-10">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE} height={SIZE} className="shrink-0">
        {total === 0 ? (
          <circle
            cx={C}
            cy={C}
            r={(R_OUTER + R_INNER) / 2}
            fill="none"
            stroke="var(--color-border)"
            strokeWidth={R_OUTER - R_INNER}
          />
        ) : (
          arcs.map((a) =>
            a.frac > 0 ? (
              <path key={a.key} d={arc(a.a0, a.a1)} fill={a.color} stroke="var(--color-paper)" strokeWidth={1.5} />
            ) : null,
          )
        )}
        <text x={C} y={C - 4} textAnchor="middle" className="fill-muted font-mono" fontSize={11} letterSpacing="1">
          OUTCOMES
        </text>
        <text x={C} y={C + 18} textAnchor="middle" className="fill-ink font-mono" fontSize={20}>
          {num(total)}
        </text>
      </svg>

      <ul className="w-full max-w-xs space-y-2.5">
        {arcs.map((a) => (
          <li key={a.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2.5">
              <span className="inline-block h-3 w-3 rounded-[3px]" style={{ background: a.color }} />
              <span className="text-[0.95rem]">{a.label}</span>
            </span>
            <span className="font-mono text-sm text-muted">
              {num(a.value)} · {total ? Math.round(a.frac * 100) : 0}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
