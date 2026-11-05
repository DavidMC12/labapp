import { describe, expect, it } from "vitest";
import {
  orderStatusLabel,
  type Order,
  type OrderLine,
  type OrderList,
  type OrderSummary,
  type Product,
  type Shortage,
} from "./types";

describe("orderStatusLabel", () => {
  it("labels the five statuses in Spanish", () => {
    expect(orderStatusLabel("draft")).toBe("Borrador");
    expect(orderStatusLabel("confirmed")).toBe("Confirmado");
    expect(orderStatusLabel("paid")).toBe("Pagado");
    expect(orderStatusLabel("shipped")).toBe("Enviado");
    expect(orderStatusLabel("cancelled")).toBe("Cancelado");
  });
});

describe("the order types", () => {
  it("matches the literal Order of the corrected spec (S5)", () => {
    // The answer body of POST /api/orders/8/lines with ETag "2".
    const order: Order = {
      id: 8,
      number: "PED-0008",
      status: "draft",
      customer: {
        id: 1,
        name: "Acme Industrial S.A.",
        status: "active",
      },
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
    expect(order.customer.status).toBe("active");
    expect(order.lines[0].line_total).toBe("39.80");
  });

  it("carries money as strings and the tax rate as a string", () => {
    // A cancelled order has a frozen tax rate and frozen totals (S3).
    const cancelled: Order = {
      id: 6,
      number: "PED-0006",
      status: "cancelled",
      customer: { id: 10, name: "Joyería Júpiter", status: "active" },
      lines: [
        {
          id: 9,
          product_id: 12,
          sku: "SW-8P",
          name: "Switch 8 puertos",
          quantity: 4,
          unit_price: "27.40",
          line_total: "109.60",
        },
      ],
      subtotal: "109.60",
      tax_rate: "10.00",
      tax: "10.96",
      total: "120.56",
      invoice_id: null,
      version: 2,
      created_at: "2026-01-06T10:00:00Z",
      updated_at: "2026-01-06T10:05:00Z",
    };
    expect(typeof cancelled.tax_rate).toBe("string");
    expect(typeof cancelled.total).toBe("string");
  });

  it("allows a non-null invoice id on orders with a frozen invoice", () => {
    const paid: Order = {
      id: 4,
      number: "PED-0004",
      status: "paid",
      customer: { id: 6, name: "Ferretería Fénix", status: "active" },
      lines: [],
      subtotal: "179.97",
      tax_rate: "10.00",
      tax: "18.00",
      total: "197.97",
      invoice_id: 2,
      version: 1,
      created_at: "2026-01-04T10:00:00Z",
      updated_at: "2026-01-04T10:00:00Z",
    };
    expect(paid.invoice_id).toBe(2);
  });

  it("matches the shapes of the summary, the list, a product and a shortage", () => {
    const summary: OrderSummary = {
      id: 8,
      number: "PED-0008",
      status: "draft",
      customer_id: 1,
      customer_name: "Acme Industrial S.A.",
      line_count: 1,
      total: "43.78",
      version: 2,
      created_at: "2026-11-05T15:00:00Z",
      updated_at: "2026-11-05T15:01:00Z",
    };
    const list: OrderList = {
      items: [summary],
      page: 1,
      page_size: 20,
      total: 1,
    };
    const product: Product = {
      id: 1,
      sku: "KB-100",
      name: "Teclado USB",
      price: "19.90",
      stock: 120,
    };
    const shortage: Shortage = {
      product_id: 1,
      sku: "KB-100",
      name: "Teclado USB",
      available: 3,
      requested: 5,
    };
    expect(list.total).toBe(1);
    expect(product.stock).toBe(120);
    expect(shortage.requested).toBe(5);
  });

  it("accepts a line id alone", () => {
    const line: OrderLine = {
      id: 10,
      product_id: 1,
      sku: "KB-100",
      name: "Teclado USB",
      quantity: 2,
      unit_price: "19.90",
      line_total: "39.80",
    };
    expect(typeof line.quantity).toBe("number");
  });
});
