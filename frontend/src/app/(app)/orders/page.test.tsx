import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OrdersPage from "./page";
import type { OrderSummary } from "@/features/orders/types";

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

/** Who the mocked /api/auth/me answers. */
let meUser: Record<string, unknown>;

/** Body and status of what the mocked /api/orders answers. */
let listBody: unknown;
let listStatus: number;

/** Registers the answer of /api/orders. */
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

/** A summary in the shape of the seed (docs/SEED.md). */
function summary(
  id: number,
  overrides: Partial<OrderSummary> = {},
): OrderSummary {
  return {
    id,
    number: `PED-000${id}`,
    status: "draft",
    customer_id: 1,
    customer_name: "Acme Industrial S.A.",
    line_count: 2,
    total: "43.78",
    version: 1,
    created_at: `2026-01-0${id}T10:00:00Z`,
    updated_at: `2026-01-0${id}T10:00:00Z`,
    ...overrides,
  };
}

/** A summary of the seed order 7: a confirmed order without tax id ties. */
function confirmedSummary(): OrderSummary {
  return summary(7, {
    number: "PED-0007",
    status: "confirmed",
    customer_id: 3,
    customer_name: "Cafetería La Esquina",
    total: "55.28",
  });
}

function listPageOf(items: OrderSummary[], total = items.length, page = 1) {
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

/** The /api/orders requests recorded so far (url with query). */
function listRequests(): string[] {
  return fetchMock.mock.calls
    .map((call) => String(call[0]))
    .filter((url) => url.startsWith("/api/orders"));
}

/** Renders the page at the given URL search, and gives it back for rerenders. */
function renderAt(search: string) {
  state.search = new URLSearchParams(search);
  const view = render(
    <QueryClientProvider client={queryClient}>
      <OrdersPage />
    </QueryClientProvider>,
  );
  const rerenderAt = (nextSearch: string) => {
    state.search = new URLSearchParams(nextSearch);
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <OrdersPage />
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
    if (url.startsWith("/api/orders")) {
      return jsonResponse(listBody ?? listPageOf([]), listStatus);
    }
    return problemResponse(
      404,
      "NOT_FOUND",
      "No se encontró el recurso solicitado.",
    );
  });
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the orders list structure", () => {
  it("answers the section title in the tab from the first paint", () => {
    renderAt("");

    expect(document.title).toBe("Pedidos · LabApp");
  });

  it("renders heading, search form, table and pagination from seed data", async () => {
    respondList(
      listPageOf(
        [
          summary(5, {
            number: "PED-0005",
            status: "shipped",
            customer_id: 9,
            customer_name: "Ibérica Importaciones",
            line_count: 1,
            total: "768.90",
            created_at: "2026-01-05T10:00:00Z",
          }),
          summary(3, {
            number: "PED-0003",
            status: "confirmed",
            customer_id: 4,
            customer_name: "Distribuidora Delta",
            total: "327.80",
          }),
        ],
        10,
      ),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Pedidos" }))
      .toHaveAttribute("data-testid", "orders-list-heading");

    for (const name of ["Número", "Cliente", "Estado", "Líneas", "Total", "Creado"]) {
      expect(screen.getByRole("columnheader", { name })).toHaveAttribute(
        "scope",
        "col",
      );
    }

    for (const id of [5, 3]) {
      expect(screen.getByTestId(`orders-list-row-${id}`)).toBeInTheDocument();
    }

    const numberLink = screen.getByTestId("orders-list-view-link-5");
    expect(numberLink).toHaveAttribute("href", "/orders/5");
    expect(numberLink).toHaveAccessibleName("PED-0005");
    expect(numberLink.closest("td")).toHaveAttribute(
      "data-testid",
      "orders-list-number-cell-5",
    );

    expect(screen.getByTestId("orders-list-customer-cell-5"))
      .toHaveTextContent("Ibérica Importaciones");
    expect(screen.getByTestId("orders-list-state-cell-5"))
      .toHaveTextContent("Enviado");
    expect(screen.getByTestId("orders-list-lines-cell-5"))
      .toHaveTextContent("1");
    // The money of the seed: 43.78 for the draft, 768.90 for the shipped.
    expect(screen.getByTestId("orders-list-total-cell-5"))
      .toHaveTextContent("$768.90");
    expect(screen.getByTestId("orders-list-created-cell-5"))
      .toHaveTextContent("05/01/2026");

    expect(screen.getByTestId("orders-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    expect(screen.getByTestId("orders-list-total-text"))
      .toHaveTextContent("10 pedidos");

    expect(screen.getByTestId("orders-list-search-input"))
      .toHaveAccessibleName("Buscar");
    expect(screen.getByTestId("orders-list-search-input")).toHaveAttribute(
      "placeholder",
      "Número o cliente",
    );
    const select = screen.getByTestId(
      "orders-list-status-select",
    ) as HTMLSelectElement;
    expect(select).toHaveAccessibleName("Estado");
    expect(
      Array.from(select.options).map((option) => [
        option.value,
        option.textContent,
      ]),
    ).toEqual([
      ["", "Todos"],
      ["draft", "Borrador"],
      ["confirmed", "Confirmado"],
      ["paid", "Pagado"],
      ["shipped", "Enviado"],
      ["cancelled", "Cancelado"],
    ]);
    expect(screen.getByTestId("orders-list-search-button"))
      .toHaveTextContent("Buscar");
  });

  it("shows a 20-row page of seed-like data with both buttons enabled", async () => {
    const items = Array.from({ length: 20 }, (_, index) =>
      summary(index + 2, { status: index % 2 === 0 ? "draft" : "confirmed" }),
    );
    respondList(listPageOf(items, 45, 2));
    renderAt("page=2");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });
    for (let id = 2; id <= 21; id += 1) {
      expect(screen.getByTestId(`orders-list-row-${id}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("orders-list-page-text"))
      .toHaveTextContent("Página 2 de 3");
    expect(screen.getByTestId("orders-list-total-text"))
      .toHaveTextContent("45 pedidos");
    expect(screen.getByTestId("orders-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("orders-list-next-button")).toBeEnabled();

    // One request per render, with the exact url of the URL state.
    expect(listRequests()[0]).toBe("/api/orders?page=2");
  });

  it("disables the pagination buttons at the first and the last page", async () => {
    const items = Array.from({ length: 20 }, (_, index) => summary(index + 1));
    respondList(listPageOf(items, 50));
    const { rerenderAt } = renderAt("page=1");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("orders-list-prev-button")).toBeDisabled();
    expect(screen.getByTestId("orders-list-next-button")).toBeEnabled();
    expect(screen.getByTestId("orders-list-page-text"))
      .toHaveTextContent("Página 1 de 3");

    rerenderAt("page=3");
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-page-text"))
        .toHaveTextContent("Página 3 de 3");
    });
    expect(listRequests().at(-1)).toBe("/api/orders?page=3");
    expect(screen.getByTestId("orders-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("orders-list-next-button")).toBeDisabled();
  });

  it("navigates to the adjacent pages keeping the URL values", async () => {
    const items = Array.from({ length: 20 }, (_, index) => summary(index + 1));
    respondList(listPageOf(items, 53));
    const { rerenderAt } = renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("orders-list-next-button"));
    expect(state.router.push).toHaveBeenCalledWith("/orders?page=2");

    // ...and from a page that carries q and status. The `&` in q stays
    // encoded through the URL and the request.
    rerenderAt("page=3&q=R%26D&status=confirmed");
    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-page-text"),
      ).toHaveTextContent("Página 3 de 3");
    });
    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("orders-list-prev-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=2&q=R%26D&status=confirmed",
    );
  });
});

describe("the orders list search", () => {
  it("applies the trimmed values and page 1 on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("");
    await waitFor(() => expect(listRequests()).toEqual(["/api/orders?page=1"]));

    const user = userEvent.setup();
    await user.type(screen.getByTestId("orders-list-search-input"), "  PED  ");
    await user.selectOptions(
      screen.getByTestId("orders-list-status-select"),
      "confirmed",
    );

    // Nothing is applied while typing.
    expect(listRequests()).toEqual(["/api/orders?page=1"]);

    await user.click(screen.getByTestId("orders-list-search-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&q=PED&status=confirmed",
    );
  });

  it("drops empty values from the URL on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=2&q=ped&status=paid");
    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("orders-list-search-input"));
    await user.selectOptions(screen.getByTestId("orders-list-status-select"), "");
    state.router.push.mockClear();
    await user.click(screen.getByTestId("orders-list-search-button"));

    expect(state.router.push).toHaveBeenCalledWith("/orders?page=1");
  });
});

describe("the orders list URL state", () => {
  it("falls back to page 1 and no status for invalid URL values", async () => {
    respondList(listPageOf([], 0));

    renderAt("page=007&status=green&q=%20");
    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/orders?page=1"]);
    });
    // The select shows no invalid status.
    expect(
      (screen.getByTestId("orders-list-status-select") as HTMLSelectElement)
        .value,
    ).toBe("");
  });

  it("sends the exact list url with q=R&D encoded", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=3&q=R%26D");

    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/orders?page=3&q=R%26D"]);
    });
  });
});

describe("the orders list correction of a page beyond the last", () => {
  it("replaces the url with the last page instead of an empty page", async () => {
    respondList(
      listPageOf([summary(1), summary(2), summary(3)]),
    );
    const { rerenderAt } = renderAt("page=2&q=ped");

    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledWith(
        "/orders?page=1&q=ped",
      );
    });
    // The correction happens exactly once.
    rerenderAt("page=2&q=ped");
    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledTimes(1);
    });

    // Following the replacement, the screen renders the last page.
    rerenderAt("page=1&q=ped");
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("orders-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    expect(listRequests().slice(0, 2)).toEqual([
      "/api/orders?page=2&q=ped",
      "/api/orders?page=1&q=ped",
    ]);
  });

  it("does not correct a page inside the range", async () => {
    respondList(listPageOf([], 40));
    renderAt("page=2");

    await waitFor(() => expect(listRequests().length).toBe(1));
    expect(state.router.replace).not.toHaveBeenCalled();
  });
});

describe("the orders list states", () => {
  it("shows the loading status while the request runs", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/auth/me") {
        return jsonResponse(adminUser);
      }
      return new Promise<Response>(() => {});
    });

    renderAt("");

    const status = screen.getByTestId("orders-list-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
  });

  it("shows the empty status when nothing matches", async () => {
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-empty-status"))
        .toHaveTextContent("No hay pedidos que coincidan.");
    });
    expect(screen.queryByTestId("orders-list-table")).not.toBeInTheDocument();
  });

  it("shows the problem detail with a retry that refetches", async () => {
    respondList(
      {
        status: 409,
        code: "INVALID_TRANSITION",
        detail: "No se puede pasar el pedido de borrador a cancelado.",
      },
      409,
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-error-alert")).toHaveTextContent(
        "No se puede pasar el pedido de borrador a cancelado.",
      );
    });

    // The retry refetches the same query without touching the URL.
    respondList(listPageOf([confirmedSummary()]));
    await userEvent.setup().click(screen.getByTestId("orders-list-retry-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
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
      expect(screen.getByTestId("orders-list-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("orders-list-retry-button")).toBeInTheDocument();
  });
});

describe("the orders list permission", () => {
  it("shows Nuevo pedido for admin", async () => {
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-new-link")).toHaveAttribute(
        "href",
        "/orders/new",
      );
    });
  });

  it("hides Nuevo pedido for readonly", async () => {
    meUser = readonlyUser;
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));
    expect(
      screen.queryByTestId("orders-list-new-link"),
    ).not.toBeInTheDocument();
  });

  it("hides Nuevo pedido for finance", async () => {
    meUser = { ...readonlyUser, name: "Finanzas Demo", role: "finance" };
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));
    expect(
      screen.queryByTestId("orders-list-new-link"),
    ).not.toBeInTheDocument();
  });
});

describe("the customer filter of the orders list", () => {
  /** The seed customer 4, as /api/customers/4 answers it. */
  const customer4 = {
    id: 4,
    name: "Distribuidora Delta",
    email: "delta@example.test",
    phone: null,
    tax_id: null,
    address: null,
    status: "active",
    version: 1,
    created_at: "2026-01-01T09:04:00Z",
    updated_at: "2026-01-01T09:04:00Z",
  };

  function customerFilterRequests(): string[] {
    return fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) => url.startsWith("/api/customers/"));
  }

  async function assertFilterLine(
    expected: string,
  ): Promise<void> {
    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-customerfilter-text"),
      ).toHaveTextContent(expected);
    });
  }

  it("sends the request with and without the customer_id filter", async () => {
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");
    await waitFor(() => {
      expect(listRequests().some((url) => url === "/api/orders?page=1&customer_id=4")).toBe(
        true,
      );
    });

    // Without the parameter the request must not carry it.
    fetchMock.mockClear();
    renderAt("");
    await waitFor(() => {
      expect(listRequests().some((url) => url === "/api/orders?page=1")).toBe(
        true,
      );
    });
    expect(
      listRequests().every((url) => !url.includes("customer_id")),
    ).toBe(true);
  });

  it("sends the filter together with q, status and page", async () => {
    respondList(listPageOf([], 3));
    renderAt("page=2&q=ped&status=draft&customer_id=4");

    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/orders?page=2&q=ped&status=draft&customer_id=4",
      );
    });
  });

  it("shows the customer name once it loads", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url === "/api/customers/4") {
        return jsonResponse(customer4);
      }
      if (url.startsWith("/api/orders")) {
        return jsonResponse(listBody ?? listPageOf([]), listStatus);
      }
      return problemResponse(
        404,
        "NOT_FOUND",
        "No se encontró el recurso solicitado.",
      );
    });
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");

    await assertFilterLine("Pedidos de Distribuidora Delta");
  });

  it("keeps the id while the customer loads", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url === "/api/customers/4") {
        return new Promise<Response>(() => {});
      }
      return problemResponse(
        404,
        "NOT_FOUND",
        "No se encontró el recurso solicitado.",
      );
    });
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-customerfilter-text"),
      ).toBeInTheDocument();
    });
    expect(customerFilterRequests()).toContain("/api/customers/4");
    await assertFilterLine("Pedidos del cliente #4");
  });

  it("keeps the id when the customer does not exist", async () => {
    // The default mock 404s /api/customers/{id}.
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");

    await assertFilterLine("Pedidos del cliente #4");
    expect(customerFilterRequests()).toContain("/api/customers/4");
  });

  it("links Quitar filtro to the list without customer_id, keeping the rest", async () => {
    respondList(listPageOf([], 3));
    renderAt("customer_id=4&page=2&q=ped&status=draft");

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-customerfilter-clear-link"),
      ).toHaveAttribute("href", "/orders?page=2&q=ped&status=draft");
    });
  });

  it("keeps the customer filter when searching", async () => {
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-customerfilter-text"),
      ).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("orders-list-search-input"),
      "PED-000",
    );
    await user.click(screen.getByTestId("orders-list-search-button"));

    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&q=PED-000&customer_id=4",
    );
  });

  it("keeps the customer filter when changing the status filter", async () => {
    respondList(listPageOf([], 3));
    renderAt("customer_id=4");

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-list-customerfilter-text"),
      ).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-list-status-select"),
      "cancelled",
    );
    await user.click(screen.getByTestId("orders-list-search-button"));

    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&status=cancelled&customer_id=4",
    );
  });

  it("keeps the customer filter when paging", async () => {
    respondList(listPageOf(Array.from({ length: 20 }, (_, i) => summary(i + 1)), 50));
    renderAt("customer_id=4");

    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("orders-list-next-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=2&customer_id=4",
    );
  });
});

describe("the orders list sorting", () => {
  function seededSummaries(): OrderSummary[] {
    // Names in a different order than the numbers, so an ascending sort
    // of one is not an ascending sort of the other.
    return [
      summary(2, { number: "PED-0002", customer_name: "Zeta Ferretería" }),
      summary(1, { number: "PED-0001", customer_name: "Acme Industrial S.A." }),
      summary(3, { number: "PED-0003", customer_name: "Cafetería La Esquina" }),
    ];
  }

  it("renders a sorting button with its label in the Número, Cliente and Creado headers", async () => {
    respondList(listPageOf(seededSummaries()));
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Número" }))
      .toHaveAttribute("data-testid", "orders-list-sort-number-button");
    expect(screen.getByRole("button", { name: "Cliente" }))
      .toHaveAttribute("data-testid", "orders-list-sort-customer-button");
    expect(screen.getByRole("button", { name: "Creado" }))
      .toHaveAttribute("data-testid", "orders-list-sort-created-button");

    // On arrival Creado sorts descending (the plain order) and every
    // other column has no aria-sort.
    expect(
      screen.getByRole("columnheader", { name: "Creado" }),
    ).toHaveAttribute("aria-sort", "descending");
    expect(
      screen.getByRole("columnheader", { name: "Número" }),
    ).not.toHaveAttribute("aria-sort");
    expect(
      screen.getByRole("columnheader", { name: "Cliente" }),
    ).not.toHaveAttribute("aria-sort");
    expect(screen.getByTestId("orders-list-sort-text")).toHaveTextContent(
      "Ordenado por Creado, descendente",
    );
  });

  it("sorts Cliente ascending on the first click and flips it on the second", async () => {
    respondList(listPageOf(seededSummaries(), 80));
    const { rerenderAt } = renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("orders-list-sort-customer-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&sort=customer&direction=asc",
    );

    rerenderAt("page=1&sort=customer&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/orders?page=1&sort=customer&direction=asc",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Cliente" }),
    ).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByTestId("orders-list-sort-customer-button"))
      .toHaveAttribute("data-state", "ascending");
    expect(screen.getByTestId("orders-list-sort-text")).toHaveTextContent(
      "Ordenado por Cliente, ascendente",
    );

    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("orders-list-sort-customer-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&sort=customer&direction=desc",
    );
  });

  it("keeps the filters and the customer filter on a sort", async () => {
    respondList(listPageOf(seededSummaries(), 80));
    const { rerenderAt } = renderAt("page=2&q=ped&status=draft&customer_id=4");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/orders?page=2&q=ped&status=draft&customer_id=4",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("orders-list-sort-number-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/orders?page=1&q=ped&status=draft&customer_id=4&sort=number&direction=asc",
    );

    // The follow-up navigation keeps the whole state and asks the API.
    rerenderAt("page=1&q=ped&status=draft&customer_id=4&sort=number&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/orders?page=1&q=ped&status=draft&customer_id=4&sort=number&direction=asc",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("orders-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Número" }),
    ).toHaveAttribute("aria-sort", "ascending");
  });
});
