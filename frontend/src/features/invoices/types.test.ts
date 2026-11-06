import { describe, expect, it } from "vitest";
import {
  invoiceStatusLabel,
  paymentMethodLabel,
  paymentReasonLabel,
  paymentStatusLabel,
  type Invoice,
  type InvoiceList,
  type InvoiceSummary,
  type Payment,
  type PaymentResult,
} from "./types";

describe("the status, method and reason labels", () => {
  it("labels the invoice states in Spanish", () => {
    expect(invoiceStatusLabel("issued")).toBe("Emitida");
    expect(invoiceStatusLabel("paid")).toBe("Pagada");
    expect(invoiceStatusLabel("void")).toBe("Anulada");
  });

  it("labels the payment states and methods in Spanish", () => {
    expect(paymentStatusLabel("approved")).toBe("Aprobado");
    expect(paymentStatusLabel("declined")).toBe("Rechazado");
    expect(paymentStatusLabel("failed")).toBe("Fallido");
    expect(paymentMethodLabel("card")).toBe("Tarjeta");
    expect(paymentMethodLabel("transfer")).toBe("Transferencia");
    expect(paymentMethodLabel("cash")).toBe("Efectivo");
  });

  it("labels the gateway reasons in Spanish", () => {
    expect(paymentReasonLabel("CARD_DECLINED")).toBe("Tarjeta rechazada");
    expect(paymentReasonLabel("GATEWAY_UNAVAILABLE"))
      .toBe("Pasarela no disponible");
  });
});

describe("the invoice types", () => {
  it("matches the shape of the seed invoice FAC-0001", () => {
    const invoice: Invoice = {
      id: 1,
      number: "FAC-0001",
      status: "issued",
      order_id: 3,
      order_number: "PED-0003",
      // Snapshot: the customer's data at issue time.
      customer: {
        id: 4,
        name: "Distribuidora Delta",
        tax_id: "DELT-700789",
        address: null,
      },
      lines: [
        {
          id: 3,
          product_id: 3,
          sku: "MN-240",
          name: "Monitor 24\"",
          quantity: 2,
          unit_price: "149.00",
          line_total: "298.00",
        },
      ],
      subtotal: "298.00",
      tax_rate: "10.00",
      tax: "29.80",
      total: "327.80",
      payments: [
        {
          id: 1,
          method: "card",
          status: "declined",
          amount: "327.80",
          reference: null,
          card_last4: "0002",
          reason: "CARD_DECLINED",
          created_at: "2026-01-03T15:00:00Z",
        },
      ],
      version: 1,
      created_at: "2026-01-03T14:00:00Z",
      updated_at: "2026-01-03T14:00:00Z",
    };
    expect(invoice.customer.tax_id).toBe("DELT-700789");
    expect(invoice.payments[0].card_last4).toBe("0002");
    // The card number itself is never part of any shape.
    expect(JSON.stringify(invoice)).not.toContain("4242");
  });

  it("carries money as strings and nullable fields as null", () => {
    const withoutOptionals: Payment = {
      id: 3,
      method: "transfer",
      status: "approved",
      amount: "197.97",
      reference: "TRF-2026-0001",
      card_last4: null,
      reason: null,
      created_at: "2026-01-04T15:00:00Z",
    };
    expect(withoutOptionals.card_last4).toBeNull();

    const result: PaymentResult = {
      payment: withoutOptionals,
      invoice: {
        id: 2,
        number: "FAC-0002",
        status: "paid",
        order_id: 4,
        order_number: "PED-0004",
        customer: { id: 6, name: "Ferretería Fénix", tax_id: null, address: null },
        lines: [],
        subtotal: "179.97",
        tax_rate: "10.00",
        tax: "18.00",
        total: "197.97",
        payments: [withoutOptionals],
        version: 2,
        created_at: "2026-01-04T14:00:00Z",
        updated_at: "2026-01-04T15:00:00Z",
      },
    };
    expect(result.invoice.status).toBe("paid");
  });

  it("matches the shape of the list page", () => {
    const summary: InvoiceSummary = {
      id: 2,
      number: "FAC-0002",
      status: "paid",
      order_id: 4,
      order_number: "PED-0004",
      customer_name: "Ferretería Fénix",
      total: "197.97",
      version: 2,
      created_at: "2026-01-04T14:00:00Z",
      updated_at: "2026-01-04T15:00:00Z",
    };
    const list: InvoiceList = {
      items: [summary],
      page: 1,
      page_size: 20,
      total: 1,
    };
    expect(list.page_size).toBe(20);
  });
});
