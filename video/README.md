# Launch video

A [Remotion](https://www.remotion.dev/) motion-graphics launch video for the
**Unsafe Commercial Autonomy** benchmark.

This is a **standalone project**. It is intentionally kept separate from the
Next.js app in [`../web`](../web) so the video's heavy render toolchain
(bundler, headless-Chromium renderer) never lands in the product's dependency
tree. It has its own `package.json` and `node_modules`.

## Setup

```bash
cd video
npm install
```

## Preview (live editor)

```bash
npm run dev        # opens Remotion Studio at http://localhost:3000
```

## Render

```bash
npm run render         # → out/launch-video.mp4  (1920×1080, 30fps, ~28s)
npm run render:still   # → out/poster.png        (a poster frame)
```

Rendered output lands in `out/`, which is git-ignored.

## Structure

| File | Purpose |
| --- | --- |
| `src/index.ts` | Remotion entry point (`registerRoot`). |
| `src/Root.tsx` | Registers the `LaunchVideo` composition (size, fps, duration). |
| `src/LaunchVideo.tsx` | Sequences the scenes; single source of truth for scene order and durations. |
| `src/scenes.tsx` | The seven scene components (title → shift → question → trap scenario → benchmark scale → metric → outro). |
| `src/components.tsx` | Shared animation primitives (`FadeUp`, `Kicker`, `Card`, `Backdrop`). |
| `src/theme.ts` | Palette + fonts lifted from the product site (`static/styles.css`) so the video is on-brand. |

## Editing content

Copy in each scene lives in `src/scenes.tsx`. To retime the video, change the
per-scene `duration` values in `src/LaunchVideo.tsx` — the composition length
is derived from their sum, so nothing else needs updating.
