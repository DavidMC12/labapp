import { describe, expect, it } from "vitest";
import { parseOrderIdParam, parseOrderListParams } from "./params";
import type { OrderListParams } from "./params";

describe("parseOrderIdParam", () => {
  it("accepts a positive integer id up to 2147483647", () => {
    expect(parseOrderIdParam("7")).toBe(7);
    expect(parseOrderIdParam("2147483647")).toBe(2147483647);
  });

  it("rejects zero, leading zeros, signs and other syntaxes", () => {
    for (const value of ["0", "007", "1e3", "-7", "+7", "7.5", " 7", "", "siete"]) {
      expect(parseOrderIdParam(value), JSON.stringify(value)).toBeNull();
    }
    expect(parseOrderIdParam(7)).toBeNull();
    expect(parseOrderIdParam(undefined)).toBeNull();
  });

  it("rejects an id above the 32-bit range", () => {
    expect(parseOrderIdParam("2147483648")).toBeNull();
  });
});

describe("parseOrderListParams", () => {
  function read(search: string): OrderListParams {
    return parseOrderListParams(new URLSearchParams(search));
  }

  it("reads the four parameters", () => {
    expect(read("page=2&q=ped&status=confirmed&customer_id=4")).toEqual({
      page: 2,
      q: "ped",
      status: "confirmed",
      customerId: 4,
    });
  });

  it("falls back to page 1 and no values on an empty URL", () => {
    expect(read("")).toEqual({
      page: 1,
      q: null,
      status: null,
      customerId: null,
    });
  });

  it("accepts a customer id up to 2147483647", () => {
    expect(read("customer_id=4").customerId).toBe(4);
    expect(read("customer_id=2147483647").customerId).toBe(2147483647);
  });

  it("ignores zero, signs, decimals, letters and ids above the limit", () => {
    for (const value of [
      "0",
      "007",
      "1e3",
      "-4",
      "4.5",
      " 4",
      "cuatro",
      "",
      "2147483648",
    ]) {
      expect(read(`customer_id=${value}`).customerId, value).toBeNull();
    }
  });

  it("reads the first occurrence of a repeated customer id", () => {
    expect(read("customer_id=4&customer_id=9").customerId).toBe(4);
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
    expect(read("q=%20ped%20").q).toBe("ped");
    expect(read("q=%20").q).toBeNull();
  });

  it("accepts the five statuses and rejects any other value", () => {
    for (const status of [
      "draft",
      "confirmed",
      "paid",
      "shipped",
      "cancelled",
    ]) {
      expect(read(`status=${status}`).status).toBe(status);
    }
    expect(read("status=green").status).toBeNull();
    expect(read("status=").status).toBeNull();
    expect(read("status=confirmed%20").status).toBeNull();
  });
});
