import { describe, expect, it } from "vitest";
import { apiRewrites } from "../next.config";

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
