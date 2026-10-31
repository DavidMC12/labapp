# Task 005: login screen and application shell

Assignee: Worker 2. Branch: `w2/auth-shell`. Reviewer: Supervisor.

## Goal

Build the login screen and the authenticated application shell (header, navigation, logout) against the authentication API described in the spec. The backend does not serve these endpoints yet, so everything is developed and tested with a mocked `fetch`; later the same code talks to the real API without changes. That promise is the reason for the precise request and failure rules below: a mocked test must not pass where the real API would fail.

## Read first

- `docs/SPEC.md`: section 2 (roles and the API role values), section 3 (authentication and sessions), section 7 (error catalog and labels) and section 8 (`problem+json`).
- `docs/SEED.md`: the four demo users and the demo password.
- `docs/TESTABILITY.md`: the whole file. Every id below follows its grammar; the pattern check in `src/lib/testid.ts` must accept them.
- `frontend/src/components/ui/` and `frontend/src/lib/testid.ts`: the components and helpers you must reuse.

## Scope

You may create and edit files only under `frontend/`. Add the dev dependency `@testing-library/user-event` with `pnpm add -D @testing-library/user-event` and commit `package.json` and `pnpm-lock.yaml` together; add nothing else. Do not add an `/api` rewrite to `next.config.ts`: that is a deployment decision made later.

## Requirements

### API client

1. `src/lib/api.ts` exports `apiFetch<T>(path: string, options?: { method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"; body?: unknown; headers?: Record<string, string> })`. It calls `fetch` with the relative `path` (for example `/api/auth/me`), `credentials: "same-origin"` and the header `Accept: application/json`. When `body` is defined it sends `Content-Type: application/json` and `JSON.stringify(body)`; without that header FastAPI does not read the body as JSON, so tests must assert the request headers and body.
2. A 2xx answer returns the parsed JSON, or `undefined` for 204.
3. Any other answer throws an `ApiRequestError` that carries an `ApiProblem` (`type`, `title`, `status`, `code`, `detail`, optional `errors[]` of `{field, code, message}`, and any extra members). The answer counts as a problem document when its body parses as a JSON object with a string `code` and a string `detail`, whatever its `content-type`. If it does not (for example HTML from a proxy), or if `fetch` itself rejects (network error), throw an `ApiRequestError` with status 0 for a rejection or the real status otherwise, code `INTERNAL_ERROR` and the detail "Ocurrió un error inesperado. Inténtalo de nuevo."

### Types and labels

4. `src/features/auth/types.ts` holds `Role` (`"admin" | "sales" | "finance" | "readonly"`), `User` (`{ id: number; name: string; email: string; role: Role }`) and `roleLabel(role)`, which returns the Spanish labels of SPEC section 7 (Admin, Ventas, Finanzas, Solo lectura).

### Auth hooks

5. `src/features/auth/` exports a constant `ME_QUERY_KEY = ["auth", "me"]` and three hooks on TanStack Query. Queries and mutations use `retry: false`.
   - `useMe()` calls `GET /api/auth/me` and resolves to `null` on a 401 (an expired session is treated as "no session" and redirects silently for now); any other error stays an error.
   - `useLogin()` calls `POST /api/auth/login` with `{ email, password }`. On success it must write the returned user with `setQueryData(ME_QUERY_KEY, user)` **before** the page navigates. Only invalidating the query is not enough: when the visitor first met a 401, the cache holds `null`, and the shell would read that stale value and bounce back to the login.
   - `useLogout()` calls `POST /api/auth/logout`. Whatever the answer (success, error or network failure), it clears the whole query cache with `queryClient.clear()` so one user's cached data is never shown to the next, and the caller then goes to `/login`.

### Login page (`src/app/login/page.tsx`), all text in Spanish

6. Structure: a heading "Iniciar sesión"; a `<form>` with `noValidate` (so the native browser validation never replaces our messages); the fields "Email" (`type="email"`, `autoComplete="username"`) and "Contraseña" (`type="password"`, `autoComplete="current-password"`); a submit button "Ingresar" that shows "Ingresando…" and the loading state while the request runs.
7. Behavior:
   - Before sending, an empty field shows "Este campo es obligatorio." on that field and nothing is sent. The email is trimmed first, so a whitespace-only email counts as empty; the password is checked as typed. The email is sent trimmed.
   - Each submit clears the errors of the previous one.
   - A second submit while one is pending is ignored (the guard lives in the handler, not only in the disabled button).
   - A 422 answer maps `errors[].field` (`email`, `password`) to the matching field error. A 422 with no matching entry, and any other problem (for example 401 `INVALID_CREDENTIALS`, 429 `RATE_LIMITED`, a network error), shows its `detail` in the form-level alert, which has `role="alert"`.
   - After a failed submit, focus goes to the form-level alert when it is shown, otherwise to the first field with an error.
   - On success, call `router.replace("/")` (the login page must not stay in the history).
8. A box titled "Usuarios de demostración" lists the four seeded users in the order of `docs/SEED.md` (email and role label) and the sentence "Contraseña para todos: Demo-LabApp-2026!". It is static: no click-to-fill. The title is a `<p>` that labels a `<section>` through `aria-labelledby`, not a heading, so the rule that every heading has a test id is not triggered.

### Shell (`src/app/(app)/layout.tsx`)

9. Move the current home page to `src/app/(app)/page.tsx` (heading "LabApp"). The layout renders `<header>`, `<nav aria-label="Principal">` and the single `<main>` that wraps the pages; pages do not render their own `<main>`.
10. While `useMe` loads, show the text "Cargando…" in a status element with `aria-busy="true"`. If it resolves to `null`, call `router.replace("/login")`. If it ends in an error other than a 401, show the error `detail` in an element with `role="alert"` and a button "Reintentar" that refetches.
11. Header: the name "LabApp" as a link to `/`; navigation links "Clientes" (`/customers`), "Pedidos" (`/orders`) and "Facturas" (`/invoices`), visible to every role; the user's name, the role label and a button "Salir". "Salir" shows the loading state and is disabled while the logout runs (no double click), then goes to `/login` with `router.replace`.
12. Placeholder pages `src/app/(app)/customers/page.tsx`, `src/app/(app)/orders/page.tsx` and `src/app/(app)/invoices/page.tsx`, each with only a heading ("Clientes", "Pedidos", "Facturas").

### Test ids

13. Use exactly these:

| Element | Test id |
|---|---|
| Login heading | `auth-login-heading` |
| Login form | `auth-login-form` |
| Email input (its error: derived) | `auth-login-email-input` |
| Password input (its error: derived) | `auth-login-password-input` |
| Submit button | `auth-login-submit-button` |
| Form-level alert | `auth-login-form-alert` |
| Demo box title | `auth-login-demo-title-text` |
| Demo users list | `auth-login-demo-list` |
| Demo user entries (1 to 4, in SEED order) | `auth-login-demo-item-1` to `auth-login-demo-item-4` |
| Demo password sentence (the whole sentence) | `auth-login-demo-password-text` |
| Shell loading status | `app-shell-loading-status` |
| Shell error alert | `app-shell-error-alert` |
| Shell retry button | `app-shell-retry-button` |
| Home link | `app-nav-home-link` |
| Customers, orders, invoices links | `app-nav-customers-link`, `app-nav-orders-link`, `app-nav-invoices-link` |
| User name | `app-user-name-text` |
| User role | `app-user-role-text` |
| Logout button | `app-logout-button` |
| Home heading | `app-home-heading` |
| Placeholder headings | `customers-list-heading`, `orders-list-heading`, `invoices-list-heading` |

### Tests and docs

14. **Tests.** Mock `fetch` and `next/navigation` (the router mock returns a stable object, so effects do not re-run on every render); do not use the network. Test `QueryClient` instances use `retry: false`. Cover:
    - the API client: success, 204, a problem document (also without a JSON `content-type`), a non-JSON failure, a rejected `fetch`, and the request headers and body (`Accept`, `Content-Type`, JSON body);
    - `roleLabel`;
    - the login page: client-side validation (empty fields, whitespace-only email), server field errors, an unmatched 422, the form alert, the loading state, the ignored second submit, focus after a failure, `router.replace("/")` on success, and the demo box;
    - the whole sequence "visit the shell, get a 401, land on the login, log in successfully, reach the shell without being sent back to the login";
    - the shell: loading, redirect without a session, the error alert with retry, the user and the navigation for each role label, and logout (also when the logout request fails);
    - that every test id in the table passes `isValidTestId`.
15. **Docs.** Add a short "Authentication" section to `frontend/README.md` (hooks, mocked testing, the placeholder pages, the decision that a 401 on `me` redirects silently for now).

## Acceptance criteria

From `frontend/`, all of these pass:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Rules for this task

- Commit as you go, in small real steps (about 12 to 16 commits). Messages follow Conventional Commits, in English, for example `feat(frontend): add api client`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
