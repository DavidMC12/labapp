# LabApp frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS + TanStack Query.
The test id contract implemented here is defined in `docs/TESTABILITY.md`.

## Requirements

- Node `24.22.2` and pnpm `12.16.1` (pinned in the repository's `mise.toml`).

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
  components/
    ui/       Button, Input, Select, Textarea, Link — interactive elements
              take a required testId; fields also share Field
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

## Customers

Feature code in `src/features/customers/`, screens under
`src/app/(app)/customers/`. Every screen is a client component; all text is
Spanish.

- Pages: the list (`/customers`), the create form (`/customers/new`), the
  detail (`/customers/{id}`) and the edit form (`/customers/{id}/edit`).
  Create and edit share `src/features/customers/CustomerForm.tsx`.
- URL parameters of the list (the state lives in the URL so links can be
  shared): `page` (integer, falls back to 1 when invalid), `q` (the search
  text, trimmed, present only when it has a value) and `status`
  (`active`/`inactive`, no filter when absent). Submitting the search goes
  back to page 1; a page beyond the last one is replaced in the URL by the
  last page (`max(1, ceil(total / 20))`).
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
