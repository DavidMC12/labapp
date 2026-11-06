import { describe, expect, it } from "vitest";
import { isValidTestId, type TestId } from "@/lib/testid";

/**
 * Every test id of the brief 020 table plus the ids the static audit
 * requires for the `h2` elements of the detail, declared as `TestId[]` so
 * `tsc` rejects any id the grammar rejects. The `{...}` ids are derived
 * with the sample invoice id 7, the line id 3 and the payment id 5.
 */
const REQUIRED_IDS: readonly TestId[] = [
  // List
  "invoices-list-heading",
  "invoices-list-search-form",
  "invoices-list-search-input",
  "invoices-list-status-select",
  "invoices-list-search-button",
  "invoices-list-loading-status",
  "invoices-list-empty-status",
  "invoices-list-error-alert",
  "invoices-list-retry-button",
  "invoices-list-table",
  "invoices-list-row-7",
  "invoices-list-number-cell-7",
  "invoices-list-order-cell-7",
  "invoices-list-customer-cell-7",
  "invoices-list-state-cell-7",
  "invoices-list-total-cell-7",
  "invoices-list-created-cell-7",
  "invoices-list-view-link-7",
  "invoices-list-order-link-7",
  "invoices-list-footer-item",
  "invoices-list-prev-button",
  "invoices-list-next-button",
  "invoices-list-page-text",
  "invoices-list-total-text",
  // Detail
  "invoices-detail-heading",
  "invoices-detail-state-status",
  "invoices-detail-order-link",
  "invoices-detail-customer-text",
  "invoices-detail-taxid-text",
  "invoices-detail-address-text",
  "invoices-detail-created-text",
  "invoices-detail-lines-table",
  "invoices-detail-lines-heading",
  "invoices-detail-line-row-3",
  "invoices-detail-line-product-cell-3",
  "invoices-detail-line-quantity-cell-3",
  "invoices-detail-line-price-cell-3",
  "invoices-detail-line-total-cell-3",
  "invoices-detail-subtotal-text",
  "invoices-detail-taxrate-text",
  "invoices-detail-tax-text",
  "invoices-detail-total-text",
  "invoices-detail-payments-table",
  "invoices-detail-payments-heading",
  "invoices-detail-payment-row-5",
  "invoices-detail-payment-method-cell-5",
  "invoices-detail-payment-state-cell-5",
  "invoices-detail-payment-amount-cell-5",
  "invoices-detail-payment-detail-cell-5",
  "invoices-detail-nopayments-text",
  "invoices-detail-loading-status",
  "invoices-detail-error-alert",
  "invoices-detail-retry-button",
  "invoices-detail-back-link",
  "invoices-detail-closed-text",
  // Payment form
  "payments-register-form",
  "payments-register-heading",
  "payments-register-method-select",
  "payments-register-amount-input",
  "payments-register-cardnumber-input",
  "payments-register-cardexpiry-input",
  "payments-register-cardcvc-input",
  "payments-register-reference-input",
  "payments-register-submit-button",
  "payments-register-alert",
  "payments-register-success-status",
  // Order detail
  "orders-detail-invoice-button",
];

describe("the test ids of the invoices screens", () => {
  it("lists every id of the task table exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
