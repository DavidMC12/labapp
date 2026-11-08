import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import InvoicesPage from "./page";
import type { InvoiceSummary } from "@/features/invoices/types";

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

/** Body and status of what the mocked /api/invoices answers. */
let listBody: unknown;
let listStatus: number;

/** A summary in the shape of the seed (docs/SEED.md). */
function summary(
  id: number,
  overrides: Partial<InvoiceSummary> = {},
): InvoiceSummary {
  return {
    id,
    number: `FAC-000${id}`,
    status: "issued",
    order_id: id,
    order_number: `PED-000${id}`,
    customer_name: "Distribuidora Delta",
    total: "327.80",
    version: 1,
    created_at: `2026-01-0${id}T14:00:00Z`,
    updated_at: `2026-01-0${id}T14:00:00Z`,
    ...overrides,
  };
}

function listPageOf(items: InvoiceSummary[], total = items.length, page = 1) {
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

/** The /api/invoices requests recorded so far (url with query). */
function listRequests(): string[] {
  return fetchMock.mock.calls
    .map((call) => String(call[0]))
    .filter((url) => url.startsWith("/api/invoices"));
}

/** Renders the page at the given URL search, and gives it back for rerenders. */
function renderAt(search: string) {
  state.search = new URLSearchParams(search);
  const view = render(
    <QueryClientProvider client={queryClient}>
      <InvoicesPage />
    </QueryClientProvider>,
  );
  const rerenderAt = (nextSearch: string) => {
    state.search = new URLSearchParams(nextSearch);
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <InvoicesPage />
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
    if (url.startsWith("/api/invoices")) {
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

describe("the invoices list structure", () => {
  it("answers the section title in the tab from the first paint", () => {
    renderAt("");

    expect(document.title).toBe("Facturas · LabApp");
  });

  it("renders heading, search form, table and pagination from seed data", async () => {
    respondList(
      listPageOf(
        [
          summary(2, {
            number: "FAC-0002",
            status: "paid",
            order_id: 4,
            order_number: "PED-0004",
            customer_name: "Ferretería Fénix",
            total: "197.97",
            created_at: "2026-01-04T14:00:00Z",
          }),
          summary(1, {
            number: "FAC-0001",
            status: "issued",
            order_id: 3,
            order_number: "PED-0003",
          }),
        ],
        3,
      ),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Facturas" }))
      .toHaveAttribute("data-testid", "invoices-list-heading");

    for (const name of ["Número", "Pedido", "Cliente", "Estado", "Total", "Creada"]) {
      expect(screen.getByRole("columnheader", { name })).toHaveAttribute(
        "scope",
        "col",
      );
    }

    for (const id of [2, 1]) {
      expect(screen.getByTestId(`invoices-list-row-${id}`)).toBeInTheDocument();
    }

    const numberLink = screen.getByTestId("invoices-list-view-link-2");
    expect(numberLink).toHaveAttribute("href", "/invoices/2");
    expect(numberLink).toHaveAccessibleName("FAC-0002");
    expect(numberLink.closest("td")).toHaveAttribute(
      "data-testid",
      "invoices-list-number-cell-2",
    );

    const orderLink = screen.getByTestId("invoices-list-order-link-2");
    expect(orderLink).toHaveAttribute("href", "/orders/4");
    expect(orderLink.closest("td")).toHaveAttribute(
      "data-testid",
      "invoices-list-order-cell-2",
    );

    expect(screen.getByTestId("invoices-list-customer-cell-2"))
      .toHaveTextContent("Ferretería Fénix");
    expect(screen.getByTestId("invoices-list-state-cell-2"))
      .toHaveTextContent("Pagada");
    expect(screen.getByTestId("invoices-list-total-cell-2"))
      .toHaveTextContent("$197.97");
    expect(screen.getByTestId("invoices-list-created-cell-2"))
      .toHaveTextContent("04/01/2026");

    expect(screen.getByTestId("invoices-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    // The footer item holds the total, out of the pagination nav.
    expect(
      screen.getByTestId("invoices-list-total-text").closest("div"),
    ).toHaveAttribute("data-testid", "invoices-list-footer-item");
    expect(screen.getByTestId("invoices-list-total-text"))
      .toHaveTextContent("3 facturas");

    expect(screen.getByTestId("invoices-list-search-input"))
      .toHaveAccessibleName("Buscar");
    expect(screen.getByTestId("invoices-list-search-input")).toHaveAttribute(
      "placeholder",
      "Número o cliente",
    );
    const select = screen.getByTestId(
      "invoices-list-status-select",
    ) as HTMLSelectElement;
    expect(select).toHaveAccessibleName("Estado");
    expect(
      Array.from(select.options).map((option) => [
        option.value,
        option.textContent,
      ]),
    ).toEqual([
      ["", "Todas"],
      ["issued", "Emitidas"],
      ["paid", "Pagadas"],
      ["void", "Anuladas"],
    ]);
    expect(screen.getByTestId("invoices-list-search-button"))
      .toHaveTextContent("Buscar");
    // Invoices are issued from the order: no "new invoice" button.
    expect(
      screen.queryByTestId("invoices-list-new-link"),
    ).not.toBeInTheDocument();
  });

  it("shows a 20-row page of seed-like data with both buttons enabled", async () => {
    const items = Array.from({ length: 20 }, (_, index) =>
      summary(index + 1, { status: index % 3 === 1 ? "paid" : "issued" }),
    );
    respondList(listPageOf(items, 45, 2));
    renderAt("page=2");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    for (let id = 1; id <= 20; id += 1) {
      expect(screen.getByTestId(`invoices-list-row-${id}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("invoices-list-page-text"))
      .toHaveTextContent("Página 2 de 3");
    expect(screen.getByTestId("invoices-list-total-text"))
      .toHaveTextContent("45 facturas");
    expect(screen.getByTestId("invoices-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("invoices-list-next-button")).toBeEnabled();

    // One request per render, with the exact url of the URL state.
    expect(listRequests()[0]).toBe("/api/invoices?page=2");
  });

  it("disables the pagination buttons at the first and the last page", async () => {
    const items = Array.from({ length: 20 }, (_, index) => summary(index + 1));
    respondList(listPageOf(items, 50));
    const { rerenderAt } = renderAt("page=1");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-list-prev-button")).toBeDisabled();
    expect(screen.getByTestId("invoices-list-next-button")).toBeEnabled();
    expect(screen.getByTestId("invoices-list-page-text"))
      .toHaveTextContent("Página 1 de 3");

    rerenderAt("page=3");
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-page-text"))
        .toHaveTextContent("Página 3 de 3");
    });
    expect(listRequests().at(-1)).toBe("/api/invoices?page=3");
    expect(screen.getByTestId("invoices-list-prev-button")).toBeEnabled();
    expect(screen.getByTestId("invoices-list-next-button")).toBeDisabled();
  });

  it("navigates to the adjacent pages keeping the URL values", async () => {
    const items = Array.from({ length: 20 }, (_, index) => summary(index + 1));
    respondList(listPageOf(items, 53));
    const { rerenderAt } = renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("invoices-list-next-button"));
    expect(state.router.push).toHaveBeenCalledWith("/invoices?page=2");

    rerenderAt("page=3&q=fac&status=paid");
    await waitFor(() => {
      expect(
        screen.getByTestId("invoices-list-page-text"),
      ).toHaveTextContent("Página 3 de 3");
    });
    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("invoices-list-prev-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/invoices?page=2&q=fac&status=paid",
    );
  });
});

describe("the invoices list search", () => {
  it("applies the trimmed values and page 1 on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("");
    await waitFor(() =>
      expect(listRequests()).toEqual(["/api/invoices?page=1"]),
    );

    const user = userEvent.setup();
    await user.type(screen.getByTestId("invoices-list-search-input"), "  FAC  ");
    await user.selectOptions(
      screen.getByTestId("invoices-list-status-select"),
      "paid",
    );

    // Nothing is applied while typing.
    expect(listRequests()).toEqual(["/api/invoices?page=1"]);

    await user.click(screen.getByTestId("invoices-list-search-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/invoices?page=1&q=FAC&status=paid",
    );
  });

  it("drops empty values from the URL on submit", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=2&q=fac&status=void");
    await waitFor(() => expect(listRequests().length).toBeGreaterThan(0));

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("invoices-list-search-input"));
    await user.selectOptions(screen.getByTestId("invoices-list-status-select"), "");
    state.router.push.mockClear();
    await user.click(screen.getByTestId("invoices-list-search-button"));

    expect(state.router.push).toHaveBeenCalledWith("/invoices?page=1");
  });
});

describe("the invoices list URL state", () => {
  it("falls back to page 1 and no status for invalid URL values", async () => {
    respondList(listPageOf([], 0));

    renderAt("page=007&status=green&q=%20");
    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/invoices?page=1"]);
    });
    expect(
      (screen.getByTestId("invoices-list-status-select") as HTMLSelectElement)
        .value,
    ).toBe("");
  });

  it("sends the exact list url with q=R&D encoded", async () => {
    respondList(listPageOf([], 0));
    renderAt("page=3&q=R%26D");

    await waitFor(() => {
      expect(listRequests()).toEqual(["/api/invoices?page=3&q=R%26D"]);
    });
  });
});

describe("the invoices list correction of a page beyond the last", () => {
  it("replaces the url with the last page instead of an empty page", async () => {
    respondList(listPageOf([summary(1), summary(2), summary(3)]));
    const { rerenderAt } = renderAt("page=2&q=fac");

    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledWith(
        "/invoices?page=1&q=fac",
      );
    });
    rerenderAt("page=2&q=fac");
    await waitFor(() => {
      expect(state.router.replace).toHaveBeenCalledTimes(1);
    });

    rerenderAt("page=1&q=fac");
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-list-page-text"))
      .toHaveTextContent("Página 1 de 1");
    expect(listRequests().slice(0, 2)).toEqual([
      "/api/invoices?page=2&q=fac",
      "/api/invoices?page=1&q=fac",
    ]);
  });

  it("does not correct a page inside the range", async () => {
    respondList(listPageOf([], 40));
    renderAt("page=2");

    await waitFor(() => expect(listRequests().length).toBe(1));
    expect(state.router.replace).not.toHaveBeenCalled();
  });
});

describe("the invoices list states", () => {
  it("shows the loading status while the request runs", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL) => {
        if (String(input).startsWith("/api/invoices")) {
          return new Promise<Response>(() => {});
        }
        return problemResponse(404, "NOT_FOUND", "No se encontró el recurso.");
      },
    );

    renderAt("");

    const status = screen.getByTestId("invoices-list-loading-status");
    expect(status).toHaveTextContent("Cargando…");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
  });

  it("shows the empty status when nothing matches", async () => {
    respondList(listPageOf([], 0));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-empty-status"))
        .toHaveTextContent("No hay facturas que coincidan.");
    });
    expect(screen.queryByTestId("invoices-list-table")).not.toBeInTheDocument();
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
      expect(screen.getByTestId("invoices-list-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });

    respondList(listPageOf([summary(1)]));
    await userEvent.setup().click(screen.getByTestId("invoices-list-retry-button"));

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(state.router.replace).not.toHaveBeenCalled();
  });

  it("shows the INTERNAL_ERROR text for a network failure", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input).startsWith("/api/invoices")) {
        throw new TypeError("Failed to fetch");
      }
      return problemResponse(404, "NOT_FOUND", "No se encontró el recurso.");
    });
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });
    expect(screen.getByTestId("invoices-list-retry-button")).toBeInTheDocument();
  });

  it("keeps the total inside the footer item on a one-invoice page", async () => {
    respondList(listPageOf([summary(1)], 1));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-list-total-text"))
      .toHaveTextContent("1 factura");
  });
});

function respondList(body: unknown, status = 200): void {
  listBody = body;
  listStatus = status;
}

describe("the invoices list sorting", () => {
  function seededSummaries(): InvoiceSummary[] {
    // Names and totals in a different order than the numbers, so an
    // ascending sort of one is not an ascending sort of the other.
    return [
      summary(2, { number: "FAC-0002", customer_name: "Zeta Ferretería", total: "120.50" }),
      summary(1, { number: "FAC-0001", customer_name: "Acme Industrial S.A.", total: "55.28" }),
      summary(3, { number: "FAC-0003", customer_name: "Cafetería La Esquina", total: "327.80" }),
    ];
  }

  it("renders a sorting button with its label in the Número, Cliente, Total and Creada headers", async () => {
    respondList(listPageOf(seededSummaries()));
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });

    for (const [label, testid] of [
      ["Número", "invoices-list-sort-number-button"],
      ["Cliente", "invoices-list-sort-customer-button"],
      ["Total", "invoices-list-sort-total-button"],
      ["Creada", "invoices-list-sort-created-button"],
    ] as Array<[string, string]>) {
      const button = screen.getByRole("button", { name: label });
      expect(button).toHaveAttribute("data-testid", testid);
    }

    // On arrival Creada sorts descending (the plain order) and every
    // other column has no aria-sort.
    expect(
      screen.getByRole("columnheader", { name: "Creada" }),
    ).toHaveAttribute("aria-sort", "descending");
    expect(
      screen.getByRole("columnheader", { name: "Número" }),
    ).not.toHaveAttribute("aria-sort");
    expect(screen.getByTestId("invoices-list-sort-text")).toHaveTextContent(
      "Ordenado por Creada, descendente",
    );
  });

  it("sorts Total descending on the first click and flips it on the second", async () => {
    respondList(listPageOf(seededSummaries(), 80));
    const { rerenderAt } = renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByTestId("invoices-list-sort-total-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/invoices?page=1&sort=total&direction=asc",
    );

    rerenderAt("page=1&sort=total&direction=asc");
    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/invoices?page=1&sort=total&direction=asc",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Total" }),
    ).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByTestId("invoices-list-sort-total-button"))
      .toHaveAttribute("data-state", "ascending");
    expect(screen.getByTestId("invoices-list-sort-text")).toHaveTextContent(
      "Ordenado por Total, ascendente",
    );

    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("invoices-list-sort-total-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/invoices?page=1&sort=total&direction=desc",
    );
  });

  it("keeps the filters on a sort and falls back on invalid URL values", async () => {
    respondList(listPageOf(seededSummaries(), 80));
    renderAt("sort=basket&direction=upwards&page=2&q=fac&status=paid");

    await waitFor(() => {
      expect(listRequests().at(-1)).toBe(
        "/api/invoices?page=2&q=fac&status=paid",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("invoices-list-table")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("columnheader", { name: "Creada" }),
    ).toHaveAttribute("aria-sort", "descending");
    expect(screen.getByTestId("invoices-list-sort-text")).toHaveTextContent(
      "Ordenado por Creada, descendente",
    );

    // Sorting from here goes back to page 1 with the filters intact.
    state.router.push.mockClear();
    await userEvent.setup().click(screen.getByTestId("invoices-list-sort-customer-button"));
    expect(state.router.push).toHaveBeenCalledWith(
      "/invoices?page=1&q=fac&status=paid&sort=customer&direction=asc",
    );
  });
});
