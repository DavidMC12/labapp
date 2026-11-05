/**
 * Requests of the Orders API (docs/SPEC.md section 5, "Orders API"), all
 * through the thin client of `src/lib/api.ts`. Money travels as strings
 * with 2 decimals and ids as integers; `version` is included in the
 * bodies that change the order and as an `If-Match` header on the
 * transitions and the line deletion.
 */

import { apiFetch } from "@/lib/api";
import type {
  Order,
  OrderList,
  OrderStatus,
  Product,
} from "./types";

/** Parameters of one list page: `page` always, the rest only when set. */
export type OrderListRequest = {
  page: number;
  q?: string;
  status?: OrderStatus;
};

/**
 * Builds the `URLSearchParams` of the list request: `page` is always
 * present, while `q` and `status` are present only when they have a value
 * (an empty `status=` would be a 422 from the real API). `URLSearchParams`
 * encodes reserved characters such as `&`, so `q=R&D` becomes `q=R%26D`.
 */
export function buildOrderListQuery(
  params: OrderListRequest,
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

export function orderListUrl(params: OrderListRequest): string {
  return `/api/orders?${buildOrderListQuery(params).toString()}`;
}

/** GET /api/orders — 200 `{items, page, page_size, total}`. */
export function fetchOrders(params: OrderListRequest): Promise<OrderList> {
  return apiFetch<OrderList>(orderListUrl(params));
}

/** GET /api/orders/{id} — 200 `Order`. */
export function fetchOrder(id: number): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}`);
}

/** GET /api/products — 200 `{items: [Product]}`, no paging. */
export function fetchProducts(): Promise<{ items: Product[] }> {
  return apiFetch<{ items: Product[] }>("/api/products");
}

/** POST /api/orders — 201 `Order` (a new draft of one line set). */
export function createOrder(customerId: number): Promise<Order> {
  return apiFetch<Order>("/api/orders", {
    method: "POST",
    body: { customer_id: customerId },
  });
}

/** The body of the customer change: `customer_id` plus the version. */
export type OrderCustomerBody = { customer_id: number; version: number };

/** PATCH /api/orders/{id} — change the customer of a draft. */
export function setOrderCustomer(
  id: number,
  body: OrderCustomerBody,
): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}`, { method: "PATCH", body });
}

/**
 * The body of an add-line or set-quantity request. A quantity that is a
 * full digit string is sent as an integer; anything else (`"5.5"`,
 * `"-1"`, text) is sent as the typed string so the server's
 * `INVALID_FORMAT` message shows on the field (integers are strict on the
 * server).
 */
export type OrderLineBody = {
  product_id?: number;
  quantity: number | string;
  version: number;
};

/** POST /api/orders/{id}/lines — 201 `Order`. */
export function addOrderLine(
  id: number,
  body: OrderLineBody & { product_id: number },
): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}/lines`, { method: "POST", body });
}

/** PATCH /api/orders/{id}/lines/{lineId} — 200 `Order`. */
export function setOrderLineQuantity(
  id: number,
  lineId: number,
  body: OrderLineBody,
): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}/lines/${lineId}`, {
    method: "PATCH",
    body,
  });
}

/**
 * DELETE /api/orders/{id}/lines/{lineId} with
 * `If-Match: "<version>"`: the answer is the order after the removal.
 */
export function removeOrderLine(
  id: number,
  lineId: number,
  version: number,
): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}/lines/${lineId}`, {
    method: "DELETE",
    headers: { "If-Match": `"${version}"` },
  });
}

/** The three transitions the UI can ask for. */
export type OrderTransitionAction = "confirm" | "cancel" | "ship";

/**
 * POST /api/orders/{id}/confirm, /cancel or /ship. No body; the version
 * travels as `If-Match: "<version>"`, where a stale value is a 409 and an
 * absent value would skip the check (the UI always sends one).
 */
export function transitionOrder(
  id: number,
  action: OrderTransitionAction,
  version: number,
): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${id}/${action}`, {
    method: "POST",
    headers: { "If-Match": `"${version}"` },
  });
}
