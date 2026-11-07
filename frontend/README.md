# LabApp frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS + TanStack Query.
The test id contract implemented here is defined in `docs/TESTABILITY.md`.

## Requirements

- Node `24.22.2` and pnpm `12.16.1` (pinned in the repository's `mise.toml`).

## Design

- The visual design is the "Libro mayor" theme in two voices: a warm
  paper background with dark green ink (light) and the same design on a
  dark ground with a light green accent (dark). Both share a
  fixed-width side rail for navigation and tables in the style of an
  accounting ledger.
- **Colors live once, in `src/app/globals.css`** as CSS custom properties
  on `:root` (the tokens: `paper`, `surface`, `ink`, `muted`, `line`,
  `control-border`, `rail`, `rail-ink`, `rail-muted`, `rail-hover`,
  `accent`, `accent-hover`, `accent-ink`, `ok-bg`, `off-bg`, `danger`,
  `danger-bg`, `focus`), mapped to Tailwind with `@theme inline`
  (`--color-paper: var(--paper)`), so utilities such as `bg-paper` and
  `text-ink` exist. Components and screens use only those utilities.
- **The tokens have three places.** The light values sit on bare `:root`
  with `color-scheme: light`. The dark values redefine **every** token in
  exactly two further places, both carrying the same values and
  `color-scheme: dark`: inside
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"])
  { … } }` (the default: the app follows the system preference, and the
  `:not([data-theme="light"])` guard respects a pinned light choice) and
  in `:root[data-theme="dark"] { … }` (the explicit choice, which wins
  over a light system preference). Nothing is defined only inside a media
  query or an attribute selector: every token has its first definition on
  bare `:root`, so a theme change is a value change, never a shape
  change.
- **The theme selector** (`src/components/ui/ThemeSelect.tsx`, a `Select`
  labeled "Tema" with the options "Sistema", "Claro" and "Oscuro")
  writes `data-theme` on `<html>` for an explicit choice and removes the
  attribute for "Sistema". It appears in the user block of the shell rail
  (`app-theme-select`, which is the same DOM slot under the links on the
  phone layout) and at the top right of the form column of the login
  (`auth-login-theme-select`), above the heading.
- **The choice is remembered** in `localStorage` under the key
  `labapp-theme` with the values `light` and `dark` (no key means
  system). Every read and write goes through `src/lib/theme.ts`, sits
  inside try/catch and degrades to the system theme when storage is
  blocked or empty (private windows, permissions policy), so the page
  never breaks.
- **There is no flash of the wrong theme:** the root layout carries an
  inline script (`THEME_INIT_SCRIPT` in `src/lib/theme.ts`) in the
  `<head>` that applies the stored choice before the first paint, again
  inside try/catch, and `<html>` is marked with
  `suppressHydrationWarning` because the script may add the attribute
  before hydration. The selector reads the real choice only after
  hydration, so the server and the client markup match.
- Typography: IBM Plex Sans (body) and IBM Plex Serif (headings, brand),
  loaded in the root `layout.tsx` with `next/font/google` and exposed as
  `--font-plex-sans` / `--font-plex-serif`.
- **Adding another theme** is still a change of `src/app/globals.css`
  alone, plus the new values under the same token names in all three
  places: bare `:root`, the media query place and the explicit
  `data-theme` place, with their `color-scheme` set. Two guard tests
  keep it honest:
  - `tokens.test.ts` parses the three places and checks that every token
    is defined on `:root` and redefined in both dark places with the
    fixed values, that the `color-scheme` declarations are in place, and
    that the WCAG contrast of every checked token pair holds for the
    light and the dark values.
  - `colors-guard.test.ts` scans every `.ts`/`.tsx`/`.css` file under
    `src/` except `globals.css` and the tests themselves, and fails on a
    hex color, on `rgb(`, `rgba(`, `hsl(`, `hsla(`, `oklch(`, `oklab(`,
    `lab(`, `lch(`, `hwb(`, `color(` or `color-mix(` and on any Tailwind
    palette class (`border-gray-200`, `bg-white`, `text-black`, …).
    `transparent`, `currentColor` and `inherit` are allowed.

## Commands

Run from this `frontend/` directory:

```bash
# install (exact versions from pnpm-lock.yaml)
pnpm install --frozen-lockfile

# dev server
pnpm dev

# production build, then server
pnpm build
pnpm start

# lint (ESLint, Next.js + TypeScript presets, zero warnings)
pnpm lint

# type check
pnpm typecheck

# unit tests (Vitest + Testing Library, jsdom)
pnpm test
```

## Layout

```
src/
  app/        layout ( providers + hydration marker) and pages
  app/globals.css     the design tokens of the theme (the only colored file)
  components/
    ui/       Button (primary/secondary/rail), Input, Select, Textarea,
              Link (text/primary/secondary/rail), Alert, ThemeSelect —
              interactive elements take a required testId; fields also
              share Field
    LedgerMark.tsx  the brand mark of the theme
  features/   customers + auth (hooks, api, screens helpers)
  lib/        testid.ts — the test id grammar: pattern, type and helpers
              theme.ts — the storage key, the setting and the no-flash
              script of the theme (see Design above)
  test/       Vitest setup
```

## Test id contract

- The grammar (`<module>-<name>-<kind>` with the numeric record id as the
  final suffix), the kind table and the observable state attributes are
  defined in [docs/TESTABILITY.md](../docs/TESTABILITY.md); the enforced
  pattern lives in `src/lib/testid.ts` as `TEST_ID_PATTERN`.
- Every interactive element renders `data-testid` built from `TestId`.
- `Button` exposes `data-state` (`idle`/`loading`) and `aria-busy`.
- `Input`, `Select` and `Textarea` render field errors as
  `<p role="alert">` with the test id derived by `errorTestId()` and
  linked from the control via `aria-describedby`; `Select` takes its
  options as children.
- `Link` wraps `next/link` and always renders `data-testid`.
- The hydration marker sets `data-hydrated="true"` on `<body>` once the
  client has hydrated.

## Authentication

- Hooks in `src/features/auth/hooks.ts` on TanStack Query (all with
  `retry: false`): `useMe()` (`GET /api/auth/me`, resolves to `null` on a
  401), `useLogin()` (`POST /api/auth/login`, caches the returned user with
  `setQueryData(ME_QUERY_KEY, user)` *before* the page navigates) and
  `useLogout()` (`POST /api/auth/logout`, clears the whole query cache
  whatever the answer).
- The backend does not serve the auth endpoints yet: everything is
  developed and tested against a mocked `fetch` (no test uses the
  network), so the same code talks to the real API without changes.
- A 401 on `me` is treated as "no session" and redirects to the login
  silently for now; the redirect decision will change when roles and
  protected routes arrive.
- `src/app/login/page.tsx` is the login screen (validation, field and
  form-level errors, demo users box). `src/app/(app)/` is the
  authenticated shell (header, navigation, logout) with placeholder pages
  for clients, orders and invoices.
- API access goes through `src/lib/api.ts` (`apiFetch`), which speaks the
  `application/problem+json` contract of docs/SPEC.md section 8: failures
  throw `ApiRequestError` with the problem document, or a synthesized
  `INTERNAL_ERROR` problem for non-JSON bodies and network errors.

## Summary

- The home page (`/`, after login) is the "Resumen": a heading, the line
  "Hola, {name} · {role label}" (`useMe`), and three sections — Clientes
  (Activos, Inactivos), Pedidos (Borrador, Confirmado, Pagado, Enviado,
  Cancelado) and Facturas (Emitida, Pagada, Anulada) — in a responsive
  grid (one column on a phone, up to four on a wide screen).
- The data layer is `src/features/summary/hooks.ts`: `useSummary()`
  returns the three groups, each group its counters, and each counter is
  the **live `total` of a list request** (`GET ...?page=1&status=...`,
  `retry: false`), made through the list hooks of the customers, orders
  and invoices modules. Nothing is hard coded, and because the request is
  the same one the list screens make, the summary and a visited list
  share the cache entry. A failing request breaks only its own card:
  the counter shows "—" while the section shows a "Reintentar" button,
  and a card that is loading shows "Cargando…". A 401 keeps the other
  hooks' behavior (it writes `null` into the me key, so the shell
  redirects to the login).
- Every counter is a link to the filtered list (what the parsers of the
  three list screens read): `/customers?status=active`,
  `/orders?status=confirmed`, `/invoices?status=issued`, and so on.
  The counts use `Intl.NumberFormat("es-US")` thousands separators
  (`src/features/summary/format.ts`) and the labels come from the label
  helpers of each module (`statusLabel`, `orderStatusLabel`,
  `invoiceStatusLabel`); they are never retyped.
- The ids use the `home` module of the test id contract
  (`home-customers-active-link`, `home-orders-draft-count-text`,
  `home-customers-active-count-text`), with the per-counter
  `home-{group}-{status}-loading-status` while a card loads and
  `home-{group}-retry-button` while a group has failed; the id list is
  asserted valid and unique in `src/app/(app)/page.test.tsx`.

## Invoices and payments

- Pages: the invoices list (`/invoices`) and the invoice detail
  (`/invoices/{id}`) with the payment history and the payment form;
  invoices are issued from the order (the "Facturar" button of the order
  detail for Admin and Finance on a confirmed order without an invoice).
  Feature code in `src/features/invoices/` (`api.ts`, `hooks.ts`,
  `params.ts`, `permissions.ts`, `types.ts`).
- URL parameters of the list: `page` (integer up to 1000000, valid or
  page 1), `q` (trimmed, matched against the invoice number or the
  customer snapshot) and `status` (`issued`/`paid`/`void`, no filter when
  absent). The list has no "new invoice" button.
- Keys: `["invoices","list",{page,q,status}]`, `["invoices","detail",id]`
  (numbers always). `useIssueInvoice` writes the new invoice into its
  detail key and invalidates the order detail, the order and invoice
  lists; `useRegisterPayment` writes the invoice of `PaymentResult`
  on the 201, and the 402 `PAYMENT_DECLINED` and 503
  `PAYMENT_GATEWAY_UNAVAILABLE` answers invalidate the invoice detail,
  the orders detail and both lists (the attempt is stored despite the
  error). A 401 writes `null` into `["auth","me"]`.
- **The idempotency key** lives in the payment form:
  `crypto.randomUUID()` (`^[A-Za-z0-9._-]{1,64}$`), sent as the
  `Idempotency-Key` header next to `If-Match: "<invoice version>"`. The
  form keeps the same key after a network error (no answer arrived, a
  retry is safe and replays or continues), takes a **new** key after any
  HTTP answer — a retry after a decline (402) or a gateway failure (503)
  is a new attempt — and whenever the user changes a field.
- Permissions (`canManageInvoices`): issuing and paying are Admin and
  Finance only; the UI hides the controls for the other roles and the
  server remains the authority. While a payment runs, the submit is
  disabled (`aria-busy`); a second submit is ignored by the guard.
- The card number travels as typed in the request body only: it is never
  written to the DOM outside its own input (`autocomplete="off"` on the
  field), to storage or to any log, and the form clears the card fields
  after a success.

## Orders

- Pages: the list (`/orders`), the create page (`/orders/new`) and the
  detail (`/orders/{id}`) of flow 2, following docs/SPEC.md section 5.
  Feature code in `src/features/orders/` (`api.ts`, `hooks.ts`,
  `params.ts`, `permissions.ts`, `types.ts`); money, dates and time are
  formatted by `src/lib/format.ts` (`formatMoney`, `formatDate`,
  `formatTime`, `formatDateTime`, both in UTC).
- URL parameters of the list: `page` (integer up to 1000000, valid or page
  1), `q` (trimmed, only when it has a value, matched against the order
  number or the customer name), `status` (one of the five states, no
  filter when absent) and `customer_id` (a strict positive integer up to
  2147483647, ignored when invalid; the customer detail links here).
  While `customer_id` is set, a line under the heading names the customer
  ("Pedidos de {name}", "Pedidos del cliente #{id}" while loading or for
  an unknown one) with a "Quitar filtro" link that keeps the other
  parameters. Search goes to page 1; a page beyond the last is
  `max(1, ceil(total / 20))` and the URL is replaced by it.
- Keys: `["orders","list",{page,q,status}]`, `["orders","detail",id]`
  (numbers always), `["products"]`. Every successful order mutation
  writes the returned order with `setQueryData` on its detail key,
  invalidates `["orders","list"]`, and a 401 writes `null` into
  `["auth","me"]`.
- Bodies follow the spec: money as strings, `customer_id`,
  `product_id` and `quantity` as integers (a non-digit quantity typed in
  the UI is sent as the typed string so the server's `INVALID_FORMAT`
  shows on the field), `version` in the bodies that change the order,
  `If-Match: "<version>"` on confirm/cancel/ship and the line deletion.
  Confirm and cancel additionally invalidate `["products"]` (stock).
- Permissions (`src/features/orders/permissions.ts`):
  `canEditOrders(role)` (create, change the customer, add/edit/remove
  lines) and `canTransitionOrders(role)` (confirm, cancel, ship) are true
  for `admin` and `sales` only; the UI hides the controls for the other
  roles and the server remains the authority. On a draft, every mutation
  control of the detail is disabled while any one of them is pending
  (they would otherwise race on `version`).
- Customer pickers (create and "Cambiar cliente") start with a disabled
  "Elige un cliente" placeholder, list at most 20 active customers and
  reset a choice the list no longer contains.

## Settings

- Page `/settings` ("Configuración"), feature code in
  `src/features/settings/` (`api.ts`, `hooks.ts`, `permissions.ts`,
  `types.ts`). Data layer on TanStack Query with `retry: false`:
  `useSettings()` (`GET /api/settings`, key `["settings"]`) and
  `useUpdateTaxRate()` (`PATCH /api/settings` with the body
  `{"tax_rate": "<the string exactly as typed>"}`; on success the answer
  replaces the `["settings"]` entry and every query whose key starts with
  `"orders"` is invalidated, so the draft previews and totals read the
  new rate).
- **Permission rule** (`canChangeTaxRate`): exactly `admin` (docs/SPEC.md
  section 2). Every role sees the heading, the "Impuesto" section and the
  current rate ("10.00 %"); only the Admin sees the form, the other roles
  see "Solo un administrador puede cambiar el impuesto." The server
  remains the authority.
- **The screen adds no validation**: no `min`/`max`/`step`, no trimming,
  no parsing. The input is `type="text" inputMode="decimal"` inside a
  `noValidate` form and the raw string travels to the server exactly as
  typed, so `" 7"`, `"1e1"` and `"10.123"` reach the API and come back as
  errors. The field errors of `tax_rate` (422 `INVALID_FORMAT` and
  `OUT_OF_RANGE`, with the `message` of the answer) show next to the
  field with the derived id `settings-taxrate-error` (the
  `errorTestId()` pattern of the other forms); any other problem (403,
  500, network) shows its `detail` in the form alert
  `settings-taxrate-alert`. On success the returned value stays in the
  input and a `role="status"` region announces it.
- The navigation link "Configuración" (`app-nav-settings-link`) is
  visible to every role; the current-section highlight covers it.

## Customers

Feature code in `src/features/customers/`, screens under
`src/app/(app)/customers/`. Every screen is a client component; all text is
Spanish.

- Pages: the list (`/customers`), the create form (`/customers/new`), the
  detail (`/customers/{id}`) and the edit form (`/customers/{id}/edit`).
  Create and edit share `src/features/customers/CustomerForm.tsx`.
- URL parameters of the list (the state lives in the URL so links can be
  shared): `page` (integer up to 1000000, falls back to 1 when invalid or
  out of range — the API answers 422 `OUT_OF_RANGE` beyond that), `q`
  (the search text, trimmed, present only when it has a value) and
  `status` (`active`/`inactive`, no filter when absent). Submitting the
  search goes back to page 1; a page beyond the last one is replaced in
  the URL by the last page (`max(1, ceil(total / 20))`).
- The detail page has a "Pedidos" section ("Ver pedidos de este cliente")
  that links to `/orders?customer_id={id}` — visible to every role, for
  active and inactive customers alike.
- Data layer on TanStack Query, all with `retry: false`:
  `useCustomers({page, q, status})`, `useCustomer(id)`,
  `useCreateCustomer()`, `useUpdateCustomer()` and
  `useSetCustomerStatus()`. Keys: `["customers","list",{page,q,status}]`  and `["customers","detail",id]`, with the id always a number (the route
  parameter is parsed once by `parseCustomerIdParam`, which only accepts
  `^[1-9][0-9]*$` up to 2147483647). A successful write caches the returned
  customer under its detail key before navigating and invalidates
  `["customers","list"]`; a status change sends
  `If-Match: "<version>"`, and any failure refetches the customer.
- Permission rule: `canManageCustomers(role)` in
  `src/features/customers/permissions.ts` is true for `admin` and `sales`
  only; the UI hides the write controls ("Nuevo cliente", "Editar",
  "Desactivar"/"Reactivar") for `finance` and `readonly`, which also see
  the "No tienes permiso para realizar esta acción." alert on the create
  and edit pages. The server remains the authority.
- The edit form captures the `version` when it is initialized or last
  reset ("Recargar datos"), never the one of a later background refetch,
  so an update cannot silently overwrite another user's change.
