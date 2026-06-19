import type { NextConfig } from "next";

// Static export so the site can be served from Vercel without a project-level
// "Root Directory = web" setting: the repo-root vercel.json builds this app and
// serves the generated `out/` directory. The site is fully static (client-side
// Supabase fetch + bundled data), so export loses nothing.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
