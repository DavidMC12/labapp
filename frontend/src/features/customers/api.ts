/**
 * Requests of the Customers API (docs/SPEC.md section 4), all through the
 * thin client of `src/lib/api.ts`.
 */

import { apiFetch } from "@/lib/api";
import type { Customer, CustomerList, CustomerStatus } from "./types";

/** Parameters of one list page: `page` always, the rest only when set. */
export type CustomerListRequest = {
  page: number;
  q?: string;
  status?: CustomerStatus;
};

/**
 * Builds the `URLSearchParams` of the list request: `page` is always
 * present, while `q` and `status` are present only when they have a value
 * (an empty `status=` would be a 422 from the real API). `URLSearchParams`
 * encodes reserved characters such as `&`, so `q=R&D` becomes `q=R%26D`.
 */
export function buildCustomerListQuery(
  params: CustomerListRequest,
): URLSearchParams {
  const search = new URLSearchParams();
  search.set("page", String(params.page));
  if (params.q) {
    search.set("q", params.q);
  }
  if (params.status) {
    search.set("status", params.status);
  }
  return search;
}

export function customerListUrl(params: CustomerListRequest): string {
  return `/api/customers?${buildCustomerListQuery(params).toString()}`;
}

/** GET /api/customers — 200 `{items, page, page_size, total}`. */
export function fetchCustomers(
  params: CustomerListRequest,
): Promise<CustomerList> {
  return apiFetch<CustomerList>(customerListUrl(params));
}

/** GET /api/customers/{id} — 200 `Customer`. */
export function fetchCustomer(id: number): Promise<Customer> {
  return apiFetch<Customer>(`/api/customers/${id}`);
}

/** The five editable fields of the customer form, once trimmed. */
export type CustomerFormValues = {
  name: string;
  email: string;
  phone: string | null;
  tax_id: string | null;
  address: string | null;
};

/** POST /api/customers — 201 `Customer`. */
export function createCustomer(values: CustomerFormValues): Promise<Customer> {
  return apiFetch<Customer>("/api/customers", { method: "POST", body: values });
}

/** An update body: the editable fields plus the captured `version`. */
export type CustomerUpdateBody = CustomerFormValues & { version: number };

/** PATCH /api/customers/{id} — the body must carry `version`. */
export function updateCustomer(
  id: number,
  body: CustomerUpdateBody,
): Promise<Customer> {
  return apiFetch<Customer>(`/api/customers/${id}`, {
    method: "PATCH",
    body,
  });
}

/** The two status transitions of the spec. */
export type CustomerStatusAction = "deactivate" | "reactivate";

/**
 * POST /api/customers/{id}/deactivate or /reactivate. Both accept
 * `If-Match: "<version>"`; the value carries quotes, because an unquoted
 * version would be a malformed `If-Match` for the real API.
 */
export function setCustomerStatus(
  id: number,
  action: CustomerStatusAction,
  version: number,
): Promise<Customer> {
  return apiFetch<Customer>(`/api/customers/${id}/${action}`, {
    method: "POST",
    headers: { "If-Match": `"${version}"` },
  });
}
