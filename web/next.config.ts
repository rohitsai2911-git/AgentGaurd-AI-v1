import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root so Turbopack does not walk up to the home
  // directory (where an unrelated pnpm-lock.yaml lives).
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
