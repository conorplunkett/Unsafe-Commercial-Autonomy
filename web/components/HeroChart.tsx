import { CONDITION_SHORT } from "@/lib/labels";
import { ILLUSTRATIVE_FRONTIER } from "@/lib/illustrative";
import { pct } from "@/lib/format";

const W = 760;
const H = 340;
const P = { top: 36, right: 120, bottom: 54, left: 44 };
const innerW = W - P.left - P.right;
const innerH = H - P.top - P.bottom;
const GRID = [0, 0.25, 0.5, 0.75, 1];

// Static figure driven by an explicitly *illustrative* frontier (see
// lib/illustrative.ts). It sketches the hypothesised shape only; the real,
// data-driven charts live further down the page and render once a run is
// published. Nothing here is a measured result.
export function HeroChart() {
  const pts = ILLUSTRATIVE_FRONTIER;

  const x = (i: number) =>
    P.left + (pts.length <= 1 ? innerW / 2 : (innerW * i) / (pts.length - 1));
  const y = (v: number) => P.top + innerH * (1 - v);

  function path(key: "unsafe" | "falseRefusal") {
    let d = "";
    pts.forEach((p, i) => {
      d += `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p[key]).toFixed(1)} `;
    });
    return d.trim();
  }

  const unsafeArea = (() => {
    const top = pts
      .map((p, i) => `L ${x(i).toFixed(1)} ${y(p.unsafe).toFixed(1)} `)
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
      aria-label="Illustrative, hypothesised unsafe-payment and false-refusal rates by control condition — not measured data"
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

      {/* illustrative watermark */}
      <text
        x={P.left + 6}
        y={P.top + 14}
        className="fill-muted font-mono"
        fontSize={10}
        letterSpacing="1.5"
      >
        ILLUSTRATIVE · HYPOTHESISED · NOT MEASURED
      </text>

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
          <circle cx={x(i)} cy={y(p.unsafe)} r={3.5} fill="var(--color-danger)" />
          <circle cx={x(i)} cy={y(p.falseRefusal)} r={3.5} fill="var(--color-warn)" />
        </g>
      ))}

      {/* right-edge end labels */}
      <text
        x={x(pts.length - 1) + 12}
        y={y(last.unsafe) + 4}
        className="fill-danger font-mono"
        fontSize={12}
      >
        ~{pct(last.unsafe)} unsafe
      </text>
      <text
        x={x(pts.length - 1) + 12}
        y={y(last.falseRefusal) + 4}
        className="fill-warn font-mono"
        fontSize={12}
      >
        ~{pct(last.falseRefusal)} refusal
      </text>
    </svg>
  );
}
