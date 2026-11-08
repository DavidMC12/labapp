import { describe, expect, it } from "vitest";
import {
  flipInvoiceSortDirection,
  isDefaultInvoiceSort,
  invoiceSortDefaultDirection,
  invoiceSortLabel,
  parseInvoiceIdParam,
  parseInvoiceListParams,
  resolveInvoiceSort,
  type InvoiceListParams,
} from "./params";

describe("the invoices sort helpers", () => {
  it("acts the default direction of each field out", () => {
    expect(invoiceSortDefaultDirection("created_at")).toBe("desc");
    expect(invoiceSortDefaultDirection("number")).toBe("asc");
    expect(invoiceSortDefaultDirection("customer")).toBe("asc");
    expect(invoiceSortDefaultDirection("total")).toBe("asc");
  });

  it("flips one direction and never leaves the valid pair", () => {
    expect(flipInvoiceSortDirection("asc")).toBe("desc");
    expect(flipInvoiceSortDirection("desc")).toBe("asc");
  });

  it("resolves the effective sort of the URL values", () => {
    expect(resolveInvoiceSort({ sort: null, direction: null })).toEqual({
      sort: "created_at",
      direction: "desc",
    });
    expect(resolveInvoiceSort({ sort: "total", direction: null })).toEqual({
      sort: "total",
      direction: "asc",
    });
    // A present direction applies to the default field without `sort`.
    expect(resolveInvoiceSort({ sort: null, direction: "asc" })).toEqual({
      sort: "created_at",
      direction: "asc",
    });
    expect(resolveInvoiceSort({ sort: "number", direction: "desc" })).toEqual({
      sort: "number",
      direction: "desc",
    });
  });

  it("answers whether a sort is the one of the plain list", () => {
    expect(isDefaultInvoiceSort({ sort: "created_at", direction: "desc" }))
      .toBe(true);
    expect(isDefaultInvoiceSort({ sort: "created_at", direction: "asc" }))
      .toBe(false);
    expect(isDefaultInvoiceSort({ sort: "total", direction: "desc" }))
      .toBe(false);
  });

  it("labels each field in Spanish", () => {
    expect(invoiceSortLabel("number")).toBe("Número");
    expect(invoiceSortLabel("customer")).toBe("Cliente");
    expect(invoiceSortLabel("total")).toBe("Total");
    expect(invoiceSortLabel("created_at")).toBe("Creada");
  });
});

describe("parseInvoiceIdParam", () => {
  it("accepts a positive integer id up to 2147483647", () => {
    expect(parseInvoiceIdParam("7")).toBe(7);
    expect(parseInvoiceIdParam("2147483647")).toBe(2147483647);
  });

  it("rejects zero, leading zeros, signs and other syntaxes", () => {
    for (const value of ["0", "007", "1e3", "-7", "+7", "7.5", " 7", "", "siete"]) {
      expect(parseInvoiceIdParam(value), JSON.stringify(value)).toBeNull();
    }
    expect(parseInvoiceIdParam(7)).toBeNull();
    expect(parseInvoiceIdParam(undefined)).toBeNull();
    expect(parseInvoiceIdParam("2147483648")).toBeNull();
  });
});

describe("parseInvoiceListParams", () => {
  function read(search: string): InvoiceListParams {
    return parseInvoiceListParams(new URLSearchParams(search));
  }

  it("reads the three parameters", () => {
    expect(read("page=2&q=fac&status=paid")).toEqual({
      page: 2,
      q: "fac",
      status: "paid",
      sort: null,
      direction: null,
    });
  });

  it("falls back to page 1 and no values on an empty URL", () => {
    expect(read("")).toEqual({
      page: 1,
      q: null,
      status: null,
      sort: null,
      direction: null,
    });
  });

  it("rejects every invalid page as page 1", () => {
    for (const page of ["0", "007", "1e3", "-1", "1.5", "siete", "1000001"]) {
      expect(read(`page=${page}`).page, page).toBe(1);
    }
  });

  it("accepts page up to 1000000", () => {
    expect(read("page=1000000").page).toBe(1000000);
  });

  it("trims q and drops an empty one", () => {
    expect(read("q=%20fac%20").q).toBe("fac");
    expect(read("q=%20").q).toBeNull();
  });

  it("accepts the three statuses and rejects any other value", () => {
    expect(read("status=issued").status).toBe("issued");
    expect(read("status=paid").status).toBe("paid");
    expect(read("status=void").status).toBe("void");
    expect(read("status=draft").status).toBeNull(); // an order status is not an invoice status
    expect(read("status=green").status).toBeNull();
    expect(read("status=").status).toBeNull();
    expect(read("status=paid%20").status).toBeNull();
  });

  it("reads a valid sort and direction and falls back on invalid ones", () => {
    expect(read("sort=total&direction=desc")).toMatchObject({
      sort: "total",
      direction: "desc",
    });
    expect(read("sort=created_at")).toMatchObject({
      sort: "created_at",
      direction: null,
    });
    // Any other value of either falls back like a broken status.
    expect(read("sort=subtotal")).toMatchObject({ sort: null });
    expect(read("direction=upwards")).toMatchObject({ direction: null });
  });
});
