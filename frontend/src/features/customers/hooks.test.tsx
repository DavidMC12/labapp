import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "@/features/auth/session";
import type { User } from "@/features/auth/types";
import {
  CUSTOMERS_LIST_KEY,
  customerDetailKey,
  customersListQueryKey,
  useCreateCustomer,
  useCustomer,
  useCustomers,
  useSetCustomerStatus,
  useUpdateCustomer,
} from "./hooks";
import type { Customer, CustomerList } from "./types";

const fetchMock = vi.fn();

/** A customer as the API returns it (seed customer 4). */
const customer: Customer = {
  id: 4,
  name: "Distribuidora Delta",
  email: "delta@example.test",
  phone: "+34 910 000 004",
  tax_id: "DELT-700789",
  address: "Calle Mayor 45",
  status: "active",
  version: 2,
  created_at: "2026-01-01T09:04:00Z",
  updated_at: "2026-01-02T10:00:00Z",
};

const listPage: CustomerList = {
  items: [customer],
  page: 1,
  page_size: 20,
  total: 1,
};

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

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status });
}

function problem(status: number, code: string, detail: string): Response {
  return jsonResponse({ status, code, detail }, status);
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useCustomers", () => {
  it("requests the exact list url and caches under the param key", async () => {
    fetchMock.mockResolvedValue(jsonResponse(listPage, 200));
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(
      () => useCustomers({ page: 5, q: "R&D", status: "inactive" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers?page=5&q=R%26D&status=inactive");
    expect(init.method).toBe("GET");

    expect(queryClient.getQueryData(customersListQueryKey({
      page: 5,
      q: "R&D",
      status: "inactive",
    }))).toEqual(listPage);
  });

  it("uses one shared entry for repeated renders of the same params", async () => {
    fetchMock.mockResolvedValue(jsonResponse(listPage, 200));
    const { queryClient, wrapper } = createWrapper();
    renderHook(
      () =>
        useCustomers({ page: 1, q: undefined, status: undefined }),
      { wrapper },
    );
    renderHook(() => useCustomers({ page: 1 }), { wrapper });

    await waitFor(
      () => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(1),
    );
    await act(async () => {});
    // Both hooks share the key `["customers","list",{page:1}]`; an empty
    // status would otherwise be `status: undefined` in one call and a
    // missing member in the other.
    expect(
      queryClient
        .getQueryCache()
        .findAll({ queryKey: CUSTOMERS_LIST_KEY })
        .filter((query) => query.state.data !== undefined),
    ).toHaveLength(1);
  });

  it("does not retry a failed request", async () => {
    fetchMock.mockResolvedValue(problem(500, "INTERNAL_ERROR", "fallo"));
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useCustomers({ page: 1 }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect((result.current.error as { problem: { code: string } }).problem.code)
      .toBe("INTERNAL_ERROR");
  });
});

describe("useCustomer", () => {
  it("requests GET /api/customers/{id} and caches under a numeric id", async () => {
    fetchMock.mockResolvedValue(jsonResponse(customer, 200));
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useCustomer(7), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const [path] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers/7");

    // The key entry carries the number, not the string of the route.
    expect(queryClient.getQueryData(customerDetailKey(7))).toEqual(customer);
    expect(
      queryClient.getQueryData(["customers", "detail", "7"]),
    ).toBeUndefined();
  });
});

describe("useCreateCustomer", () => {
  it("posts the body and seeds the detail cache before navigating", async () => {
    const created: Customer = { ...customer, id: 11, version: 1 };
    fetchMock.mockResolvedValue(jsonResponse(created, 201));
    const { queryClient, wrapper } = createWrapper();
    // A pre-existing list entry so the invalidation is observable.
    const referenceKey = customersListQueryKey({ page: 1 });
    queryClient.setQueryData(referenceKey, listPage);
    const { result } = renderHook(() => useCreateCustomer(), { wrapper });

    await act(async () => {
      const saved = await result.current.mutateAsync({
        name: "Nueva Ultramarinos",
        email: "nueva@example.test",
        phone: null,
        tax_id: null,
        address: null,
      });
      // The detail entry is already written when the mutation resolves,
      // i.e. before the caller navigates.
      expect(queryClient.getQueryData(customerDetailKey(saved.id))).toEqual(
        created,
      );
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      name: "Nueva Ultramarinos",
      email: "nueva@example.test",
      phone: null,
      tax_id: null,
      address: null,
    });
    expect(queryClient.getQueryState(referenceKey)?.isInvalidated).toBe(true);
  });
});

describe("useUpdateCustomer", () => {
  it("patches the fields with the captured version and refreshes the detail cache", async () => {
    fetchMock.mockResolvedValue(jsonResponse(customer, 200));
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useUpdateCustomer(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 7,
        body: {
          name: "Distribuidora Delta",
          email: "delta@example.test",
          phone: "+34 910 000 004",
          tax_id: "DELT-700789",
          address: null,
          version: 2,
        },
      });
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calls = [
      fetchMock.mock.calls[0] as [string, RequestInit],
    ];
    expect(calls[0][0]).toBe("/api/customers/7");
    expect(calls[0][1].method).toBe("PATCH");
    expect(JSON.parse(calls[0][1].body as string)).toMatchObject({
      version: 2,
      address: null,
    });
    expect(queryClient.getQueryData(customerDetailKey(7))).toEqual(customer);
  });
});

describe("useSetCustomerStatus", () => {
  it("posts the transition with a quoted If-Match and updates the detail cache", async () => {
    const updated: Customer = { ...customer, status: "inactive", version: 3 };
    fetchMock.mockResolvedValue(jsonResponse(updated, 200));
    const { queryClient, wrapper } = createWrapper();
    // A pre-existing list entry so the invalidation is observable.
    const referenceKey = customersListQueryKey({ page: 1 });
    queryClient.setQueryData(referenceKey, listPage);
    const { result } = renderHook(() => useSetCustomerStatus(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 4,
        action: "deactivate",
        version: 2,
      });
    });

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/customers/4/deactivate");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["If-Match"]).toBe('"2"');

    // The screen changes without reloading: the cached detail is the
    // returned customer, keyed by the numeric id.
    expect(queryClient.getQueryData(customerDetailKey(4))).toEqual(updated);
    expect(queryClient.getQueryState(referenceKey)?.isInvalidated).toBe(true);
  });

  it("sends the version that was given, not one captured later", async () => {
    fetchMock.mockResolvedValue(jsonResponse(customer, 200));
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSetCustomerStatus(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        id: 4,
        action: "reactivate",
        version: 5,
      });
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["If-Match"]).toBe('"5"');
    expect((fetchMock.mock.calls[0] as [string])[0]).toBe(
      "/api/customers/4/reactivate",
    );
  });
});

describe("the 401 handling of the customers hooks", () => {
  it("writes null into the auth me entry when a customers query gets a 401", async () => {
    fetchMock.mockResolvedValue(
      problem(401, "SESSION_EXPIRED", "Tu sesión expiró. Inicia sesión de nuevo."),
    );
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { id: 1 } as User);
    const { result } = renderHook(() => useCustomers({ page: 1 }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });

  it("writes both session keys on a 401 SESSION_EXPIRED", async () => {
    fetchMock.mockResolvedValue(
      problem(
        401,
        "SESSION_EXPIRED",
        "Tu sesión expiró. Inicia sesión de nuevo.",
      ),
    );
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { id: 1 } as User);
    const { result } = renderHook(() => useCustomers({ page: 1 }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });

  it("writes null into the auth me entry when a mutation gets a 401", async () => {
    fetchMock.mockResolvedValue(
      problem(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, { id: 1 } as User);
    const { result } = renderHook(() => useCreateCustomer(), { wrapper });

    await act(async () => {
      await expect(
        result.current.mutateAsync({
          name: "Nueva Ultramarinos",
          email: "nueva@example.test",
          phone: null,
          tax_id: null,
          address: null,
        }),
      ).rejects.toBeTruthy();
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });
});
