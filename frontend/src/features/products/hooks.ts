/**
 * Data layer of the products catalog screen. The catalog already exists
 * in the orders module (the draft editor's product pickers read it), so
 * this file re-exports it instead of duplicating the fetch: one data
 * layer, one request, one cache entry under `["products"]`, shared with
 * the order screen.
 */

export { PRODUCTS_KEY, useProducts } from "@/features/orders/hooks";
export { fetchProducts } from "@/features/orders/api";
export type { Product } from "@/features/orders/types";
