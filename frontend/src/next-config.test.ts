import { describe, expect, it } from "vitest";
import {
  apiRewrites,
  APP_HEADERS_SOURCE,
  securityHeaders,
} from "../next.config";

describe("apiRewrites", () => {
  it("adds no rewrite when the API url is not set", () => {
    expect(apiRewrites(undefined)).toEqual([]);
    expect(apiRewrites("")).toEqual([]);
  });

  it("forwards /api and /__test__ to the API process", () => {
    expect(apiRewrites("http://127.0.0.1:8000")).toEqual([
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
      { source: "/__test__/:path*", destination: "http://127.0.0.1:8000/__test__/:path*" },
    ]);
  });

  it("ignores trailing slashes in the API url", () => {
    expect(apiRewrites("http://localhost:9000//")[0]?.destination).toBe(
      "http://localhost:9000/api/:path*",
    );
  });
});

describe("the source pattern of the web app headers", () => {
  // The pattern Next.js receives is a path-to-regexp source; for the paths
  // below its compilation matches the same values as this plain regular
  // expression of the regex group after the leading slash.
  const matches = new RegExp(`^${APP_HEADERS_SOURCE}$`);

  it("matches the pages and the assets of the web app", () => {
    expect(matches.test("/")).toBe(true);
    expect(matches.test("/login")).toBe(true);
    expect(matches.test("/orders/3")).toBe(true);
  });

  it("matches look-alike paths that are not the API's", () => {
    expect(matches.test("/apiary")).toBe(true);
    expect(matches.test("/api-docs")).toBe(true);
    expect(matches.test("/__test__x")).toBe(true);
    expect(matches.test("/customers/api")).toBe(true);
  });

  it("does not match the paths of the API", () => {
    expect(matches.test("/api/docs")).toBe(false);
    expect(matches.test("/api/openapi.json")).toBe(false);
    expect(matches.test("/api")).toBe(false);
  });

  it("does not match the test controls", () => {
    expect(matches.test("/__test__/reset")).toBe(false);
    expect(matches.test("/__test__")).toBe(false);
  });
});

describe("securityHeaders", () => {
  const names = (entry: { headers: Array<{ key: string }> }) =>
    entry.headers.map((header) => header.key);

  it("always sends the five environment-independent headers outside production", () => {
    for (const nodeEnv of [undefined, "development", "test"]) {
      const entry = securityHeaders(nodeEnv)[0];
      expect(entry?.source).toBe(APP_HEADERS_SOURCE);
      expect(names(entry!)).toEqual([
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cross-Origin-Opener-Policy",
      ]);
      expect(entry?.headers).toContainEqual({
        key: "X-Content-Type-Options",
        value: "nosniff",
      });
      expect(entry?.headers).toContainEqual({
        key: "X-Frame-Options",
        value: "DENY",
      });
      expect(entry?.headers).toContainEqual({
        key: "Referrer-Policy",
        value: "strict-origin-when-cross-origin",
      });
      expect(entry?.headers).toContainEqual({
        key: "Permissions-Policy",
        value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
      });
      expect(entry?.headers).toContainEqual({
        key: "Cross-Origin-Opener-Policy",
        value: "same-origin",
      });
    }
  });

  it("adds the strict Content-Security-Policy in production only", () => {
    expect(names(securityHeaders("development")[0]!)).not.toContain(
      "Content-Security-Policy",
    );
    expect(names(securityHeaders(undefined)[0]!)).not.toContain(
      "Content-Security-Policy",
    );

    const entry = securityHeaders("production")[0];
    expect(names(entry!)).toContain("Content-Security-Policy");
    expect(entry?.headers).toContainEqual({
      key: "Content-Security-Policy",
      value:
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        + "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        + "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
        + "base-uri 'self'; form-action 'self'; object-src 'none'",
    });
  });
});
