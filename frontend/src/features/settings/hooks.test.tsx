import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { SETTINGS_KEY, useSettings, useUpdateTaxRate } from "./hooks";
import type { Settings } from "./types";

const fetchMock = vi.fn();

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

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSettings", () => {
  it("requests GET /api/settings and caches under [\"settings\"]", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ tax_rate: "10.00" }, 200),
    );
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/settings");
    expect(queryClient.getQueryData<Settings>(SETTINGS_KEY)).toEqual({
      tax_rate: "10.00",
    });
  });

  it("keeps the error and does not retry", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        { status: 500, code: "INTERNAL_ERROR", detail: "Fallo." },
        500,
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toMatchObject({
      problem: { status: 500, code: "INTERNAL_ERROR" },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("writes null into the me key on a 401", async () => {
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, {
      id: 1,
      role: "admin",
    });

    fetchMock.mockResolvedValue(
      jsonResponse(
        { status: 401, code: "UNAUTHENTICATED", detail: "Inicia sesión." },
        401,
      ),
    );
    const { result } = renderHook(() => useSettings(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });
});

describe("useUpdateTaxRate", () => {
  it("patches the raw string and stores the answer in [\"settings\"]", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ tax_rate: "7.00" }, 200),
    );
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(SETTINGS_KEY, { tax_rate: "10.00" });

    const { result } = renderHook(() => useUpdateTaxRate(), { wrapper });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    await result.current.mutateAsync("7");

    expect(fetchMock.mock.calls[0]).toEqual([
      "/api/settings",
      expect.objectContaining({ method: "PATCH" }),
    ]);
    expect(
      JSON.parse(String(fetchMock.mock.calls[0]?.[1].body)),
    ).toEqual({ tax_rate: "7" });
    expect(queryClient.getQueryData<Settings>(SETTINGS_KEY)).toEqual({
      tax_rate: "7.00",
    });
  });

  it("invalidates every orders query on success", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ tax_rate: "7.00" }, 200),
    );
    const { queryClient, wrapper } = createWrapper();
    const ordersListKey = ["orders", "list", { page: 1 }];
    const ordersDetailKey = ["orders", "detail", 8];
    queryClient.setQueryData(ordersListKey, { note: "list" });
    queryClient.setQueryData(ordersDetailKey, { note: "detail" });
    queryClient.setQueryData(["customers"], { note: "customers" });

    const { result } = renderHook(() => useUpdateTaxRate(), { wrapper });
    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    await result.current.mutateAsync("7.5");

    await waitFor(() => {
      expect(
        queryClient.getQueryState(ordersListKey)?.isInvalidated,
      ).toBe(true);
      expect(
        queryClient.getQueryState(ordersDetailKey)?.isInvalidated,
      ).toBe(true);
    });
    expect(
      queryClient.getQueryState(["customers"])?.isInvalidated,
    ).toBe(false);
  });

  it("keeps the settings on an error and writes null into me on a 401", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        { status: 401, code: "UNAUTHENTICATED", detail: "Inicia sesión." },
        401,
      ),
    );
    const { queryClient, wrapper } = createWrapper();
    const oldSettings: Settings = { tax_rate: "10.00" };
    queryClient.setQueryData(SETTINGS_KEY, oldSettings);
    queryClient.setQueryData(ME_QUERY_KEY, { id: 1, role: "admin" });

    const { result } = renderHook(() => useUpdateTaxRate(), { wrapper });
    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    await expect(result.current.mutateAsync("7")).rejects.toMatchObject({
      problem: { status: 401 },
    });

    expect(queryClient.getQueryData<Settings>(SETTINGS_KEY))
      .toEqual(oldSettings);
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });
});
