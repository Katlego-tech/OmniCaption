import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export: the frontend deploys to any CDN, fully decoupled from the
  // FastAPI backend (docs/18-frontend-architecture.md). The API base URL is
  // injected at build time via NEXT_PUBLIC_API_URL and overridable at runtime
  // from the Accounts page.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
