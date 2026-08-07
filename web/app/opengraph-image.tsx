import { ImageResponse } from "next/og";

// Required for `output: export` — generate this image once at build time.
export const dynamic = "force-static";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt =
  "PayBench: A Benchmark for Unsafe Commercial Autonomy in AI Agents with Delegated Payment Authority";

// Static-content OG card in the site's cream/serif palette. Flexbox only
// (satori does not support grid). No emoji/custom fonts to keep the build safe.
export default function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#ffffff",
        color: "#0b1c30",
        padding: "72px 80px",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          fontSize: 26,
          letterSpacing: 4,
          textTransform: "uppercase",
          color: "#556274",
        }}
      >
        A benchmark for AI agents spending human money
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", fontSize: 150, fontWeight: 600 }}>
          <span>Pay</span>
          <span style={{ color: "#1b5e55" }}>Bench</span>
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 40,
            fontStyle: "italic",
            color: "rgba(11,28,48,0.8)",
            marginTop: 8,
            maxWidth: 1000,
          }}
        >
          Unsafe commercial autonomy in AI agents with delegated payment
          authority
        </div>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 28,
          color: "#556274",
        }}
      >
        <span>Conor Plunkett · Independent researcher</span>
        <span>paybench.org</span>
      </div>
    </div>,
    { ...size },
  );
}
