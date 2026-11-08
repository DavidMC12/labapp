import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "./(app)/layout";
import LoginPage from "./login/page";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import type { User } from "@/features/auth/types";

const { routerMock } = vi.hoisted(() => ({
  routerMock: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const fetchMock = vi.fn();

const adminUser: User = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
};

let queryClient: QueryClient;

function renderWithClient(ui: React.ReactElement) {
  render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function problemResponse(status: number, code: string, detail: string) {
  return new Response(
    JSON.stringify({ status, code, detail }),
    {
      status,
      headers: { "content-type": "application/problem+json" },
    },
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  routerMock.replace.mockClear();
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the whole 401 to login to shell sequence", () => {
  it("visits the shell, gets a 401, lands on the login, logs in and reaches the shell without being sent back", async () => {
    // Step 1: visit the app shell without a session; useMe resolves to null.
    fetchMock.mockResolvedValueOnce(
      problemResponse(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );
    renderWithClient(
      <AppLayout>
        <h1 data-testid="app-page-heading">Página</h1>
      </AppLayout>,
    );

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/login");
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Step 2: land on the login page and log in successfully.
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(adminUser), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    renderWithClient(<LoginPage />);
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("auth-login-email-input"),
      "admin@labapp.test",
    );
    await user.type(
      screen.getByTestId("auth-login-password-input"),
      "Demo-LabApp-2026!",
    );
    await user.click(screen.getByTestId("auth-login-submit-button"));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/");
    });
    // The user was written into the cache before the navigation.
    expect(queryClient.getQueryData(ME_QUERY_KEY)).toEqual(adminUser);

    // Step 3: reach the shell with the cached session; the client-side
    // navigation keeps the provider tree, so no me request runs, and the
    // shell must not bounce back to the login.
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    queryClient.setQueryData(ME_QUERY_KEY, adminUser);
    routerMock.replace.mockClear();
    // The fresh shell revalidates the session in the background; the real
    // API answers 200 with the user, so it does not bounce back.
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(adminUser), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    renderWithClient(
      <AppLayout>
        <h1 data-testid="app-page-heading">Página</h1>
      </AppLayout>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toHaveTextContent(
        "Admin Demo",
      );
    });
    expect(screen.getByTestId("app-user-role-text")).toHaveTextContent(
      "Admin",
    );
    expect(routerMock.replace).not.toHaveBeenCalledWith("/login");
  });
});
