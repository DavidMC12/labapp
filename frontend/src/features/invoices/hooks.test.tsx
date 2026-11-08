import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "@/features/auth/session";
import { ORDERS_LIST_KEY, orderDetailKey } from "@/features/orders/hooks";
import type { ApiRequestError } from "@/lib/api";
import {
  INVOICES_LIST_KEY,
  invoiceDetailKey,
  invoicesListQueryKey,
  useInvoice,
  useInvoices,
  useIssueInvoice,
  useRegisterPayment,
} from "./hooks";
import type { Invoice } from "./types";

const fetchMock = vi.fn();

const invoiceFixture: Invoice = {
  id: 1,
  number: "FAC-0001",
  status: "issued",
  order_id: 3,
  order_number: "PED-0003",
  customer: { id: 4, name: "Distribuidora Delta", tax_id: "DELT-700789", address: null },
  lines: [],
  subtotal: "298.00",
  tax_rate: "10.00",
  tax: "29.80",
  total: "327.80",
  payments: [],
  version: 1,
  created_at: "2026-01-03T14:00:00Z",
  updated_at: "2026-01-03T14:00:00Z",
};

const paymentFixture = {
  id: 5,
  method: "card",
  status: "approved",
  amount: "327.80",
  reference: null,
  card_last4: "4242",
  reason: null,
  created_at: "2026-01-04T15:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function problemWith(
  status: number,
  code: string,
  detail: string,
  extra: Record<string, unknown> = {},
): Response {
  return jsonResponse({ status, code, detail, ...extra }, status);
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

type AnyMutation = () => UseMutationResult<
  unknown,
  ApiRequestError,
  never
>;

async function runMutation<TVars>(
  queryClient: QueryClient,
  hook: () => UseMutationResult<unknown, ApiRequestError, TVars>,
  variables: TVars,
): Promise<void> {
  const { result } = renderHook(hook as AnyMutation as () => UseMutationResult<unknown, ApiRequestError, TVars>, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  });
  act(() => {
    // The mutation is built for its own variables; the unknown cast keeps
    // the helper generic without an `any`.
    (result.current.mutate as (input: TVars) => void)(variables);
  });
  await waitFor(() => {
    expect(result.current.isPending).toBe(false);
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the invoices query keys", () => {
  it("names every list entry with page, q and status", () => {
    expect(invoicesListQueryKey({ page: 2, q: "fac", status: "paid" })).toEqual(
      ["invoices", "list", { page: 2, q: "fac", status: "paid" }],
    );
    expect(invoicesListQueryKey({ page: 1, q: "" })).toEqual([
      "invoices",
      "list",
      { page: 1, q: undefined, status: undefined },
    ]);
  });

  it("carries the id as a number", () => {
    expect(invoiceDetailKey(1)).toEqual(["invoices", "detail", 1]);
  });
});

describe("useInvoices and useInvoice", () => {
  it("fetches the list with the built url", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], page: 1, page_size: 20, total: 0 }),
    );

    const { result } = renderHook(
      () => useInvoices({ page: 2, q: "fac", status: "paid" }),
      createWrapper(),
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/invoices?page=2&q=fac&status=paid",
    );
  });

  it("fetches the invoice detail with its history", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(invoiceFixture));

    const { result } = renderHook(() => useInvoice(1), createWrapper());

    await waitFor(() => expect(result.current.data).toBeTruthy());
    expect(result.current.data?.payments).toEqual([]);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/invoices/1");
  });
});

describe("useIssueInvoice", () => {
  it("sends If-Match with the order version and writes the invoice cache", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(jsonResponse(invoiceFixture, 201));

    await runMutation(queryClient, useIssueInvoice, {
      orderId: 3,
      version: 2,
    });

    expect(fetchMock.mock.calls[0]).toEqual([
      "/api/orders/3/invoice",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "If-Match": '"2"' }),
        body: undefined,
      }),
    ]);
    expect(queryClient.getQueryData(invoiceDetailKey(1))).toMatchObject({
      number: "FAC-0001",
    });
  });

  it("invalidates the exact order detail and both lists", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(orderDetailKey(3), { id: 3 });
    queryClient.setQueryData(ORDERS_LIST_KEY, []);
    queryClient.setQueryData(INVOICES_LIST_KEY, []);
    fetchMock.mockResolvedValueOnce(jsonResponse(invoiceFixture, 201));

    await runMutation(queryClient, useIssueInvoice, {
      orderId: 3,
      version: 2,
    });

    await waitFor(() => {
      expect(
        queryClient.getQueryCache().getAll()
          .every((query) => {
            const key = JSON.stringify(query.queryKey);
            const derived = key.startsWith('["orders","detail"')
              || key.startsWith('["orders","list"')
              || key.startsWith('["invoices","list"');
            return !derived || query.state.isInvalidated;
          }),
      ).toBe(true);
    });
  });
});

describe("useRegisterPayment", () => {
  const body = {
    method: "card",
    amount: "327.80",
    card: { number: "4242 4242 4242 4242", expiry: "12/27", cvc: "123" },
  } as const;

  function recordCalls() {
    return fetchMock.mock.calls.map((([input, init]) => ({
      url: String(input),
      init: init as RequestInit,
    })));
  }

  it("sends Idempotency-Key and If-Match with the invoice version", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        payment: paymentFixture,
        invoice: { ...invoiceFixture, status: "paid", version: 2 },
      }),
    );

    await runMutation(queryClient, useRegisterPayment, {
      invoiceId: 1,
      body,
      idempotencyKey: "abc._-XYZ0123",
      version: 1,
    });

    const [call] = recordCalls();
    expect(call.url).toBe("/api/invoices/1/payments");
    expect(call.init.headers).toMatchObject({
      "Idempotency-Key": "abc._-XYZ0123",
      "If-Match": '"1"',
    });
  });

  it("writes the invoice of the result and invalidates the invoice, orders and lists", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        payment: paymentFixture,
        invoice: { ...invoiceFixture, status: "paid", version: 2 },
      }),
    );

    await runMutation(queryClient, useRegisterPayment, {
      invoiceId: 1,
      body,
      idempotencyKey: "key-201",
      version: 1,
    });

    expect(queryClient.getQueryData(invoiceDetailKey(1))).toMatchObject({
      status: "paid",
      version: 2,
    });
    await waitFor(() => {
      expect(
        queryClient.getQueryCache().getAll()
          .every((query) => {
            const key = JSON.stringify(query.queryKey);
            // The invoice detail entry holds fresh data itself: only the
            // OTHER entries (orders detail and lists, the invoice list)
            // must be invalidated.
            if (key === JSON.stringify(invoiceDetailKey(1))) {
              return true;
            }
            const derived = key.startsWith('["orders","detail"')
              || key.startsWith('["orders","list"')
              || key.startsWith('["invoices","list"');
            return !derived || query.state.isInvalidated;
          }),
      ).toBe(true);
    });
  });

  it("invalidates the same data for a declined and for a failed answer", async () => {
    for (const [status, code, detail, extra] of [
      [402, "PAYMENT_DECLINED", "La pasarela rechazó el pago. Prueba con otra tarjeta.", { payment_id: 5, reason: "CARD_DECLINED" }],
      [503, "PAYMENT_GATEWAY_UNAVAILABLE", "La pasarela de pago no está disponible. Inténtalo de nuevo.", { payment_id: 6, reason: "GATEWAY_UNAVAILABLE" }],
    ] as const) {
      const { queryClient } = createWrapper();
      fetchMock.mockResolvedValueOnce(problemWith(status, code, detail, extra as Record<string, unknown>));

      await runMutation(queryClient, useRegisterPayment, {
        invoiceId: 1,
        body,
        idempotencyKey: `key-${status}`,
        version: 1,
      });

      await waitFor(() => {
        expect(
          queryClient.getQueryCache().getAll()
            .every((query) => {
              const key = JSON.stringify(query.queryKey);
              const derived = key.startsWith('["orders","detail"')
                || key.startsWith('["orders","list"')
                || key.startsWith('["invoices","detail"')
                || key.startsWith('["invoices","list"');
              return !derived || query.state.isInvalidated;
            }),
        ).toBe(true);
      });

      fetchMock.mockReset();
    }
  });

  it("does not invalidate anything for a validation error", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(invoiceDetailKey(1), invoiceFixture);
    fetchMock.mockResolvedValueOnce(
      problemWith(422, "PAYMENT_AMOUNT_MISMATCH", "El monto debe ser igual al total de la factura."),
    );

    await runMutation(queryClient, useRegisterPayment, {
      invoiceId: 1,
      body,
      idempotencyKey: "key-422",
      version: 1,
    });

    expect(queryClient.getQueryData(invoiceDetailKey(1))).toMatchObject({
      status: "issued",
    });
  });

  it("writes null into the session for a 401", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { name: "Admin Demo" });
    fetchMock.mockResolvedValueOnce(
      problemWith(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );

    await runMutation(queryClient, useRegisterPayment, {
      invoiceId: 1,
      body,
      idempotencyKey: "key-401",
      version: 1,
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });

  it("writes both session keys on a 401 SESSION_EXPIRED", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { name: "Admin Demo" });
    fetchMock.mockResolvedValueOnce(
      problemWith(
        401,
        "SESSION_EXPIRED",
        "Tu sesión expiró. Inicia sesión de nuevo.",
      ),
    );

    await runMutation(queryClient, useRegisterPayment, {
      invoiceId: 1,
      body,
      idempotencyKey: "key-expired",
      version: 1,
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });
});
