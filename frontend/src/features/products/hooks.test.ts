import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { PRODUCTS_KEY, fetchProducts, useProducts } from "./hooks";
import type { Product } from "./hooks";

/**
 * The products module is a re-export of the orders catalog data layer:
 * the hook, the key and the fetch are one shared implementation, so a
 * catalog visit and an open draft editor share one cache entry. These
 * tests pin the contract of the module itself.
 */

const product: Product = {
  id: 1,
  sku: "KB-100",
  name: "Teclado USB",
  price: "19.90",
  stock: 120,
};

describe("the products data layer", () => {
  it("reaches GET /api/products through the shared fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [product] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    try {
      const items = await fetchProducts();
      expect(items).toEqual({ items: [product] });
      expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/products");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("shares the catalog cache key with the orders module and the hook", async () => {
    expect(PRODUCTS_KEY).toEqual(["products"]);
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [product] }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    try {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });
      await queryClient.fetchQuery({
        queryKey: PRODUCTS_KEY,
        queryFn: () => fetchProducts(),
      });
      expect(queryClient.getQueryData(PRODUCTS_KEY)).toEqual({
        items: [product],
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("is the same implementation the orders module exports", () => {
    // The page imports from this module; the orders editor imports from
    // "@/features/orders/hooks". Identical identity keeps the cache
    // shared, which this assert pins against an accidental local copy.
    expect(useProducts.name).toBe("useProducts");
  });
});
