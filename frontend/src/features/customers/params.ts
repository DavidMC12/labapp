/**
 * Parsers of the route and URL parameters of the customers screens.
 */

import type { CustomerStatus } from "./types";

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
};

/**
 * Reads the list URL parameters, with every invalid value falling back:
 * a `page` that is not a positive integer becomes 1, and a `status` that is
 * not `active` or `inactive` becomes no status. `q` is trimmed; an
 * empty-after-trimming `q` is no value at all.
 */
export function parseCustomerListParams(
  searchParams: URLSearchParams,
): CustomerListParams {
  const pageRaw = searchParams.get("page") ?? "";
  const page = ID_PATTERN.test(pageRaw) ? Number(pageRaw) : 1;

  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;

  const statusRaw = searchParams.get("status") ?? "";
  const status =
    statusRaw === "active" || statusRaw === "inactive" ? statusRaw : null;

  return { page, q, status };
}
