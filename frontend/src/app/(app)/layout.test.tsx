import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "./layout";import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { SESSION_EXPIRED_QUERY_KEY } from "@/features/auth/session";

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

  it("redirects to /login?expired=1 when the session expired", async () => {
    // The session request never runs: the stale me entry and the flag
    // raised by noteUnauthorized are already in the cache.
    queryClient.setQueryData(
      SESSION_EXPIRED_QUERY_KEY,
      true,
    );
    queryClient.setQueryData(ME_QUERY_KEY, null);

    renderShell();

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/login?expired=1");
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
      // The catalog is read-only and open to every role (docs/SPEC.md
      // section 5), so the link never hides.
      expect(screen.getByTestId("app-nav-products-link")).toHaveAttribute(
        "href",
        "/products",
      );
      expect(screen.getByTestId("app-nav-invoices-link")).toHaveAttribute(
        "href",
        "/invoices",
      );
      // The settings screen exists for every role (the form inside is
      // what hides for the non-admin roles).
      expect(screen.getByTestId("app-nav-settings-link")).toHaveAttribute(
        "href",
        "/settings",
      );
      expect(
        screen.getByRole("link", { name: "Configuración" }),
      ).toHaveAttribute("href", "/settings");
      expect(screen.getByRole("navigation", { name: "Principal" }))
        .toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: "Clientes" }),
      ).toHaveAttribute("href", "/customers");
      expect(
        screen.getByRole("link", { name: "Pedidos" }),
      ).toHaveAttribute("href", "/orders");
      expect(
        screen.getByRole("link", { name: "Productos" }),
      ).toHaveAttribute("href", "/products");
      expect(
        screen.getByRole("link", { name: "Facturas" }),
      ).toHaveAttribute("href", "/invoices");
    });
  }
});

describe("the skip link and the landmarks of the shell", () => {
  beforeEach(async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );
  });

  it("puts the skip link first in the tab order, with the target ready", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    const skipLink = screen.getByTestId("app-skip-link");
    expect(skipLink).toHaveTextContent("Saltar al contenido");
    expect(skipLink).toHaveAttribute("href", "#main-content");

    // First focusable element: the first Tab of a fresh page reaches it.
    const user = userEvent.setup();
    await user.tab();
    expect(document.activeElement).toBe(skipLink);

    // The screen content is one heading further, not the brand or the nav.
    await user.tab();
    expect(document.activeElement).not.toBe(skipLink);
    expect(document.activeElement).toHaveAttribute("data-testid",
      "app-nav-home-link");
  });

  it("gives the main landmark the id the link points at", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    const main = document.querySelector("main");
    expect(main).not.toBeNull();
    expect(main).toHaveAttribute("id", "main-content");
    expect(main).toHaveAttribute("tabindex", "-1");

    // The shell keeps its navigation landmark.
    expect(
      screen.getByRole("navigation", { name: "Principal" }),
    ).toBeInTheDocument();
  });
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

describe("the shell navigation row", () => {
  it("scrolls the phone row in one line instead of wrapping it", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-nav-customers-link")).toBeInTheDocument();
    });

    const nav = screen.getByRole("navigation", { name: "Principal" });

    // One horizontal line on a phone inside its own scroll container,
    // with the right-edge fade as the affordance; the rail keeps its
    // column from md up (task 038).
    expect(nav.className).not.toContain("flex-wrap");
    expect(nav.className).toContain("overflow-x-auto");
    expect(nav.className).toContain("md:flex-col");
    expect(nav.className).toContain("md:overflow-x-visible");
    // The fade is the div after the nav, over its right edge.
    const fade = nav.parentElement?.querySelector('div[aria-hidden="true"]');
    expect(fade?.className).toContain("bg-linear-to-r");
    expect(fade?.className).toContain("md:hidden");
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

describe("the phone shell layout", () => {
  beforeEach(async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );
  });

  it("keeps the focusable order of the shell unchanged", async () => {
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    // The wrappers of the phone layout (task 038) add no focusable
    // element: the tab order keeps the DOM order of the shell.
    const focusables = [
      ...(document.querySelectorAll("a[href], button, select") as NodeListOf<
        Element
      >),
    ];
    expect(
      focusables.map((element) => element.getAttribute("data-testid")),
    ).toEqual([
      "app-skip-link",
      "app-nav-home-link",
      "app-nav-customers-link",
      "app-nav-orders-link",
      "app-nav-products-link",
      "app-nav-invoices-link",
      "app-nav-settings-link",
      "app-theme-select",
      "app-logout-button",
    ]);
  });

  it("keeps the label of the theme select accessible on the phone", async () => {
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-theme-select")).toBeInTheDocument();
    });

    // Hidden visually on the phone, in the DOM as sr-only; from md up
    // the visible label of the rail comes back with its color.
    const label = screen.getByText("Tema");
    expect(label).toHaveClass("sr-only", "md:not-sr-only", "text-rail-ink");
    expect(
      screen.getByRole("combobox", { name: "Tema" }),
    ).toBeInTheDocument();
  });

  it("sizes the theme select to its content on the phone", async () => {
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-theme-select")).toBeInTheDocument();
    });

    const select = screen.getByTestId("app-theme-select");
    expect(select).toHaveClass("w-auto", "md:w-full");
    expect(select).not.toHaveClass("w-full");
  });

  it("keeps the desktop rail classes with the phone as the base", async () => {
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    // The rail: grid at md, sticky full-height aside.
    const rail = document.querySelector("aside");
    expect(rail?.className).toContain("md:sticky");
    expect(rail?.className).toContain("md:h-screen");
    expect(rail?.parentElement?.className).toContain(
      "md:grid-cols-[212px_minmax(0,1fr)]",
    );

    // The rows of the rail, top to bottom: brand (phone py-2, desktop
    // pt-4 pb-3), navigation column, user block, logout full width.
    expect(rail?.firstElementChild?.className).toContain("py-2");
    expect(rail?.firstElementChild?.className).toContain("md:pt-4");
    expect(rail?.firstElementChild?.className).toContain("md:pb-3");

    // The wrapper of the user name and the role reads as its children
    // again in the desktop column.
    const knownUserBlock = screen.getByTestId(
      "app-user-role-text",
    ).parentElement;
    expect(knownUserBlock).toHaveClass("md:contents");
    const userBlock = knownUserBlock?.parentElement;
    expect(userBlock?.className).toContain("md:mt-auto");
    expect(userBlock?.className).toContain("md:flex-col");
    expect(userBlock?.className).toContain("md:items-stretch");
    expect(userBlock?.className).toContain("md:border-t");

    // The theme select of the rail keeps filling its column from md up;
    // the label block is plain there (md:w-auto undoes no phone class).
    const themeWrapper = screen
      .getByTestId("app-theme-select")
      .closest('[class*="md:w-auto"]');
    expect(themeWrapper).not.toBeNull();
    expect(themeWrapper?.className).toContain("md:w-auto");

    expect(screen.getByTestId("app-logout-button")).toHaveClass(
      "md:ml-0",
      "md:w-full",
    );
  });
});

describe("app shell logout re-entry", () => {
  it("ignores a second logout while the first POST /logout is pending", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(userPayload("admin", "admin@labapp.test"), 200,
        "application/json"),
    );
    const heldLogout = new Promise<Response>(() => {});
    fetchMock.mockReturnValueOnce(heldLogout);

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    const button = screen.getByTestId("app-logout-button");
    await userEvent.setup().click(button);
    const logoutCalls = () =>
      fetchMock.mock.calls.filter(([input, init]) =>
        String(input) === "/api/auth/logout"
        && String((init as RequestInit | undefined)?.method) === "POST");
    await waitFor(() => expect(logoutCalls()).toHaveLength(1));

    // While the request runs the button shows its loading state; a click
    // dispatched to it anyway is ignored by the handler guard.
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(button).toHaveAttribute("data-state", "loading");
    expect(logoutCalls()).toHaveLength(1);
  });
});
