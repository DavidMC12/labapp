/**
 * Parsers of the route and URL parameters of the customers screens.
 */

import type { CustomerStatus } from "./types";

/** The fields the customers list URL may sort by (docs/SPEC.md section 4). */
export type CustomerSortField = "created_at" | "name" | "email";

/** The two directions the URLs of the list can carry for one field. */
export type CustomerSortDirection = "asc" | "desc";

/** One full sort: a field and its direction, the state the headers write. */
export type CustomerSort = {
  sort: CustomerSortField;
  direction: CustomerSortDirection;
};

/** The fields the list accepts; any other `sort` value in the URL falls back. */
const SORT_FIELDS: readonly CustomerSortField[] = [
  "created_at",
  "name",
  "email",
];

/** The sort of the plain list: newest customer first. */
export const DEFAULT_CUSTOMER_SORT: CustomerSort = {
  sort: "created_at",
  direction: "desc",
};

/** The direction one field sorts with when the click does not flip it. */
export function customerSortDefaultDirection(
  field: CustomerSortField,
): CustomerSortDirection {
  return field === "created_at" ? "desc" : "asc";
}

/** The other direction of one sort (there is no "unsorted" state). */
export function flipCustomerSortDirection(
  direction: CustomerSortDirection,
): CustomerSortDirection {
  return direction === "asc" ? "desc" : "asc";
}

/**
 * The effective sort of one visit: the URL pair, with a missing or
 * invalid `sort` meaning `created_at` and a missing or invalid
 * `direction` meaning the default direction of that field. The API rule
 * (a present `direction` applies to the field it stands for, active even
 * without `sort`) is kept here.
 */
export function resolveCustomerSort(params: {
  sort: CustomerSortField | null;
  direction: CustomerSortDirection | null;
}): CustomerSort {
  const sort = params.sort ?? DEFAULT_CUSTOMER_SORT.sort;
  return {
    sort,
    direction: params.direction ?? customerSortDefaultDirection(sort),
  };
}

/** True when the pair is the one of the plain list. */
export function isDefaultCustomerSort(sort: CustomerSort): boolean {
  return sort.sort === DEFAULT_CUSTOMER_SORT.sort
    && sort.direction === DEFAULT_CUSTOMER_SORT.direction;
}

/** The Spanish label of a sort field, the text the announcement carries. */
const CUSTOMER_SORT_LABELS: Record<CustomerSortField, string> = {
  "created_at": "Creado",
  "name": "Nombre",
  "email": "Email",
};

export function customerSortLabel(field: CustomerSortField): string {
  return CUSTOMER_SORT_LABELS[field];
}

/** Largest page the list API recognizes (docs/SPEC.md section 4). */
const MAX_PAGE = 1000000;

/** Largest id the API recognizes (docs/SPEC.md section 4). */
const MAX_ID = 2147483647;

/**
 * Strict page pattern of the list URL: no sign, no leading zeros, no other
 * syntax (`"1e3"`, `"0"` and `"007"` are rejected). Otherwise an invalid
 * value would silently become a number and, below, a second query key.
 */
const ID_PATTERN = /^[1-9][0-9]*$/;

/**
 * Parses the `id` route parameter once, per screen. Accepts only the
 * pattern `^[1-9][0-9]*$` and at most 2147483647; anything else (including
 * `"0"`, `"007"` and `"1e3"`) returns `null`, so the screen can show the
 * "not found" alert without calling the API. A strict parse also keeps the
 * query keys distinct-but-single: `"7"` and `7` would be two different
 * entries under the same screen.
 */
export function parseCustomerIdParam(value: unknown): number | null {
  if (typeof value !== "string" || !ID_PATTERN.test(value)) {
    return null;
  }
  const id = Number(value);
  return id > MAX_ID ? null : id;
}

/** Parsed state of the list URL: `?page=2&q=ana&status=active`. */
export type CustomerListParams = {
  page: number;
  q: string | null;
  status: CustomerStatus | null;
  /** Parsed `sort` of the URL: null is the default field (`created_at`). */
  sort: CustomerSortField | null;
  /** Parsed `direction` of the URL: null is the default of `sort`. */
  direction: CustomerSortDirection | null;
};

/**
 * Reads the list URL parameters, with every invalid value falling back:
 * a `page` that is not a positive integer up to 1000000 becomes 1 (the
 * API answers 422 `OUT_OF_RANGE` to anything else), and a `status` that is
 * not `active` or `inactive` becomes no status. `q` is trimmed; an
 * empty-after-trimming `q` is no value at all.
 */
export function parseCustomerListParams(
  searchParams: URLSearchParams,
): CustomerListParams {
  const pageRaw = searchParams.get("page") ?? "";
  const page = ID_PATTERN.test(pageRaw) && Number(pageRaw) <= MAX_PAGE
    ? Number(pageRaw)
    : 1;

  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;

  const statusRaw = searchParams.get("status") ?? "";
  const status =
    statusRaw === "active" || statusRaw === "inactive" ? statusRaw : null;

  const sortRaw = searchParams.get("sort") ?? "";
  const sort = (SORT_FIELDS as readonly string[]).includes(sortRaw)
    ? (sortRaw as CustomerSortField)
    : null;

  const directionRaw = searchParams.get("direction") ?? "";
  const direction =
    directionRaw === "asc" || directionRaw === "desc"
      ? directionRaw
      : null;

  return { page, q, status, sort, direction };
}
