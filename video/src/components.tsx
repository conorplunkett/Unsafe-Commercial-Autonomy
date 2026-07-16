import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "./theme";

// Fade + rise-in wrapper. `delay` staggers entrance (in frames).
export const FadeUp: React.FC<{
  delay?: number;
  distance?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ delay = 0, distance = 28, children, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, mass: 0.6 },
  });
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const translateY = interpolate(s, [0, 1], [distance, 0]);
  return (
    <div style={{ opacity, transform: `translateY(${translateY}px)`, ...style }}>
      {children}
    </div>
  );
};

// Small uppercase label ("kicker") used above headings.
export const Kicker: React.FC<{
  children: React.ReactNode;
  color?: string;
}> = ({ children, color = theme.accent }) => (
  <div
    style={{
      fontFamily: theme.sans,
      fontSize: 26,
      fontWeight: 600,
      letterSpacing: 4,
      textTransform: "uppercase",
      color,
    }}
  >
    {children}
  </div>
);

// A soft "paper card" surface matching the site's panels.
export const Card: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
  accent?: string;
}> = ({ children, style, accent }) => (
  <div
    style={{
      background: theme.surface,
      border: `1px solid ${theme.border}`,
      borderLeft: accent ? `6px solid ${accent}` : `1px solid ${theme.border}`,
      borderRadius: 16,
      boxShadow: "0 18px 40px rgba(42, 36, 28, 0.10)",
      padding: "34px 40px",
      ...style,
    }}
  >
    {children}
  </div>
);

// Full-frame paper background with a faint vignette.
export const Backdrop: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: `radial-gradient(circle at 50% 38%, ${theme.surface} 0%, ${theme.paper} 55%, ${theme.paperDeep} 100%)`,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: 120,
    }}
  >
    {children}
  </div>
);
