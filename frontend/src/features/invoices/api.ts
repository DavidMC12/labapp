/**
 * Requests of the "Invoices and payments API" (docs/SPEC.md section 6),
 * all through the thin client of `src/lib/api.ts`. Money travels as
 * strings with 2 decimals; the payment body carries only the fields of
 * its method; the payment request always carries the `Idempotency-Key`
 * header and the version as an optional `If-Match`.
 */

import { apiFetch } from "@/lib/api";
import type {
  Invoice,
  InvoiceList,
  InvoiceStatus,
  PaymentMethod,
  PaymentResult,
} from "./types";

/** Parameters of one list page: `page` always, the rest only when set. */
export type InvoiceListRequest = {
  page: number;
  q?: string;
  status?: InvoiceStatus;
};

/**
 * Builds the `URLSearchParams` of the list request: `page` is always
 * present, while `q` and `status` are present only when they have a value
 * (an empty `status=` would be a 422 from the real API). `URLSearchParams`
 * encodes reserved characters such as `&`, so `q=R&D` becomes `q=R%26D`.
 */
export function buildInvoiceListQuery(
  params: InvoiceListRequest,
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

export function invoiceListUrl(params: InvoiceListRequest): string {
  return `/api/invoices?${buildInvoiceListQuery(params).toString()}`;
}

/** GET /api/invoices — 200 `{items, page, page_size, total}`. */
export function fetchInvoices(
  params: InvoiceListRequest,
): Promise<InvoiceList> {
  return apiFetch<InvoiceList>(invoiceListUrl(params));
}

/** GET /api/invoices/{id} — 200 `Invoice` (with its payment history). */
export function fetchInvoice(id: number): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/invoices/${id}`);
}

/**
 * POST /api/orders/{id}/invoice: issue the invoice of a `confirmed`
 * order; no body and `If-Match: "<version>"` (the version of the order).
 * The answer is the 201 `Invoice`.
 */
export function issueInvoice(orderId: number, version: number): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/orders/${orderId}/invoice`, {
    method: "POST",
    headers: { "If-Match": `"${version}"` },
  });
}

/** The body of a payment, per method: card, transfer and cash. */
export type CardBody = { number: string; expiry: string; cvc: string };

export type PaymentBody = {
  method: PaymentMethod;
  amount: string;
  /** Only for `card`; never sent with the other methods. */
  card?: CardBody;
  /** Only for `transfer`; never sent with the other methods. */
  reference?: string;
};

/**
 * POST /api/invoices/{id}/payments: register a payment. The answer is a
 * 201 `PaymentResult`; a 402 or a 503 carries `payment_id` and `reason`
 * and arrives as an `ApiRequestError` for the screen and the hook to
 * handle.
 */
export function registerPayment(
  invoiceId: number,
  body: PaymentBody,
  idempotencyKey: string,
  version: number,
): Promise<PaymentResult> {
  return apiFetch<PaymentResult>(`/api/invoices/${invoiceId}/payments`, {
    method: "POST",
    body,
    headers: {
      "Idempotency-Key": idempotencyKey,
      "If-Match": `"${version}"`,
    },
  });
}
