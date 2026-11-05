import type { NextConfig } from "next";

/**
 * Locally, the web dev server forwards the API routes to the API process so the
 * browser sees a single origin (the session cookie needs it). Online, the
 * platform routes them and `API_URL` is not set, so no rewrite exists.
 */
export function apiRewrites(apiUrl: string | undefined) {
  if (!apiUrl) {
    return [];
  }
  const base = apiUrl.replace(/\/+$/, "");
  return [
    { source: "/api/:path*", destination: `${base}/api/:path*` },
    { source: "/__test__/:path*", destination: `${base}/__test__/:path*` },
  ];
}

const nextConfig: NextConfig = {
  async rewrites() {
    return apiRewrites(process.env.API_URL);
  },
};

export default nextConfig;
