# Testability contract

LabApp exists to be easy and reliable to automate. These rules apply to every screen. They are a contract, not a suggestion; the enforcement described below is in place except the lint rule, which is planned.

## Locators

1. Semantic HTML first: real `button`, `a`, `label`, `table`, `form`, headings and landmarks.
2. Every interactive element has an accessible name, so `getByRole` works.
3. Every interactive element, every field error, every page heading and every value a test would assert on (status badges, totals, numbers, names in lists and details) has a `data-testid`.
4. Naming: `<module>-<name>-<kind>` in kebab-case, with the numeric record id appended after the kind for list items.
   - `module` is one of `app`, `auth`, `customers`, `products`, `orders`, `invoices`, `payments`, `settings`, `home`.
   - `name` is one or more kebab-case words describing the element (`form-email`, `confirm`, `list`). Each word starts with a letter, so a numeric record id can appear only as the final suffix after the kind: `customers-list-row-42` is valid, `customers-list-row-42-view-button` and `orders-line-7-quantity-input` are not (write `orders-line-quantity-input-7`).
   - `kind` is one of `button`, `input`, `select`, `textarea`, `checkbox`, `radio`, `switch`, `link`, `tab`, `menuitem`, `form`, `table`, `row`, `cell`, `list`, `item`, `dialog`, `alert`, `error`, `status`, `text`, `heading`.
   - Examples: `customers-form-email-input`, `customers-form-email-error`, `orders-confirm-button`, `customers-list-row-42`, `orders-total-text`.
   - The pattern checked by the lint rule, the types and the audit is:

```
^(app|auth|customers|products|orders|invoices|payments|settings|home)(-[a-z][a-z0-9]*)+-(button|input|select|textarea|checkbox|radio|switch|link|tab|menuitem|form|table|row|cell|list|item|dialog|alert|error|status|text|heading)(-[0-9]+)?$
```

Playwright configuration for this attribute:

```ts
// playwright.config.ts
export default defineConfig({ use: { testIdAttribute: 'data-testid' } });
```

## Observable state

The document title names the page: `{page} · LabApp` (the
`useDocumentTitle` hook of the frontend; the details keep their section
title until the record arrives).

| Attribute | Meaning |
|---|---|
| `data-state` | The current state of a component (for example `idle`, `loading`, `success`, `error`). |
| `aria-busy="true"` | A region is loading or submitting. |
| `data-hydrated="true"` | Set on `<body>` once the client has hydrated, so tests never click a server-only render. |

Errors from the API are shown in an element with `role="alert"` and a `data-testid`, containing the Spanish message from the response. A field-level error uses kind `error` (`customers-form-email-error`); a form- or page-level API error uses kind `alert` (`customers-form-alert`). The app has two confirmation dialogs on the native `<dialog>`: `orders-cancel-confirm-dialog` (the cancel of an order) and `customers-deactivate-confirm-dialog` (the deactivation of a customer); every other action runs at the first click.

## Which kind to use

| Element | Kind |
|---|---|
| `button`, `summary`, `[role=button]` | `button` |
| `a[href]`, `[role=link]` | `link` |
| `input` of type text, email, password, number, search, tel or url; `[role=textbox]`, `[role=spinbutton]`, `[role=slider]` | `input` |
| `input[type=checkbox]` | `checkbox` |
| `input[type=radio]` | `radio` |
| `[role=switch]` | `switch` |
| `select`, `[role=combobox]` | `select` |
| `textarea` | `textarea` |
| `[role=tab]`, `[role=menuitem]` | `tab`, `menuitem` |
| `[role=option]`, list entries | `item` |

## What counts as interactive

An element is interactive if it is natively focusable or clickable (`a[href]`, `button`, `input` other than `type=hidden`, `select`, `textarea`, `summary`), has a `tabindex` of 0 or more, has one of the roles `button`, `link`, `checkbox`, `radio`, `switch`, `tab`, `menuitem`, `option`, `combobox`, `textbox`, `slider` or `spinbutton`, or has a click handler.

## Enforcement

- **Types (in place):** shared UI components take a required `testId` prop; a missing one fails `tsc`.
- **Static audit (in place):** `tools/audit/testid-audit.mjs` parses the frontend source and fails when an interactive or semantic element, a shared UI component or an element with `role="alert"` or `role="status"` has no test id, or when a literal id does not match the grammar. It runs in CI (see [tools/audit/README.md](../tools/audit/README.md)).
- **Lint (planned):** an ESLint rule rejects interactive elements without `data-testid` and ids that do not match the pattern above.
- **Browser audit (in place, `tools/audit/browser-audit.mjs`):** it opens a headless browser on every route and scripted state listed in `tools/audit/states.json` (each dialog, empty state, validation-error state and error state, and the detail pages of fixed seed records; the list grows with every screen). It fails if an interactive element lacks a valid `data-testid` or if axe reports serious or critical violations, and it prints the states it covered. The 100% goal is measured over those states, so a state missing from the list is a gap in the audit, not a pass. It runs in CI, in the light and in the dark theme.
- **Catalog (in place):** [TESTIDS.md](TESTIDS.md) lists every id of every audited state with its element, for the author of the automation suite. It is generated by the browser audit (`--catalog`) and CI fails when the committed copy is out of date.

## Deterministic data

- A one-command start and a reset that restores the seed data in seconds.
- A controllable clock and fault injection (see [ARCHITECTURE.md](ARCHITECTURE.md)), available locally and, online, only with a token.
- Stable error `code` values for every rule (see [SPEC.md](SPEC.md)) and an `X-Request-Id` on every response.

## Goals

1. 100% of interactive elements carry `data-testid`, verified in CI.
2. One command starts the app and the data reset takes seconds.
3. No serious or critical accessibility violations reported by axe.

## Not covered here

The end-to-end and API automation suite is written by the repository owner in `tests/`. Tests that belong to the application itself live next to the code.
