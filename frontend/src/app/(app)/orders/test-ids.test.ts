import { describe, expect, it } from "vitest";
import { isValidTestId, type TestId } from "@/lib/testid";

/**
 * Every test id of the brief 016 table plus the corrected-review ids
 * (B5), declared as `TestId[]` so `tsc` rejects any id the grammar
 * rejects. The `{...}` ids are derived with the sample order id 7, the
 * line id 3 and the product id 5.
 */
const REQUIRED_IDS: readonly TestId[] = [
  // List
  "orders-list-heading",
  "orders-list-new-link",
  "orders-list-customerfilter-text",
  "orders-list-customerfilter-clear-link",
  "orders-list-search-form",
  "orders-list-search-input",
  "orders-list-status-select",
  "orders-list-search-button",
  "orders-list-loading-status",
  "orders-list-empty-status",
  "orders-list-error-alert",
  "orders-list-retry-button",
  "orders-list-table",
  "orders-list-row-7",
  "orders-list-number-cell-7",
  "orders-list-customer-cell-7",
  "orders-list-state-cell-7",
  "orders-list-lines-cell-7",
  "orders-list-total-cell-7",
  "orders-list-created-cell-7",
  "orders-list-view-link-7",
  "orders-list-prev-button",
  "orders-list-next-button",
  "orders-list-page-text",
  "orders-list-total-text",
  "orders-list-footer-item",
  // Create
  "orders-form-heading",
  "orders-customer-form",
  "orders-form-customersearch-form",
  "orders-form-customersearch-input",
  "orders-form-customersearch-button",
  "orders-form-customer-select",
  "orders-form-customer-text",
  "orders-form-submit-button",
  "orders-form-cancel-link",
  "orders-form-alert",
  "orders-form-loading-status",
  "orders-form-forbidden-alert",
  "orders-form-error-alert",
  "orders-form-retry-button",
 // B5: states of the customers picker
  "orders-form-customer-loading-status",
  "orders-form-customer-empty-status",
  // Detail
  "orders-detail-heading",
  "orders-detail-state-status",
  "orders-detail-customer-link",
  "orders-detail-created-text",
  "orders-detail-updated-text",
  "orders-detail-invoice-link",
  "orders-detail-lines-table",
  "orders-detail-lines-heading",
  "orders-detail-line-row-3",
  "orders-detail-line-form-3",
  "orders-detail-line-product-cell-3",
  "orders-detail-line-quantity-cell-3",
  "orders-detail-line-price-cell-3",
  "orders-detail-line-total-cell-3",
  "orders-detail-nolines-text",
  "orders-detail-line-quantity-input-3",
  "orders-detail-line-save-button-3",
  "orders-detail-line-remove-button-3",
  "orders-detail-subtotal-text",
  "orders-detail-taxrate-text",
  "orders-detail-tax-text",
  "orders-detail-total-text",
  "orders-detail-preview-text",
  "orders-detail-addline-form",
  "orders-detail-addline-heading",
  "orders-detail-addline-product-select",
  "orders-detail-addline-quantity-input",
  "orders-detail-addline-submit-button",
  "orders-detail-changecustomer-form",
  "orders-detail-changecustomer-search-input",
  "orders-detail-changecustomer-search-button",
  "orders-detail-changecustomer-select",
  "orders-detail-changecustomer-submit-button",
  // B5 + B3: the toggle of the changer with its own search form
  "orders-detail-changecustomer-button",
  "orders-detail-changecustomer-search-form",
  "orders-detail-changecustomer-loading-status",
  "orders-detail-changecustomer-empty-status",
  "orders-detail-changecustomer-error-alert",
  "orders-detail-changecustomer-retry-button",
  "orders-detail-products-error-alert",
  "orders-detail-products-retry-button",
  "orders-detail-confirm-button",
  "orders-detail-cancel-button",
  "orders-detail-ship-button",
  "orders-detail-alert",
  "orders-detail-shortages-list",
  "orders-detail-shortage-item-5",
  "orders-detail-loading-status",
  "orders-detail-error-alert",
  "orders-detail-retry-button",
  "orders-detail-back-link",
];

describe("the test ids of the orders screens", () => {
  it("lists every id of the task table exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
