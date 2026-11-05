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

  it("accepts a page above 2147483647 only as far as the URL state goes", () => {
    // The parser keeps numeric pages as they are; the page-beyond-the-last
    // logic of the list corrects them against the real total.
    expect(
      parseCustomerListParams(new URLSearchParams("page=99")),
    ).toMatchObject({ page: 99 });
  });
});
