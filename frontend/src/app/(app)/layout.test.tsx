import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "./layout";

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
  // "/": no section is current for the shell behavior tests.
  usePathname: () => "/",
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

function jsonResponse(
  body: string,
  status: number,
  contentType = "application/problem+json",
) {
  return new Response(body, {
    status,
    headers: { "content-type": contentType },
  });
}

function problemResponse(status: number, code: string, detail: string) {
  return jsonResponse(
    JSON.stringify({ status, code, detail }),
    status,
  );
}

function userPayload(role: string, email: string) {
  return JSON.stringify({
    id: 1,
    name: "Admin Demo",
    email,
    role,
  });
}

function renderShell() {
  render(
    <QueryClientProvider client={queryClient}>
      <AppLayout>
        <h1 data-testid="app-page-heading">Página</h1>
      </AppLayout>
    </QueryClientProvider>,
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

describe("app shell states", () => {
  it("shows a busy status element while the session loads", async () => {
    fetchMock.mockReturnValueOnce(new Promise<Response>(() => {}));

    renderShell();

    const status = screen.getByTestId("app-shell-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
  });

  it("redirects without a session", async () => {
    fetchMock.mockResolvedValueOnce(
      problemResponse(401, "UNAUTHENTICATED", "Inicia sesión para continuar."),
    );

    renderShell();

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/login");
    });
  });

  it("shows the error detail with retry for a failure other than 401", async () => {
    fetchMock.mockResolvedValue(
      problemResponse(
        500,
        "INTERNAL_ERROR",
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      ),
    );
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-shell-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });

    // Retry succeeds this time.
    fetchMock.mockResolvedValueOnce(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );

    await userEvent.setup().click(
      screen.getByTestId("app-shell-retry-button"),
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toHaveTextContent(
        "Admin Demo",
      );
    });
  });

  it("shows the error alert with retry when a 2xx answer is not JSON", async () => {
    // A proxy serves its own HTML with status 200; the session cannot be
    // read, so the shell must not fall through to a blank page.
    fetchMock.mockResolvedValue(
      new Response("<html>fallback</html>", {
        status: 200,
        headers: { "content-type": "text/html" },
      }),
    );

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-shell-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("app-shell-retry-button")).toBeInTheDocument();
  });
});

describe("app shell session", () => {
  const cases = [
    { role: "admin", email: "admin@labapp.test", label: "Admin" },
    { role: "sales", email: "sales@labapp.test", label: "Ventas" },
    { role: "finance", email: "finance@labapp.test", label: "Finanzas" },
    { role: "readonly", email: "readonly@labapp.test", label: "Solo lectura" },
  ] as const;

  for (const { role, email, label } of cases) {
    it(`shows the user and the navigation for ${label}`, async () => {
      fetchMock.mockResolvedValue(
        jsonResponse(userPayload(role, email), 200, "application/json"),
      );

      renderShell();

      await waitFor(() => {
        expect(screen.getByTestId("app-user-name-text")).toHaveTextContent(
          "Admin Demo",
        );
      });

      expect(screen.getByTestId("app-user-role-text")).toHaveTextContent(
        label,
      );

      expect(screen.getByTestId("app-nav-home-link")).toHaveAttribute(
        "href",
        "/",
      );
      expect(screen.getByTestId("app-nav-customers-link")).toHaveAttribute(
        "href",
        "/customers",
      );
      expect(screen.getByTestId("app-nav-orders-link")).toHaveAttribute(
        "href",
        "/orders",
      );
      expect(screen.getByTestId("app-nav-invoices-link")).toHaveAttribute(
        "href",
        "/invoices",
      );
      expect(screen.getByRole("navigation", { name: "Principal" }))
        .toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Clientes" }),
      ).toHaveAttribute("href", "/customers");
      expect(
        screen.getByRole("link", { name: "Pedidos" }),
      ).toHaveAttribute("href", "/orders");
      expect(
        screen.getByRole("link", { name: "Facturas" }),
      ).toHaveAttribute("href", "/invoices");
    });
  }
});

describe("app shell logout", () => {
  it("logs out, goes to /login and clears the cache", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    // What the mocked router never unmounts, the shell refetches; keep it
    // pending so the emptied cache stays stable.
    fetchMock.mockReturnValueOnce(new Promise<Response>(() => {}));

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });
    expect(queryClient.getQueryData(["auth", "me"])).toMatchObject({
      role: "admin",
    });

    await userEvent.setup().click(screen.getByTestId("app-logout-button"));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/login");
    });
    expect(
      queryClient
        .getQueryCache()
        .getAll()
        .every((query) => query.state.data === undefined),
    ).toBe(true);
  });

  it("goes to /login and clears the cache even when the logout request fails", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    fetchMock.mockReturnValueOnce(new Promise<Response>(() => {}));

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("app-logout-button"));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/login");
    });
    expect(
      queryClient
        .getQueryCache()
        .getAll()
        .every((query) => query.state.data === undefined),
    ).toBe(true);
  });
});

describe("app shell theme", () => {
  it("offers the Tema control in the rail user block", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );

    renderShell();

    const select = await screen.findByTestId(
      "app-theme-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("system");

    const options = [...select.options].map((option) => option.textContent);
    expect(options).toEqual(["Sistema", "Claro", "Oscuro"]);

    // One DOM instance only: responsive CSS moves it between the rail
    // block and the phone layout, and the browser audit counts ids.
    expect(screen.getAllByTestId("app-theme-select")).toHaveLength(1);
    expect(screen.getByText("Tema")).toHaveClass("text-rail-ink");
  });

  it("applies and stays with the stored choice after hydration", async () => {
    window.localStorage.setItem("labapp-theme", "dark");
    fetchMock.mockResolvedValue(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );

    renderShell();

    await waitFor(() => {
      expect(
        (screen.getByTestId("app-theme-select") as HTMLSelectElement).value,
      ).toBe("dark");
    });
    expect(document.documentElement.getAttribute("data-theme")).toBe(null);
  });
});
