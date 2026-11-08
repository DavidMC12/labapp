import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY, useLogin, useLogout, useMe } from "./hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "./session";
import type { User } from "./types";

const fetchMock = vi.fn();
const adminUser: User = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
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

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useMe", () => {
  it("resolves to the user", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(adminUser), { status: 200 }),
    );
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useMe(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(adminUser);
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(adminUser);
  });

  it("resolves to null on a 401", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 401,
          code: "UNAUTHENTICATED",
          detail: "Inicia sesión para continuar.",
        }),
        { status: 401 },
      ),
    );
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useMe(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
  });

  it("records the expired flag on a 401 SESSION_EXPIRED", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 401,
          code: "SESSION_EXPIRED",
          detail: "Tu sesión expiró. Inicia sesión de nuevo.",
        }),
        { status: 401 },
      ),
    );
    const { queryClient, wrapper } = createWrapper();
    const { result } = renderHook(() => useMe(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY)).toBe(true);
  });

  it("stays in error state for a failure other than a 401", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 500,
          code: "INTERNAL_ERROR",
          detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
        }),
        { status: 500 },
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useMe(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));

    const error = result.current.error;
    expect(error).toBeInstanceOf(Error);
    expect((error as { problem: { code: string } }).problem.code).toBe(
      "INTERNAL_ERROR",
    );
  });
});

describe("useLogin", () => {
  it("posts the trimmed credentials and caches the user", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(adminUser), { status: 200 }),
    );
    const { queryClient, wrapper } = createWrapper();
    // The cache holds a stale null from a former 401.
    queryClient.setQueryData(ME_QUERY_KEY, null);
    const { result } = renderHook(() => useLogin(), { wrapper });

    let onSuccessRan = false;
    await act(async () => {
      const user = await result.current.mutateAsync({
        email: "admin@labapp.test",
        password: "Demo-LabApp-2026!",
      });
      onSuccessRan = user.id === adminUser.id;
    });

    expect(onSuccessRan).toBe(true);
    // The cache was updated synchronously with the success, before any page
    // navigation: the value is no longer the stale null.
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(adminUser);

    const [, init] = fetchMock.mock.calls[0] as [
      string,
      { method: string; body: string },
    ];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      email: "admin@labapp.test",
      password: "Demo-LabApp-2026!",
    });
  });

  it("clears the expired-session flag on success", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(adminUser), { status: 200 }),
    );
    const { queryClient, wrapper } = createWrapper();
    // A former expired session left the flag behind.
    queryClient.setQueryData(SESSION_EXPIRED_QUERY_KEY, true);
    const { result } = renderHook(() => useLogin(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        email: "admin@labapp.test",
        password: "Demo-LabApp-2026!",
      });
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(adminUser);
    expect(queryClient.getQueryData(SESSION_EXPIRED_QUERY_KEY))
      .toBeUndefined();
  });

  it("rejects with the problem document", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 401,
          code: "INVALID_CREDENTIALS",
          detail: "Email o contraseña incorrectos.",
        }),
        { status: 401 },
      ),
    );
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper });

    await act(async () => {
      await expect(
        result.current.mutateAsync({
          email: "admin@labapp.test",
          password: "wrong",
        }),
      ).rejects.toMatchObject({
        name: "ApiRequestError",
        problem: { code: "INVALID_CREDENTIALS" },
      });
    });
    expect(result.current.isError).toBe(true);
  });
});

describe("useLogout", () => {
  it("clears the cache on success", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, adminUser);
    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeUndefined();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("clears the cache even when the answer is a failure", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 500,
          code: "INTERNAL_ERROR",
          detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
        }),
        { status: 500 },
      ),
    );
    const { queryClient, wrapper } = createWrapper();
    queryClient.setQueryData(ME_QUERY_KEY, adminUser);
    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      await expect(result.current.mutateAsync()).rejects.toBeTruthy();
    });

    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});
