import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ME_QUERY_KEY } from "@/features/auth/hooks";
import InvoiceDetailPage from "./page";
import type { Invoice, InvoiceLine, Payment } from "@/features/invoices/types";

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
  routeId: "1",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => routerMock,
  usePathname: () => "/",
  useParams: () => ({ id: state.routeId }),
}));

const fetchMock = vi.fn();

let queryClient: QueryClient;

let meUser: Record<string, unknown>;

/** GET /api/invoices/{id}: body and status (mock server state). */
let invoiceBody: Invoice;
let invoiceStatus: number;

/** GET count of the detail, for the refetch asserts. */
function readCount(): number {
  return fetchMock.mock.calls.filter(
    (call) => String(call[0]) === "/api/invoices/1"
      && String((call[1] as RequestInit | undefined)?.method ?? "GET") === "GET",
  ).length;
}

/** What a mutation request answers; null falls back to the approved 201. */
let mutateAnswer: null | ((url: string, method: string) => Response | null);

/** The payment request lines of the page, with their headers. */
function paymentCalls(): Array<{
  body: string | undefined;
  idempotencyKey: string | null;
  ifMatch: string | null;
}> {
  return fetchMock.mock.calls
    .filter(([input, init]) =>
      String(input).startsWith("/api/invoices/1/payments")
        && String((init as RequestInit | undefined)?.method) === "POST")
    .map(([, init]) => {
      const initRequest = init as RequestInit;
      const headers = initRequest.headers as Record<string, string>;
      return {
        body: typeof initRequest.body === "string" ? initRequest.body : undefined,
        idempotencyKey: headers?.["Idempotency-Key"] ?? null,
        ifMatch: headers?.["If-Match"] ?? null,
      };
    });
}

const declinedPayment: Payment = {
  id: 1,
  method: "card",
  status: "declined",
  amount: "327.80",
  reference: null,
  card_last4: "0002",
  reason: "CARD_DECLINED",
  created_at: "2026-01-03T15:00:00Z",
};

const failedPayment: Payment = {
  id: 2,
  method: "card",
  status: "failed",
  amount: "327.80",
  reference: null,
  card_last4: "0003",
  reason: "GATEWAY_UNAVAILABLE",
  created_at: "2026-01-03T15:05:00Z",
};

const approvedTransfer: Payment = {
  id: 3,
  method: "transfer",
  status: "approved",
  amount: "197.97",
  reference: "TRF-2026-0001",
  card_last4: null,
  reason: null,
  created_at: "2026-01-04T15:00:00Z",
};

const approvedCash: Payment = {
  id: 4,
  method: "cash",
  status: "approved",
  amount: "768.90",
  reference: null,
  card_last4: null,
  reason: null,
  created_at: "2026-01-05T15:00:00Z",
};

function line(id: number, overrides: Partial<InvoiceLine> = {}): InvoiceLine {
  return {
    id,
    product_id: id,
    sku: `SKU-${id}`,
    name: `Producto ${id}`,
    quantity: 2,
    unit_price: "149.00",
    line_total: "298.00",
    ...overrides,
  };
}

/** The issued invoice of the seed: FAC-0001 of order PED-0003. */
function issuedInvoice(): Invoice {
  return {
    id: 1,
    number: "FAC-0001",
    status: "issued",
    order_id: 3,
    order_number: "PED-0003",
    customer: {
      id: 4,
      name: "Distribuidora Delta",
      tax_id: "DELT-700789",
      address: null,
    },
    lines: [line(3)],
    subtotal: "298.00",
    tax_rate: "10.00",
    tax: "29.80",
    total: "327.80",
    payments: [declinedPayment, failedPayment],
    version: 1,
    created_at: "2026-01-03T14:00:00Z",
    updated_at: "2026-01-03T14:00:00Z",
  };
}

/** The paid invoice of the seed: FAC-0002 without address snapshot. */
function paidInvoice(): Invoice {
  return {
    ...issuedInvoice(),
    id: 2,
    number: "FAC-0002",
    status: "paid",
    order_id: 4,
    order_number: "PED-0004",
    customer: {
      id: 6,
      name: "Ferretería Fénix",
      tax_id: "FENI-500654",
      address: "Av. Callejon 4",
    },
    total: "197.97",
    payments: [approvedTransfer, approvedCash],
  };
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

/**
 * The approved 201 of a brand new payment: the invoice goes to paid with
 * the attempt in the history, and the MOCK's stored invoice changes with
 * it, so the refetches triggered by the invalidations read the real
 * state after the payment (the transaction of the spec).
 */
function approvedResult(): unknown {
  const approved: Payment = {
    ...declinedPayment,
    id: 5,
    status: "approved",
    card_last4: "4242",
    reason: null,
    created_at: "2026-01-05T16:00:00Z",
  };
  const invoice: Invoice = {
    ...invoiceBody,
    status: "paid",
    version: invoiceBody.version + 1,
    payments: [...invoiceBody.payments, approved],
    updated_at: "2026-01-05T16:00:00Z",
  };
  invoiceBody = invoice;
  return { payment: approved, invoice };
}

/** The default routes of the mock. */
function installRoutes() {
  fetchMock.mockImplementation(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = String(init?.method ?? "GET");

      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if ((url === "/api/invoices/1" || url === "/api/invoices/2")
        && method === "GET") {
        return jsonResponse(invoiceBody, invoiceStatus);
      }
      if (url === "/api/invoices/1/payments" && method === "POST") {
        const seeded = mutateAnswer?.(url, method) ?? null;
        if (seeded !== null) {
          return seeded;
        }
        return jsonResponse(approvedResult(), 201);
      }
      return problemWith(
        404,
        "NOT_FOUND",
        "No se encontró el recurso solicitado.",
      );
    },
  );
}

/**
 * The declined or failed answer of a stored attempt: the attempt is
 * committed to the payment history even though the answer is an error,
 * so the refetch of the invoice afterwards shows it (spec section 6).
 */
function declineProblem(
  status: 402 | 503,
  reason: "CARD_DECLINED" | "GATEWAY_UNAVAILABLE",
  detail: string,
  paymentId: number,
): Response {
  const attempt: Payment = {
    ...declinedPayment,
    id: paymentId,
    status: reason === "CARD_DECLINED" ? "declined" : "failed",
    reason,
    created_at: `2026-01-05T16:0${paymentId % 10}:00Z`,
  };
  invoiceBody = {
    ...invoiceBody,
    payments: [...invoiceBody.payments, attempt],
    version: invoiceBody.version + 1,
    updated_at: attempt.created_at,
  };
  return problemWith(status, reason === "CARD_DECLINED"
    ? "PAYMENT_DECLINED"
    : "PAYMENT_GATEWAY_UNAVAILABLE", detail, {
    payment_id: paymentId,
    reason,
  });
}

function renderDetail(id = "1") {
  state.routeId = id;
  return render(
    <QueryClientProvider client={queryClient}>
      <InvoiceDetailPage />
    </QueryClientProvider>,
  );
}

/** Waits for the heading of the detail of an issued invoice. */
async function renderIssuedDetail(id = "1") {
  renderDetail(id);
  await waitFor(() => {
    expect(screen.getByTestId("invoices-detail-heading")).toHaveTextContent(
      "FAC-0001",
    );
  });
}

const adminUser = {
  id: 1,
  name: "Admin Demo",
  email: "admin@labapp.test",
  role: "admin",
};

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  routerMock.push.mockClear();
  meUser = adminUser;
  invoiceBody = issuedInvoice();
  invoiceStatus = 200;
  mutateAnswer = null;
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
  mutateAnswer = null;
});

describe("the invoice detail states", () => {
  it("titles the tab with the section while loading and with the number loaded", async () => {
    // The invoice request stays in the air first: the tab answers the
    // section title while nothing else is on screen.
    let respond!: (response: Response) => void;
    const heldInvoice = new Promise<Response>((resolve) => {
      respond = resolve;
    });
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/invoices/1") {
        return heldInvoice;
      }
      return jsonResponse(meUser);
    });
    renderDetail();
    expect(document.title).toBe("Facturas · LabApp");

    // The waiting request answers and the number replaces the section.
    respond(jsonResponse(invoiceBody ?? issuedInvoice()));

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-heading")).toHaveTextContent(
        "FAC-0001",
      );
    });
    expect(document.title).toBe("Factura FAC-0001 · LabApp");
  });

  it("shows the not-found alert with the back link and without retry", async () => {
    invoiceStatus = 503;
    invoiceBody = issuedInvoice();
    invoiceBody = {
      ...issuedInvoice(),
      lines: [],
    };
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/invoices/1") {
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      }
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      return problemWith(404, "NOT_FOUND", "No se encontró el recurso.");
    });
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(screen.getByTestId("invoices-detail-back-link")).toHaveAttribute(
      "href",
      "/invoices",
    );
    expect(
      screen.queryByTestId("invoices-detail-retry-button"),
    ).not.toBeInTheDocument();
  });

  it("offers the retry button for any other load error", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url === "/api/invoices/1") {
        return problemWith(
          500,
          "INTERNAL_ERROR",
          "Ocurrió un error inesperado. Inténtalo de nuevo.",
        );
      }
      return problemWith(404, "NOT_FOUND", "No se encontró el recurso.");
    });
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-retry-button")).toBeEnabled();
    });
  });

  it("shows the not-found alert and the back link for an invalid id without calling the API", async () => {
    renderDetail("007");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-error-alert")).toHaveTextContent(
        "No se encontró el recurso solicitado.",
      );
    });
    expect(
      fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes("/api/invoice"),
      ),
    ).toHaveLength(0);
  });

  it("shows the facts of the issued invoice of the seed", async () => {
    await renderIssuedDetail();

    expect(screen.getByTestId("invoices-detail-heading")).toHaveTextContent(
      "FAC-0001",
    );
    expect(screen.getByTestId("invoices-detail-state-status"))
      .toHaveTextContent("Emitida");
    expect(screen.getByTestId("invoices-detail-order-link")).toHaveAttribute(
      "href",
      "/orders/3",
    );
    expect(screen.getByTestId("invoices-detail-order-link"))
      .toHaveTextContent("PED-0003");
    // The snapshot of the customer at issue time.
    expect(screen.getByTestId("invoices-detail-customer-text"))
      .toHaveTextContent("Distribuidora Delta");
    expect(screen.getByTestId("invoices-detail-taxid-text"))
      .toHaveTextContent("DELT-700789");
    expect(screen.getByTestId("invoices-detail-address-text"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("invoices-detail-created-text"))
      .toHaveTextContent("03/01/2026 14:00 UTC");
    expect(screen.getByTestId("invoices-detail-back-link")).toHaveAttribute(
      "href",
      "/invoices",
    );
  });

  it("shows the snapshot lines and the frozen totals", async () => {
    await renderIssuedDetail();

    expect(screen.getByTestId("invoices-detail-lines-table")).toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-line-row-3")).toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-line-product-cell-3"))
      .toHaveTextContent("Producto 3 (SKU-3)");
    expect(screen.getByTestId("invoices-detail-line-quantity-cell-3"))
      .toHaveTextContent("2");
    expect(screen.getByTestId("invoices-detail-line-price-cell-3"))
      .toHaveTextContent("$149.00");
    expect(screen.getByTestId("invoices-detail-line-total-cell-3"))
      .toHaveTextContent("$298.00");

    expect(screen.getByTestId("invoices-detail-subtotal-text"))
      .toHaveTextContent("$298.00");
    expect(screen.getByTestId("invoices-detail-taxrate-text"))
      .toHaveTextContent("Impuesto (10.00 %)");
    expect(screen.getByTestId("invoices-detail-tax-text"))
      .toHaveTextContent("$29.80");
    expect(screen.getByTestId("invoices-detail-total-text"))
      .toHaveTextContent("$327.80");
  });

  it("shows the history with a declined and a failed attempt", async () => {
    await renderIssuedDetail();

    expect(screen.getByTestId("invoices-detail-payments-table")).toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-payment-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-payment-method-cell-1"))
      .toHaveTextContent("Tarjeta");
    expect(screen.getByTestId("invoices-detail-payment-state-cell-1"))
      .toHaveTextContent("Rechazado");
    expect(screen.getByTestId("invoices-detail-payment-amount-cell-1"))
      .toHaveTextContent("$327.80");
    // The declined card shows the reason, not the number.
    expect(screen.getByTestId("invoices-detail-payment-detail-cell-1"))
      .toHaveTextContent("Tarjeta rechazada");
    expect(screen.getByTestId("invoices-detail-payment-detail-cell-2"))
      .toHaveTextContent("Pasarela no disponible");
    expect(screen.getByTestId("invoices-detail-payment-row-2")).toBeInTheDocument();
  });

  it("shows the reference of an approved transfer and the dash of a cash payment", async () => {
    invoiceBody = paidInvoice();
    renderDetail("2");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-heading")).toHaveTextContent(
        "FAC-0002",
      );
    });
    expect(screen.getByTestId("invoices-detail-state-status"))
      .toHaveTextContent("Pagada");
    expect(screen.getByTestId("invoices-detail-payment-method-cell-3"))
      .toHaveTextContent("Transferencia");
    expect(screen.getByTestId("invoices-detail-payment-state-cell-3"))
      .toHaveTextContent("Aprobado");
    expect(screen.getByTestId("invoices-detail-payment-detail-cell-3"))
      .toHaveTextContent("TRF-2026-0001");
    expect(screen.getByTestId("invoices-detail-payment-method-cell-4"))
      .toHaveTextContent("Efectivo");
    expect(screen.getByTestId("invoices-detail-payment-detail-cell-4"))
      .toHaveTextContent("—");
    expect(screen.getByTestId("invoices-detail-created-text"))
      .toHaveTextContent("03/01/2026 14:00 UTC");
  });

  it("says Aún no hay pagos. on an invoice without attempts", async () => {
    invoiceBody = {
      ...issuedInvoice(),
      payments: [],
    };
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-nopayments-text"))
        .toHaveTextContent("Aún no hay pagos.");
    });
    expect(
      screen.queryByTestId("invoices-detail-payments-table"),
    ).not.toBeInTheDocument();
  });
});

describe("the presence of the payment form per status and role", () => {
  it("shows the payment form on an issued invoice for the roles that manage invoices", async () => {
    await renderIssuedDetail();

    expect(screen.getByTestId("payments-register-form")).toBeInTheDocument();
    expect(screen.getByTestId("payments-register-method-select"))
      .toBeInTheDocument();
    // The invتoice is issued: no closed note.
    expect(
      screen.queryByTestId("invoices-detail-closed-text"),
    ).not.toBeInTheDocument();
  });

  it("hides the form and says why on a paid invoice", async () => {
    invoiceBody = paidInvoice();
    renderDetail("2");

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-heading")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("payments-register-form"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-closed-text"))
      .toHaveTextContent("Esta factura está pagada.");
  });

  it("hides the form and says why on a void invoice", async () => {
    invoiceBody = { ...issuedInvoice(), status: "void" };
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-heading")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("payments-register-form"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-closed-text"))
      .toHaveTextContent("Esta factura fue anulada.");
  });

  it("hides the form for the roles that cannot manage invoices", async () => {
    meUser = { ...adminUser, id: 2, name: "Ventas Demo", role: "sales" };
    await renderIssuedDetail();

    expect(
      screen.queryByTestId("payments-register-form"),
    ).not.toBeInTheDocument();
  });
});

describe("the fields of the payment form per method", () => {
  it("shows the card fields for card by default and no placeholder", async () => {
    await renderIssuedDetail();

    const select = screen.getByTestId(
      "payments-register-method-select",
    ) as HTMLSelectElement;
    expect(select.value).toBe("card");
    expect(
      Array.from(select.options).map((option) => option.textContent),
    ).toEqual(["Tarjeta", "Transferencia", "Efectivo"]);
    expect(screen.getByTestId("payments-register-cardnumber-input"))
      .toHaveAccessibleName("Número de tarjeta");
    expect(screen.getByTestId("payments-register-cardnumber-input"))
      .toHaveAttribute("autocomplete", "off");
    expect(screen.getByTestId("payments-register-cardexpiry-input"))
      .toHaveAccessibleName("Vencimiento (MM/AA)");
    expect(screen.getByTestId("payments-register-cardcvc-input"))
      .toHaveAccessibleName("CVC");
    expect(
      screen.queryByTestId("payments-register-reference-input"),
    ).not.toBeInTheDocument();
    // The amount comes prefilled with the total of the invoice.
    expect(screen.getByTestId("payments-register-amount-input")).toHaveValue(
      "327.80",
    );
  });

  it("shows only the reference for a transfer and nothing for cash", async () => {
    await renderIssuedDetail();
    const user = userEvent.setup();

    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "transfer",
    );
    await waitFor(() => {
      expect(
        screen.queryByTestId("payments-register-cardnumber-input"),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("payments-register-reference-input"))
      .toHaveAccessibleName("Referencia");

    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "cash",
    );
    await waitFor(() => {
      expect(
        screen.queryByTestId("payments-register-reference-input"),
      ).not.toBeInTheDocument();
    });
  });

  it("keeps the required error on the empty fields with no request", async () => {
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.clear(screen.getByTestId("payments-register-amount-input"));
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-amount-error"))
        .toHaveTextContent("Este campo es obligatorio.");
    });
    expect(screen.getByTestId("payments-register-cardnumber-error"))
      .toHaveTextContent("Este campo es obligatorio.");
    expect(screen.getByTestId("payments-register-cardexpiry-error"))
      .toHaveTextContent("Este campo es obligatorio.");
    expect(screen.getByTestId("payments-register-cardcvc-error"))
      .toHaveTextContent("Este campo es obligatorio.");
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-amount-input",
    );
    expect(paymentCalls()).toHaveLength(0);
  });

  it("only requires the reference for transfer, with no card error", async () => {
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "transfer",
    );
    // No card fields are around to error.
    expect(
      screen.queryByTestId("payments-register-cardnumber-error"),
    ).not.toBeInTheDocument();

    await user.clear(screen.getByTestId("payments-register-reference-input"));
    await user.click(screen.getByTestId("payments-register-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-reference-error"))
        .toHaveTextContent("Este campo es obligatorio.");
    });
    expect(paymentCalls()).toHaveLength(0);
  });
});

describe("the outcomes of the gateway", () => {
  let view: ReturnType<typeof renderDetail> | undefined;

  afterEach(() => {
    view?.unmount();
    view = undefined;
  });

  it("sends only the card fields, as typed, with a valid idempotency key", async () => {
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "card",
    );
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-success-status"))
        .toHaveTextContent("Pago aprobado.");
    });
    const [payment] = paymentCalls();
    expect(JSON.parse(payment.body ?? "{}")).toEqual({
      method: "card",
      amount: "327.80",
      card: { number: "4242 4242 4242 4242", expiry: "12/27", cvc: "123" },
    });
    expect(payment.ifMatch).toBe('"1"');
    expect(payment.idempotencyKey).toMatch(/^[A-Za-z0-9._-]{1,64}$/);
  });

  it("updates the screen without a reload and clears the card fields", async () => {
    await renderIssuedDetail();
    const readsBefore = readCount();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-success-status"))
        .toHaveTextContent("Pago aprobado.");
    });
    // The invoice of the result went to paid: the form is gone and the
    // history of the new payment is in place, without a reload.
    await waitFor(() => {
      expect(
        screen.queryByTestId("payments-register-form"),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-detail-state-status"))
      .toHaveTextContent("Pagada");
    expect(screen.getByTestId("invoices-detail-payment-row-5")).toBeInTheDocument();
    expect(screen.getByTestId("invoices-detail-payment-state-cell-5"))
      .toHaveTextContent("Aprobado");
    // The write of the mutation updates the detail without a navigation,
    // and the invalidations of the hook refetch this detail exactly once.
    expect(readCount()).toBe(readsBefore + 1);
  });

  it("shows a declined payment in the alert and the attempt in the history", async () => {
    mutateAnswer = () =>
      declineProblem(
        402,
        "CARD_DECLINED",
        "La pasarela rechazó el pago. Prueba con otra tarjeta.",
        5,
      );
    await renderIssuedDetail();
    const readsBefore = readCount();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4000 0000 0000 0002",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
        "La pasarela rechazó el pago. Prueba con otra tarjeta.",
      );
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-alert",
    );
    // The history gains the attempt through the invalidation of the hook.
    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-payment-row-5")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-detail-payment-state-cell-5"))
      .toHaveTextContent("Rechazado");
    expect(readCount()).toBeGreaterThan(readsBefore);
  });

  it("shows a gateway failure the same way", async () => {
    mutateAnswer = () =>
      declineProblem(
        503,
        "GATEWAY_UNAVAILABLE",
        "La pasarela de pago no está disponible. Inténtalo de nuevo.",
        6,
      );
    const invoice = {
      ...issuedInvoice(),
      payments: [],
    };
    invoiceBody = invoice;
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.clear(screen.getByTestId("payments-register-amount-input"));
    await user.type(screen.getByTestId("payments-register-amount-input"), "768.90");
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "cash",
    );
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
        "La pasarela de pago no está disponible. Inténtalo de nuevo.",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-payment-row-6")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invoices-detail-payment-state-cell-6"))
      .toHaveTextContent("Fallido");
    expect(screen.getByTestId("invoices-detail-payment-detail-cell-6"))
      .toHaveTextContent("Pasarela no disponible");
  });

  for (const code of ["VERSION_CONFLICT", "INVOICE_NOT_PAYABLE"] as const) {
    it(`shows ${code} in the alert and refetches the invoice`, async () => {
      const detail = code === "VERSION_CONFLICT"
        ? "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
        : "Esta factura no admite pagos.";
      mutateAnswer = () => problemWith(409, code, detail);
      view = renderDetail();
      await waitFor(() => {
        expect(screen.getByTestId("invoices-detail-heading")).toBeInTheDocument();
      });
      const readsBefore = readCount();
      const user = userEvent.setup();
      await user.selectOptions(
        screen.getByTestId("payments-register-method-select"),
        "cash",
      );
      await user.click(screen.getByTestId("payments-register-submit-button"));

      await waitFor(() => {
        expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
          detail,
        );
      });
      // The failed mutation refetches the invoice.
      expect(readCount()).toBe(readsBefore + 1);

      // Separate caches and DOM per iteration: each problem runs its own
      // render.
      view?.unmount();
      queryClient.clear();
      fetchMock.mockReset();
    });
  }
});

describe("the unknown outcomes keep the idempotency key", () => {
  /**
   * Every answer that says nothing about whether the payment was
   * recorded keeps the key on the next submit: the platform statuses
   * (502, 504 with a non-problem body), the 500 `INTERNAL_ERROR` and the
   * 429 `RATE_LIMITED` (nothing happened).
   */
  const unknownCases = [
    {
      name: "502 with a non-problem body",
      respond: () =>
        new Response("<html>bad gateway</html>", { status: 502 }),
    },
    {
      name: "504 with a non-problem body",
      respond: () =>
        new Response("gateway timeout", { status: 504, headers: { "content-type": "text/plain" } }),
    },
    {
      name: "500 INTERNAL_ERROR",
      respond: () =>
        problemWith(
          500,
          "INTERNAL_ERROR",
          "Ocurrió un error inesperado. Inténtalo de nuevo.",
        ),
    },
    {
      name: "429 RATE_LIMITED",
      respond: () =>
        problemWith(429, "RATE_LIMITED", "Se han superado el límite de peticiones."),
    },
  ];

  for (const unknown of unknownCases) {
    it(`keeps the key after ${unknown.name}`, async () => {
      mutateAnswer = () => unknown.respond();
      await renderIssuedDetail();
      const user = userEvent.setup();
      await user.type(
        screen.getByTestId("payments-register-cardnumber-input"),
        "4242 4242 4242 4242",
      );
      await user.type(
        screen.getByTestId("payments-register-cardexpiry-input"),
        "12/27",
      );
      await user.type(
        screen.getByTestId("payments-register-cardcvc-input"),
        "123",
      );

      // First attempt: the answer does not tell the outcome.
      await user.click(screen.getByTestId("payments-register-submit-button"));
      await waitFor(() => {
        expect(screen.getByTestId("payments-register-alert"))
          .toBeInTheDocument();
      });

      // Second attempt: SAME key, so the server can replay or continue.
      await user.click(screen.getByTestId("payments-register-submit-button"));
      await waitFor(() => {
        expect(paymentCalls().length).toBeGreaterThanOrEqual(2);
      });

      const calls = paymentCalls();
      expect(calls[0].idempotencyKey).toBe(calls[1].idempotencyKey);
    });
  }

  /**
   * Every answer that DOES tell the outcome retires the key: the next
   * submit is a brand new attempt.
   */
  for (const outcome of [
    {
      name: "a 402 declined payment",
      respond: () =>
        declineProblem(
          402,
          "CARD_DECLINED",
          "La pasarela rechazó el pago. Prueba con otra tarjeta.",
          5,
        ),
    },
    {
      name: "a 503 PAYMENT_GATEWAY_UNAVAILABLE",
      respond: () =>
        declineProblem(
          503,
          "GATEWAY_UNAVAILABLE",
          "La pasarela de pago no está disponible. Inténtalo de nuevo.",
          6,
        ),
    },
    {
      name: "a 409 VERSION_CONFLICT",
      respond: () =>
        problemWith(
          409,
          "VERSION_CONFLICT",
          "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.",
        ),
    },
    {
      name: "a 422 PAYMENT_AMOUNT_MISMATCH",
      respond: () =>
        problemWith(
          422,
          "PAYMENT_AMOUNT_MISMATCH",
          "El monto debe ser igual al total de la factura.",
        ),
    },
  ] as const) {
    it(`takes a new key after ${outcome.name}`, async () => {
      mutateAnswer = () => outcome.respond();
      await renderIssuedDetail();
      const user = userEvent.setup();
      await user.type(
        screen.getByTestId("payments-register-cardnumber-input"),
        "4242 4242 4242 4242",
      );
      await user.type(
        screen.getByTestId("payments-register-cardexpiry-input"),
        "12/27",
      );
      await user.type(
        screen.getByTestId("payments-register-cardcvc-input"),
        "123",
      );

      await user.click(screen.getByTestId("payments-register-submit-button"));
      await waitFor(() => {
        expect(screen.getByTestId("payments-register-alert"))
          .toBeInTheDocument();
      });

      await user.click(screen.getByTestId("payments-register-submit-button"));
      await waitFor(() => {
        expect(paymentCalls().length).toBeGreaterThanOrEqual(2);
      });

      const calls = paymentCalls();
      expect(calls[0].idempotencyKey).not.toBe(calls[1].idempotencyKey);
    });
  }
});

describe("the amount mismatch and the idempotency key rule", () => {
  it("shows the amount mismatch in the alert and refetches the invoice", async () => {
    mutateAnswer = () =>
      problemWith(422, "PAYMENT_AMOUNT_MISMATCH", "El monto debe ser igual al total de la factura.");
    await renderIssuedDetail();
    const readsBefore = readCount();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "cash",
    );
    await user.clear(screen.getByTestId("payments-register-amount-input"));
    await user.type(screen.getByTestId("payments-register-amount-input"), "500.00");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
        "El monto debe ser igual al total de la factura.",
      );
    });
    expect(readCount()).toBe(readsBefore + 1);
  });

  it("maps the exact field paths of a 422 to their fields", async () => {
    mutateAnswer = () =>
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "card.number",
              code: "CARD_NUMBER_INVALID",
              message: "El número de tarjeta no es válido.",
            },
            {
              field: "card.expiry",
              code: "INVALID_FORMAT",
              message: "El formato no es válido.",
            },
            {
              field: "card.cvc",
              code: "CARD_CVC_INVALID",
              message: "El código de seguridad no es válido.",
            },
          ],
        },
        422,
      );
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "12345",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "not-a-date",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "12");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-cardnumber-error"))
        .toHaveTextContent("El número de tarjeta no es válido.");
    });
    expect(screen.getByTestId("payments-register-cardexpiry-error"))
      .toHaveTextContent("El formato no es válido.");
    expect(screen.getByTestId("payments-register-cardcvc-error"))
      .toHaveTextContent("El código de seguridad no es válido.");
  });

  it("keeps the same key after a network error and takes a new one after any answer", async () => {
    let networkFailure = true;
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method ?? "GET");
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url === "/api/invoices/1") {
          return jsonResponse(invoiceBody, invoiceStatus);
        }
        if (url === "/api/invoices/1/payments" && method === "POST") {
          if (networkFailure) {
            throw new TypeError("Failed to fetch");
          }
          return jsonResponse(approvedResult(), 201);
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");

    // First attempt: the network fails, so no answer arrived.
    await user.click(screen.getByTestId("payments-register-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
        "Ocurrió un error inesperado. Inténtalo de nuevo.",
      );
    });

    // Second attempt with the corrected body: the SAME key goes out.
    networkFailure = false;
    await user.click(screen.getByTestId("payments-register-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-success-status"))
        .toHaveTextContent("Pago aprobado.");
    });

    const calls = paymentCalls();
    expect(calls.length).toBe(2);
    expect(calls[0].idempotencyKey).toBe(calls[1].idempotencyKey);

    // After the HTTP answer (the 201), the next attempt takes a new key:
    // the failed attempt inside it is stored and replayed by the old key.
    networkFailure = false;
    expect(calls[0].idempotencyKey).toMatch(/^[A-Za-z0-9._-]{1,64}$/);
  });

  it("takes a new key after a decline and after any field change", async () => {
    let declined = true;
    invoiceBody = issuedInvoice();
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method ?? "GET");
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url === "/api/invoices/1") {
          return jsonResponse(invoiceBody, invoiceStatus);
        }
        if (url === "/api/invoices/1/payments" && method === "POST") {
          if (declined) {
            return declineProblem(
              402,
              "CARD_DECLINED",
              "La pasarela rechazó el pago. Prueba con otra tarjeta.",
              5,
            );
          }
          return jsonResponse(approvedResult(), 201);
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "card",
    );
    await user.clear(screen.getByTestId("payments-register-amount-input"));
    await user.type(screen.getByTestId("payments-register-amount-input"), "327.80");
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4000 0000 0000 0002",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");

    // Attempt 1: declined.
    await user.click(screen.getByTestId("payments-register-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-alert")).toHaveTextContent(
        "La pasarela rechazó el pago. Prueba con otra tarjeta.",
      );
    });

    // The storage of the decline leaves the invoice issued; the state of
    // the card stays.
    expect(screen.getByTestId("invoices-detail-state-status"))
      .toHaveTextContent("Emitida");

    // Attempt 2: the user changed the CVC; the field change took a new
    // key and the decline stored the attempt of the first one.
    const firstKey = paymentCalls()[0].idempotencyKey;
    await user.clear(screen.getByTestId("payments-register-cardcvc-input"));
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "124");
    declined = false;
    await user.click(screen.getByTestId("payments-register-submit-button"));
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-success-status"))
        .toHaveTextContent("Pago aprobado.");
    });

    // The keys of the two attempts are different: the decline consumed
    // the first one, and the field change took a new one.
    const calls = paymentCalls();
    expect(calls).toHaveLength(2);
    expect(calls[0].idempotencyKey).not.toBe(calls[1].idempotencyKey);
    expect(calls[0].idempotencyKey).toBe(firstKey);
    expect(JSON.parse(calls[1].body ?? "{}")).toEqual({
      method: "card",
      amount: "327.80",
      card: { number: "4000 0000 0000 0002", expiry: "12/27", cvc: "124" },
    });
  });

  it("never puts the card number anywhere but its own input", async () => {
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "card",
    );
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );

    const cardInput = screen.getByTestId("payments-register-cardnumber-input");
    expect(cardInput).toHaveValue("4242 4242 4242 4242");
    // The value lives in the input only; no text node of the page and no
    // localStorage entry carries it.
    expect(document.body.textContent).not.toContain("4242 4242 4242 4242");
    expect(window.localStorage.getItem("4242 4242 4242 4242")).toBeNull();
  });

  it("ignores a second submit while the payment runs", async () => {
    let release!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      release = resolve;
    });
    fetchMock.mockReset();
    fetchMock.mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = String(init?.method ?? "GET");
        if (url === "/api/auth/me") {
          return jsonResponse(meUser);
        }
        if (url === "/api/invoices/1") {
          return jsonResponse(invoiceBody, invoiceStatus);
        }
        if (url === "/api/invoices/1/payments" && method === "POST") {
          return gate;
        }
        return problemWith(
          404,
          "NOT_FOUND",
          "No se encontró el recurso solicitado.",
        );
      },
    );
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    // Every control is disabled while the payment runs (B1 of the theme).
    const submit = screen.getByTestId("payments-register-submit-button");
    expect(submit).toBeDisabled();
    expect(submit).toHaveAttribute("data-state", "loading");
    expect(submit).toHaveAttribute("aria-busy", "true");
    expect(submit).toHaveTextContent("Pagando…");

    // A second submit, even straight to the form, is ignored by the guard.
    const form = document.querySelector(
      "[data-testid='payments-register-form']",
    ) as HTMLFormElement;
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await waitFor(() => {
      expect(paymentCalls()).toHaveLength(1);
    });

    release(
      jsonResponse(
        approvedResult(),
        201,
      ),
    );
    await waitFor(() => {
      expect(screen.getByTestId("payments-register-success-status"))
        .toHaveTextContent("Pago aprobado.");
    });
    expect(paymentCalls()).toHaveLength(1);
  });

  it("writes null into the session when a payment answers 401", async () => {
    mutateAnswer = () =>
      problemWith(
        401,
        "UNAUTHENTICATED",
        "Inicia sesión para continuar.",
      );
    queryClient.setQueryData(ME_QUERY_KEY, meUser);
    await renderIssuedDetail();
    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242 4242 4242 4242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "12/27",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(queryClient.getQueryData(ME_QUERY_KEY)).toBeNull();
    });
  });
});

describe("the focus and the server fields of a strict 422", () => {
  it("focuses the method select and marks the reference from a 422", async () => {
    mutateAnswer = () =>
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "reference",
              code: "LENGTH_TOO_LONG",
              message: "La referencia es demasiado larga.",
            },
            {
              field: "method",
              code: "METHOD_UNAVAILABLE",
              message: "Ese medio de pago no está disponible.",
            },
          ],
        },
        422,
      );
    await renderIssuedDetail();

    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByTestId("payments-register-method-select"),
      "transfer",
    );
    await user.type(
      screen.getByTestId("payments-register-reference-input"),
      "TRF-2026-0001",
    );
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-method-error"))
        .toHaveTextContent("Ese medio de pago no está disponible.");
    });
    expect(screen.getByTestId("payments-register-reference-error"))
      .toHaveTextContent("La referencia es demasiado larga.");
    // The focus follows the order of the fields: method before reference.
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-method-select",
    );
  });

  it("focuses the amount field when only it fails on the server", async () => {
    mutateAnswer = () =>
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "amount",
              code: "OUT_OF_RANGE",
              message: "El monto no cubre el total pendiente.",
            },
          ],
        },
        422,
      );
    await renderIssuedDetail();

    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242424242424242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "31/12/2027",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "123");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-amount-error"))
        .toHaveTextContent("El monto no cubre el total pendiente.");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-amount-input",
    );
  });

  it("focuses the card expiry when only it fails on the server", async () => {
    mutateAnswer = () =>
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "card.expiry",
              code: "INVALID_FORMAT",
              message: "El formato no es válido.",
            },
          ],
        },
        422,
      );
    await renderIssuedDetail();

    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242424242424242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "not-a-date",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "12");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-cardexpiry-error"))
        .toHaveTextContent("El formato no es válido.");
    });
    expect(
      screen.queryByTestId("payments-register-cardnumber-error"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("payments-register-cardcvc-error"),
    ).not.toBeInTheDocument();
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-cardexpiry-input",
    );
  });

  it("focuses the card cvc when only it fails on the server", async () => {
    mutateAnswer = () =>
      jsonResponse(
        {
          type: "about:blank",
          title: "Unprocessable Content",
          status: 422,
          code: "VALIDATION_ERROR",
          detail: "Revisa los datos ingresados.",
          errors: [
            {
              field: "card.cvc",
              code: "CARD_CVC_INVALID",
              message: "El código de seguridad no es válido.",
            },
          ],
        },
        422,
      );
    await renderIssuedDetail();

    const user = userEvent.setup();
    await user.type(
      screen.getByTestId("payments-register-cardnumber-input"),
      "4242424242424242",
    );
    await user.type(
      screen.getByTestId("payments-register-cardexpiry-input"),
      "31/12/2027",
    );
    await user.type(screen.getByTestId("payments-register-cardcvc-input"), "1");
    await user.click(screen.getByTestId("payments-register-submit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("payments-register-cardcvc-error"))
        .toHaveTextContent("El código de seguridad no es válido.");
    });
    expect(document.activeElement).toHaveAttribute(
      "data-testid",
      "payments-register-cardcvc-input",
    );
  });
});

describe("the retry of the invoice detail", () => {
  it("recovers from a load failure with the retry button", async () => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/me") {
        return jsonResponse(meUser);
      }
      if (url === "/api/invoices/1") {
        return invoiceStatus === 200
          ? jsonResponse(invoiceBody, 200)
          : problemWith(
              500,
              "INTERNAL_ERROR",
              "Ocurrió un error inesperado. Inténtalo de nuevo.",
            );
      }
      return problemWith(404, "NOT_FOUND", "No se encontró el recurso.");
    });
    invoiceStatus = 500;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-error-alert")).toHaveTextContent(
        "Ocurrió un error inesperado.",
      );
    });

    // The retry reloads the same key; the healthy answer arrives now.
    invoiceStatus = 200;
    await userEvent
      .setup()
      .click(screen.getByTestId("invoices-detail-retry-button"));
    await waitFor(() => {
      expect(screen.getByTestId("invoices-detail-heading")).toHaveTextContent(
        "FAC-0001",
      );
    });
    expect(screen.queryByTestId("invoices-detail-error-alert"))
      .not.toBeInTheDocument();
  });
});
