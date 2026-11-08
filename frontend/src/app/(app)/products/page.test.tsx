import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ProductsPage from "./page";
import type { Product } from "@/features/products/hooks";

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

/** Body and status of what the mocked catalog endpoint answers. */
let listBody: unknown;
let listStatus: number;
/** When set, the catalog request rejects like `fetch` would. */
let failNetwork = false;

/** Registers the answer of /api/products; a fresh Response per request. */
function respondCatalog(body: unknown, status = 200): void {
  listBody = body;
  listStatus = status;
}

/** A product in the shape of the seed (docs/SEED.md). */
function seededProduct(
  id: number,
  overrides: Partial<Product> = {},
): Product {
  return {
    id,
    sku: `SKU-${id}`,
    name: `Producto ${id}`,
    price: "10.00",
    stock: 100,
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const catalogOf = (products: Product[]) => ({ items: products });

/** Calls to /api/products so far, for the "no request" and "once" rules. */
function productCalls(): string[] {
  return fetchMock.mock.calls
    .map(([url]) => String(url))
    .filter((url) => url === "/api/products");
}

/** Renders the page at the given URL search, and gives it back. */
function renderAt(search: string) {
  state.search = new URLSearchParams(search);
  const view = render(
    <QueryClientProvider client={queryClient}>
      <ProductsPage />
    </QueryClientProvider>,
  );
  // A rerender with the same client, for a url written by the screen
  // itself (the search push) or by a shared link.
  const rerenderAt = (nextSearch: string) => {
    state.search = new URLSearchParams(nextSearch);
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <ProductsPage />
      </QueryClientProvider>,
    );
  };
  return { rerenderAt };
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  failNetwork = false;
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

  fetchMock.mockImplementation(async () => {
    if (failNetwork) {
      throw new TypeError("Failed to fetch");
    }
    return jsonResponse(listBody ?? catalogOf([]), listStatus);
  });
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
});

describe("the products catalog structure", () => {
  it("titles the document from the moment the page mounts", async () => {
    renderAt("");

    // Even while the catalog request is in the air, the tab answers.
    expect(document.title).toBe("Productos · LabApp");
  });

  it("renders the heading, the search form and the catalog table", async () => {
    // The API returns the catalog ordered by id (SEED order), so the
    // rows appear in the answer order.
    respondCatalog(
      catalogOf([
        seededProduct(1, {
          sku: "KB-100",
          name: "Teclado USB",
          price: "19.90",
          stock: 120,
        }),
        seededProduct(2, { sku: "MS-200", name: "Mouse óptico", price: "9.50" }),
      ]),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Productos" }))
      .toHaveAttribute("data-testid", "products-list-heading");

    expect(screen.getByRole("columnheader", { name: "SKU" })).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Producto" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Precio" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Stock" }),
    ).toBeInTheDocument();

    expect(screen.getByTestId("products-list-search-input"))
      .toHaveAccessibleName("Buscar por SKU o nombre");

    // The rows follow the answer order, and the answer is the catalog
    // ordered by id ascending: 1 before 2.
    const rows = [
      ...document.querySelectorAll(
        "[data-testid^='products-list-row-']",
      ),
    ];
    expect(rows.map((row) => row.getAttribute("data-testid"))).toEqual([
      "products-list-row-1",
      "products-list-row-2",
    ]);

    expect(screen.getByTestId("products-list-sku-cell-1"))
      .toHaveTextContent("KB-100");
    expect(screen.getByTestId("products-list-name-cell-1"))
      .toHaveTextContent("Teclado USB");
    // The money of the API string through formatMoney, and the stock as a
    // plain integer.
    expect(screen.getByTestId("products-list-price-cell-1"))
      .toHaveTextContent("$19.90");
    expect(screen.getByTestId("products-list-stock-cell-1"))
      .toHaveTextContent("120");
  });

  it("requests GET /api/products exactly once, with no paging", async () => {
    respondCatalog(catalogOf([seededProduct(1)]));
    renderAt("");

    await waitFor(() => {
      expect(productCalls()).toHaveLength(1);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("right aligns the price and stock columns", async () => {
    respondCatalog(catalogOf([seededProduct(1)]));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });

    for (const cell of [
      "products-list-price-cell-1",
      "products-list-stock-cell-1",
    ]) {
      expect(screen.getByTestId(cell)).toHaveClass("text-right");
    }
    for (const cell of [
      "products-list-sku-cell-1",
      "products-list-name-cell-1",
    ]) {
      expect(screen.getByTestId(cell)).not.toHaveClass("text-right");
    }
  });

  it("marks the footer with the count of the loaded catalog", async () => {
    respondCatalog(
      catalogOf([seededProduct(1), seededProduct(2), seededProduct(3)]),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-footer-item"))
        .toHaveTextContent("3 productos");
    });
    expect(productCalls()).toHaveLength(1);
  });
});

describe("the stock badges", () => {
  it("shows Agotado for a stock of 0", async () => {
    respondCatalog(catalogOf([seededProduct(9, { stock: 0 })]));
    renderAt("");

    const badge = await screen.findByTestId(
      "products-list-stockstate-status-9",
      {},
      { timeout: 3000 },
    );
    expect(badge).toHaveTextContent("Agotado");
    expect(screen.getByTestId("products-list-stock-cell-9"))
      .toHaveTextContent("0");
  });

  it("shows Poco stock for a stock of 1 and of 5", async () => {
    respondCatalog(
      catalogOf([
        seededProduct(7, { stock: 1 }),
        seededProduct(15, { stock: 5 }),
        seededProduct(1, { stock: 6 }),
      ]),
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("products-list-stockstate-status-7"))
      .toHaveTextContent("Poco stock");
    expect(screen.getByTestId("products-list-stockstate-status-15"))
      .toHaveTextContent("Poco stock");
    // A stock of 6 carries no badge: only the number.
    expect(
      screen.queryByTestId("products-list-stockstate-status-1"),
    ).not.toBeInTheDocument();
  });

  it("carries no badge above the threshold", async () => {
    respondCatalog(catalogOf([seededProduct(1, { stock: 6 })]));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-stock-cell-1"))
        .toHaveTextContent("6");
    });
    expect(
      screen.queryByTestId("products-list-stockstate-status-1"),
    ).not.toBeInTheDocument();
  });
});

describe("the search of the catalog", () => {
  it("writes the trimmed term into the url with the button", async () => {
    respondCatalog(catalogOf([seededProduct(1)]));
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    const user = userEvent.setup();

    await user.type(
      screen.getByTestId("products-list-search-input"),
      "  mouse óptico  ",
    );
    await user.click(screen.getByTestId("products-list-search-button"));

    expect(state.router.push).toHaveBeenCalledTimes(1);
    expect(state.router.push).toHaveBeenCalledWith(
      "/products?q=mouse%20%C3%B3ptico",
    );
  });

  it("submits with Enter and rebuilds the rows from the loaded rows", async () => {
    respondCatalog(
      catalogOf([
        seededProduct(1, { sku: "KB-100", name: "Teclado USB" }),
        seededProduct(2, { sku: "MS-200", name: "Mouse óptico" }),
      ]),
    );
    renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    const user = userEvent.setup();
    expect(productCalls()).toHaveLength(1);

    await user.type(
      screen.getByTestId("products-list-search-input"),
      "ms{Enter}",
    );

    expect(state.router.push).toHaveBeenCalledWith("/products?q=ms");
    // Still exactly one request: the rows come from the loaded catalog.
    expect(productCalls()).toHaveLength(1);
  });

  it("filters the loaded rows with the url q, folded, without a request", async () => {
    respondCatalog(
      catalogOf([
        seededProduct(1, { sku: "KB-100", name: "Teclado USB" }),
        seededProduct(2, { sku: "MS-200", name: "Mouse óptico" }),
      ]),
    );
    const { rerenderAt } = renderAt("");
    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    const callsWithFullCatalog = productCalls().length;

    // The url is the search state: an arriving link (or the router of a
    // push) narrows the rows in the client, without any second request.
    rerenderAt("q=mouse%20optico");

    expect(screen.getByTestId("products-list-row-2")).toBeInTheDocument();
    expect(
      screen.queryByTestId("products-list-row-1"),
    ).not.toBeInTheDocument();
    // The filter works on the folded name too ("mouse optico" for the
    // accented "Mouse óptico"), and the cell still shows the real name.
    expect(screen.getByTestId("products-list-name-cell-2"))
      .toHaveTextContent("Mouse óptico");
    expect(screen.getByTestId("products-list-footer-item"))
      .toHaveTextContent("1 producto");
    // No second request: the filter is client-side.
    expect(productCalls()).toHaveLength(callsWithFullCatalog);
  });

  it("filters the sku with case folded", async () => {
    respondCatalog(catalogOf([seededProduct(9, { sku: "PR-400" })]));
    const { rerenderAt } = renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    rerenderAt("q=pr-400");

    expect(screen.getByTestId("products-list-row-9")).toBeInTheDocument();
    expect(screen.getByTestId("products-list-footer-item"))
      .toHaveTextContent("1 producto");
  });
});

describe("the states of the catalog", () => {
  it("shows the loading status while the request runs", async () => {
    fetchMock.mockImplementation(
      () => new Promise<Response>(() => {}),
    );
    renderAt("");

    const status = screen.getByTestId("products-list-loading-status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
    expect(status).toHaveTextContent("Cargando…");
  });

  it("shows the error detail with a retry that asks again", async () => {
    respondCatalog(
      { status: 500, code: "INTERNAL_ERROR", detail: "Ocurrió un error inesperado." },
      500,
    );
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-error-alert"))
        .toHaveTextContent("Ocurrió un error inesperado.");
    });
    expect(screen.queryByTestId("products-list-table")).not.toBeInTheDocument();

    respondCatalog(catalogOf([seededProduct(1)]));
    await userEvent.setup().click(
      screen.getByTestId("products-list-retry-button"),
    );

    await waitFor(() => {
      expect(screen.getByTestId("products-list-table")).toBeInTheDocument();
    });
    expect(productCalls()).toHaveLength(2);
  });

  it("maps a network failure to the synthesized internal problem", async () => {
    failNetwork = true;
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-error-alert"))
        .toHaveTextContent(
          "Ocurrió un error inesperado. Inténtalo de nuevo.",
        );
    });
  });

  it("shows the empty status when the catalog matches nothing", async () => {
    respondCatalog(catalogOf([]));
    renderAt("");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-empty-status"))
        .toHaveTextContent("No hay productos que coincidan");
    });
  });

  it("shows the empty status when the search matches nothing", async () => {
    respondCatalog(
      catalogOf([
        seededProduct(1, { sku: "KB-100", name: "Teclado USB" }),
        seededProduct(2, { sku: "MS-200", name: "Mouse óptico" }),
      ]),
    );
    renderAt("q=inexistente");

    await waitFor(() => {
      expect(screen.getByTestId("products-list-empty-status"))
        .toHaveTextContent("No hay productos que coincidan");
    });
    expect(screen.queryByTestId("products-list-table")).not.toBeInTheDocument();
  });
});
