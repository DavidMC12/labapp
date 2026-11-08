import { isValidTestId, type TestId } from "@/lib/testid";
import { describe, expect, it } from "vitest";

/**
 * Every test id of the settings screen (task 025). The ids are unique per
 * page: the form and the readonly sentence never render together.
 *
 * Note: the field error id follows `errorTestId` of src/lib/testid.ts,
 * like every other form of the app ("customers-form-email-input" ->
 * "customers-form-email-error"), so the input's derived error id is
 * `settings-taxrate-error` (the brief table wrote it as
 * `settings-taxrate-input-error`).
 */
const REQUIRED_IDS: readonly TestId[] = [
  // Shell
  "app-nav-settings-link",
  // Page
  "settings-page-heading",
  "settings-page-loading-status",
  "settings-page-error-alert",
  "settings-page-retry-button",
  // Tax rate section
  "settings-taxrate-heading",
  "settings-taxrate-current-text",
  "settings-taxrate-readonly-text",
  "settings-taxrate-form",
  "settings-taxrate-input",
  "settings-taxrate-error",
  "settings-taxrate-save-button",
  "settings-taxrate-alert",
  "settings-taxrate-success-status",
];

describe("the test ids of the settings screen", () => {
  it("lists every id exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
