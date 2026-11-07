import { describe, expect, it } from "vitest";
import { isValidTestId, type TestId } from "@/lib/testid";

/**
 * Every test id required by the task 005 table. Declaring them as TestId[]
 * makes `tsc` reject any id the grammar rejects.
 */
const REQUIRED_IDS: readonly TestId[] = [
  // Login page
  "auth-login-heading",
  "auth-login-form",
  "auth-login-email-input",
  "auth-login-password-input",
  "auth-login-submit-button",
  "auth-login-form-alert",
  "auth-login-tagline-text",
  "auth-login-notice-text",
  "auth-login-demo-title-text",
  "auth-login-demo-list",
  "auth-login-demo-item-1",
  "auth-login-demo-item-2",
  "auth-login-demo-item-3",
  "auth-login-demo-item-4",
  "auth-login-demo-password-text",
  // Shell
  "app-shell-loading-status",
  "app-shell-error-alert",
  "app-shell-retry-button",
  "app-nav-home-link",
  "app-nav-customers-link",
  "app-nav-orders-link",
  "app-nav-invoices-link",
  "app-user-name-text",
  "app-user-role-text",
  "app-logout-button",
  "app-home-heading",
  "customers-list-heading",
  "orders-list-heading",
  "invoices-list-heading",
  // Derived error ids of the login fields
  "auth-login-email-error",
  "auth-login-password-error",
];

/** The test ids of the theme (task 023), declared for the grammar too. */
const THEME_IDS: readonly TestId[] = [
  "app-theme-select",
  "auth-login-theme-select",
];

describe("the theme ids of task 023", () => {
  it("lists every id of the theme exactly once", () => {
    expect(new Set(THEME_IDS).size).toBe(THEME_IDS.length);
  });

  it("makes every theme id pass isValidTestId", () => {
    for (const id of THEME_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});

describe("the test ids of the auth shell", () => {
  it("lists every id of the task table exactly once", () => {
    expect(new Set(REQUIRED_IDS).size).toBe(REQUIRED_IDS.length);
  });

  it("makes every id pass isValidTestId", () => {
    for (const id of REQUIRED_IDS) {
      expect(isValidTestId(id), id).toBe(true);
    }
  });
});
