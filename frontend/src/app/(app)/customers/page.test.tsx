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
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the customers list structure", () => {
  it("answers the section title in the tab from the first paint", () => {
    renderAt("");

    // The hook lives in the wrapper, so the tab answers even inside the
    // Suspense fallback, before the list request resolves.
    expect(document.title).toBe("Clientes · LabApp");
  });

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

describe("the customers list sorting", () => {
  it("renders a sorting button with its label in every sortable header", async () => {
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]),
    );
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Nombre" }))
      .toHaveAttribute("data-testid", "customers-list-sort-name-button");
    expect(screen.getByRole("button", { name: "Email" }))
      .toHaveAttribute("data-testid", "customers-list-sort-email-button");
    expect(screen.getByRole("button", { name: "Creado" }))
      .toHaveAttribute("data-testid", "customers-list-sort-created-button");

    // On arrival the order is the plain one: Creado sorts descending and
    // every other column is a button with no aria-sort.
    expect(
      screen.getByRole("columnheader", { name: "Creado" }),
    ).toHaveAttribute("aria-sort", "descending");
    expect(
      screen.getByRole("columnheader", { name: "Nombre" }),
    ).not.toHaveAttribute("aria-sort");
    expect(
      screen.getByRole("columnheader", { name: "Email" }),
    ).not.toHaveAttribute("aria-sort");
    expect(screen.getByTestId("customers-list-sort-text")).toHaveTextContent(
      "Ordenado por Creado, descendente",
    );
  });

  it("sorts ascending on the first click of Nombre and asks the API for it", async () => {
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]),
    );
    const { rerenderAt } = renderAt("");
    await waitFor(() => expect(listRequests()).toEqual(["/api/customers?page=1"]));
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("customers-list-sort-name-button"));

    // The URL of the sort rule: page 1, the sort visible, no third state.
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&sort=name&direction=asc",
    );

    // Following the navigation, the rendered list asks the API for it.
    rerenderAt("page=1&sort=name&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/customers?page=1&sort=name&direction=asc",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Nombre" }),
    ).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByTestId("customers-list-sort-name-button"))
      .toHaveAttribute("data-state", "ascending");
    expect(screen.getByTestId("customers-list-sort-text")).toHaveTextContent(
      "Ordenado por Nombre, ascendente",
    );
  });

  it("flips to descending on the second click of the same column", async () => {
    (state.search as unknown as URLSearchParams) =
      new URLSearchParams("sort=name&direction=asc");
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]),
    );
    renderAt("sort=name&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/customers?page=1&sort=name&direction=asc",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("customers-list-sort-name-button"));

    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&sort=name&direction=desc",
    );
  });

  it("sorts Creado ascending on the first click and back to the clean URL on the second", async () => {
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]),
    );
    const { rerenderAt } = renderAt("");
    await waitFor(() => expect(listRequests()).toEqual(["/api/customers?page=1"]));
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    // The default table is already sorted by Creado, descending, so the
    // first click flips it to ascending.
    await userEvent.setup().click(screen.getByTestId("customers-list-sort-created-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&sort=created_at&direction=asc",
    );

    // And the second click goes back to the plain order: both sort
    // parameters leave the URL again.
    state.router.push.mockClear();
    rerenderAt("page=1&sort=created_at&direction=asc");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("customers-list-sort-created-button"))
      .toHaveAttribute("data-state", "ascending");
    await userEvent.setup().click(screen.getByTestId("customers-list-sort-created-button"));
    expect(state.router.push).toHaveBeenCalledWith("/customers?page=1");
  });

  it("keeps the filters on a sort and falls back on invalid URL values", async () => {
    // Enough rows for page 4 to exist, so the correction does not run.
    respondList(
      listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)], 80),
    );
    // A broken sort falls back to the plain list order; the filters stay.
    renderAt("sort=phone&direction=upwards&page=4&q=ana&status=inactive");

    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/customers?page=4&q=ana&status=inactive",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Nombre" }),
    ).not.toHaveAttribute("aria-sort");
    expect(screen.getByTestId("customers-list-sort-text")).toHaveTextContent(
      "Ordenado por Creado, descendente",
    );

    // Sorting from here goes back to page 1 with the filters intact.
    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("customers-list-sort-email-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&q=ana&status=inactive&sort=email&direction=asc",
    );
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
      expect(screen.getByTestId("customers-list-import-link")).toHaveAttribute(
        "href",
        "/customers/import",
      );
    });
  });

  it("hides the import link for readonly", async () => {
    meUser = readonlyUser;
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));
    expect(
      screen.queryByTestId("customers-list-new-link"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("customers-list-import-link"),
    ).not.toBeInTheDocument();
  });
});

describe("the customers list export link", () => {
  it("renders the plain download anchor of the plain list", () => {
    renderAt("");

    const link = screen.getByTestId("customers-list-export-link");
    expect(link.tagName).toBe("A");
    expect(link).toHaveAccessibleName("Exportar CSV");
    expect(link).toHaveAttribute("href", "/api/customers/export");
    expect(link).toHaveAttribute("download");
  });

  it("renders it in the empty state too", async () => {
    respondList(listPageOf([], 0));
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-empty-status"))
        .toBeInTheDocument();
    });
    expect(screen.getByTestId("customers-list-export-link")).toBeDefined();
  });

  it("renders it in the error state too", async () => {
    respondList(
      problemResponse(500, "INTERNAL_ERROR", "Fallo inesperado."),
      500,
    );
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-error-alert"))
        .toBeInTheDocument();
    });
    expect(screen.getByTestId("customers-list-export-link")).toBeDefined();
  });

  it("follows the applied filters and the sort of the URL", () => {
    renderAt("?page=2&q=ana&status=active&sort=name&direction=asc");

    expect(screen.getByTestId("customers-list-export-link")).toHaveAttribute(
      "href",
      "/api/customers/export?q=ana&status=active&sort=name&direction=asc",
    );
  });

  it("leaves the parameters that are the default out", () => {
    // The direction alone is the default of the default field; the plain
    // list (whatever its page) exports with no parameters at all.
    renderAt("?page=3&sort=created_at&direction=desc");

    expect(screen.getByTestId("customers-list-export-link")).toHaveAttribute(
      "href",
      "/api/customers/export",
    );
  });

  it("never carries the page parameter", () => {
    renderAt("?page=9&q=ana");

    const href = screen.getByTestId("customers-list-export-link")
      .getAttribute("href");
    expect(href).toBe("/api/customers/export?q=ana");
    expect(href).not.toContain("page=");
  });

  it("is rebuilt from the URL state, not from the search box", async () => {
    const user = userEvent.setup();
    renderAt("?q=ana");

    await user.type(
      screen.getByTestId("customers-list-search-input"),
      "maria",
    );

    expect(screen.getByTestId("customers-list-export-link")).toHaveAttribute(
      "href",
      "/api/customers/export?q=ana",
    );
  });

  it("follows the URL state when it changes", () => {
    const { rerenderAt } = renderAt("?q=ana");
    expect(screen.getByTestId("customers-list-export-link")).toHaveAttribute(
      "href",
      "/api/customers/export?q=ana",
    );

    rerenderAt("?q=ana&status=inactive&sort=email&direction=desc");
    expect(screen.getByTestId("customers-list-export-link")).toHaveAttribute(
      "href",
      "/api/customers/export?q=ana&status=inactive&sort=email&direction=desc",
    );
  });

  it("is a plain anchor: no router call on click", async () => {
    renderAt("?q=ana");

    await userEvent.setup().click(screen.getByTestId("customers-list-export-link"));

    expect(state.router.push).not.toHaveBeenCalled();
    expect(state.router.replace).not.toHaveBeenCalled();
  });
});

describe("the previous data of the customers list while the next request loads", () => {
  /** Swaps the mock so the request of the next URL stays pending. */
  function deferNext(url: string): () => void {
    let release: (response: Response) => void = () => {};
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === url) {
        return new Promise<Response>((resolve) => {
          release = resolve;
        });
      }
      if (String(input) === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      return jsonResponse(listBody ?? listPageOf([]), listStatus);
    });
    return () => release(jsonResponse(listPageOf([seededCustomer(1)])));
  }

  it("still shows the loading text on the first load, with no table region", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/customers?page=1") {
        return new Promise<Response>(() => {});
      }
      if (String(input) === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      return jsonResponse({}, 404);
    });
    renderAt("");

    const status = screen.getByTestId("customers-list-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByTestId("customers-list-scroll-region"))
      .not.toBeInTheDocument();
  });

  it("keeps the previous rows, region busy and sorted header focused while the sort loads", async () => {
    respondList(listPageOf([seededCustomer(1), seededCustomer(2), seededCustomer(3)]));
    const { rerenderAt } = renderAt("");
    await waitFor(() => expect(listRequests()).toEqual(["/api/customers?page=1"]));
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("customers-list-scroll-region"))
      .not.toHaveAttribute("aria-busy");

    const button = screen.getByTestId("customers-list-sort-name-button");
    await userEvent.setup().click(button);
    expect(state.router.push).toHaveBeenCalledWith(
      "/customers?page=1&sort=name&direction=asc",
    );

    // Following the navigation, the sorted request stays pending: the
    // previous rows stay on screen and the region announces the wait.
    const release = deferNext("/api/customers?page=1&sort=name&direction=asc");
    rerenderAt("page=1&sort=name&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1))
        .toBe("/api/customers?page=1&sort=name&direction=asc");
    });
    const region = screen.getByTestId("customers-list-scroll-region");
    await waitFor(() => {
      expect(region).toHaveAttribute("aria-busy", "true");
    });
    expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    // The click left the button focused and it must stay there.
    expect(button).toHaveFocus();

    release();
    await waitFor(() => {
      expect(region).not.toHaveAttribute("aria-busy");
    });
    expect(button).toHaveFocus();
  });

  it("keeps the focus on Siguiente while the page request loads", async () => {
    respondList(listPageOf([seededCustomer(1), seededCustomer(2)], 25));
    const { rerenderAt } = renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    const next = screen.getByTestId("customers-list-next-button");
    await userEvent.setup().click(next);
    expect(state.router.push).toHaveBeenCalledWith("/customers?page=2");

    const release = deferNext("/api/customers?page=2");
    rerenderAt("page=2");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe("/api/customers?page=2");
    });
    const region = screen.getByTestId("customers-list-scroll-region");
    await waitFor(() => {
      expect(region).toHaveAttribute("aria-busy", "true");
    });
    expect(next).toHaveFocus();

    release();
    await waitFor(() => {
      expect(region).not.toHaveAttribute("aria-busy");
    });
    expect(next).toHaveFocus();
  });

  it("keeps the focus on the search input through the filter request", async () => {
    respondList(listPageOf([seededCustomer(1), seededCustomer(2)]));
    const { rerenderAt } = renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("customers-list-table")).toBeInTheDocument();
    });

    const input = screen.getByTestId("customers-list-search-input");
    await userEvent.setup().type(input, "beta{Enter}");
    expect(state.router.push).toHaveBeenCalledWith("/customers?page=1&q=beta");

    const release = deferNext("/api/customers?page=1&q=beta");
    rerenderAt("page=1&q=beta");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe("/api/customers?page=1&q=beta");
    });
    const region = screen.getByTestId("customers-list-scroll-region");
    await waitFor(() => {
      expect(region).toHaveAttribute("aria-busy", "true");
    });
    // The form with the input stays mounted: the focus paid to the filter
    // is never thrown away by the data behind it.
    expect(input).toHaveFocus();

    release();
    await waitFor(() => {
      expect(region).not.toHaveAttribute("aria-busy");
    });
    expect(input).toHaveFocus();
  });
});
