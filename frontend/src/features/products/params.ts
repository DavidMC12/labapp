/**
 * Parsers of the url parameters of the products screen, with the same
 * discipline as the customers and orders ones. There is no paging and no
 * statuses: the catalog is one request and the search filters it in the
 * browser, so the url state is only `q` and the sort of the catalog.
 */

/**
 * The fields the catalog URL may sort by (the `GET /api/products` row of
 * docs/SPEC.md). `id` is the default order of the catalog and has no
 * header, so no id of the screen ever writes it on its own.
 */
export type ProductSortField = "id" | "sku" | "name" | "price" | "stock";

/** The two directions the catalog URL can carry for one field. */
export type ProductSortDirection = "asc" | "desc";

/** One full sort: a field and its direction, the state the headers write. */
export type ProductSort = {
  sort: ProductSortField;
  direction: ProductSortDirection;
};

/** The fields the catalog accepts; any other `sort` value falls back. */
const SORT_FIELDS: readonly ProductSortField[] = [
  "id",
  "sku",
  "name",
  "price",
  "stock",
];

/**
 * The sort of the plain catalog: by id ascending, the one
 * `GET /api/products` answers without sort parameters.
 */
export const DEFAULT_PRODUCT_SORT: ProductSort = {
  sort: "id",
  direction: "asc",
};

/**
 * The direction one field sorts with when the click does not flip it.
 * The catalog has no `created_at` field: the API default of every
 * sortable field is `asc`, so this answers `asc` for all of them (the
 * shape the other lists share, applied to a catalog without dates).
 */
export function productSortDefaultDirection(): ProductSortDirection {
  return "asc";
}

/** The other direction of one sort (there is no "unsorted" state). */
export function flipProductSortDirection(
  direction: ProductSortDirection,
): ProductSortDirection {
  return direction === "asc" ? "desc" : "asc";
}

/**
 * The effective sort of one visit: the URL pair, with a missing or
 * invalid value meaning the plain catalog order (id ascending). The API
 * applies the direction to the field it stands for, even without `sort`.
 */
export function resolveProductSort(params: {
  sort: ProductSortField | null;
  direction: ProductSortDirection | null;
}): ProductSort {
  const sort = params.sort ?? DEFAULT_PRODUCT_SORT.sort;
  return {
    sort,
    direction: params.direction ?? productSortDefaultDirection(),
  };
}

/** True when the pair is the one of the plain catalog. */
export function isDefaultProductSort(sort: ProductSort): boolean {
  return sort.sort === DEFAULT_PRODUCT_SORT.sort
    && sort.direction === DEFAULT_PRODUCT_SORT.direction;
}

/** The Spanish label of a sort field, the text the announcement carries. */
const PRODUCT_SORT_LABELS: Record<ProductSortField, string> = {
  "id": "Id",
  "sku": "SKU",
  "name": "Producto",
  "price": "Precio",
  "stock": "Stock",
};

export function productSortLabel(field: ProductSortField): string {
  return PRODUCT_SORT_LABELS[field];
}

/** Parsed state of the list url: `/products?q=mouse`. */
export type ProductListParams = {
  q: string | null;
  /** Parsed `sort` of the url: null is the plain catalog order (`id`). */
  sort: ProductSortField | null;
  /** Parsed `direction` of the url: null is the default of `sort`. */
  direction: ProductSortDirection | null;
};

/**
 * Reads the url parameters exactly as the other screens: `q` is trimmed
 * and an empty-after-trimming value is no filter at all; a `sort` or
 * `direction` that the catalog does not accept falls back to the plain
 * order, as an invalid `status` does in the other lists.
 * `URLSearchParams.get` reads the first occurrence of a repeated
 * parameter; the rest are ignored.
 */
export function parseProductListParams(
  searchParams: URLSearchParams,
): ProductListParams {
  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;

  const sortRaw = searchParams.get("sort") ?? "";
  const sort = (SORT_FIELDS as readonly string[]).includes(sortRaw)
    ? (sortRaw as ProductSortField)
    : null;

  const directionRaw = searchParams.get("direction") ?? "";
  const direction = directionRaw === "asc" || directionRaw === "desc"
    ? directionRaw
    : null;

  return { q, sort, direction };
}
