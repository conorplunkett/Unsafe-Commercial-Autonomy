import React from "react";
import { Composition } from "remotion";
import { LaunchVideo, LAUNCH_VIDEO_DURATION } from "./LaunchVideo";
import { FPS } from "./theme";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="LaunchVideo"
      component={LaunchVideo}
      durationInFrames={LAUNCH_VIDEO_DURATION}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
};
