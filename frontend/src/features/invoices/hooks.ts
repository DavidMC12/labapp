/**
 * TanStack Query hooks of the invoices module. Every hook uses
 * `retry: false`: a failed request is a user-visible state, not something
 * a retry loop hides. The keys always carry the id as a **number**.
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { ApiRequestError } from "@/lib/api";
import { noteUnauthorized } from "@/features/auth/session";
import { ORDERS_LIST_KEY, orderDetailKey } from "@/features/orders/hooks";
import {
  fetchInvoice,
  fetchInvoices,
  issueInvoice,
  registerPayment,
  type InvoiceListRequest,
  type PaymentBody,
} from "./api";
import type { Invoice, InvoiceList, PaymentResult } from "./types";

/** Prefix of every list key; used to invalidate the lists at once. */
export const INVOICES_LIST_KEY = ["invoices", "list"] as const;

/**
 * Key of one list query: `["invoices", "list", { page, q, status, sort,
 * direction }]`. An empty `q` never has one of these keys, so
 * `{ page: 1, q: "" }` and `{ page: 1 }` do not split the cache in two;
 * the absent sort values of the default order hash the same way.
 */
export function invoicesListQueryKey(
  params: InvoiceListRequest,
): readonly [string, string, {
  page: number;
  q?: string;
  status?: string;
  sort?: string;
  direction?: string;
}] {
  return [INVOICES_LIST_KEY[0], INVOICES_LIST_KEY[1], {
    page: params.page,
    q: params.q || undefined,
    status: params.status || undefined,
    sort: params.sort,
    direction: params.direction,
  }];
}

/**
 * Key of one detail query. The id is a number taken from the route by
 * `parseInvoiceIdParam`; a string id here would create a second, dead
 * cache entry.
 */
export function invoiceDetailKey(
  id: number,
): readonly [string, string, number] {
  return ["invoices", "detail", id];
}

/**
 * Any 401 of the invoices endpoints means "no session": it writes `null`
 * into the `["auth", "me"]` cache entry so the shell redirects to the
 * login instead of showing "Reintentar" for ever, and a 401
 * `SESSION_EXPIRED` also raises the expired flag (see `noteUnauthorized`).
 */
function note401(error: unknown, queryClient: QueryClient): void {
  noteUnauthorized(error, queryClient);
}

/** One page of the invoices list, url state of `?page=&q=&status=`. */
export function useInvoices(
  params: InvoiceListRequest,
): UseQueryResult<InvoiceList, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<InvoiceList, ApiRequestError>({
    queryKey: invoicesListQueryKey(params),
    queryFn: async () => {
      try {
        return await fetchInvoices(params);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    // A new page, sort or filter keeps the previous data on screen while
    // it loads, so the table never disappears and the header button the
    // keyboard focused stays the active element.
    placeholderData: keepPreviousData,
    retry: false,
  });
}

/** One invoice by numeric id, with its payment history. */
export function useInvoice(
  id: number,
): UseQueryResult<Invoice, ApiRequestError> {
  const queryClient = useQueryClient();

  return useQuery<Invoice, ApiRequestError>({
    queryKey: invoiceDetailKey(id),
    queryFn: async () => {
      try {
        return await fetchInvoice(id);
      } catch (error) {
        note401(error, queryClient);
        throw error;
      }
    },
    retry: false,
  });
}

/**
 * POST /api/orders/{id}/invoice with `If-Match: "<version>"` (the order
 * version on screen). On success the invoice enters its detail cache and
 * the order reads, its detail and the lists are invalidated: the order
 * now carries its `invoice_id`.
 */
export function useIssueInvoice(): UseMutationResult<
  Invoice,
  ApiRequestError,
  { orderId: number; version: number }
> {
  const queryClient = useQueryClient();

  return useMutation<
    Invoice,
    ApiRequestError,
    { orderId: number; version: number }
  >({
    mutationFn: ({ orderId, version }) => issueInvoice(orderId, version),
    retry: false,
    onSuccess: (invoice, { orderId }) => {
      queryClient.setQueryData(invoiceDetailKey(invoice.id), invoice);
      void queryClient.invalidateQueries({
        queryKey: orderDetailKey(orderId),
      });
      void queryClient.invalidateQueries({ queryKey: ORDERS_LIST_KEY });
      void queryClient.invalidateQueries({ queryKey: INVOICES_LIST_KEY });
    },
    onError: (error) => {
      note401(error, queryClient);
    },
  });
}

/**
 * Every answer of the payment endpoint that carries a payment: the 201
 * and the 402 `PAYMENT_DECLINED` and the 503 `PAYMENT_GATEWAY_UNAVAILABLE`.
 * Each one stores the attempt, so the invoice history must refetch.
 */
function afterPaymentError(
  queryClient: QueryClient,
  error: ApiRequestError,
): boolean {
  const code = error.problem.code;
  if (code !== "PAYMENT_DECLINED" && code !== "PAYMENT_GATEWAY_UNAVAILABLE") {
    return false;
  }
  void queryClient.invalidateQueries({ queryKey: ["invoices", "detail"] });
  void queryClient.invalidateQueries({ queryKey: ORDERS_LIST_KEY });
  void queryClient.invalidateQueries({ queryKey: ["orders", "detail"] });
  return true;
}

/**
 * POST /api/invoices/{id}/payments with `Idempotency-Key` and
 * `If-Match: "<version>"` (the invoice version on screen). A 201 writes
 * the invoice from `PaymentResult.invoice` into its detail cache and
 * invalidates the derived data; a declined (402) or failed (503) answer
 * is an error whose attempt is also in the history, so the same
 * invalidations run.
 */
export function useRegisterPayment(): UseMutationResult<
  PaymentResult,
  ApiRequestError,
  { invoiceId: number; body: PaymentBody; idempotencyKey: string; version: number }
> {
  const queryClient = useQueryClient();

  return useMutation<
    PaymentResult,
    ApiRequestError,
    {
      invoiceId: number;
      body: PaymentBody;
      idempotencyKey: string;
      version: number;
    }
  >({
    mutationFn: ({ invoiceId, body, idempotencyKey, version }) =>
      registerPayment(invoiceId, body, idempotencyKey, version),
    retry: false,
    onSuccess: (result, { invoiceId }) => {
      queryClient.setQueryData(invoiceDetailKey(invoiceId), result.invoice);
      void queryClient.invalidateQueries({ queryKey: invoiceDetailKey(invoiceId) });
      void queryClient.invalidateQueries({ queryKey: ORDERS_LIST_KEY });
      void queryClient.invalidateQueries({ queryKey: ["orders", "detail"] });
      void queryClient.invalidateQueries({ queryKey: INVOICES_LIST_KEY });
    },
    onError: (error) => {
      note401(error, queryClient);
      afterPaymentError(queryClient, error);
    },
  });
}
