/**
 * Test id contract, defined in docs/TESTABILITY.md.
 */

/**
 * The exact regular expression checked by the lint rule, the types and the
 * audit:
 *
 * ^(app|auth|customers|products|orders|invoices|payments|settings)(-[a-z][a-z0-9]*)+-(button|input|select|textarea|checkbox|radio|switch|link|tab|menuitem|form|table|row|cell|list|item|dialog|alert|error|status|text|heading)(-[0-9]+)?$
 */
export const TEST_ID_PATTERN =
  /^(app|auth|customers|products|orders|invoices|payments|settings)(-[a-z][a-z0-9]*)+-(button|input|select|textarea|checkbox|radio|switch|link|tab|menuitem|form|table|row|cell|list|item|dialog|alert|error|status|text|heading)(-[0-9]+)?$/;

export type TestIdModule =
  | "app"
  | "auth"
  | "customers"
  | "products"
  | "orders"
  | "invoices"
  | "payments"
  | "settings";

export type TestIdKind =
  | "button"
  | "input"
  | "select"
  | "textarea"
  | "checkbox"
  | "radio"
  | "switch"
  | "link"
  | "tab"
  | "menuitem"
  | "form"
  | "table"
  | "row"
  | "cell"
  | "list"
  | "item"
  | "dialog"
  | "alert"
  | "error"
  | "status"
  | "text"
  | "heading";

/**
 * The `<name>` part: one or more kebab-case words describing the element.
 * Template literal types cannot express "lowercase kebab-case words", so
 * casing and word structure are enforced at runtime by `isValidTestId` (and
 * later by the audit), while modules and kinds are enforced here by `tsc`.
 */
export type TestIdName = `${string}`;

/**
 * A valid test id: `<module>-<name>-<kind>` in kebab-case, with the numeric
 * record id appended after the kind for list items.
 */
export type TestId =
  | `${TestIdModule}-${TestIdName}-${TestIdKind}`
  | `${TestIdModule}-${TestIdName}-${TestIdKind}-${number}`;

/**
 * Checks that an id matches the test id grammar. Unlike the `TestId` type,
 * this works on strings coming from runtime sources.
 */
export function isValidTestId(id: string): boolean {
  return TEST_ID_PATTERN.test(id);
}

/**
 * Turns the test id of a field input into the test id of its error message:
 * `customers-form-email-input` -> `customers-form-email-error`.
 *
 * Throws when the id does not end in `-input`.
 */
export function errorTestId(inputTestId: TestId): TestId {
  if (!inputTestId.endsWith("-input")) {
    throw new Error(
      `errorTestId expects an id ending in "-input", received: "${inputTestId}"`,
    );
  }
  return `${inputTestId.slice(0, -"-input".length)}-error` as TestId;
}
