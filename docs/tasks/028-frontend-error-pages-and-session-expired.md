# Task 028: frontend error pages and the expired session notice

Assignee: Worker 2. Branch: `w2/error-pages`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 027 is merged (the supervisor merges it before this starts, or tells you to branch from `w2/customer-orders`).

## Goal

Two gaps that a test author will hit at once. (1) There is no page for an unknown route or for a crash: the user sees Next.js defaults, with no design, no Spanish and no test ids. (2) When a session expires, the shell redirects to the login silently; SPEC section 3 defines the code `SESSION_EXPIRED` ("Tu sesión expiró. Inicia sesión de nuevo.") precisely so that tests can move the clock and observe the expiry, but the user never sees it.

## Read first

`docs/SPEC.md` section 3 (sessions, `SESSION_EXPIRED` and `UNAUTHENTICATED`) and section 7; `docs/TESTABILITY.md`; `frontend/src/app/layout.tsx`, `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/features/auth/hooks.ts`, the `note401` helpers of `frontend/src/features/{customers,orders,invoices,settings}/hooks.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/testid.ts`, `frontend/src/components/ui/`.

## Scope

You may create and edit files only under `frontend/`: `src/app/not-found.tsx`, `src/app/error.tsx` and their tests, `src/features/auth/` (a small session helper), the `note401` helpers of the four feature hooks files (each keeps its behavior and delegates to the new helper), the shell layout (only the redirect target), the login page (only the notice) and their tests, and the README. No new dependencies. Do not change any existing `data-testid` or text.

## Requirements

1. **Not found** (`src/app/not-found.tsx`, a server component in the root layout, themed with the existing tokens, readable in both themes): heading "Página no encontrada", a sentence "La dirección que buscas no existe o fue movida." and a link "Ir al inicio" to `/`. Ids: `app-notfound-heading`, `app-notfound-home-link`. It must be what Next renders for any unknown path (no extra route needed).
2. **Error boundary** (`src/app/error.tsx`, a client component with the `error` and `reset` props): heading "Algo salió mal", a sentence "Ocurrió un error inesperado. Puedes intentarlo de nuevo.", a button "Reintentar" that calls `reset`, and a link "Ir al inicio". Ids: `app-error-heading`, `app-error-retry-button`, `app-error-home-link`. The text never shows `error.message` or `error.digest` (a crash can carry data). The component logs nothing to the console.
3. **Session helper** (`src/features/auth/session.ts`): one function `noteUnauthorized(error, queryClient)`: for an `ApiRequestError` with status 401 it writes `null` into the `["auth", "me"]` entry (as the four `note401` helpers do today) and, when the problem code is `SESSION_EXPIRED`, also writes `true` under a second key `["auth", "session-expired"]`. `useMe` and the four `note401` helpers use it (their other behavior stays). A successful login clears the second key.
4. **Redirect.** When the shell has no session it replaces the location with `/login?expired=1` if the second key is `true`, and with `/login` otherwise (exactly as today).
5. **Login notice.** The login page shows, above the form, an alert "Tu sesión expiró. Inicia sesión de nuevo." with the id `auth-login-expired-alert` only when the URL has `expired=1` (read with `useSearchParams` inside a `Suspense` boundary). Nothing else on the page changes; without the parameter the notice is absent. It does not hide the demo credentials or any existing id.
6. **Test ids.** All the new ids are valid and unique; the static audit passes (the audit requires an id on every heading, link, button and `role="alert"`).
7. **Tests.** Mock `fetch` and `next/navigation`. Cover: the not-found and error pages (texts, ids, the retry button calling `reset`, no `message` or `digest` in the output), `noteUnauthorized` for a 401 `SESSION_EXPIRED`, a 401 `UNAUTHENTICATED`, a non-401 error and a non-API error; each of the four hooks files writing both keys on a 401 `SESSION_EXPIRED`; the shell redirect target in both cases; the login notice with and without the parameter, and that it disappears after a successful login. Keep every existing test passing.
8. **Docs.** A short "Error pages and the expired session" section in `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
