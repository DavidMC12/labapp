import { describe, expect, it } from "vitest";
import { isValidTestId, type TestId } from "@/lib/testid";

/**
 * Every test id of the task table for the customers screens, declared as
 * TestId[] so `tsc` rejects any id the grammar rejects. The `{id}` ids are
 * derived with the sample id 7.
 */
const REQUIRED_IDS: readonly TestId[] = [
  // List
  "customers-list-heading",
  "customers-list-new-link",
  "customers-list-search-form",
  "customers-list-search-input",
  "customers-list-status-select",
  "customers-list-search-button",
  "customers-list-loading-status",
  "customers-list-empty-status",
  "customers-list-error-alert",
  "customers-list-retry-button",
  "customers-list-table",
  "customers-list-row-7",
  "customers-list-name-cell-7",
  "customers-list-email-cell-7",
  "customers-list-taxid-cell-7",
  "customers-list-state-cell-7",
  "customers-list-view-link-7",
  "customers-list-prev-button",
  "customers-list-next-button",
  "customers-list-page-text",
  "customers-list-total-text",
  // Shared create/edit form
  "customers-form-heading",
  "customers-customer-form",
  "customers-form-name-input",
  "customers-form-email-input",
  "customers-form-phone-input",
  "customers-form-taxid-input",
  "customers-form-address-textarea",
  "customers-form-submit-button",
  "customers-form-cancel-link",
  "customers-form-alert",
  "customers-form-reload-button",
  "customers-form-loading-status",
  "customers-form-error-alert",
  "customers-form-retry-button",
  "customers-form-forbidden-alert",
  // Detail
  "customers-detail-heading",
  "customers-detail-name-text",
  "customers-detail-email-text",
  "customers-detail-phone-text",
  "customers-detail-taxid-text",
  "customers-detail-address-text",
  "customers-detail-state-status",
  "customers-detail-edit-link",
  "customers-detail-deactivate-button",
  "customers-detail-reactivate-button",
  "customers-detail-back-link",
  "customers-detail-alert",
  "customers-detail-loading-status",
  "customers-detail-error-alert",
  "customers-detail-retry-button",
  // Derived error ids of the form fields
  "customers-form-name-error",
  "customers-form-email-error",
  "customers-form-phone-error",
  "customers-form-taxid-error",
  "customers-form-address-error",
];

describe("the test ids of the customers screens", () => {
  it("lists every id of the task table exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });

  it("appends the numeric id after the kind of the rows and cells", () => {
    for (const sample of [7, 99, 2147483647]) {
      for (const template of [
        "row",
        "name-cell",
        "email-cell",
        "taxid-cell",
        "state-cell",
        "view-link",
      ] as const) {
        expect(
          isValidTestId(`customers-list-${template}-${sample}`),
          `customers-list-${template}-${sample}`,
        ).toBe(true);
      }
    }
  });
});
