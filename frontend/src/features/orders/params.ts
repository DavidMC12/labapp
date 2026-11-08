/**
 * Parsers of the route and URL parameters of the orders screens, with the
 * same discipline as the customers ones: a strict parse keeps the query
 * keys distinct-but-single and the route ids free of surprises.
 */

import type { OrderStatus } from "./types";

/** The fields the orders list URL may sort by (docs/SPEC.md section 5). */
export type OrderSortField = "created_at" | "number" | "customer";

/** The two directions the URLs of the list can carry for one field. */
export type OrderSortDirection = "asc" | "desc";

/** One full sort: a field and its direction, the state the headers write. */
export type OrderSort = {
  sort: OrderSortField;
  direction: OrderSortDirection;
};

/** The fields the list accepts; any other `sort` value in the URL falls back. */
const SORT_FIELDS: readonly OrderSortField[] = [
  "created_at",
  "number",
  "customer",
];

/** The order of the plain list: newest order first. */
export const DEFAULT_ORDER_SORT: OrderSort = {
  sort: "created_at",
  direction: "desc",
};

/** The direction one field sorts with when the click does not flip it. */
export function orderSortDefaultDirection(
  field: OrderSortField,
): OrderSortDirection {
  return field === "created_at" ? "desc" : "asc";
}

/** The other direction of one sort (there is no "unsorted" state). */
export function flipOrderSortDirection(
  direction: OrderSortDirection,
): OrderSortDirection {
  return direction === "asc" ? "desc" : "asc";
}

/**
 * The effective sort of one visit: the URL pair, with a missing or
 * invalid value meaning the default of the field (the customers list
 * rule, docs/SPEC.md section 5).
 */
export function resolveOrderSort(params: {
  sort: OrderSortField | null;
  direction: OrderSortDirection | null;
}): OrderSort {
  const sort = params.sort ?? DEFAULT_ORDER_SORT.sort;
  return {
    sort,
    direction: params.direction ?? orderSortDefaultDirection(sort),
  };
}

/** True when the pair is the one of the plain list. */
export function isDefaultOrderSort(sort: OrderSort): boolean {
  return sort.sort === DEFAULT_ORDER_SORT.sort
    && sort.direction === DEFAULT_ORDER_SORT.direction;
}

/** The Spanish label of a sort field, the text the announcement carries. */
const ORDER_SORT_LABELS: Record<OrderSortField, string> = {
  "created_at": "Creado",
  "number": "Número",
  "customer": "Cliente",
};

export function orderSortLabel(field: OrderSortField): string {
  return ORDER_SORT_LABELS[field];
}

/** Largest page the list API recognizes (docs/SPEC.md section 5). */
const MAX_PAGE = 1000000;

/** Largest id the API recognizes (docs/SPEC.md section 5). */
const MAX_ID = 2147483647;

/**
 * Strict page pattern of the list URL: no sign, no leading zeros, no other
 * syntax (`"1e3"`, `"0"` and `"007"` are rejected).
 */
const ID_PATTERN = /^[1-9][0-9]*$/;

/** The five statuses of an order accepted by the list API. */
const STATUSES: readonly OrderStatus[] = [
  "draft",
  "confirmed",
  "paid",
  "shipped",
  "cancelled",
];

/**
 * Parses the `id` route parameter once, per screen. Accepts only the
 * pattern `^[1-9][0-9]*$` and at most 2147483647; anything else (including
 * `"0"`, `"007"` and `"1e3"`) returns `null`, so the screen can show the
 * "not found" alert without calling the API.
 */
export function parseOrderIdParam(value: unknown): number | null {
  if (typeof value !== "string" || !ID_PATTERN.test(value)) {
    return null;
  }
  const id = Number(value);
  return id > MAX_ID ? null : id;
}

/**
 * Parses a `customer_id` from the url (`/orders/new?customer_id=7`), with
 * the exact rules the API and the list parser put on it: a positive
 * integer without sign, leading zeros or other syntax, at most
 * 2147483647. Anything else returns `null`, so `/orders/new` can treat it
 * as if the parameter were absent instead of guessing.
 */
export function parseCustomerIdParam(value: unknown): number | null {
  if (typeof value !== "string" || !ID_PATTERN.test(value)) {
    return null;
  }
  const id = Number(value);
  return id > MAX_ID ? null : id;
}

/** Parsed state of the list URL: `?page=2&q=ped&status=confirmed`. */
export type OrderListParams = {
  page: number;
  q: string | null;
  status: OrderStatus | null;
  /** The `customer_id` filter, or null when the URL has none or a bad one. */
  customerId: number | null;
  /** Parsed `sort` of the URL: null is the default field (`created_at`). */
  sort: OrderSortField | null;
  /** Parsed `direction` of the URL: null is the default of `sort`. */
  direction: OrderSortDirection | null;
};

/**
 * Reads the list URL parameters, with every invalid value falling back: a
 * `page` that is not a positive integer up to 1000000 becomes 1, a
 * `status` that is not one of the five states becomes no status, and a
 * `customer_id` that is not a positive integer up to 2147483647 becomes
 * no filter. `q` is trimmed; an empty-after-trimming `q` is no value at
 * all. `URLSearchParams.get` reads the first occurrence of a repeated
 * parameter; the rest are ignored.
 */
export function parseOrderListParams(
  searchParams: URLSearchParams,
): OrderListParams {
  const pageRaw = searchParams.get("page") ?? "";
  const page = ID_PATTERN.test(pageRaw) && Number(pageRaw) <= MAX_PAGE
    ? Number(pageRaw)
    : 1;

  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;

  const statusRaw = searchParams.get("status") ?? "";
  const status = (
    STATUSES as readonly string[]
  ).includes(statusRaw)
    ? (statusRaw as OrderStatus)
    : null;

  const customerId = parseCustomerIdParam(
    searchParams.get("customer_id") ?? "",
  );

  const sortRaw = searchParams.get("sort") ?? "";
  const sort = (SORT_FIELDS as readonly string[]).includes(sortRaw)
    ? (sortRaw as OrderSortField)
    : null;

  const directionRaw = searchParams.get("direction") ?? "";
  const direction = directionRaw === "asc" || directionRaw === "desc"
    ? directionRaw
    : null;

  return { page, q, status, customerId, sort, direction };
}
