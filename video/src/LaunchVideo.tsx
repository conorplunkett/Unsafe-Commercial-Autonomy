import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { theme } from "./theme";
import {
  BenchmarkScene,
  MetricsScene,
  OutroScene,
  ProblemScene,
  QuestionScene,
  ScenarioScene,
  TitleScene,
} from "./scenes";

// Ordered scene list with per-scene durations (in frames). Keep this in sync
// with LAUNCH_VIDEO_DURATION below, which the Root uses to size the composition.
const SCENES: { Component: React.FC; duration: number }[] = [
  { Component: TitleScene, duration: 90 },
  { Component: ProblemScene, duration: 130 },
  { Component: QuestionScene, duration: 90 },
  { Component: ScenarioScene, duration: 170 },
  { Component: BenchmarkScene, duration: 130 },
  { Component: MetricsScene, duration: 130 },
  { Component: OutroScene, duration: 110 },
];

export const LAUNCH_VIDEO_DURATION = SCENES.reduce(
  (sum, s) => sum + s.duration,
  0,
);

export const LaunchVideo: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: theme.paper }}>
      {SCENES.map(({ Component, duration }, i) => {
        const seq = (
          <Sequence key={i} from={from} durationInFrames={duration}>
            <Component />
          </Sequence>
        );
        from += duration;
        return seq;
      })}
    </AbsoluteFill>
  );
};
