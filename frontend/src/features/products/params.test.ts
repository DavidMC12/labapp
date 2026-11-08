import { describe, expect, it } from "vitest";
import { parseProductListParams } from "./params";

describe("parseProductListParams", () => {
  it("trims q and ignores an empty-after-trimming value", () => {
    expect(parseProductListParams(new URLSearchParams("q=  mouse  ")))
      .toEqual({ q: "mouse" });
    expect(parseProductListParams(new URLSearchParams("q=   ")))
      .toEqual({ q: null });
  });

  it("works without the parameter and takes the first of a repeated one", () => {
    expect(parseProductListParams(new URLSearchParams())).toEqual({ q: null });
    // `URLSearchParams.toString()` serializes both, but `get` reads the
    // first; the parsers of the other screens share the behavior.
    const repeated = new URLSearchParams();
    repeated.append("q", "mouse");
    repeated.append("q", "teclado");
    expect(parseProductListParams(repeated)).toEqual({ q: "mouse" });
  });
});
