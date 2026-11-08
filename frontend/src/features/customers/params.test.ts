import { describe, expect, it } from "vitest";
import {
  customerSortDefaultDirection,
  customerSortLabel,
  flipCustomerSortDirection,
  isDefaultCustomerSort,
  parseCustomerListParams,
  parseCustomerIdParam,
  resolveCustomerSort,
} from "./params";

describe("the customers sort helpers", () => {
  it("acts the default direction of each field out", () => {
    expect(customerSortDefaultDirection("created_at")).toBe("desc");
    expect(customerSortDefaultDirection("name")).toBe("asc");
    expect(customerSortDefaultDirection("email")).toBe("asc");
  });

  it("flips one direction and never leaves the valid pair", () => {
    expect(flipCustomerSortDirection("asc")).toBe("desc");
    expect(flipCustomerSortDirection("desc")).toBe("asc");
  });

  it("resolves the effective sort of the URL values", () => {
    // Nothing in the URL: the plain-list order.
    expect(resolveCustomerSort({ sort: null, direction: null })).toEqual({
      sort: "created_at",
      direction: "desc",
    });
    // The direction default depends on the field.
    expect(resolveCustomerSort({ sort: "name", direction: null })).toEqual({
      sort: "name",
      direction: "asc",
    });
    // An explicit direction applies to the field of the URL, even
    // without `sort` (created_at is the default field).
    expect(resolveCustomerSort({ sort: null, direction: "asc" })).toEqual({
      sort: "created_at",
      direction: "asc",
    });
    expect(resolveCustomerSort({ sort: "email", direction: "desc" })).toEqual({
      sort: "email",
      direction: "desc",
    });
  });

  it("answers whether a sort is the one of the plain list", () => {
    expect(isDefaultCustomerSort({ sort: "created_at", direction: "desc" }))
      .toBe(true);
    expect(isDefaultCustomerSort({ sort: "created_at", direction: "asc" }))
      .toBe(false);
    expect(isDefaultCustomerSort({ sort: "name", direction: "asc" })).toBe(false);
  });

  it("labels each field in Spanish", () => {
    expect(customerSortLabel("name")).toBe("Nombre");
    expect(customerSortLabel("email")).toBe("Email");
    expect(customerSortLabel("created_at")).toBe("Creado");
  });
});

describe("parseCustomerIdParam", () => {
  it("accepts a plain positive decimal id", () => {
    expect(parseCustomerIdParam("7")).toBe(7);
    expect(parseCustomerIdParam("2147483647")).toBe(2147483647);
  });

  it("rejects every value outside the strict pattern", () => {
    expect(parseCustomerIdParam(undefined)).toBeNull();
    expect(parseCustomerIdParam("")).toBeNull();
    expect(parseCustomerIdParam("0")).toBeNull();
    expect(parseCustomerIdParam("007")).toBeNull();
    expect(parseCustomerIdParam("1e3")).toBeNull();
    expect(parseCustomerIdParam("-1")).toBeNull();
    expect(parseCustomerIdParam(" 7")).toBeNull();
    expect(parseCustomerIdParam("7.0")).toBeNull();
    expect(parseCustomerIdParam("ab")).toBeNull();
    // An id handed over as a route object value is never trusted either.
    expect(parseCustomerIdParam(["7"])).toBeNull();
    expect(parseCustomerIdParam(7)).toBeNull();
  });

  it("rejects ids above 2147483647", () => {
    expect(parseCustomerIdParam("2147483648")).toBeNull();
    expect(parseCustomerIdParam("999999999999999")).toBeNull();
  });
});

describe("parseCustomerListParams", () => {
  it("reads page, q and status", () => {
    expect(
      parseCustomerListParams(new URLSearchParams("page=2&q=ana&status=active")),
    ).toEqual({
      page: 2,
      q: "ana",
      status: "active",
      sort: null,
      direction: null,
    });
  });

  it("falls back to page 1 and no values for an empty URL", () => {
    expect(parseCustomerListParams(new URLSearchParams())).toEqual({
      page: 1,
      q: null,
      status: null,
      sort: null,
      direction: null,
    });
  });

  it("falls back for invalid values", () => {
    expect(
      parseCustomerListParams(new URLSearchParams("page=0")),
    ).toEqual({ page: 1, q: null, status: null, sort: null, direction: null });
    expect(
      parseCustomerListParams(new URLSearchParams("page=1e3")),
    ).toMatchObject({ page: 1 });
    expect(
      parseCustomerListParams(new URLSearchParams("page=007")),
    ).toMatchObject({ page: 1 });
    expect(
      parseCustomerListParams(new URLSearchParams("status=everybody")),
    ).toMatchObject({ status: null });
    expect(
      parseCustomerListParams(new URLSearchParams("page=abc&q=%20%20")),
    ).toEqual({ page: 1, q: null, status: null, sort: null, direction: null });
  });

  it("reads a valid sort and direction and falls back on invalid ones", () => {
    expect(
      parseCustomerListParams(new URLSearchParams("sort=name&direction=desc")),
    ).toMatchObject({ sort: "name", direction: "desc" });
    expect(
      parseCustomerListParams(new URLSearchParams("sort=created_at")),
    ).toMatchObject({ sort: "created_at", direction: null });
    // Any other value of either is as absent as a broken status.
    expect(
      parseCustomerListParams(new URLSearchParams("sort=tax_id")),
    ).toMatchObject({ sort: null });
    expect(
      parseCustomerListParams(new URLSearchParams("direction=upwards")),
    ).toMatchObject({ direction: null });
  });

  it("keeps a page inside the API range", () => {
    expect(
      parseCustomerListParams(new URLSearchParams("page=1000000")),
    ).toMatchObject({ page: 1000000 });
  });

  it("falls back to page 1 above the API range", () => {
    // The API answers 422 OUT_OF_RANGE to page > 1000000; the URL is page
    // state, so the boundary value falls back like any other invalid one.
    expect(
      parseCustomerListParams(new URLSearchParams("page=1000001")),
    ).toMatchObject({ page: 1 });
    expect(
      parseCustomerListParams(new URLSearchParams("page=999999999999999")),
    ).toMatchObject({ page: 1 });
  });

  it("does not correct a page inside the range for the detail id", () => {
    // The detail id keeps its own larger cap (docs/SPEC.md section 4 cap:
    // 2147483647), unchanged by the page range.
    expect(parseCustomerIdParam("2147483647")).toBe(2147483647);
  });
});
