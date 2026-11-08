import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "@/features/auth/session";
import type { ApiRequestError } from "@/lib/api";
import {
  PRODUCTS_KEY,
  orderDetailKey,
  ordersListQueryKey,
  useAddLine,
  useCreateOrder,
  useOrder,
  useOrderTransition,
  useOrders,
  useProducts,
  useRemoveLine,
  useSetLineQuantity,
  useSetOrderCustomer,
} from "./hooks";
import type { Order } from "./types";

const fetchMock = vi.fn();

/** The literal Order of the corrected spec (S5). */
const order: Order = {
  id: 8,
  number: "PED-0008",
  status: "draft",
  customer: { id: 1, name: "Acme Industrial S.A.", status: "active" },
  lines: [
    {
      id: 10,
      product_id: 1,
      sku: "KB-100",
      name: "Teclado USB",
      quantity: 2,
      unit_price: "19.90",
      line_total: "39.80",
    },
  ],
  subtotal: "39.80",
  tax_rate: "10.00",
  tax: "3.98",
  total: "43.78",
  invoice_id: null,
  version: 2,
  created_at: "2026-11-05T15:00:00Z",
  updated_at: "2026-11-05T15:01:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function problemResponse(status: number, code: string, detail: string) {
  return jsonResponse({ status, code, detail }, status);
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

async function runMutation<TVars>(
  queryClient: QueryClient,
  hook: () => UseMutationResult<Order, ApiRequestError, TVars>,
  variables: TVars,
): Promise<void> {
  const { result } = renderHook(hook, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  });
  act(() => {
    result.current.mutate(variables);
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

describe("the orders query keys", () => {
  it("names every list entry with page, q and status", () => {
    expect(ordersListQueryKey({ page: 2, q: "ped", status: "confirmed" })).toEqual(
      ["orders", "list", { page: 2, q: "ped", status: "confirmed" }],
    );
    // An empty q never splits the cache.
    expect(ordersListQueryKey({ page: 1, q: "" })).toEqual([
      "orders",
      "list",
      { page: 1, q: undefined, status: undefined },
    ]);
  });

  it("carries the id as a number", () => {
    expect(orderDetailKey(8)).toEqual(["orders", "detail", 8]);
  });
});

describe("useOrders and useOrder", () => {
  it("fetches the list with the built url", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], page: 1, page_size: 20, total: 0 }),
    );

    const { result } = renderHook(
      () => useOrders({ page: 2, q: "ped", status: "confirmed" }),
      createWrapper(),
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/orders?page=2&q=ped&status=confirmed",
    );
  });

  it("updates the detail from the cache without a second fetch", async () => {
    fetchMock.mockResolvedValue(jsonResponse(order));

    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useOrder(8), { wrapper });

    await waitFor(() => expect(result.current.data).toMatchObject({ version: 2 }));
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // The mutation answer written with setQueryData must be the same
    // entry: the read of the screen follows without reloading.
    queryClient.setQueryData(orderDetailKey(8), { ...order, version: 3 });
    await waitFor(() => expect(result.current.data?.version).toBe(3));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("fetches the product catalog once under ['products']", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [{ id: 1, sku: "KB-100", name: "Teclado USB", price: "19.90", stock: 120 }],
      }),
    );

    const { result } = renderHook(() => useProducts(), createWrapper());

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/products");
  });
});

describe("the orders mutations", () => {
  it("creates a draft and writes the detail, invalidating the list", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(
      ordersListQueryKey({ page: 1 }),
      { items: [], page: 1, page_size: 20, total: 0 },
    );
    fetchMock.mockResolvedValueOnce(jsonResponse(order, 201));

    await runMutation(queryClient, useCreateOrder, 1);

    expect(fetchMock.mock.calls[0]).toEqual([
      "/api/orders",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ customer_id: 1 }),
      }),
    ]);
    expect(queryClient.getQueryData(orderDetailKey(8))).toMatchObject({
      version: 2,
    });
    // The seeded list query is marked invalidated.
    expect(
      queryClient.getQueryCache().getAll()
        .some((query) => query.state.isInvalidated
          && query.queryKey[0] === "orders"),
    ).toBe(true);
  });

  it("changes the customer and keeps a same-value answer working (S4)", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(orderDetailKey(8), order);
    // Same customer, same version: the server answers 200 untouched.
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await runMutation(queryClient, useSetOrderCustomer, {
      id: 8,
      body: { customer_id: 1, version: 2 },
    });

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/orders/8");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({ customer_id: 1, version: 2 }),
    );
    expect(queryClient.getQueryData(orderDetailKey(8))).toMatchObject({
      version: 2,
    });
  });

  it("adds a line and stores the returned order", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(jsonResponse(order, 201));

    await runMutation(queryClient, useAddLine, {
      id: 8,
      body: { product_id: 1, quantity: 2, version: 2 },
    });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/orders/8/lines");
    expect(queryClient.getQueryData(orderDetailKey(8))).toMatchObject({
      version: 2,
    });
  });

  it("changes a line quantity with the version at click time", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await runMutation(queryClient, useSetLineQuantity, {
      id: 8,
      lineId: 10,
      body: { quantity: 3, version: 2 },
    });

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/orders/8/lines/10");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ quantity: 3, version: 2 }));
  });

  it("removes a line with DELETE and If-Match", async () => {
    const { queryClient } = createWrapper();
    fetchMock.mockResolvedValueOnce(jsonResponse(order));

    await runMutation(queryClient, useRemoveLine, {
      id: 8,
      lineId: 10,
      version: 2,
    });

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/orders/8/lines/10");
    expect(init.method).toBe("DELETE");
    expect(init.headers).toMatchObject({ "If-Match": '"2"' });
  });

  it("invalidates the products for confirm and cancel, not for ship", async () => {
    for (const [action, productsInvalidated] of [
      ["confirm", true],
      ["cancel", true],
      ["ship", false],
    ] as const) {
      const { queryClient } = createWrapper();
      queryClient.setQueryData(PRODUCTS_KEY, { items: [] });
      fetchMock.mockResolvedValueOnce(jsonResponse(order));

      await runMutation(queryClient, useOrderTransition, {
        id: 8,
        action,
        version: 2,
      });

      const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(path).toBe(`/api/orders/8/${action}`);
      expect(init.method).toBe("POST");
      expect(init.headers).toMatchObject({ "If-Match": '"2"' });

      const productsQuery = queryClient
        .getQueryCache()
        .getAll()
        .find((query) => query.queryKey[0] === "products");
      expect(Boolean(productsQuery?.state.isInvalidated)).toBe(
        productsInvalidated,
      );
      if (!productsInvalidated) {
        // The ship answer leaves the stock untouched: no fetch of
        // /api/products has any reason to run.
        expect(productsQuery?.state.data).toEqual({ items: [] });
      }

      fetchMock.mockReset();
    }
  });
});

describe("the 401 of the orders endpoints", () => {
  it("writes null into the session cache entry", async () => {
    fetchMock.mockResolvedValueOnce(
      problemResponse(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );

    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { name: "Admin Demo" });
    const { result } = renderHook(() => useOrder(8), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });

  it("writes both session keys on a 401 SESSION_EXPIRED", async () => {
    fetchMock.mockResolvedValueOnce(
      problemResponse(
        401,
        "SESSION_EXPIRED",
        "Tu sesión expiró. Inicia sesión de nuevo.",
      ),
    );

    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { name: "Admin Demo" });
    const { result } = renderHook(() => useOrder(8), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });

  it("does the same for a failed mutation", async () => {
    const { queryClient } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { name: "Admin Demo" });
    fetchMock.mockResolvedValueOnce(
      problemResponse(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );

    const { result } = renderHook(() => useOrderTransition(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      ),
    });
    act(() => {
      result.current.mutate({ id: 8, action: "confirm", version: 2 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });
});
