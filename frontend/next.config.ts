import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pin the build root to this app. Without it Next walks up past the repo and
  // can infer a workspace root from an unrelated lockfile outside the project.
  turbopack: { root: __dirname },
};

export default nextConfig;
