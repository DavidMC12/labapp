# Task 005: login screen and application shell

Assignee: Worker 2. Branch: `w2/auth-shell`. Reviewer: Supervisor.

## Goal

Build the login screen and the authenticated application shell (header, navigation, logout) against the authentication API described in the spec. The backend does not serve these endpoints yet, so everything is developed and tested with a mocked `fetch`; later the same code talks to the real API without changes.

## Read first

- `docs/SPEC.md`: section 2 (roles and the API role values), section 3 (authentication and sessions), section 7 (error catalog and labels) and section 8 (`problem+json`).
- `docs/SEED.md`: the four demo users and the demo password.
- `docs/TESTABILITY.md`: the whole file. Every id below follows its grammar; the pattern check in `src/lib/testid.ts` must accept them.
- `frontend/src/components/ui/` and `frontend/src/lib/testid.ts`: the components and helpers you must reuse.

## Scope

You may create and edit files only under `frontend/`. You may add `@testing-library/user-event` as a dev dependency; add nothing else.

## Requirements

1. **API client** (`src/lib/api.ts`). `apiFetch<T>(path, init?)` calls `fetch` with a relative path (for example `/api/auth/me`), `credentials: "same-origin"` and a JSON body when one is given. A 2xx answer returns the parsed body, or `undefined` for 204. Any other answer throws an `ApiRequestError` that carries an `ApiProblem` (`type`, `title`, `status`, `code`, `detail`, optional `errors[]` of `{field, code, message}`, and any extra members). If the failure body is not a problem document (for example HTML from a proxy), throw an `ApiRequestError` with status, code `INTERNAL_ERROR` and the detail "Ocurrió un error inesperado. Inténtalo de nuevo."
2. **Types and labels.** `Role` is `"admin" | "sales" | "finance" | "readonly"`. `User` is `{id, name, email, role}`. A `roleLabel(role)` helper returns the Spanish labels of SPEC section 7 (Admin, Ventas, Finanzas, Solo lectura).
3. **Auth hooks** (`src/features/auth/`), built on TanStack Query. `useMe()` calls `GET /api/auth/me` and resolves to `null` on a 401 instead of throwing. `useLogin()` calls `POST /api/auth/login` with `{email, password}` and refreshes `me` on success. `useLogout()` calls `POST /api/auth/logout` and clears `me`.
4. **Login page** (`src/app/login/page.tsx`), all text in Spanish:
   - Heading "Iniciar sesión"; fields "Email" and "Contraseña" (a password input); submit button "Ingresar", which shows "Ingresando…" and the loading state while the request runs.
   - Client-side check before sending: an empty field shows the message "Este campo es obligatorio." on that field and nothing is sent.
   - A 422 answer maps `errors[].field` (`email`, `password`) to the matching field error. Any other problem (for example 401 `INVALID_CREDENTIALS`, 429 `RATE_LIMITED`) shows its `detail` in the form-level alert.
   - On success, go to `/`.
   - A box "Usuarios de demostración" lists the four seeded users (email and role label) and the sentence "Contraseña para todos: Demo-LabApp-2026!".
5. **Shell** (`src/app/(app)/layout.tsx`, and move the current home page under `src/app/(app)/`):
   - While `useMe` loads, show the text "Cargando…" (a status element with `aria-busy="true"`). If there is no session, replace the location with `/login`.
   - Header: the name "LabApp" as a link to `/`; navigation links "Clientes" (`/customers`), "Pedidos" (`/orders`) and "Facturas" (`/invoices`), visible to every role; the user's name, the role label and a "Salir" button that logs out and goes to `/login`.
   - Placeholder pages for `/customers`, `/orders` and `/invoices`, each with only a heading ("Clientes", "Pedidos", "Facturas").
6. **Test ids.** Use exactly these:

| Element | Test id |
|---|---|
| Login heading | `auth-login-heading` |
| Login form | `auth-login-form` |
| Email input (its error: derived) | `auth-login-email-input` |
| Password input (its error: derived) | `auth-login-password-input` |
| Submit button | `auth-login-submit-button` |
| Form-level alert | `auth-login-form-alert` |
| Demo users list | `auth-login-demo-list` |
| Demo user entries (1 to 4) | `auth-login-demo-item-1` to `auth-login-demo-item-4` |
| Demo password text | `auth-login-demo-password-text` |
| Shell loading status | `app-shell-loading-status` |
| Home link | `app-nav-home-link` |
| Customers, orders, invoices links | `app-nav-customers-link`, `app-nav-orders-link`, `app-nav-invoices-link` |
| User name | `app-user-name-text` |
| User role | `app-user-role-text` |
| Logout button | `app-logout-button` |
| Home heading | `app-home-heading` |
| Placeholder headings | `customers-list-heading`, `orders-list-heading`, `invoices-list-heading` |

7. **Tests.** Mock `fetch` (and `next/navigation`); do not use the network. Cover: the API client (success, 204, a problem document, a non-JSON failure), `roleLabel`, the login page (client-side validation, server field errors, the form alert, the loading state, redirect on success, the demo box), the shell (loading, redirect without session, user and nav rendering for each role label, logout), and that every test id in the table passes `isValidTestId`.
8. **Docs.** Add a short "Authentication" section to `frontend/README.md` (hooks, mocked testing, the placeholder pages).

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

- Commit as you go, in small real steps (about 10 to 14 commits). Messages follow Conventional Commits, in English, for example `feat(frontend): add api client`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
