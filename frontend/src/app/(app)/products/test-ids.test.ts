import { describe, expect, it } from "vitest";
import { isValidTestId, type TestId } from "@/lib/testid";

/**
 * Every test id of the brief 029 table, declared as `TestId[]` so `tsc`
 * rejects any id the grammar rejects. The `{id}` ids are derived with the
 * sample product id 9 (the out-of-stock seed product).
 */
const REQUIRED_IDS: readonly TestId[] = [
  "products-list-heading",
  "products-list-search-form",
  "products-list-search-input",
  "products-list-search-button",
  "products-list-table",
  "products-list-row-9",
  "products-list-sku-cell-9",
  "products-list-name-cell-9",
  "products-list-price-cell-9",
  "products-list-stock-cell-9",
  // Only rendered when the stock is low or out.
  "products-list-stockstate-status-9",
  "products-list-footer-item",
  "products-list-loading-status",
  "products-list-empty-status",
  "products-list-error-alert",
  "products-list-retry-button",
  // The nav link of the shell.
  "app-nav-products-link",
];

describe("the test ids of the products screens", () => {
  it("lists every id of the task table exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
