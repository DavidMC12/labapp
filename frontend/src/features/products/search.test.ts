import { describe, expect, it } from "vitest";
import type { ProductSearchInput } from "./search";
import { normalizeForSearch, productMatchesSearch } from "./search";

/** Seed product 2, with the accent the search must fold. */
const mouse: ProductSearchInput = {
  sku: "MS-200",
  name: "Mouse óptico",
};

describe("normalizeForSearch", () => {
  it("folds accents and lowercases", () => {
    expect(normalizeForSearch("Mouse óptico")).toBe("mouse optico");
    expect(normalizeForSearch("KB-100")).toBe("kb-100");
  });
});

describe("productMatchesSearch", () => {
  it("matches with case folded and accents folded on both sides", () => {
    expect(productMatchesSearch(mouse, "mouse")).toBe(true);
    expect(productMatchesSearch(mouse, "MOUSE")).toBe(true);
    expect(productMatchesSearch(mouse, "mouse optico")).toBe(true);
    expect(productMatchesSearch(mouse, "mouse óptico")).toBe(true);
    // The accent of the term folds away, so "optico" matches "óptico".
    expect(productMatchesSearch(mouse, "optico")).toBe(true);
    expect(productMatchesSearch(mouse, "ÓPTICO")).toBe(true);
  });

  it("matches the sku too and contains partials", () => {
    expect(productMatchesSearch(mouse, "MS-200")).toBe(true);
    expect(productMatchesSearch(mouse, "ms")).toBe(true);
    expect(productMatchesSearch(mouse, "200")).toBe(true);
    expect(productMatchesSearch(mouse, "kb")).toBe(false);
  });

  it("matches everything on an empty or blank term", () => {
    expect(productMatchesSearch(mouse, "")).toBe(true);
    expect(productMatchesSearch(mouse, "   ")).toBe(true);
  });

  it("matches by name and rejects a foreign term", () => {
    const disco: ProductSearchInput = {
      sku: "HD-500",
      name: "Disco externo 1 TB",
    };
    expect(productMatchesSearch(disco, "externo")).toBe(true);
    expect(productMatchesSearch(disco, "tarjeta")).toBe(false);
  });
});
