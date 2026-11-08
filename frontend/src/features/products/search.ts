/**
 * The client-side search of the catalog screen: the rows are already
 * loaded (`GET /api/products` has no paging), so the filter runs in the
 * browser and never sends a request. The match is the same kind of case-
 * and accent-insensitive "contains" the list APIs use (docs/SPEC.md
 * section 8): Unicode NFKD, combining marks removed, case-folded on both
 * sides, applied to the SKU or the name.
 */

/**
 * Folds one text for comparison: NFKD keeps the base letters of the
 * accents and the range `U+0300-U+036F` collects exactly the combining
 * marks that NFKD produced, so `óptico` and `optico` compare equal. The
 * lowercasing runs after the fold, because Turkish-style exceptions do
 * not concern this screen and `toLowerCase` keeps the result stable.
 */
export function normalizeForSearch(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/** The search contract of one product as the page uses it. */
export type ProductSearchInput = {
  sku: string;
  name: string;
};

/**
 * Whether one product matches a search term: a case- and accent-insensi-
 * tive "contains" on the SKU **or** the name. An empty (or whitespace-
 * only) term matches everything — the parsers hand this function the
 * trimmed `q`, and there are defensive cases in the tests for the empty
 * string anyway.
 */
export function productMatchesSearch(
  product: ProductSearchInput,
  term: string,
): boolean {
  const needle = normalizeForSearch(term.trim());
  if (needle === "") {
    return true;
  }
  return normalizeForSearch(product.sku).includes(needle)
    || normalizeForSearch(product.name).includes(needle);
}
