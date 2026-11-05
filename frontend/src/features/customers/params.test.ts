import { describe, expect, it } from "vitest";
import {
  parseCustomerListParams,
  parseCustomerIdParam,
} from "./params";

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
    ).toEqual({ page: 2, q: "ana", status: "active" });
  });

  it("falls back to page 1 and no values for an empty URL", () => {
    expect(parseCustomerListParams(new URLSearchParams())).toEqual({
      page: 1,
      q: null,
      status: null,
    });
  });

  it("falls back for invalid values", () => {
    expect(
      parseCustomerListParams(new URLSearchParams("page=0")),
    ).toEqual({ page: 1, q: null, status: null });
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
    ).toEqual({ page: 1, q: null, status: null });
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
