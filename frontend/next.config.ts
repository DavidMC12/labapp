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

/**
 * The `source` pattern of every web app header. Next.js compiles the regex
 * group after the first `/`: the negative lookahead refuses any path whose
 * first segment is `api` or `__test__`. Those paths belong to the API (the
 * API service answers them online and the local rewrite forwards them), and
 * the Swagger page that `/api/docs` serves loads its assets from a CDN, so
 * the web app's Content-Security-Policy must not be sent there.
 */
export const APP_HEADERS_SOURCE = "/((?!api|__test__).*)";

/**
 * The headers every page of the web app carries, whatever the environment:
 * refuse content sniffing, refuse to be framed, tame the referrer, switch
 * off the sensors and surfaces the app does not use, and isolate the
 * browsing context from attackers that go through window.open.
 */
const ALWAYS_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

/**
 * Content-Security-Policy in production only. In development Next.js needs
 * `eval` and inline styles for its error overlay, so in development no CSP
 * is sent at all. `'unsafe-inline'` for scripts is needed by the
 * framework's own inline bootstrap and by the no-flash theme script of
 * `src/app/layout.tsx` (both are inline `<script>` blocks without a
 * nonce); a nonce-based policy is the next step. Styles keep
 * `'unsafe-inline'` for the inline bootstrap of the framework. Google
 * Fonts arrives self-hosted at build time (`next/font`), so `font-src
 * 'self'` covers it.
 */
const PRODUCTION_CSP_HEADER = {
  key: "Content-Security-Policy",
  value:
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    + "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    + "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
    + "base-uri 'self'; form-action 'self'; object-src 'none'",
};

type HeadersEntry = {
  source: string;
  headers: Array<{ key: string; value: string }>;
};

/**
 * The `headers()` result of the web app as a pure function of the
 * environment, so a unit test can ask for it with and without
 * `NODE_ENV=production` (mirroring `apiRewrites`).
 */
export function securityHeaders(
  nodeEnv: string | undefined,
): HeadersEntry[] {
  return [
    {
      source: APP_HEADERS_SOURCE,
      headers:
        nodeEnv === "production"
          ? [...ALWAYS_HEADERS, PRODUCTION_CSP_HEADER]
          : [...ALWAYS_HEADERS],
    },
  ];
}

const nextConfig: NextConfig = {
  async headers() {
    return securityHeaders(process.env.NODE_ENV);
  },
  async rewrites() {
    return apiRewrites(process.env.API_URL);
  },
};

export default nextConfig;
