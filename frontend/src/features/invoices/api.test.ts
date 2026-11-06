import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildInvoiceListQuery,
  fetchInvoice,
  fetchInvoices,
  issueInvoice,
  invoiceListUrl,
  registerPayment,
} from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Reads the path (with the query) and the init of the recorded call. */
function call(index: number): [string, RequestInit] {
  return fetchMock.mock.calls[index] as [string, RequestInit];
}

const invoiceFixture = {
  id: 1,
  number: "FAC-0001",
  status: "issued",
  order_id: 3,
  order_number: "PED-0003",
  customer: { id: 4, name: "Distribuidora Delta", tax_id: "DELT-700789", address: null },
  lines: [],
  subtotal: "298.00",
  tax_rate: "10.00",
  tax: "29.80",
  total: "327.80",
  payments: [],
  version: 1,
  created_at: "2026-01-03T14:00:00Z",
  updated_at: "2026-01-03T14:00:00Z",
};

describe("buildInvoiceListQuery", () => {
  it("always includes page", () => {
    expect(buildInvoiceListQuery({ page: 3 }).toString()).toBe("page=3");
  });

  it("includes q and status only when they have a value", () => {
    expect(invoiceListUrl({ page: 2, q: "", status: undefined })).toBe(
      "/api/invoices?page=2",
    );
    expect(invoiceListUrl({ page: 2, q: "fac", status: "paid" })).toBe(
      "/api/invoices?page=2&q=fac&status=paid",
    );
  });

  it("encodes a q that contains reserved characters", () => {
    expect(invoiceListUrl({ page: 1, q: "R&D" })).toBe(
      "/api/invoices?page=1&q=R%26D",
    );
  });
});

describe("the invoice requests", () => {
  it("sends the list request with the built query", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [], page: 1, page_size: 20, total: 0 }), {
        status: 200,
      }),
    );

    await fetchInvoices({ page: 2, q: "R&D", status: "void" });

    const [path, init] = call(0);
    expect(path).toBe("/api/invoices?page=2&q=R%26D&status=void");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
  });

  it("reads one invoice by numeric id", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(invoiceFixture), { status: 200 }),
    );

    const result = await fetchInvoice(1);

    expect(call(0)[0]).toBe("/api/invoices/1");
    expect(result.version).toBe(1);
  });

  it("issues an invoice with no body and the order version in If-Match", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(invoiceFixture), { status: 201 }),
    );

    await issueInvoice(3, 2);

    const [path, init] = call(0);
    expect(path).toBe("/api/orders/3/invoice");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(init.headers).toMatchObject({ "If-Match": '"2"' });
  });
});

describe("the payment request", () => {
  it("sends Idempotency-Key and If-Match, and only the card fields for card", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ payment: {}, invoice: invoiceFixture }), {
        status: 201,
      }),
    );

    await registerPayment(
      1,
      { method: "card", amount: "327.80", card: { number: "4242 4242 4242 4242", expiry: "12/27", cvc: "123" } },
      "pay-key-1",
      1,
    );

    const [path, init] = call(0);
    expect(path).toBe("/api/invoices/1/payments");
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({
      "Idempotency-Key": "pay-key-1",
      "If-Match": '"1"',
    });
    expect(init.body).toBe(
      JSON.stringify({
        method: "card",
        amount: "327.80",
        card: { number: "4242 4242 4242 4242", expiry: "12/27", cvc: "123" },
      }),
    );
  });

  it("sends only the reference for a transfer and nothing extra for cash", async () => {
    fetchMock.mockImplementation(async () =>
      new Response(JSON.stringify({ payment: {}, invoice: invoiceFixture }), {
        status: 201,
      }),
    );

    await registerPayment(
      1,
      { method: "transfer", amount: "327.80", reference: "TRF-2026-0001" },
      "key-2",
      1,
    );
    await registerPayment(1, { method: "cash", amount: "327.80" }, "key-3", 1);

    const [, transferInit] = call(0);
    expect(transferInit.body).toBe(
      JSON.stringify({ method: "transfer", amount: "327.80", reference: "TRF-2026-0001" }),
    );
    const [, cashInit] = call(1);
    expect(cashInit.body).toBe(JSON.stringify({ method: "cash", amount: "327.80" }));
  });

  it("throws the problem document of a declined payment", async () => {
    // The literal problem of a declined payment (S5-like): the attempt is
    // stored and the body carries payment_id and reason.
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Payment Required",
          status: 402,
          code: "PAYMENT_DECLINED",
          detail: "La pasarela rechazó el pago. Prueba con otra tarjeta.",
          payment_id: 5,
          reason: "CARD_DECLINED",
        }),
        { status: 402 },
      ),
    );

    await expect(
      registerPayment(
        1,
        { method: "card", amount: "327.80", card: { number: "4000 0000 0000 0002", expiry: "12/27", cvc: "123" } },
        "key-4",
        1,
      ),
    ).rejects.toMatchObject({
      name: "ApiRequestError",
      problem: {
        status: 402,
        code: "PAYMENT_DECLINED",
        payment_id: 5,
        reason: "CARD_DECLINED",
      },
    });
  });

  it("throws the problem document of a gateway failure", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Service Unavailable",
          status: 503,
          code: "PAYMENT_GATEWAY_UNAVAILABLE",
          detail: "La pasarela de pago no está disponible. Inténtalo de nuevo.",
          payment_id: 6,
          reason: "GATEWAY_UNAVAILABLE",
        }),
        { status: 503 },
      ),
    );

    await expect(
      registerPayment(1, { method: "cash", amount: "327.80" }, "key-5", 1),
    ).rejects.toMatchObject({
      problem: { status: 503, code: "PAYMENT_GATEWAY_UNAVAILABLE", payment_id: 6 },
    });
  });
});
