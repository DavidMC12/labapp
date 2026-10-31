# Testability contract

LabApp exists to be easy and reliable to automate. These rules apply to every screen. They are a contract, not a suggestion; the enforcement described below is planned for M1 and is not in place yet.

## Locators

1. Semantic HTML first: real `button`, `a`, `label`, `table`, `form`, headings and landmarks.
2. Every interactive element has an accessible name, so `getByRole` works.
3. Every interactive element and every element a test needs to read has a `data-testid`.
4. Naming: `module-element-action` in kebab-case, for example `customers-form-email-input`, `orders-confirm-button`. List rows add the record id: `customers-row-42`.

Playwright configuration for this attribute:

```ts
// playwright.config.ts
export default defineConfig({ use: { testIdAttribute: 'data-testid' } });
```

## Observable state

| Attribute | Meaning |
|---|---|
| `data-state` | The current state of a component (for example `idle`, `loading`, `success`, `error`). |
| `aria-busy="true"` | A region is loading or submitting. |
| `data-hydrated="true"` | Set on `<body>` once the client has hydrated, so tests never click a server-only render. |

Errors from the API are shown in an element with `role="alert"` and a `data-testid`, containing the Spanish message from the response.

## Enforcement (planned for M1)

- **Types:** shared UI components take a required `testId` prop; a missing one fails `tsc`.
- **Lint:** an ESLint rule rejects interactive elements without `data-testid`.
- **Audit:** `tools/audit/` loads each route in a browser and fails if an interactive element lacks `data-testid` or if axe reports serious accessibility violations. It runs in CI.

## Deterministic data

- A one-command start and a reset that restores the seed data in seconds.
- A controllable clock and fault injection (see [ARCHITECTURE.md](ARCHITECTURE.md)), available locally and, online, only with a token.
- Stable error `code` values for every rule (see [SPEC.md](SPEC.md)) and an `X-Request-Id` on every response.

## Goals

1. 100% of interactive elements carry `data-testid`, verified in CI.
2. One command starts the app and the data reset takes seconds.
3. No serious accessibility violations reported by axe.

## Not covered here

The end-to-end and API automation suite is written by the repository owner in `tests/`. Tests that belong to the application itself live next to the code.
