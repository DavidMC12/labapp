/**
 * Parsers of the route and URL parameters of the invoices screens, with
 * the same discipline as the orders ones: a strict parse keeps the query
 * keys distinct-but-single and the route ids free of surprises.
 */

import type { InvoiceStatus } from "./types";

/** The fields the invoices list URL may sort by (docs/SPEC.md section 6). */
export type InvoiceSortField = "created_at" | "number" | "customer" | "total";

/** The two directions the URLs of the list can carry for one field. */
export type InvoiceSortDirection = "asc" | "desc";

/** One full sort: a field and its direction, the state the headers write. */
export type InvoiceSort = {
  sort: InvoiceSortField;
  direction: InvoiceSortDirection;
};

/** The fields the list accepts; any other `sort` value in the URL falls back. */
const SORT_FIELDS: readonly InvoiceSortField[] = [
  "created_at",
  "number",
  "customer",
  "total",
];

/** The order of the plain list: newest invoice first. */
export const DEFAULT_INVOICE_SORT: InvoiceSort = {
  sort: "created_at",
  direction: "desc",
};

/** The direction one field sorts with when the click does not flip it. */
export function invoiceSortDefaultDirection(
  field: InvoiceSortField,
): InvoiceSortDirection {
  return field === "created_at" ? "desc" : "asc";
}

/** The other direction of one sort (there is no "unsorted" state). */
export function flipInvoiceSortDirection(
  direction: InvoiceSortDirection,
): InvoiceSortDirection {
  return direction === "asc" ? "desc" : "asc";
}

/**
 * The effective sort of one visit: the URL pair, with a missing or
 * invalid value meaning the default of the field (the customers list
 * rule, docs/SPEC.md section 6).
 */
export function resolveInvoiceSort(params: {
  sort: InvoiceSortField | null;
  direction: InvoiceSortDirection | null;
}): InvoiceSort {
  const sort = params.sort ?? DEFAULT_INVOICE_SORT.sort;
  return {
    sort,
    direction: params.direction ?? invoiceSortDefaultDirection(sort),
  };
}

/** True when the pair is the one of the plain list. */
export function isDefaultInvoiceSort(sort: InvoiceSort): boolean {
  return sort.sort === DEFAULT_INVOICE_SORT.sort
    && sort.direction === DEFAULT_INVOICE_SORT.direction;
}

/** The Spanish label of a sort field, the text the announcement carries. */
const INVOICE_SORT_LABELS: Record<InvoiceSortField, string> = {
  "created_at": "Creada",
  "number": "Número",
  "customer": "Cliente",
  "total": "Total",
};

export function invoiceSortLabel(field: InvoiceSortField): string {
  return INVOICE_SORT_LABELS[field];
}

/** Largest page the list API recognizes (docs/SPEC.md section 6). */
const MAX_PAGE = 1000000;

/** Largest id the API recognizes (docs/SPEC.md section 6). */
const MAX_ID = 2147483647;

/**
 * Strict page pattern of the list URL: no sign, no leading zeros, no other
 * syntax (`"1e3"`, `"0"` and `"007"` are rejected).
 */
const ID_PATTERN = /^[1-9][0-9]*$/;

/** The three statuses of an invoice accepted by the list API. */
const STATUSES: readonly InvoiceStatus[] = ["issued", "paid", "void"];

/**
 * Parses the `id` route parameter once, per screen. Accepts only the
 * pattern `^[1-9][0-9]*$` and at most 2147483647; anything else (including
 * `"0"`, `"007"` and `"1e3"`) returns `null`, so the screen can show the
 * "not found" alert without calling the API.
 */
export function parseInvoiceIdParam(value: unknown): number | null {
  if (typeof value !== "string" || !ID_PATTERN.test(value)) {
    return null;
  }
  const id = Number(value);
  return id > MAX_ID ? null : id;
}

/** Parsed state of the list URL: `?page=2&q=fac&status=paid`. */
export type InvoiceListParams = {
  page: number;
  q: string | null;
  status: InvoiceStatus | null;
  /** Parsed `sort` of the URL: null is the default field (`created_at`). */
  sort: InvoiceSortField | null;
  /** Parsed `direction` of the URL: null is the default of `sort`. */
  direction: InvoiceSortDirection | null;
};

/**
 * Reads the list URL parameters, with every invalid value falling back: a
 * `page` that is not a positive integer up to 1000000 becomes 1, and a
 * `status` that is not one of the three states becomes no status. `q` is
 * trimmed; an empty-after-trimming `q` is no value at all.
 */
export function parseInvoiceListParams(
  searchParams: URLSearchParams,
): InvoiceListParams {
  const pageRaw = searchParams.get("page") ?? "";
  const page = ID_PATTERN.test(pageRaw) && Number(pageRaw) <= MAX_PAGE
    ? Number(pageRaw)
    : 1;

  const qRaw = (searchParams.get("q") ?? "").trim();
  const q = qRaw === "" ? null : qRaw;

  const statusRaw = searchParams.get("status") ?? "";
  const status = (STATUSES as readonly string[]).includes(statusRaw)
    ? (statusRaw as InvoiceStatus)
    : null;

  const sortRaw = searchParams.get("sort") ?? "";
  const sort = (SORT_FIELDS as readonly string[]).includes(sortRaw)
    ? (sortRaw as InvoiceSortField)
    : null;

  const directionRaw = searchParams.get("direction") ?? "";
  const direction = directionRaw === "asc" || directionRaw === "desc"
    ? directionRaw
    : null;

  return { page, q, status, sort, direction };
}

/**
 * The href of the "Exportar CSV" link of the list (docs/SPEC.md section
 * 8): the export endpoint of the resource plus the applied list state,
 * with each parameter only when it has a value and is not the default,
 * exactly the rule `listUrl` follows for the list URL — and never `page`,
 * because the export answers every row the filters select, not one page.
 */
export function invoicesExportUrl(params: InvoiceListParams): string {
  const search = new URLSearchParams();
  if (params.q) {
    search.set("q", params.q);
  }
  if (params.status) {
    search.set("status", params.status);
  }
  const sort = resolveInvoiceSort({
    sort: params.sort,
    direction: params.direction,
  });
  if (!isDefaultInvoiceSort(sort)) {
    search.set("sort", sort.sort);
    search.set("direction", sort.direction);
  }
  const query = search.toString();
  return query === ""
    ? "/api/invoices/export"
    : `/api/invoices/export?${query}`;
}
