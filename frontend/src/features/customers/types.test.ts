import { describe, expect, it } from "vitest";
import { statusLabel, type Customer, type CustomerList } from "./types";

describe("statusLabel", () => {
  it("labels the two statuses in Spanish", () => {
    expect(statusLabel("active")).toBe("Activo");
    expect(statusLabel("inactive")).toBe("Inactivo");
  });
});

describe("the customer types", () => {
  it("matches the shape of a seeded customer", () => {
    const customer: Customer = {
      id: 1,
      name: "Acme Industrial S.A.",
      email: "acme@example.test",
      phone: "+1 555 010 0001",
      tax_id: "ACME-900123",
      address: "Av. Principal 100",
      status: "active",
      version: 1,
      created_at: "2026-01-01T09:00:00Z",
      updated_at: "2026-01-01T09:00:00Z",
    };
    // Optional fields accept null as well.
    const withoutOptionals: Customer = { ...customer, phone: null, tax_id: null, address: null };
    expect(withoutOptionals.phone).toBeNull();
  });

  it("matches the shape of a list page", () => {
    const list: CustomerList = {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    };
    expect(list.page_size).toBe(20);
  });
});
