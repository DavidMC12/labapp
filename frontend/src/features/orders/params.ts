/**
 * Parsers of the route and URL parameters of the orders screens, with the
 * same discipline as the customers ones: a strict parse keeps the query
 * keys distinct-but-single and the route ids free of surprises.
 */

import type { OrderStatus } from "./types";

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

/** Parsed state of the list URL: `?page=2&q=ped&status=confirmed`. */
export type OrderListParams = {
  page: number;
  q: string | null;
  status: OrderStatus | null;
};

/**
 * Reads the list URL parameters, with every invalid value falling back: a
 * `page` that is not a positive integer up to 1000000 becomes 1, and a
 * `status` that is not one of the five states becomes no status. `q` is
 * trimmed; an empty-after-trimming `q` is no value at all.
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

  return { page, q, status };
}
