import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CustomersPage from "./page";
import type { Customer, CustomerList } from "@/features/customers/types";

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
  useSearchParams: () => state.search,
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

/** Who the mocked /api/auth/me answers. */
let meUser: Record<string, unknown>;

/** Body and status of what the mocked list endpoint answers. */
let listBody: unknown;
let listStatus: number;

/** Registers the answer of /api/customers; a fresh Response per request. */
function respondList(body: unknown, status = 200): void {
  listBody = body;
  listStatus = status;
}

const adminUser = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
};

const readonlyUser = {
  id: 4,
  name: "Solo Lectura Demo",
  email: "readonly@labapp.test",
  role: "readonly",
};

/** A customer in the shape of the seed (docs/SEED.md). */
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

function listPageOf(
  items: Customer[],
  total = items.length,
  page = 1,
): CustomerList {
  return { items, page, page_size: 20, total };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function problemResponse(
  status: number,
  code: string,
  detail: string,
): Response {
  return jsonResponse({ status, code, detail }, status);
}

/** The /api/customers requests recorded so far (url with query). */
function listRequests(): string[] {
  return fetchMock.mock.calls
    .map((call) => String(call[0]))
    .filter((url) => url.startsWith("/api/customers"));
}

/** Renders the page at the given URL search, and gives it back for rerenders. */
function renderAt(search: string) {
  state.search = new URLSearchParams(search);
  const view = render(
    <QueryClientProvider client={queryClient}>
      <CustomersPage />
    </QueryClientProvider>,
  );
  const rerenderAt = (nextSearch: string) => {
    state.search = new URLSearchParams(nextSearch);
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <CustomersPage />
      </QueryClientProvider>,
    );
  };
  return { rerenderAt };
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  state.router.push.mockClear();
  state.router.replace.mockClear();
  meUser = adminUser;
  listBody = null;
  listStatus = 200;
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
      return jsonResponse(listBody ?? listPageOf([]), listStatus);
    }
    return problemResponse(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the customers list structure", () => {
  it("renders heading, search form, table and pagination from seed data", async () => {
    respondList(
      listPageOf(
        [
          seededCustomer(5, {
            name: "Estudio Épsilon",
            email: "epsilon@example.test",
            status: "inactive",
          }),
          seededCustomer(3, {
            name: "Cafetería La Esquina",
            email: "cafe@example.test",
          }),
          seededCustomer(1, {
            name: "Acme Industrial S.A.",
            email: "acme@example.test",
            tax_id: "ACME-900123",
            phone: "+1 555 010 0001",
            address: "Av. Principal 100",
          }),
        ],
        10,
      ),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Clientes" }))
      .toHaveAttribute("data-testid", "customers-list-heading");

    expect(screen.getByRole("columnheader", { name: "Nombre" }))
      .toHaveAttribute("scope", "col");
    expect(screen.getByRole("columnheader", { name: "Email" }))
      .toHaveAttribute("scope", "col");
    expect(screen.getByRole("columnheader", { name: "ID fiscal" }))
      .toHaveAttribute("scope", "col");
    expect(screen.getByRole("columnheader", { name: "Estado" }))
      .toHaveAttribute("scope", "col");

    for (const id of [5, 3, 1]) {
      expect(screen.getByTestId(`customers-list-row-${id}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("customers-list-name-cell-5"))
      .toHaveTextContent("Estudio Épsilon");
    expect(screen.getByTestId("customers-list-email-cell-5"))
      .toHaveTextContent("epsilon@example.test");
    expect(screen.getByTestId("customers-list-state-cell-5"))
      .toHaveTextContent("Inactivo");
    expect(screen.getByTestId("customers-list-taxid-cell-3"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("customers-list-taxid-cell-1"))
      .toHaveTextContent("ACME-900123");

    const nameLink = screen.getByTestId("customers-list-view-link-1");
    expect(nameLink).toHaveAttribute("href", "/customers/1");
    expect(nameLink).toHaveAccessibleName("Acme Industrial S.A.");
    expect(nameLink.closest("td")).toHaveAttribute(
      "data-testid",
      "customers-list-name-cell-1",
    );

    expect(screen.getByTestId("customers-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    expect(screen.getByTestId("customers-list-total-text"))
      .toHaveTextContent("10 clientes");

    expect(screen.getByTestId("customers-list-search-input"))
      .toHaveAccessibleName("Buscar");
    const select = screen.getByTestId(
      "customers-list-status-select",
    ) as HTMLSelectElement;
    expect(select).toHaveAccessibleName("Estado");
    expect(
      Array.from(select.options).map((option) => [
        option.value,
        option.textContent,
      ]),
    ).toEqual([
      ["", "Todos"],
      ["active", "Activos"],
      ["inactive", "Inactivos"],
    ]);
    expect(screen.getByTestId("customers-list-search-button"))
      .toHaveTextContent("Buscar");
  });

  it("shows a 20-row page of seed-like data with both buttons enabled", async () => {
    const items = Array.from({ length: 20 }, (_, index) =>
      seededCustomer(index + 2, {
        status: index % 5 === 4 ? "inactive" : "active",
        tax_id: index % 2 === 0 ? `ZET-900${index}` : null,
      }),
    );
    respondList(listPageOf(items, 45, 2));
    renderAt("page=2");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    for (let id = 2; id <= 21; id += 1) {
      expect(screen.getByTestId(`customers-list-row-${id}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("customers-list-page-text"))
      .toHaveTextContent("Página 2 de 3");
    expect(screen.getByTestId("customers-list-total-text"))
      .toHaveTextContent("45 clientes");
    expect(screen.getByTestId("customers-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("customers-list-next-button")).toBeEnabled();

    // One request per render, with the exact url of the URL state.
    expect(listRequests()[0]).toBe("/api/customers?page=2");
  });

  it("disables the pagination buttons at the first and the last page", async () => {
    const items = Array.from({ length: 20 }, (_, index) =>
      seededCustomer(index + 1),
    );
    respondList(listPageOf(items, 50));
    const { rerenderAt } = renderAt("page=1");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("customers-list-prev-button")).toBeDisabled();
    expect(screen.getByTestId("customers-list-next-button")).toBeEnabled();
    expect(screen.getByTestId("customers-list-page-text"))
      .toHaveTextContent("Página 1 de 3");

    rerenderAt("page=3");
    await waitFor(() => {
      expect(
        screen.getByTestId("customers-list-page-text"),
      ).toHaveTextContent("Página 3 de 3");
    });
    expect(listRequests().at(-1)).toBe("/api/customers?page=3");
    expect(screen.getByTestId("customers-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("customers-list-next-button")).toBeDisabled();
  });

  it("navigates to the adjacent pages keeping the URL values", async () => {
    const items = Array.from({ length: 20 }, (_, index) =>
      seededCustomer(index + 1),
    );
    respondList(listPageOf(items, 53));
    const { rerenderAt } = renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    // From page 1 with no other values...
    await userEvent.setup().click(screen.getByTestId("customers-list-next-button"));
    expect(state.router.push).toHaveBeenCalledWith("/customers?page=2");

    // ...and from a page that carries q and status.
    rerenderAt("page=2&q=ana&status=active");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(listRequests().at(-1)).toBe(
      "/api/customers?page=2&q=ana&status=active",
    );
    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("customers-list-prev-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&q=ana&status=active",
    );
  });
});

describe("the customers list search", () => {
  it("applies the trimmed values and page 1 on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("");
    await waitFor(() => expect(listRequests()).toEqual(["/api/customers?page=1"]));

    const user = userEvent.setup();
    await user.type(screen.getByTestId("customers-list-search-input"), "  Ana  ");
    await user.selectOptions(
      screen.getByTestId("customers-list-status-select"),
      "active",
    );

    // Nothing is applied while typing.
    expect(listRequests()).toEqual(["/api/customers?page=1"]);

    await user.click(screen.getByTestId("customers-list-search-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&q=Ana&status=active",
    );
  });

  it("drops empty values from the URL on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=2&q=ana&status=active");
    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("customers-list-search-input"));
    await user.selectOptions(screen.getByTestId("customers-list-status-select"), "");
    state.router.push.mockClear();
    await user.click(screen.getByTestId("customers-list-search-button"));

    expect(state.router.push).toHaveBeenCalledWith("/customers?page=1");
  });
});

describe("the customers list URL state", () => {
  it("falls back to page 1 and no status for invalid URL values", async () => {
    respondList(listPageOf([], 0));

    renderAt("page=007&status=red&q=%20");
    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/customers?page=1"]);
    });
    // The select shows no invalid status.
    expect(
      (screen.getByTestId("customers-list-status-select") as HTMLSelectElement)
        .value,
    ).toBe("");
  });

  it("rejects page=0 and page=1e3 the same way", async () => {
    respondList(listPageOf([], 0));
    const { rerenderAt } = renderAt("page=0");
    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/customers?page=1"]);
    });

    rerenderAt("page=1e3");
    await waitFor(() => {
      // page=1e3 normalizes to page 1 again: the same query key, so no
      // second request and no correction is needed.
      expect(listRequests()).toEqual(["/api/customers?page=1"]);
    });
    expect(state.router.replace).not.toHaveBeenCalled();
  });

  it("sends the exact list url with q=R&D encoded", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=3&q=R%26D");

    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/customers?page=3&q=R%26D"]);
    });
  });
});

describe("the customers list correction of a page beyond the last", () => {
  it("replaces the url with the last page instead of an empty page", async () => {
    // The URL asks for page 2, the server only has three customers.
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]),
    );
    const { rerenderAt } = renderAt("page=2&q=ana");

    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledWith(
        "/customers?page=1&q=ana",
      );
    });
    // The correction happens exactly once.
    rerenderAt("page=2&q=ana");
    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledTimes(1);
    });

    // Following the replacement, the screen renders the last page.
    rerenderAt("page=1&q=ana");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("customers-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    expect(listRequests()).toEqual([
      "/api/customers?page=2&q=ana",
      "/api/customers?page=1&q=ana",
    ]);
  });

  it("does not correct a page inside the range", async () => {
    respondList(listPageOf([], 40));
    renderAt("page=2");

    await waitFor(() => expect(listRequests().length).toBe(1));
    expect(state.router.replace).not.toHaveBeenCalled();
  });
});

describe("the customers list states", () => {
  it("shows the loading status while the request runs", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(adminUser);
      }
      return new Promise<Response>(() => {});
    });

    renderAt("");

    const status = screen.getByTestId("customers-list-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
  });

  it("shows the empty status when nothing matches", async () => {
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-empty-status"))
        .toHaveTextContent("No hay clientes que coincidan.");
    });
    expect(screen.queryByTestId("customers-list-table")).not.toBeInTheDocument();
  });

  it("shows the problem detail with a retry that refetches", async () => {
    respondList(
      {
        status: 500,
        code: "INTERNAL_ERROR",
        detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
      },
      500,
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });

    // The retry refetches the same query without touching the URL.
    respondList(listPageOf([seededCustomer(1)]));
    await userEvent.setup().click(screen.getByTestId("customers-list-retry-button"));

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(state.router.replace).not.toHaveBeenCalled();
  });

  it("shows the INTERNAL_ERROR text for a network failure", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/me") {
        return jsonResponse(adminUser);
      }
      throw new TypeError("Failed to fetch");
    });
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("customers-list-retry-button")).toBeInTheDocument();
  });
});

describe("the customers list permission", () => {
  it("shows Nuevo cliente for admin", async () => {
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("customers-list-new-link")).toHaveAttribute(
        "href",
        "/customers/new",
      );
    });
  });

  it("hides Nuevo cliente for readonly", async () => {
    meUser = readonlyUser;
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));
    expect(
      screen.queryByTestId("customers-list-new-link"),
    ).not.toBeInTheDocument();
  });
});
