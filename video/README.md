# Launch video

Standalone Remotion project for the PayBench launch video. Its dependencies are
kept separate from the public website.

## Develop

```bash
cd video
npm install
npm run dev
```

Remotion Studio opens at `http://localhost:3000`.

## Render

```bash
npm run render         # out/launch-video.mp4
npm run render:still   # out/poster.png
```

The video is 1920×1080 at 30 fps and approximately 28 seconds. Rendered output
under `out/` is gitignored. Scene copy and timing live in
`src/scenes.tsx` and `src/LaunchVideo.tsx`.
