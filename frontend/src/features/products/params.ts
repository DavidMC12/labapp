/**
 * Parsers of the url parameters of the products screen, with the same
 * discipline as the customers and orders ones, minus everything a screen
 * without paging or statuses does not need. `GET /api/products` returns
 * the whole catalog, so the only url state is the `q` of the client-side
 * search.
 */

/** Parsed state of the list url: `/products?q=mouse`. */
export type ProductListParams = {
  q: string | null;
};

/**
 * Reads the `q` parameter exactly as the other screens: trimmed, and an
 * empty-after-trimming value is no filter at all. `URLSearchParams.get`
 * reads the first occurrence of a repeated parameter; the rest are
 * ignored.
 */
export function parseProductListParams(
  searchParams: URLSearchParams,
): ProductListParams {
  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;
  return { q };
}
