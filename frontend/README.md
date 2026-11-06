# LabApp frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS + TanStack Query.
The test id contract implemented here is defined in `docs/TESTABILITY.md`.

## Requirements

- Node `24.22.2` and pnpm `12.16.1` (pinned in the repository's `mise.toml`).

## Design

- The visual design is the "Libro mayor" light theme: a warm paper
  background, dark green ink, a fixed-width side rail for navigation and
  tables in the style of an accounting ledger.
- **Colors live once, in `src/app/globals.css`** as CSS custom properties
  on `:root` (the tokens: `paper`, `surface`, `ink`, `muted`, `line`,
  `control-border`, `rail`, `rail-ink`, `rail-muted`, `rail-hover`,
  `accent`, `accent-hover`, `accent-ink`, `ok-bg`, `off-bg`, `danger`,
  `danger-bg`, `focus`), mapped to Tailwind with `@theme inline`
  (`--color-paper: var(--paper)`), so utilities such as `bg-paper` and
  `text-ink` exist. Components and screens use only those utilities.
- Typography: IBM Plex Sans (body) and IBM Plex Serif (headings, brand),
  loaded in the root `layout.tsx` with `next/font/google` and exposed as
  `--font-plex-sans` / `--font-plex-serif`.
- **Adding a theme changes `src/app/globals.css` alone**: swap the values
  of the CSS custom properties. No component needs editing; a test guards
  it (next point).
- Two guard tests, both under `src/app/`:
  - `tokens.test.ts` reads the tokens back from `globals.css` and checks
    the WCAG contrast ratios of the token pairs the theme relies on.
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
              Link (text/primary/secondary/rail), Alert — interactive
              elements take a required testId; fields also share Field
    LedgerMark.tsx  the brand mark of the theme
  features/   customers + auth (hooks, api, screens helpers)
  lib/        testid.ts — the test id grammar: pattern, type and helpers
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
  number or the customer name) and `status` (one of the five states, no
  filter when absent). Search goes to page 1; a page beyond the last is
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
- Data layer on TanStack Query, all with `retry: false`:
  `useCustomers({page, q, status})`, `useCustomer(id)`,
  `useCreateCustomer()`, `useUpdateCustomer()` and
  `useSetCustomerStatus()`. Keys: `["customers","list",{page,q,status}]`
  and `["customers","detail",id]`, with the id always a number (the route
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
