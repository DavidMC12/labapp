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
 * The `<name>` part: one or more kebab-case words describing the element,
 * each starting with a letter (see docs/TESTABILITY.md). Template literal
 * types cannot express "lowercase kebab-case words", so casing and word
 * structure are enforced at runtime by `isValidTestId` (and later by the
 * audit), while modules and kinds are enforced here by `tsc`.
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

const FIELD_ID_PATTERN =
  /^(?<prefix>.+)-(?<kind>input|select|textarea)(?<suffix>-(?<number>[0-9]+))?$/;

/**
 * Turns the test id of a field control into the test id of its error
 * message, keeping a numeric record id suffix:
 *
 * - `customers-form-email-input` -> `customers-form-email-error`
 * - `orders-line-quantity-input-7` -> `orders-line-quantity-error-7`
 *
 * Accepts only ids whose kind is `input`, `select` or `textarea`; throws
 * for any other kind.
 */
export function errorTestId(fieldTestId: TestId): TestId {
  const match = FIELD_ID_PATTERN.exec(fieldTestId);

  if (!match?.groups) {
    throw new Error(
      `errorTestId expects an id whose kind is "input", "select" or "textarea", received: "${fieldTestId}"`,
    );
  }

  return `${match.groups.prefix}-error${match.groups.suffix ?? ""}` as TestId;
}
