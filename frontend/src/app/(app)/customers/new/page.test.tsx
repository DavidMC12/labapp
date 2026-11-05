import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomerNewPage from "./page";

const state = vi.hoisted(() => ({
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => state.router,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

/** Who the mocked /api/auth/me answers. */
let meUser: Record<string, unknown> | null;
let meStatus: number;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  meUser = { id: 1, name: "Admin Demo", email: "admin@labapp.test", role: "admin" };
  meStatus = 200;
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/me") {
      return jsonResponse(meUser, meStatus);
    }
    return jsonResponse({}, 404);
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the create customer page", () => {
  it("renders the create form", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <CustomerNewPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Nuevo cliente" }))
        .toHaveAttribute("data-testid", "customers-form-heading");
    });
    expect(screen.getByTestId("customers-form-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("customers-form-cancel-link")).toHaveAttribute(
      "href",
      "/customers",
    );
  });

  it("shows a busy status while the session loads", () => {
    fetchMock.mockImplementation(
      () => new Promise<Response>(() => {}),
    );

    render(
      <QueryClientProvider client={queryClient}>
        <CustomerNewPage />
      </QueryClientProvider>,
    );

    const status = screen.getByTestId("customers-form-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("shows only the permission alert for finance", async () => {
    meUser = { id: 3, name: "Finanzas Demo", email: "finance@labapp.test", role: "finance" };

    render(
      <QueryClientProvider client={queryClient}>
        <CustomerNewPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-forbidden-alert")).toHaveTextContent(
        "No tienes permiso para realizar esta acción.",
      );
    });
    expect(screen.queryByTestId("customers-form-heading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("customers-form-name-input")).not.toBeInTheDocument();
  });

  it("shows only the permission alert for readonly", async () => {
    meUser = { id: 4, name: "Solo Lectura Demo", email: "readonly@labapp.test", role: "readonly" };

    render(
      <QueryClientProvider client={queryClient}>
        <CustomerNewPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("customers-form-forbidden-alert")).toBeInTheDocument();
    });
  });
});
