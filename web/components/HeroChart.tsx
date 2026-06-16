"use client";

import { useData } from "./DataProvider";
import { byCondition } from "@/lib/metrics";
import { CONDITION_SHORT } from "@/lib/labels";
import { pct } from "@/lib/format";

const W = 760;
const H = 340;
const P = { top: 36, right: 120, bottom: 54, left: 44 };
const innerW = W - P.left - P.right;
const innerH = H - P.top - P.bottom;
const GRID = [0, 0.25, 0.5, 0.75, 1];

export function HeroChart() {
  const { results } = useData();
  const pts = byCondition(results);

  const x = (i: number) =>
    P.left + (pts.length <= 1 ? innerW / 2 : (innerW * i) / (pts.length - 1));
  const y = (v: number) => P.top + innerH * (1 - v);

  function path(key: "unsafe" | "falseRefusal") {
    let d = "";
    let started = false;
    pts.forEach((p, i) => {
      const v = p[key];
      if (v == null) return;
      d += `${started ? "L" : "M"} ${x(i).toFixed(1)} ${y(v).toFixed(1)} `;
      started = true;
    });
    return d.trim();
  }

  const unsafeArea = (() => {
    if (!pts.length || pts[0].unsafe == null) return "";
    const top = pts
      .map((p, i) => (p.unsafe == null ? "" : `L ${x(i).toFixed(1)} ${y(p.unsafe).toFixed(1)} `))
      .join("")
      .replace("L", "M");
    return `${top} L ${x(pts.length - 1).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`;
  })();

  const last = pts[pts.length - 1];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      role="img"
      aria-label="Unsafe payment and false refusal rates by control condition"
    >
      {/* gridlines + y labels */}
      {GRID.map((g) => (
        <g key={g}>
          <line
            x1={P.left}
            x2={P.left + innerW}
            y1={y(g)}
            y2={y(g)}
            stroke="var(--color-border)"
            strokeWidth={1}
          />
          <text
            x={P.left - 10}
            y={y(g) + 3}
            textAnchor="end"
            className="fill-muted font-mono"
            fontSize={10}
          >
            {Math.round(g * 100)}
          </text>
        </g>
      ))}

      {pts.length === 0 ? (
        <text
          x={W / 2}
          y={H / 2}
          textAnchor="middle"
          className="fill-muted font-mono"
          fontSize={13}
        >
          Awaiting first published run
        </text>
      ) : (
        <>
          {/* x ticks */}
          {pts.map((p, i) => (
            <g key={p.condition}>
              <line
                x1={x(i)}
                x2={x(i)}
                y1={P.top}
                y2={P.top + innerH}
                stroke="var(--color-border)"
                strokeWidth={1}
                strokeDasharray="2 4"
              />
              <text
                x={x(i)}
                y={P.top + innerH + 22}
                textAnchor="middle"
                className="fill-ink font-mono"
                fontSize={11}
              >
                {CONDITION_SHORT[p.condition] ?? p.condition}
              </text>
            </g>
          ))}

          {/* unsafe area + lines */}
          <path d={unsafeArea} fill="var(--color-danger)" opacity={0.08} />
          <path
            d={path("unsafe")}
            fill="none"
            stroke="var(--color-danger)"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <path
            d={path("falseRefusal")}
            fill="none"
            stroke="var(--color-warn)"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* points */}
          {pts.map((p, i) => (
            <g key={`pt-${p.condition}`}>
              {p.unsafe != null && (
                <circle cx={x(i)} cy={y(p.unsafe)} r={3.5} fill="var(--color-danger)" />
              )}
              {p.falseRefusal != null && (
                <circle cx={x(i)} cy={y(p.falseRefusal)} r={3.5} fill="var(--color-warn)" />
              )}
            </g>
          ))}

          {/* black pill on the first (no-policy) unsafe point */}
          {pts[0]?.unsafe != null && (
            <g transform={`translate(${x(0) - 4}, ${y(pts[0].unsafe) - 34})`}>
              <rect width={86} height={24} rx={5} fill="var(--color-block)" />
              <text
                x={43}
                y={16}
                textAnchor="middle"
                className="fill-paper font-mono"
                fontSize={11}
                letterSpacing="0.5"
              >
                {CONDITION_SHORT[pts[0].condition] ?? "Start"}
              </text>
            </g>
          )}

          {/* right-edge end labels */}
          {last?.unsafe != null && (
            <text
              x={x(pts.length - 1) + 12}
              y={y(last.unsafe) + 4}
              className="fill-danger font-mono"
              fontSize={12}
            >
              {pct(last.unsafe)} unsafe
            </text>
          )}
          {last?.falseRefusal != null && (
            <text
              x={x(pts.length - 1) + 12}
              y={y(last.falseRefusal) + 4}
              className="fill-warn font-mono"
              fontSize={12}
            >
              {pct(last.falseRefusal)} refusal
            </text>
          )}
        </>
      )}
    </svg>
  );
}
