import { describe, expect, it } from "vitest";
import { errorTestId, isValidTestId } from "./testid";

describe("isValidTestId", () => {
  it("accepts the examples from docs/TESTABILITY.md", () => {
    expect(isValidTestId("customers-form-email-input")).toBe(true);
    expect(isValidTestId("customers-form-email-error")).toBe(true);
    expect(isValidTestId("orders-confirm-button")).toBe(true);
    expect(isValidTestId("customers-list-row-42")).toBe(true);
    expect(isValidTestId("orders-total-text")).toBe(true);
  });

  it("accepts other valid ids", () => {
    expect(isValidTestId("app-home-heading")).toBe(true);
    expect(isValidTestId("auth-sign-in-link")).toBe(true);
    expect(isValidTestId("products-list-row-7")).toBe(true);
    expect(isValidTestId("payments-form-total-input")).toBe(true);
    expect(isValidTestId("orders-line-quantity-input-7")).toBe(true);
    expect(isValidTestId("customers-list-row-42")).toBe(true);
  });

  it("rejects a bare numeric name segment before the kind", () => {
    expect(isValidTestId("invoices-3-alert")).toBe(false);
    expect(isValidTestId("orders-line-7-quantity-input")).toBe(false);
  });

  it("rejects ids that carry more than one suffix", () => {
    expect(isValidTestId("customers-list-row-42-view-button")).toBe(false);
  });

  it("rejects an id ending in -input-x", () => {
    expect(isValidTestId("customers-form-email-input-x")).toBe(false);
  });

  it("rejects a trailing dash", () => {
    expect(isValidTestId("orders-total-text-")).toBe(false);
  });

  it("rejects an unknown module", () => {
    expect(isValidTestId("todos-list-item")).toBe(false);
  });

  it("accepts the home module of the summary screen", () => {
    expect(isValidTestId("home-customers-heading")).toBe(true);
    expect(isValidTestId("home-orders-shipped-count-text")).toBe(true);
    expect(isValidTestId("home-invoices-void-link")).toBe(true);
    expect(isValidTestId("home-customers-active-loading-status")).toBe(true);
  });

  it("rejects an unknown kind", () => {
    expect(isValidTestId("app-list-thing")).toBe(false);
  });

  it("rejects uppercase words", () => {
    expect(isValidTestId("Customers-form-email-input")).toBe(false);
    expect(isValidTestId("customers-Form-email-input")).toBe(false);
    expect(isValidTestId("customers-form-email-Input")).toBe(false);
  });

  it("rejects ids without a kind", () => {
    expect(isValidTestId("app-home")).toBe(false);
  });

  it("rejects ids without a module", () => {
    expect(isValidTestId("form-email-input")).toBe(false);
  });

  it("rejects a name segment with trailing letters on the kind", () => {
    expect(isValidTestId("app-home-heading2")).toBe(false);
  });

  it("rejects more than one numeric suffix", () => {
    expect(isValidTestId("customers-list-row-42-13")).toBe(false);
  });

  it("rejects an empty id", () => {
    expect(isValidTestId("")).toBe(false);
  });
});

describe("errorTestId", () => {
  it("turns an input id into its error id", () => {
    expect(errorTestId("customers-form-email-input")).toBe(
      "customers-form-email-error",
    );
  });

  it("keeps the numeric suffix of a suffixed field id", () => {
    expect(errorTestId("orders-line-quantity-input-7")).toBe(
      "orders-line-quantity-error-7",
    );
  });

  it("accepts select and textarea field kinds", () => {
    expect(errorTestId("customers-form-status-select")).toBe(
      "customers-form-status-error",
    );
    expect(errorTestId("orders-line-notes-textarea")).toBe(
      "orders-line-notes-error",
    );
    expect(errorTestId("orders-line-product-select-3")).toBe(
      "orders-line-product-error-3",
    );
  });

  it("throws for any other kind", () => {
    expect(() => errorTestId("orders-confirm-button")).toThrow(
      /"input", "select" or "textarea"/,
    );
    expect(() => errorTestId("customers-form-email-error")).toThrow(
      /"input", "select" or "textarea"/,
    );
  });
});
