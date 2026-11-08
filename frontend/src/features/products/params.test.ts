import { describe, expect, it } from "vitest";
import {
  flipProductSortDirection,
  isDefaultProductSort,
  parseProductListParams,
  productSortDefaultDirection,
  productSortLabel,
  resolveProductSort,
} from "./params";

describe("the products sort helpers", () => {
  it("answers asc for every field: the catalog has no created_at", () => {
    expect(productSortDefaultDirection()).toBe("asc");
  });

  it("flips one direction and never leaves the valid pair", () => {
    expect(flipProductSortDirection("asc")).toBe("desc");
    expect(flipProductSortDirection("desc")).toBe("asc");
  });

  it("resolves the effective sort of the URL values", () => {
    // Nothing in the URL: the plain catalog order.
    expect(resolveProductSort({ sort: null, direction: null })).toEqual({
      sort: "id",
      direction: "asc",
    });
    expect(resolveProductSort({ sort: "price", direction: null })).toEqual({
      sort: "price",
      direction: "asc",
    });
    // A direction without `sort` still says which way the id order runs.
    expect(resolveProductSort({ sort: null, direction: "desc" })).toEqual({
      sort: "id",
      direction: "desc",
    });
    expect(resolveProductSort({ sort: "sku", direction: "desc" })).toEqual({
      sort: "sku",
      direction: "desc",
    });
  });

  it("answers whether a sort is the one of the plain catalog", () => {
    expect(isDefaultProductSort({ sort: "id", direction: "asc" })).toBe(true);
    expect(isDefaultProductSort({ sort: "id", direction: "desc" })).toBe(false);
    expect(isDefaultProductSort({ sort: "price", direction: "asc" }))
      .toBe(false);
  });

  it("labels each field in Spanish", () => {
    expect(productSortLabel("sku")).toBe("SKU");
    expect(productSortLabel("name")).toBe("Producto");
    expect(productSortLabel("price")).toBe("Precio");
    expect(productSortLabel("stock")).toBe("Stock");
    expect(productSortLabel("id")).toBe("Id");
  });
});

describe("parseProductListParams", () => {
  it("trims q and ignores an empty-after-trimming value", () => {
    expect(parseProductListParams(new URLSearchParams("q=  mouse  ")))
      .toEqual({ q: "mouse", sort: null, direction: null });
    expect(parseProductListParams(new URLSearchParams("q=   ")))
      .toEqual({ q: null, sort: null, direction: null });
  });

  it("works without the parameter and takes the first of a repeated one", () => {
    expect(parseProductListParams(new URLSearchParams())).toEqual({
      q: null,
      sort: null,
      direction: null,
    });
    // `URLSearchParams.toString()` serializes both, but `get` reads the
    // first; the parsers of the other screens share the behavior.
    const repeated = new URLSearchParams();
    repeated.append("q", "mouse");
    repeated.append("q", "teclado");
    expect(parseProductListParams(repeated)).toEqual({
      q: "mouse",
      sort: null,
      direction: null,
    });
  });

  it("reads a valid sort and direction and falls back on invalid ones", () => {
    expect(
      parseProductListParams(new URLSearchParams("sort=price&direction=desc")),
    ).toMatchObject({ sort: "price", direction: "desc" });
    // Any other value of either falls back to the plain catalog order.
    expect(parseProductListParams(new URLSearchParams("sort=cost")))
      .toMatchObject({ sort: null });
    expect(parseProductListParams(new URLSearchParams("direction=upwards")))
      .toMatchObject({ direction: null });
  });
});
