# Launch video

A [Remotion](https://www.remotion.dev/) motion-graphics launch video for the
**Unsafe Commercial Autonomy** benchmark.

This is a standalone project. It stays separate from the Next.js app in
[`../web`](../web) so the render toolchain does not enter the website's
dependency tree. It has its own `package.json` and `node_modules`.

## Setup and preview

```bash
cd video
npm install
npm run dev
```

Remotion Studio opens at [http://localhost:3000](http://localhost:3000).

## Render

```bash
npm run render         # out/launch-video.mp4
npm run render:still   # out/poster.png
```

The video is 1920×1080 at 30 fps and approximately 28 seconds. Rendered output
under `out/` is gitignored.

## Structure

| File | Purpose |
| --- | --- |
| `src/index.ts` | Remotion entry point. |
| `src/Root.tsx` | Registers the composition, dimensions, frame rate, and duration. |
| `src/LaunchVideo.tsx` | Defines scene order and timing. |
| `src/scenes.tsx` | Contains the seven scenes and their copy. |
| `src/components.tsx` | Shared animation primitives. |
| `src/theme.ts` | Video palette and fonts. |

Edit scene copy in `src/scenes.tsx`. Change per-scene durations in
`src/LaunchVideo.tsx`; the composition length is derived from their sum.
