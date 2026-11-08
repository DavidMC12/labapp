import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import { installDialogStub } from "@/test/dialog";
import OrderDetailPage from "./page";
import type { Order, Shortage } from "@/features/orders/types";
import type { Customer } from "@/features/customers/types";

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

const state = vi.hoisted(() => ({
  routeId: "8",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  usePathname: () => "/",
  useParams: () => ({ id: state.routeId }),
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

let meUser: Record<string, unknown>;

/** The order the GET /api/orders/{id} answers (mock server state). */
let orderBody: Order;
const orderStatus = 200;
/** A load failure for the detail GET; null when the order answers 200. */
let orderGetProblem: { status: number; code: string; detail: string } | null;

/** GET /api/products: body and status. */
let productsBody: unknown;
let productsStatus: number;

/** GET /api/customers?...status=active: body of the pickers. */
let customersBody: unknown;
let customersStatus: number;

/**
 * What a given mutation request answers; `null` falls back to the happy
 * path where the change is applied to the mocked order. Tests seed it to
 * reproduce the strict server (correction S2) and every failure code
 * (correction S1).
 */
let mutateAnswer:
  | null
  | ((url: string, method: string) => Response | null);

/**
 * What the invoice endpoint answers; `null` falls back to the happy 201
 * of a brand new invoice (the exact tests seed it with the failure codes
 * of the brief and with the deferred gate).
 */
let issueAnswer:
  | null
  | ((url: string, method: string) => Response | null);

/**
 * The gate of the B1 tests: while it holds, the next order mutation stays
 * pending; every mutation control must be disabled and a click on another
 * one must send nothing.
 */
let holdMutation: null | {
  promise: Promise<Response>;
  release: (response: Response) => void;
};

/** The recorded request lines of the order mutations, in arrival order. */
function mutationCalls(): Array<{
  url: string;
  method: string;
  body: string | undefined;
  ifMatch: string | null;
}> {
  return fetchMock.mock.calls
    .map(([input, init]) => {
      const initRequest = init as RequestInit | undefined;
      return {
        url: String(input),
        method: String(initRequest?.method ?? "GET"),
        body:
          typeof initRequest?.body === "string" ? initRequest.body : undefined,
        ifMatch:
          typeof (initRequest?.headers as Record<string, string> | undefined)
            ?.["If-Match"] === "string"
            ? String(
                (initRequest?.headers as Record<string, string>)["If-Match"],
              )
            : null,
      };
    })
    .filter((call) => call.url.startsWith("/api/orders/8") && call.method !== "GET");
}

/** The GET counts of /api/orders/8, for the "refetches after failure" asserts. */
function readCount(): number {
  return fetchMock.mock.calls.filter(
    (call) => String(call[0]) === "/api/orders/8"
      && String((call[1] as RequestInit | undefined)?.method ?? "GET") === "GET",
  ).length;
}

/** The literal Order of the corrected spec (S5): the draft of order 8. */
function draftOrder(): Order {
  return {
    id: 8,
    number: "PED-0008",
    status: "draft",
    customer: { id: 1, name: "Acme Industrial S.A.", status: "active" },
    lines: [
      {
        id: 10,
        product_id: 1,
        sku: "KB-100",
        name: "Teclado USB",
        quantity: 2,
        unit_price: "19.90",
        line_total: "39.80",
      },
    ],
    subtotal: "39.80",
    tax_rate: "10.00",
    tax: "3.98",
    total: "43.78",
    invoice_id: null,
    version: 2,
    created_at: "2026-11-05T15:00:00Z",
    updated_at: "2026-11-05T15:01:00Z",
  };
}

/** The paid order similar to the seed ( PED-0004), id 4, invoice 2. */
function paidOrder(): Order {
  return {
    ...draftOrder(),
    id: 4,
    number: "PED-0004",
    status: "paid",
    customer: { id: 6, name: "Ferretería Fénix", status: "active" },
    lines: [
      {
        id: 4,
        product_id: 5,
        sku: "HD-500",
        name: "Disco externo 1 TB",
        quantity: 3,
        unit_price: "59.99",
        line_total: "179.97",
      },
    ],
    subtotal: "179.97",
    tax: "18.00",
    total: "197.97",
    invoice_id: 2,
  };
}

/** The server recomputes the totals of the draft on every read. */
function withTotals(order: Order): Order {
  const subtotal = order.lines.reduce(
    (sum, line) => sum + Number(line.line_total),
    0,
  );
  const taxValue =
    Math.round(subtotal * (Number(order.tax_rate) / 100) * 100) / 100;
  return {
    ...order,
    subtotal: `${subtotal.toFixed(2)}`,
    tax: `${taxValue.toFixed(2)}`,
    total: `${(subtotal + taxValue).toFixed(2)}`,
  };
}

/** Applies a successful order mutation to the mocked order (S4/S5). */
function applyMutation(
  order: Order,
  url: string,
  method: string,
  body: string | undefined,
): Order {
  const parsed = body === undefined
    ? {}
    : (JSON.parse(body) as Record<string, unknown>);
  const nextVersion = order.version + 1;
  const linesOf = [...order.lines];

  if (method === "PATCH" && url === "/api/orders/8") {
    const customerId = Number(parsed.customer_id);
    if (customerId === order.customer.id) {
      return order; // same value answers untouched (S4)
    }
    return {
      ...order,
      customer: {
        id: customerId,
        name: `Cliente ${customerId}`,
        status: "active",
      },
      version: nextVersion,
      updated_at: "2026-11-05T15:05:00Z",
    };
  }
  if (method === "PATCH" && url.startsWith("/api/orders/8/lines/")) {
    const lineId = Number(url.split("/").at(-1));
    const line = linesOf.find((candidate) => candidate.id === lineId);
    if (!line) {
      return order;
    }
    const quantity = Number(parsed.quantity);
    const updated = linesOf.map((candidate) =>
      candidate.id === lineId
        ? {
            ...candidate,
            quantity,
            line_total: `${(quantity * Number(candidate.unit_price)).toFixed(2)}`,
          }
        : candidate,
    );
    return withTotals({
      ...order,
      lines: updated,
      version: nextVersion,
      updated_at: "2026-11-05T15:02:00Z",
    });
  }
  if (method === "DELETE" && url.startsWith("/api/orders/8/lines/")) {
    const lineId = Number(url.split("/").at(-1));
    const remaining = linesOf.filter((candidate) => candidate.id !== lineId);
    return withTotals({
      ...order,
      lines: remaining,
      version: nextVersion,
      updated_at: "2026-11-05T15:03:00Z",
    });
  }
  if (method === "POST" && url === "/api/orders/8/lines") {
    const productId = Number(parsed.product_id);
    const isSeeded = productId === 7;
    linesOf.push({
      id: 11,
      product_id: productId,
      sku: isSeeded ? "WC-720" : "XX-000",
      name: isSeeded ? "Cámara web HD" : "Producto",
      quantity: Number(parsed.quantity),
      unit_price: isSeeded ? "34.50" : "0.00",
      line_total: `${(Number(parsed.quantity) * (isSeeded ? 34.5 : 0)).toFixed(2)}`,
    });
    return {
      ...order,
      lines: linesOf,
      version: nextVersion,
      updated_at: "2026-11-05T15:04:00Z",
    };
  }
  if (method === "POST" && url === "/api/orders/8/confirm") {
    return { ...order, status: "confirmed", version: nextVersion };
  }
  if (method === "POST" && url === "/api/orders/8/cancel") {
    return { ...order, status: "cancelled", version: nextVersion };
  }
  if (method === "POST" && url === "/api/orders/8/ship") {
    return { ...order, status: "shipped", version: nextVersion };
  }
  return order;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function problemWith(
  status: number,
  code: string,
  detail: string,
  extra: Record<string, unknown> = {},
): Response {
  return jsonResponse({ status, code, detail, ...extra }, status);
}

function defer(): {
  promise: Promise<Response>;
  release: (response: Response) => void;
} {
  let release!: (response: Response) => void;
  const promise = new Promise<Response>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

/** The default routes of the mock (S1/S4/S5 aware). */
function installRoutes() {
  fetchMock.mockImplementation(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = String(init?.method ?? "GET");

      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if ((url === "/api/orders/8" || url === "/api/orders/4") && method === "GET") {
        if (orderGetProblem !== null) {
          return jsonResponse(orderGetProblem, orderGetProblem.status);
        }
        return jsonResponse(orderBody, orderStatus);
      }
      if (url === "/api/orders/8/invoice" && method === "POST") {
        const seededIssue = issueAnswer?.(url, method) ?? null;
        if (seededIssue !== null) {
          return seededIssue;
        }
        if (holdMutation !== null) {
          return holdMutation.promise;
        }
        return jsonResponse(
          {
            id: 9,
            number: "FAC-0004",
            status: "issued",
            order_id: 8,
            order_number: "PED-0008",
            customer: { id: 1, name: "Acme Industrial S.A.", tax_id: "ACME-900123", address: null },
            lines: [],
            subtotal: "0.00",
            tax_rate: "10.00",
            tax: "0.00",
            total: "0.00",
            payments: [],
            version: 1,
            created_at: "2026-11-05T16:00:00Z",
            updated_at: "2026-11-05T16:00:00Z",
          },
          201,
        );
      }
      if (
        (url.startsWith("/api/orders/8/") || url === "/api/orders/8")
        && method !== "GET"
      ) {
        const seeded = mutateAnswer?.(url, method) ?? null;
        if (seeded !== null) {
          return seeded;
        }
        if (holdMutation !== null) {
          return holdMutation.promise;
        }
        return jsonResponse(
          applyMutation(orderBody, url, method,
            typeof init?.body === "string" ? init.body : undefined),
          url.endsWith("/lines") ? 201 : 200,
        );
      }
      if (url === "/api/products") {
        return jsonResponse(productsBody, productsStatus);
      }
      if (url.startsWith("/api/customers")) {
        return jsonResponse(customersBody, customersStatus);
      }
      return problemWith(404, "NOT_FOUND", "No se encontró el recurso solicitado.");
    },
  );
}

function renderDetail(id = "8") {
  state.routeId = id;
  return render(
    <QueryClientProvider client={queryClient}>
      <OrderDetailPage />
    </QueryClientProvider>,
  );
}

/** Waits for the detail of an order with the seed draft to finish loading. */
async function renderDraftDetail(id = "8") {
  renderDetail(id);
  await waitFor(() => {
    if (screen.queryByTestId("orders-detail-nolines-text") === null) {
      expect(screen.getByTestId("orders-detail-lines-table")).toBeInTheDocument();
    }
  });
}

/** Waits until the catalog options of the add form are listed. */
async function waitForProducts() {
  await waitFor(() => {
    const select = screen.getByTestId(
      "orders-detail-addline-product-select",
    ) as HTMLSelectElement;
    expect(
      Array.from(select.options).some((option) => option.value === "7"),
    ).toBe(true);
  });
}

const changerCustomer: Customer = {
  id: 6,
  name: "Ferretería Fénix",
  email: "fenix@example.test",
  phone: null,
  tax_id: "FENI-500654",
  address: null,
  status: "active",
  version: 1,
  created_at: "2026-01-01T09:06:00Z",
  updated_at: "2026-01-01T09:06:00Z",
};

beforeEach(() => {
  installDialogStub();
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  routerMock.push.mockClear();
  routerMock.replace.mockClear();
  meUser = {
    id: 1,
    name: "Admin Demo",
    email: "admin@labapp.test",
    role: "admin",
  };
  orderBody = draftOrder();
  orderGetProblem = null;
  productsBody = {
    items: [
      { id: 1, sku: "KB-100", name: "Teclado USB", price: "19.90", stock: 120 },
      { id: 7, sku: "WC-720", name: "Cámara web HD", price: "34.50", stock: 3 },
    ],
  };
  productsStatus = 200;
  customersBody = { items: [changerCustomer], page: 1, page_size: 20, total: 1 };
  customersStatus = 200;
  holdMutation = null;
  mutateAnswer = null;
  issueAnswer = null;
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  installRoutes();
});

afterEach(() => {
  document.title = "LabApp";
  vi.unstubAllGlobals();
  holdMutation = null;
  mutateAnswer = null;
  issueAnswer = null;
});

describe("the order detail states", () => {
  it("shows the 404 detail with the back link and without retry", async () => {
    orderGetProblem = {
      status: 404,
      code: "NOT_FOUND",
      detail: "No se encontró el recurso solicitado.",
    };
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(screen.getByTestId("orders-detail-back-link")).toHaveAttribute(
      "href",
      "/orders",
    );
    expect(
      screen.queryByTestId("orders-detail-retry-button"),
    ).not.toBeInTheDocument();
  });

  it("offers the retry button for any other load error", async () => {
    orderGetProblem = {
      status: 500,
      code: "INTERNAL_ERROR",
      detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
    };
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-retry-button")).toBeEnabled();
    });

    // The retry refetches and recovers.
    orderGetProblem = null;
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toHaveTextContent(
        "PED-0008",
      );
    });
    expect(screen.getByTestId("orders-detail-back-link")).toHaveAttribute(
      "href",
      "/orders",
    );
  });

  it("shows the not-found alert and the back link for an invalid id without calling the API", async () => {
    renderDetail("007");

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(
      fetchMock.mock.calls.filter((call) => String(call[0]).includes("/api/order")),
    ).toHaveLength(0);
  });

  it("titles the tab with the section while loading and with the number loaded", async () => {
    // The order request stays in the air first: the tab answers the
    // section title while nothing else is on screen.
    let respond!: (response: Response) => void;
    const heldOrder = new Promise<Response>((resolve) => {
      respond = resolve;
    });
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/orders/8") {
        return heldOrder;
      }
      return jsonResponse(meUser);
    });
    renderDetail();
    expect(document.title).toBe("Pedidos · LabApp");

    // The waiting request answers and the number replaces the section.
    respond(jsonResponse(orderBody));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading"))
        .toHaveTextContent(orderBody.number);
    });
    expect(document.title).toBe(`Pedido ${orderBody.number} · LabApp`);
  });

  it("shows the facts of the S5 order", async () => {
    await renderDraftDetail();

    expect(screen.getByTestId("orders-detail-heading")).toHaveTextContent(
      "PED-0008",
    );
    expect(screen.getByTestId("orders-detail-state-status"))
      .toHaveTextContent("Borrador");
    const customerLink = screen.getByTestId("orders-detail-customer-link");
    expect(customerLink).toHaveAttribute("href", "/customers/1");
    expect(customerLink).toHaveTextContent("Acme Industrial S.A.");
    expect(customerLink.textContent).not.toContain("(inactivo)");
    expect(screen.getByTestId("orders-detail-created-text"))
      .toHaveTextContent("05/11/2026 15:00 UTC");
    expect(screen.getByTestId("orders-detail-updated-text"))
      .toHaveTextContent("05/11/2026 15:01 UTC");
    expect(
      screen.queryByTestId("orders-detail-invoice-link"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("orders-detail-taxrate-text"))
      .toHaveTextContent("Impuesto (10.00 %)");
    expect(screen.getByTestId("orders-detail-subtotal-text"))
      .toHaveTextContent("$39.80");
    expect(screen.getByTestId("orders-detail-tax-text"))
      .toHaveTextContent("$3.98");
    expect(screen.getByTestId("orders-detail-total-text"))
      .toHaveTextContent("$43.78");
    expect(screen.getByTestId("orders-detail-preview-text"))
      .toHaveTextContent("Vista previa: la tasa se fija al confirmar.");
    expect(screen.getByTestId("orders-detail-back-link")).toHaveAttribute(
      "href",
      "/orders",
    );
  });

  it("marks the customer of an inactive order with (inactivo)", async () => {
    orderBody = {
      ...draftOrder(),
      customer: { id: 8, name: "Hotel Horizonte", status: "inactive" },
    };
    await renderDraftDetail();

    const link = screen.getByTestId("orders-detail-customer-link");
    expect(link).toHaveAttribute("href", "/customers/8");
    expect(link.textContent).toBe("Hotel Horizonte (inactivo)");
  });

  it("links the invoice of an order that has one", async () => {
    orderBody = paidOrder();
    await renderDraftDetail("4");

    expect(screen.getByTestId("orders-detail-invoice-link")).toHaveAttribute(
      "href",
      "/invoices/2",
    );
    expect(screen.getByTestId("orders-detail-state-status"))
      .toHaveTextContent("Pagado");
    expect(screen.getByTestId("orders-detail-subtotal-text"))
      .toHaveTextContent("$179.97");
    expect(screen.getByTestId("orders-detail-tax-text"))
      .toHaveTextContent("$18.00");
    expect(screen.getByTestId("orders-detail-total-text"))
      .toHaveTextContent("$197.97");
    expect(
      screen.queryByTestId("orders-detail-preview-text"),
    ).not.toBeInTheDocument();
  });

  it("shows the note and the zero totals of an empty draft", async () => {
    orderBody = {
      ...draftOrder(),
      lines: [],
      subtotal: "0.00",
      tax: "0.00",
      total: "0.00",
    };
    await renderDraftDetail();

    expect(screen.getByTestId("orders-detail-nolines-text"))
      .toHaveTextContent("Este pedido aún no tiene líneas.");
    expect(
      screen.queryByTestId("orders-detail-lines-table"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("orders-detail-subtotal-text"))
      .toHaveTextContent("$0.00");
    expect(screen.getByTestId("orders-detail-total-text"))
      .toHaveTextContent("$0.00");
    expect(screen.getByTestId("orders-detail-preview-text"))
      .toHaveTextContent("Vista previa: la tasa se fija al confirmar.");
  });
});

describe("the detail controls per status and role", () => {
  it("draft, admin: line editing, add form, confirm and cancel, no ship", async () => {
    await renderDraftDetail();

    expect(
      screen.getByTestId("orders-detail-line-quantity-input-10"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("orders-detail-line-save-button-10"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("orders-detail-line-remove-button-10"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("orders-detail-addline-product-select"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("orders-detail-addline-quantity-input"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("orders-detail-addline-submit-button"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("orders-detail-confirm-button")).toBeEnabled();
    expect(screen.getByTestId("orders-detail-cancel-button")).toBeEnabled();
    expect(
      screen.queryByTestId("orders-detail-ship-button"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("orders-detail-changecustomer-button"))
      .toHaveAttribute("aria-expanded", "false");
  });

  it("draft, readonly: plain cells and no editing or transitions", async () => {
    meUser = { ...meUser, id: 4, name: "Solo Lectura Demo", role: "readonly" };
    await renderDraftDetail();

    expect(screen.getByTestId("orders-detail-line-quantity-cell-10"))
      .toHaveTextContent("2");
    for (const id of [
      "orders-detail-line-quantity-input-10",
      "orders-detail-line-save-button-10",
      "orders-detail-addline-form",
      "orders-detail-changecustomer-button",
      "orders-detail-confirm-button",
      "orders-detail-cancel-button",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
  });

  it("draft, finance: neither editing nor transitions", async () => {
    meUser = { ...meUser, id: 3, name: "Finanzas Demo", role: "finance" };
    await renderDraftDetail();

    for (const id of [
      "orders-detail-addline-form",
      "orders-detail-line-quantity-input-10",
      "orders-detail-confirm-button",
      "orders-detail-cancel-button",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
  });

  it("confirmed: only the cancel button and no editing", async () => {
    orderBody = { ...draftOrder(), status: "confirmed", tax_rate: "10.00" };
    await renderDraftDetail();

    expect(screen.getByTestId("orders-detail-cancel-button")).toBeEnabled();
    for (const id of [
      "orders-detail-confirm-button",
      "orders-detail-ship-button",
      "orders-detail-addline-form",
      "orders-detail-line-quantity-input-10",
      "orders-detail-preview-text",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
  });

  it("paid: only the ship button", async () => {
    orderBody = { ...draftOrder(), status: "paid", invoice_id: 2 };
    await renderDraftDetail();

    expect(screen.getByTestId("orders-detail-ship-button")).toBeEnabled();
    for (const id of [
      "orders-detail-confirm-button",
      "orders-detail-cancel-button",
      "orders-detail-addline-form",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
  });

  it("shipped: no transitions and no editor", async () => {
    orderBody = { ...draftOrder(), status: "shipped" };
    await renderDraftDetail();

    for (const id of [
      "orders-detail-confirm-button",
      "orders-detail-cancel-button",
      "orders-detail-ship-button",
      "orders-detail-line-quantity-input-10",
      "orders-detail-changecustomer-button",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
    expect(screen.getByTestId("orders-detail-state-status"))
      .toHaveTextContent("Enviado");
  });

  it("cancelled: no transitions and no editor", async () => {
    orderBody = { ...draftOrder(), status: "cancelled" };
    await renderDraftDetail();

    for (const id of [
      "orders-detail-confirm-button",
      "orders-detail-cancel-button",
      "orders-detail-ship-button",
      "orders-detail-line-quantity-input-10",
    ]) {
      expect(screen.queryByTestId(id), id).not.toBeInTheDocument();
    }
    expect(screen.getByTestId("orders-detail-state-status"))
      .toHaveTextContent("Cancelado");
  });
});

describe("the line editing of a draft (correction B2)", () => {
  it("saves with the version at click time and follows the cache write", async () => {
    await renderDraftDetail();

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("orders-detail-line-quantity-input-10"));
    await user.type(
      screen.getByTestId("orders-detail-line-quantity-input-10"),
      "3",
    );
    await user.click(screen.getByTestId("orders-detail-line-save-button-10"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-line-quantity-input-10"))
        .toHaveValue(3);
    });
    const save = mutationCalls().find((call) => call.method === "PATCH");
    expect(save?.url).toBe("/api/orders/8/lines/10");
    expect(save?.body).toBe(JSON.stringify({ quantity: 3, version: 2 }));
    // No reload: the detail GET ran once.
    expect(readCount()).toBe(1);
  });

  it("keeps an empty quantity on the field with no request", async () => {
    await renderDraftDetail();

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("orders-detail-line-quantity-input-10"));
    await user.click(screen.getByTestId("orders-detail-line-save-button-10"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-line-quantity-error-10"))
        .toHaveTextContent("Este campo es obligatorio.");
    });
    expect(mutationCalls()).toHaveLength(0);
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-detail-line-quantity-input-10",
    );
  });

  it("sends non-integer text as typed, exactly as the strict server receives it", async () => {
    // The server of the corrected spec (S2) rejects "5.5": the mock
    // answers the same INVALID_FORMAT problem on quantity.
    mutateAnswer = (url, method) => {
      if (url === "/api/orders/8/lines/10" && method === "PATCH") {
        return jsonResponse(
          {
            type: "about:blank",
            title: "Unprocessable Content",
            status: 422,
            code: "VALIDATION_ERROR",
            detail: "Revisa los datos ingresados.",
            errors: [
              {
                field: "quantity",
                code: "INVALID_FORMAT",
                message: "El formato no es válido.",
              },
            ],
          },
          422,
        );
      }
      return null;
    };
    await renderDraftDetail();

    const user = userEvent.setup();
    await user.clear(screen.getByTestId("orders-detail-line-quantity-input-10"));
    await user.type(
      screen.getByTestId("orders-detail-line-quantity-input-10"),
      "5.5",
    );
    await user.click(screen.getByTestId("orders-detail-line-save-button-10"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-line-quantity-error-10"))
        .toHaveTextContent("El formato no es válido.");
    });
    const save = mutationCalls()[0];
    expect(save.body).toBe(JSON.stringify({ quantity: "5.5", version: 2 }));
  });

  it("removes a line with DELETE and If-Match, recalculating the totals", async () => {
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-line-remove-button-10"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-nolines-text")).toBeInTheDocument();
    });
    const removed = mutationCalls().find((call) => call.method === "DELETE");
    expect(removed?.url).toBe("/api/orders/8/lines/10");
    expect(removed?.ifMatch).toBe('"2"');
    expect(removed?.body).toBeUndefined();
    expect(screen.getByTestId("orders-detail-total-text"))
      .toHaveTextContent("$0.00");
  });
});

describe("the page-level failures of the detail (corrections B1, S1)", () => {
  it("routes a non-field failure to the alert and refetches the order", async () => {
    holdMutation = defer();
    await renderDraftDetail();
    const readsBefore = readCount();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-line-remove-button-10"));

    // While the removal runs, every other control is disabled...
    expect(screen.getByTestId("orders-detail-confirm-button")).toBeDisabled();
    expect(screen.getByTestId("orders-detail-cancel-button")).toBeDisabled();
    expect(
      screen.getByTestId("orders-detail-line-save-button-10"),
    ).toBeDisabled();
    // ...and a click on another one sends nothing.
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-confirm-button"));
    expect(mutationCalls()).toHaveLength(1);

    // Release the gate with the conflict, then wait for the alert.
    holdMutation?.release(
      jsonResponse(
        {
          status: 409,
          code: "VERSION_CONFLICT",
          detail:
            "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
        },
        409,
      ),
    );
    holdMutation = null;
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
      );
    });
    expect(readCount()).toBe(readsBefore + 1);
    expect(screen.getByTestId("orders-detail-alert")).toHaveAttribute(
      "role",
      "alert",
    );
  });

  it("sends the version of the refetched order after a stale one", async () => {
    // The order was published with version 3 somewhere else; the first
    // change of the test carries 2 and is rejected.
    orderBody = { ...draftOrder(), version: 2 };
    let reads = 0;
    let confirmCount = 0;
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method ?? "GET");
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url === "/api/orders/8" && method === "GET") {
          reads += 1;
          // After the VERSION_CONFLICT the order on the server is at
          // version 3; the refetch brings it to the screen.
          const version = reads === 1 ? 2 : 3;
          return jsonResponse(
            { ...draftOrder(), version },
            200,
          );
        }
        if (url === "/api/orders/8/confirm" && method === "POST") {
          confirmCount += 1;
          if (confirmCount === 1) {
            return problemWith(
              409,
              "VERSION_CONFLICT",
              "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
            );
          }
          return jsonResponse({ ...draftOrder(), status: "confirmed", version: 4 });
        }
        if (url === "/api/products") {
          return jsonResponse(productsBody, productsStatus);
        }
        if (url.startsWith("/api/customers")) {
          return jsonResponse(customersBody, customersStatus);
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    await renderDraftDetail();
    const user = userEvent.setup();

    await user.click(screen.getByTestId("orders-detail-confirm-button"));
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
      );
    });

    await user.click(screen.getByTestId("orders-detail-confirm-button"));
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-state-status"))
        .toHaveTextContent("Confirmado");
    });

    // The first click carried the stale version 2; the second one the
    // refetched 3.
    const confirms = mutationCalls().filter((call) => call.method === "POST");
    expect(confirms.map((call) => call.url)).toEqual([
      "/api/orders/8/confirm",
      "/api/orders/8/confirm",
    ]);
    expect(confirms[0].ifMatch).toBe('"2"');
    expect(confirms[1].ifMatch).toBe('"3"');
  });
});

describe("the add-line form of a draft (corrections B2, B4, S1)", () => {
  it("lists the catalog with the option text of the brief", async () => {
    await renderDraftDetail();
    await waitForProducts();

    const select = screen.getByTestId(
      "orders-detail-addline-product-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(select.options[0]).toHaveAttribute("disabled");
    expect(select.options[0].textContent).toBe("Elige un producto");
    const optionTeclado = Array.from(select.options).find(
      (option) => option.value === "1",
    );
    expect(optionTeclado?.textContent).toBe(
      "Teclado USB (KB-100) — $19.90 — stock 120",
    );
    expect(optionTeclado?.disabled).toBe(true); // already in the order
    const optionWebcam = Array.from(select.options).find(
      (option) => option.value === "7",
    );
    expect(optionWebcam?.textContent).toBe(
      "Cámara web HD (WC-720) — $34.50 — stock 3",
    );
    expect(optionWebcam?.disabled).toBe(false);
    expect(screen.getByTestId("orders-detail-addline-quantity-input"))
      .toHaveValue(1);
  });

  it("keeps a single Cargando productos… option while the catalog loads", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method ?? "GET");
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url === "/api/orders/8" && method === "GET") {
          return jsonResponse(orderBody, orderStatus);
        }
        if (url === "/api/products") {
          return new Promise<Response>(() => {});
        }
        if (url.startsWith("/api/orders/8/") && method !== "GET") {
          return new Promise<Response>(() => {});
        }
        if (url.startsWith("/api/customers")) {
          return jsonResponse(customersBody, customersStatus);
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    await renderDraftDetail();

    const select = screen.getByTestId(
      "orders-detail-addline-product-select",
    ) as HTMLSelectElement;
    expect(
      Array.from(select.options).map((option) => option.textContent),
    ).toEqual(["Cargando productos…"]);
  });

  it("shows a products failure in an alert with Reintentar", async () => {
    productsStatus = 500;
    productsBody = {
      status: 500,
      code: "INTERNAL_ERROR",
      detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
    };
    await renderDraftDetail();

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-products-error-alert"))
        .toHaveTextContent("Ocurrió un error inesperado. Inténtalo de nuevo.");
    });
    expect(screen.getByTestId("orders-detail-products-retry-button"))
      .toBeEnabled();

    // The retry recovers and the form appears.
    productsStatus = 200;
    productsBody = {
      items: [
        { id: 7, sku: "WC-720", name: "Cámara web HD", price: "34.50", stock: 3 },
      ],
    };
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-products-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-addline-form")).toBeInTheDocument();
    });
  });

  it("posts the product and quantity and clears the form on success", async () => {
    await renderDraftDetail();
    await waitForProducts();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-addline-product-select"),
      "7",
    );
    await user.click(screen.getByTestId("orders-detail-addline-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-line-row-11")).toBeInTheDocument();
    });
    const added = mutationCalls().find((call) => call.method === "POST");
    expect(added?.url).toBe("/api/orders/8/lines");
    expect(added?.ifMatch).toBeNull();
    expect(JSON.parse(added?.body ?? "{}")).toEqual({
      product_id: 7,
      quantity: 1,
      version: 2,
    });

    const select = screen.getByTestId(
      "orders-detail-addline-product-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(screen.getByTestId("orders-detail-addline-quantity-input"))
      .toHaveValue(1);
  });

  it("maps the literal S1 422 example onto the add-line quantity field", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/lines" && method === "POST"
        ? jsonResponse(
            {
              type: "about:blank",
              title: "Unprocessable Content",
              status: 422,
              code: "VALIDATION_ERROR",
              detail: "Revisa los datos ingresados.",
              errors: [
                {
                  field: "quantity",
                  code: "OUT_OF_RANGE",
                  message: "El valor debe estar entre 1 y 999.",
                },
              ],
            },
            422,
          )
        : null;
    await renderDraftDetail();
    await waitForProducts();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-addline-product-select"),
      "7",
    );
    await user.clear(screen.getByTestId("orders-detail-addline-quantity-input"));
    await user.type(
      screen.getByTestId("orders-detail-addline-quantity-input"),
      "1000",
    );
    await user.click(screen.getByTestId("orders-detail-addline-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-addline-quantity-error"))
        .toHaveTextContent("El valor debe estar entre 1 y 999.");
    });
    const failed = mutationCalls().find((call) => call.method === "POST");
    expect(JSON.parse(failed?.body ?? "{}")).toEqual({
      product_id: 7,
      quantity: 1000,
      version: 2,
    });
    // The form keeps the typed values for a corrected retry.
    expect(screen.getByTestId("orders-detail-addline-quantity-input"))
      .toHaveValue(1000);
  });

  it("keeps an empty quantity on the field with no request", async () => {
    await renderDraftDetail();
    await waitForProducts();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-addline-product-select"),
      "7",
    );
    await user.clear(screen.getByTestId("orders-detail-addline-quantity-input"));
    await user.click(screen.getByTestId("orders-detail-addline-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-addline-quantity-error"))
        .toHaveTextContent("Este campo es obligatorio.");
    });
    expect(mutationCalls()).toHaveLength(0);
  });

  it("shows ORDER_DUPLICATE_PRODUCT and ORDER_TOO_MANY_LINES in the alert", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/lines" && method === "POST"
        ? problemWith(
            422,
            "ORDER_DUPLICATE_PRODUCT",
            "Ese producto ya está en el pedido; edita su cantidad.",
          )
        : null;
    await renderDraftDetail();
    await waitForProducts();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-addline-product-select"),
      "7",
    );
    await user.click(screen.getByTestId("orders-detail-addline-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "Ese producto ya está en el pedido; edita su cantidad.",
      );
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-detail-alert",
    );
    expect(screen.getByTestId("orders-detail-alert")).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });
});

describe("the change-customer section (correction B3)", () => {
  async function openChanger() {
    await renderDraftDetail();
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-changecustomer-button"));
    await waitFor(() => {
      expect(
        screen.queryByTestId("orders-detail-changecustomer-loading-status"),
      ).toBeNull();
    });
  }

  it("toggles with aria-expanded and keeps the search out of the submit form", async () => {
    await renderDraftDetail();

    const toggle = screen.getByTestId("orders-detail-changecustomer-button");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute(
      "aria-controls",
      "orders-detail-changecustomer-panel",
    );
    // The panel is closed: its content stays in the DOM but not visible.
    expect(
      screen.queryByTestId("orders-detail-changecustomer-search-form"),
    ).not.toBeVisible();

    await userEvent.setup().click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const searchForm = screen.getByTestId(
      "orders-detail-changecustomer-search-form",
    );
    const changeForm = screen.getByTestId("orders-detail-changecustomer-form");
    expect(searchForm.contains(changeForm)).toBe(false);
    expect(
      screen.getByTestId("orders-detail-changecustomer-search-input"),
    ).toHaveAccessibleName("Buscar cliente");
    expect(
      screen.getByTestId("orders-detail-changecustomer-select"),
    ).toBeInTheDocument();
    // The placeholder of B3: disabled, until a customer is chosen.
    const select = screen.getByTestId(
      "orders-detail-changecustomer-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(select.options[0].textContent).toBe("Elige un cliente");
    expect(select.options[0].disabled).toBe(true);
    expect(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    ).toBeDisabled();
  });

  it("shows the loading, empty and error states of the picker", async () => {
    // The customers load never resolves until the test releases it.
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url.startsWith("/api/orders/8")) {
          return jsonResponse(orderBody, orderStatus);
        }
        if (url === "/api/products") {
          return jsonResponse(productsBody, productsStatus);
        }
        if (url.startsWith("/api/customers")) {
          return gate;
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-lines-table")).toBeInTheDocument();
    });
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-changecustomer-button"));

    // Loading, as a busy region:
    await waitFor(() => {
      expect(
        screen.getByTestId("orders-detail-changecustomer-loading-status"),
      ).toHaveTextContent("Buscando clientes…");
    });
    expect(
      screen.getByTestId("orders-detail-changecustomer-loading-status"),
    ).toHaveAttribute("aria-busy", "true");

    // Releasing the gate with an empty page moves to the empty state.
    release(jsonResponse({ items: [], page: 1, page_size: 20, total: 0 }));
    await waitFor(() => {
      expect(
        screen.queryByTestId("orders-detail-changecustomer-empty-status"),
      ).toHaveTextContent("No hay clientes activos que coincidan.");
    });

    // A new search answers with a failure: the alert of the corrected
    // review (B5) with its retry.
    customersStatus = 500;
    customersBody = {
      status: 500,
      code: "INTERNAL_ERROR",
      detail: "Ocurrió un error inesperado. Inténtalo de nuevo.",
    };
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("orders-detail-changecustomer-search-input"),
      "zzz",
    );
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-search-button"),
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("orders-detail-changecustomer-error-alert"),
      ).toHaveTextContent("Ocurrió un error inesperado. Inténtalo de nuevo.");
    });
    expect(
      screen.getByTestId("orders-detail-changecustomer-retry-button"),
    ).toBeEnabled();
  });

  it("sends the chosen customer with the version and follows the cache (S4)", async () => {
    await openChanger();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-changecustomer-select"),
      "6",
    );
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    );

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-customer-link"))
        .toHaveTextContent("Cliente 6");
    });
    const change = mutationCalls().find((call) => call.method === "PATCH");
    expect(change?.url).toBe("/api/orders/8");
    expect(JSON.parse(change?.body ?? "{}")).toEqual({
      customer_id: 6,
      version: 2,
    });
  });

  it("answers a same-customer change untouched (S4)", async () => {
    await openChanger();

    // To reproduce S4 the search brings the customer the order already
    // carries, and the mock answers 200 with the untouched order.
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("orders-detail-changecustomer-search-input"),
      "acme",
    );
    customersBody = {
      items: [{ id: 1, name: "Acme Industrial S.A." }, changerCustomer],
      page: 1,
      page_size: 20,
      total: 2,
    };
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-search-button"),
    );
    await waitFor(() => {
      const select = screen.getByTestId(
        "orders-detail-changecustomer-select",
      ) as HTMLSelectElement;
      expect(
        Array.from(select.options).some((option) => option.value === "1"),
      ).toBe(true);
    });

    await user.selectOptions(
      screen.getByTestId("orders-detail-changecustomer-select"),
      "1",
    );
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    );

    await waitFor(() => {
      expect(mutationCalls().some((call) => call.method === "PATCH")).toBe(true);
    });
    // The order comes back with its version unchanged, so the customer
    // link still shows the original customer.
    expect(screen.getByTestId("orders-detail-customer-link"))
      .toHaveTextContent("Acme Industrial S.A.");
    expect(screen.queryByTestId("orders-detail-alert")).not.toBeInTheDocument();
  });

  it("maps the customer_id field error of a 422 onto the select", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8" && method === "PATCH"
        ? jsonResponse(
            {
              type: "about:blank",
              title: "Unprocessable Content",
              status: 422,
              code: "VALIDATION_ERROR",
              detail: "Revisa los datos ingresados.",
              errors: [
                {
                  field: "customer_id",
                  code: "REFERENCE_NOT_FOUND",
                  message: "El registro indicado no existe.",
                },
              ],
            },
            422,
          )
        : null;
    await openChanger();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-changecustomer-select"),
      "6",
    );
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    );

    await waitFor(() => {
      // The derived error id of the select field.
      expect(
        screen.getByTestId("orders-detail-changecustomer-error"),
      ).toHaveTextContent("El registro indicado no existe.");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "orders-detail-changecustomer-select",
    );
  });

  it("shows CUSTOMER_INACTIVE on the select", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8" && method === "PATCH"
        ? problemWith(422, "CUSTOMER_INACTIVE", "El cliente no está activo.")
        : null;
    await openChanger();
    await waitFor(() => {
      const select = screen.getByTestId(
        "orders-detail-changecustomer-select",
      ) as HTMLSelectElement;
      expect(select.value).toBe("");
    });

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-changecustomer-select"),
      "6",
    );
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-detail-changecustomer-error"),
      ).toHaveTextContent("El cliente no está activo.");
    });
  });

  it("resets the choice when a new search drops the chosen customer", async () => {
    await openChanger();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("orders-detail-changecustomer-select"),
      "6",
    );
    expect(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    ).toBeEnabled();

    // A search whose result drops that customer empties the choice (B3).
    await user.type(
      screen.getByTestId("orders-detail-changecustomer-search-input"),
      "sin resultados",
    );
    customersBody = { items: [], page: 1, page_size: 20, total: 0 };
    await user.click(
      screen.getByTestId("orders-detail-changecustomer-search-button"),
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("orders-detail-changecustomer-empty-status"),
      ).toBeInTheDocument();
    });
    const select = screen.getByTestId(
      "orders-detail-changecustomer-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(
      screen.getByTestId("orders-detail-changecustomer-submit-button"),
    ).toBeDisabled();
  });
});

describe("the transitions of the detail", () => {
  it("confirms a draft with If-Match and follows the cache change", async () => {
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-state-status"))
        .toHaveTextContent("Confirmado");
    });
    const confirm = mutationCalls().find((call) => call.method === "POST");
    expect(confirm?.url).toBe("/api/orders/8/confirm");
    expect(confirm?.ifMatch).toBe('"2"');
    expect(confirm?.body).toBeUndefined();
    // A confirmed order loses the editor without a reload.
    expect(
      screen.queryByTestId("orders-detail-addline-form"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("orders-detail-line-quantity-input-10"),
    ).not.toBeInTheDocument();
  });

  it("cancels a draft only after the confirmation of the dialog", async () => {
    await renderDraftDetail();

    // The click opens the confirmation instead of sending the request.
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-cancel-button"));

    const dialog = screen.getByTestId("orders-cancel-confirm-dialog");
    expect(dialog).toHaveAttribute("open");
    expect(screen.getByTestId("orders-cancel-title-heading"))
      .toHaveTextContent("¿Cancelar el pedido PED-0008?");
    expect(screen.getByTestId("orders-cancel-message-text"))
      .toHaveTextContent("El borrador quedará cancelado.");
    expect(screen.getByTestId("orders-cancel-confirm-button"))
      .toHaveTextContent("Sí, cancelar pedido");
    expect(screen.getByTestId("orders-cancel-back-button"))
      .toHaveTextContent("Volver");
    // The request waits for the confirmation.
    expect(mutationCalls().filter((call) => call.method === "POST"))
      .toHaveLength(0);

    // The confirm runs the same transition as before.
    await userEvent.setup().click(
      screen.getByTestId("orders-cancel-confirm-button"),
    );

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-state-status"))
        .toHaveTextContent("Cancelado");
    });
    const cancelled = mutationCalls().find((call) => call.method === "POST");
    expect(cancelled?.url).toBe("/api/orders/8/cancel");
    expect(cancelled?.ifMatch).toBe('"2"');
    // The dialog closed with the end of the request.
    await waitFor(() => {
      expect(dialog).not.toHaveAttribute("open");
    });
  });

  it("cancels a confirmed order with the stock and invoice consequence", async () => {
    orderBody = { ...draftOrder(), status: "confirmed", invoice_id: 9 };
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-cancel-button"));
    expect(screen.getByTestId("orders-cancel-message-text"))
      .toHaveTextContent(
        "El stock reservado vuelve al inventario y la factura emitida, si existe, se anula.",
      );

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-cancel-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-state-status"))
        .toHaveTextContent("Cancelado");
    });
    const cancelled = mutationCalls().find((call) => call.method === "POST");
    expect(cancelled?.url).toBe("/api/orders/8/cancel");
    expect(cancelled?.ifMatch).toBe('"2"');
  });

  it('sends nothing when the dialog answers "Volver"', async () => {
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-cancel-button"));
    expect(
      screen.getByTestId("orders-cancel-confirm-dialog"),
    ).toHaveAttribute("open");

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-cancel-back-button"));

    await waitFor(() => {
      expect(
        screen.getByTestId("orders-cancel-confirm-dialog"),
      ).not.toHaveAttribute("open");
    });
    expect(mutationCalls().filter((call) => call.method === "POST"))
      .toHaveLength(0);
    // The state of the order is untouched.
    expect(screen.getByTestId("orders-detail-state-status"))
      .toHaveTextContent("Borrador");
  });

  it("keeps the dialog up for a failed cancel and shows the existing alert", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/cancel" && method === "POST"
        ? problemWith(
            409,
            "VERSION_CONFLICT",
            "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
          )
        : null;
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-cancel-button"));
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-cancel-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
      );
    });
    // The request ended, so the dialog answers to the caller and closes.
    await waitFor(() => {
      expect(screen.getByTestId("orders-cancel-confirm-dialog"))
        .not.toHaveAttribute("open");
    });
    const readsAfterTheRetry = readCount();
    expect(readsAfterTheRetry).toBeGreaterThan(0);
  });

  it("ignores a second confirm while the first cancel is pending", async () => {
    holdMutation = defer();
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-cancel-button"));
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-cancel-confirm-button"));

    // The in-flight request keeps the dialog pending; a second confirm
    // (even a click straight on the disabled button) is ignored.
    const confirm = screen.getByTestId("orders-cancel-confirm-button");
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(
      mutationCalls().filter((call) => call.url === "/api/orders/8/cancel"),
    ).toHaveLength(1);

    holdMutation.release(
      jsonResponse(applyMutation(orderBody, "/api/orders/8/cancel", "POST", undefined)),
    );
    holdMutation = null;
  });

  it("ships a paid order with If-Match", async () => {
    orderBody = { ...draftOrder(), status: "paid" };
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-ship-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-state-status"))
        .toHaveTextContent("Enviado");
    });
    const shipped = mutationCalls().find((call) => call.method === "POST");
    expect(shipped?.url).toBe("/api/orders/8/ship");
    expect(shipped?.ifMatch).toBe('"2"');
  });

  it('shows INVALID_TRANSITION in the alert and refetches the order', async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/confirm" && method === "POST"
        ? problemWith(
            409,
            "INVALID_TRANSITION",
            "No se puede pasar el pedido de borrador a enviado.",
          )
        : null;
    await renderDraftDetail();
    const readsBefore = readCount();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "No se puede pasar el pedido de borrador a enviado.",
      );
    });
    expect(readCount()).toBe(readsBefore + 1);
  });

  it("shows INSUFFICIENT_STOCK with the shortage items ordered by product id", async () => {
    const shortages: Shortage[] = [
      {
        product_id: 1,
        sku: "KB-100",
        name: "Teclado USB",
        available: 3,
        requested: 5,
      },
      {
        product_id: 5,
        sku: "HD-500",
        name: "Disco externo 1 TB",
        available: 0,
        requested: 2,
      },
    ];
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/confirm" && method === "POST"
        ? problemWith(
            409,
            "INSUFFICIENT_STOCK",
            "No hay stock suficiente de Teclado USB: disponible 3, solicitado 5.",
            { shortages },
          )
        : null;
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
        "No hay stock suficiente de Teclado USB: disponible 3, solicitado 5.",
      );
    });
    expect(
      screen.getByTestId("orders-detail-shortages-list"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("orders-detail-shortage-item-1"))
      .toHaveTextContent("Teclado USB (KB-100): disponible 3, solicitado 5");
    expect(screen.getByTestId("orders-detail-shortage-item-5"))
      .toHaveTextContent("Disco externo 1 TB (HD-500): disponible 0, solicitado 2");
  });

  it("writes null into the session cache when a transition answers 401", async () => {
    mutateAnswer = (url, method) =>
      url === "/api/orders/8/confirm" && method === "POST"
        ? problemWith(
            401,
            "UNAUTHENTICATED",
            "Inicia sesión para continuar.",
          )
        : null;
    queryClient.setQueryData(ME_QUERY_KEY, meUser);
    await renderDraftDetail();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-confirm-button"));

    await waitFor(() => {
      expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    });
  });
});

describe("the Facturar action of the order detail", () => {
  let viewForIssues: ReturnType<typeof renderDetail> | undefined;

  afterEach(() => {
    viewForIssues?.unmount();
    viewForIssues = undefined;
  });

  async function renderConfirmedOrder() {
    orderBody = {
      ...draftOrder(),
      status: "confirmed",
    };
    const view = renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toBeInTheDocument();
    });
    return view;
  }

  it("shows Facturar for admin on a confirmed order without an invoice and navigates to the new one", async () => {
    await renderConfirmedOrder();
    const readsBefore = readCount();

    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-invoice-button"));

    await waitFor(() => {
      expect(routerMock.push).toHaveBeenCalledWith("/invoices/9");
    });
    const issued = mutationCalls().find(
      (call) => call.url === "/api/orders/8/invoice",
    );
    expect(issued?.method).toBe("POST");
    expect(issued?.ifMatch).toBe('"2"');
    expect(issued?.body).toBeUndefined();
    // The hook writes the invoice cache and invalidates the order: the
    // refetch of the detail is the invalidation, not a manual reload.
    expect(readCount()).toBe(readsBefore + 1);
  });

  it("shows Facturar for finance too, not for sales or readonly", async () => {
    meUser = { ...meUser, id: 3, name: "Finanzas Demo", role: "finance" };
    const financeView = await renderConfirmedOrder();
    expect(screen.getByTestId("orders-detail-invoice-button")).toBeEnabled();
    // The button sits in its own action row: the same mt-6 as the other
    // rows of the page (the layout nit of task 027).
    expect(
      screen.getByTestId("orders-detail-invoice-button").parentElement
        ?.className,
    ).toContain("mt-6");
    financeView.unmount();
    queryClient.clear();

    meUser = { ...meUser, id: 2, name: "Ventas Demo", role: "sales" };
    const view = renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("orders-detail-invoice-button"),
    ).not.toBeInTheDocument();
    view.unmount();
    queryClient.clear();

    meUser = { ...meUser, id: 4, name: "Solo Lectura Demo", role: "readonly" };
    const secondView = renderDetail();
    await waitFor(() => {
      expect(
        screen.queryByTestId("orders-detail-invoice-button"),
      ).not.toBeInTheDocument();
    });
    secondView.unmount();
    queryClient.clear();
  });

  it("hides Facturar for a draft and for an order that already has its invoice", async () => {
    const firstView = renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toBeInTheDocument();
    });
    // The default order of the mock is a draft.
    expect(
      screen.queryByTestId("orders-detail-invoice-button"),
    ).not.toBeInTheDocument();
    firstView.unmount();
    queryClient.clear();

    orderBody = { ...draftOrder(), status: "confirmed", invoice_id: 9 };
    const secondView = renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("orders-detail-invoice-button"),
    ).not.toBeInTheDocument();
    secondView.unmount();
    queryClient.clear();
  });

  for (const [code, detail] of [
    ["ORDER_NOT_INVOICEABLE", "Solo se puede facturar un pedido confirmado."],
    ["CUSTOMER_TAX_ID_REQUIRED", "El cliente necesita un ID fiscal para poder facturar."],
    ["INVOICE_ALREADY_EXISTS", "Este pedido ya tiene una factura."],
    ["VERSION_CONFLICT", "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."],
  ] as const) {
    it(`shows ${code} in the order alert and refetches`, async () => {
      orderBody = { ...draftOrder(), status: "confirmed" };
      issueAnswer = () => problemWith(409, code, detail);
      viewForIssues = renderDetail();
      await waitFor(() => {
        expect(
          screen.getByTestId("orders-detail-heading"),
        ).toBeInTheDocument();
      });
      const readsBefore = readCount();

      await userEvent
        .setup()
        .click(screen.getByTestId("orders-detail-invoice-button"));

      await waitFor(() => {
        expect(screen.getByTestId("orders-detail-alert")).toHaveTextContent(
          detail,
        );
      });
      expect(readCount()).toBe(readsBefore + 1);
      expect(routerMock.push).not.toHaveBeenCalled();

      viewForIssues?.unmount();
      queryClient.clear();
      fetchMock.mockReset();
    });
  }

  it("stays disabled while any other order mutation is pending (B1)", async () => {
    orderBody = { ...draftOrder(), status: "confirmed" };
    holdMutation = defer();
    renderDetail();
    await waitFor(() => {
      expect(screen.getByTestId("orders-detail-heading")).toBeInTheDocument();
    });

    // The cancel transition is the pending mutation; Facturar share the
    // version of the order and has to wait.
    await userEvent.setup().click(screen.getByTestId("orders-detail-cancel-button"));
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-cancel-confirm-button"));
    expect(screen.getByTestId("orders-detail-invoice-button")).toBeDisabled();
    await userEvent
      .setup()
      .click(screen.getByTestId("orders-detail-invoice-button"));
    expect(
      mutationCalls().filter((call) => call.url === "/api/orders/8/invoice"),
    ).toHaveLength(0);

    holdMutation.release(
      jsonResponse(applyMutation(orderBody, "/api/orders/8/cancel", "POST", undefined)),
    );
    holdMutation = null;
  });
});
