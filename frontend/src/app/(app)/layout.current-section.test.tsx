import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "./layout";

const state = vi.hoisted(() => ({
  pathname: "/",
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  },
}));

// Unlike the other shell tests this mock defines `usePathname`, so the
// current section is derived exactly as in the app.
vi.mock("next/navigation", () => ({
  useRouter: () => state.router,
  usePathname: () => state.pathname,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  state.router.replace.mockClear();
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    if (String(input) === "/api/auth/me") {
      return new Response(
        JSON.stringify({
          id: 1,
          name: "Admin Demo",
          email: "admin@labapp.test",
          role: "admin",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }
    return new Response(null, { status: 404 });
  });
});

function renderShell() {
  return render(
    <QueryClientProvider client={queryClient}>
      <AppLayout>
        <h1 data-testid="app-page-heading">Página</h1>
      </AppLayout>
    </QueryClientProvider>,
  );
}

describe("the current section of the rail", () => {
  const cases = [
    { pathname: "/customers", testId: "app-nav-customers-link", label: "Clientes" },
    { pathname: "/customers/7", testId: "app-nav-customers-link", label: "Clientes" },
    { pathname: "/customers/new", testId: "app-nav-customers-link", label: "Clientes" },
    { pathname: "/orders", testId: "app-nav-orders-link", label: "Pedidos" },
    { pathname: "/products", testId: "app-nav-products-link", label: "Productos" },
    { pathname: "/invoices", testId: "app-nav-invoices-link", label: "Facturas" },
    { pathname: "/settings", testId: "app-nav-settings-link", label: "Configuración" },
  ];

  it("scrolls the current link into view when the pathname changes", async () => {
    // The phone navigation is a single horizontal row (task 038); the
    // shell scrolls the section link into view on every pathname change.
    // jsdom has a no-op scrollIntoView; spy it through a stub and put the
    // original back, the later tests of this file render on the same jsdom.
    const scrollSpy = vi.fn();
    const originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scrollSpy;

    // The first section in the file order: the mount scroll and the
    // navigation scroll both point at a link of this row.
    state.pathname = "/customers";

    const { rerender } = renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    // On mount the current section ("/customers" here) is scrolled into
    // view — also right after the session load makes the nav exist. The
    // `this` of the call is the current link.
    await waitFor(() => {
      expect(scrollSpy).toHaveBeenCalledWith({
        inline: "nearest",
        block: "nearest",
      });
    });
    expect(
      (scrollSpy.mock.instances[0] as HTMLElement).getAttribute("data-testid"),
    ).toBe("app-nav-customers-link");

    // Navigating to another section moves the row to that link.
    scrollSpy.mockClear();
    state.pathname = "/orders";
    rerender(
      <QueryClientProvider client={queryClient}>
        <AppLayout>
          <h1 data-testid="app-page-heading">Página</h1>
        </AppLayout>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(scrollSpy).toHaveBeenCalledWith({
        inline: "nearest",
        block: "nearest",
      });
    });
    expect(
      (scrollSpy.mock.instances[0] as HTMLElement).getAttribute("data-testid"),
    ).toBe("app-nav-orders-link");

    // The pathname change effect also runs for every later navigation;
    // restore the stub's original jsdom implementation for the next
    // tests.
    Element.prototype.scrollIntoView = originalScrollIntoView;
  });

  for (const { pathname, testId } of cases) {
    it(`marks ${pathname} as the current section with aria-current="page"`, async () => {
      state.pathname = pathname;
      renderShell();

      await waitFor(() => {
        expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
      });

      expect(screen.getByTestId(testId)).toHaveAttribute(
        "aria-current",
        "page",
      );
    });
  }

  it("marks exactly one section per pathname", async () => {
    state.pathname = "/customers/7";
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    expect(
      document.querySelectorAll('[aria-current="page"]').length,
    ).toBe(1);
  });

  it("marks no section on the home", async () => {
    state.pathname = "/";
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    expect(
      screen.getByTestId("app-nav-customers-link"),
    ).not.toHaveAttribute("aria-current");
    expect(
      screen.getByTestId("app-nav-orders-link"),
    ).not.toHaveAttribute("aria-current");
    expect(
      screen.getByTestId("app-nav-invoices-link"),
    ).not.toHaveAttribute("aria-current");
  });

  it("does not mark Clientes for a similarly named path", async () => {
    // A shared prefix is not enough: the section boundary is "/", so
    // /customers2 is not the customers section.
    state.pathname = "/customers2";
    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("app-user-name-text")).toBeInTheDocument();
    });

    expect(
      screen.getByTestId("app-nav-customers-link"),
    ).not.toHaveAttribute("aria-current");
  });
});
