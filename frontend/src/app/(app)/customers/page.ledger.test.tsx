import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomersPage from "./page";
import type { Customer, CustomerList } from "@/features/customers/types";
import { isValidTestId } from "@/lib/testid";

const state = vi.hoisted(() => ({
  search: new URLSearchParams(),
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
  usePathname: () => "/",
  useSearchParams: () => state.search,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

let meUser: Record<string, unknown>;
let listBody: unknown;

const adminUser = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
};

function seededCustomer(
  id: number,
  overrides: Partial<Customer> = {},
): Customer {
  return {
    id,
    name: `Cliente ${id}`,
    email: `cliente${id}@example.test`,
    phone: null,
    tax_id: null,
    address: null,
    status: "active",
    version: 1,
    created_at: "2026-01-01T09:00:00Z",
    updated_at: "2026-01-01T09:00:00Z",
    ...overrides,
  };
}

function listPageOf(items: Customer[], total = items.length): CustomerList {
  return { items, page: 1, page_size: 20, total };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function renderAt(search: string) {
  state.search = new URLSearchParams(search);
  render(
    <QueryClientProvider client={queryClient}>
      <CustomersPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  meUser = adminUser;
  listBody = null;
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/auth/me") {
      return jsonResponse(meUser);
    }
    if (url.startsWith("/api/customers")) {
      return jsonResponse(listBody ?? listPageOf([]));
    }
    return jsonResponse(
      {
        status: 404,
        code: "NOT_FOUND",
        detail: "No se encontró el recurso solicitado.",
      },
      404,
    );
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the customers list ledger styling", () => {
  it("keeps the tax id and the state cells on one line", async () => {
    listBody = listPageOf([
      seededCustomer(1, { tax_id: "JUPI-300210", status: "active" }),
    ]);
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    const classNamesOf = (testId: string) =>
      (screen.getByTestId(testId).getAttribute("class") ?? "").split(" ");

    // The code may not be broken in the middle when the name squeezes the
    // columns; the name still wraps.
    expect(classNamesOf("customers-list-name-cell-1")).not.toContain(
      "whitespace-nowrap",
    );
    expect(classNamesOf("customers-list-taxid-cell-1")).toContain(
      "whitespace-nowrap",
    );
    expect(classNamesOf("customers-list-state-cell-1")).toContain(
      "whitespace-nowrap",
    );
  });

  it("scrolls inside the table wrapper, never the page, on a phone", async () => {
    listBody = listPageOf([seededCustomer(1)]);
    renderAt("page=1");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    // The table holds a minimum width; the wrapper (overflow-x-auto)
    // scrolls, so the page itself does not move horizontally.
    const table = screen.getByTestId("customers-list-table");
    expect((table.getAttribute("class") ?? "").split(" ")).toContain(
      "min-w-[40rem]",
    );
    expect(table.parentElement?.getAttribute("class")).toMatch(
      /(^|\s)overflow-x-auto(\s|$)/,
    );
  });

  it("renders the active and inactive badges with their text", async () => {
    listBody = listPageOf([
      seededCustomer(1, { status: "active" }),
      seededCustomer(2, { status: "inactive" }),
    ]);
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    // The badge keeps the same text the cell had: color is never the only
    // carrier of meaning.
    expect(screen.getByTestId("customers-list-state-cell-1"))
      .toHaveTextContent("Activo");
    expect(screen.getByTestId("customers-list-state-cell-2"))
      .toHaveTextContent("Inactivo");

    const activeBadge = screen
      .getByTestId("customers-list-state-cell-1")
      .querySelector("span.badge");
    expect(activeBadge).not.toBeInTheDocument(); // no class hook
    const activeSpan = screen.getByTestId("customers-list-state-cell-1")
      .querySelector("span");
    expect(activeSpan).toHaveTextContent("Activo");
  });

  it("holds the total text and the pagination in the ledger footer item", async () => {
    listBody = listPageOf([seededCustomer(1)], 45);
    renderAt("page=1");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    const footer = screen.getByTestId("customers-list-footer-item");
    const total = screen.getByTestId("customers-list-total-text");

    // The total lives in the footer, out of the pagination nav.
    expect(footer).toContainElement(total);
    expect(total).toHaveTextContent("45 clientes");
    expect(
      total.closest("nav"),
    ).not.toBeInTheDocument();

    const pagination = footer.querySelector("nav");
    expect(pagination).toHaveAttribute(
      "aria-label",
      "Paginación de clientes",
    );
    expect(pagination).toContainElement(
      screen.getByTestId("customers-list-prev-button"),
    );
    expect(pagination).toContainElement(
      screen.getByTestId("customers-list-next-button"),
    );
    expect(pagination).toContainElement(
      screen.getByTestId("customers-list-page-text"),
    );
    expect(
      screen.getByTestId("customers-list-page-text"),
    ).toHaveTextContent("Página 1 de 3");
  });

  it("gives the new footer test id a valid grammar", () => {
    // `customers-list-footer-item` must pass isValidTestId like every new
    // id of the theme.
    expect(isValidTestId("customers-list-footer-item")).toBe(true);
  });
});
