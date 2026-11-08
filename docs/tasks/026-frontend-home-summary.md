# Task 026: frontend home summary

Assignee: Worker 2. Branch: `w2/home-summary`. Reviewer: Supervisor.

**Base.** Branch from `main` (it contains the customers, orders, invoices, settings screens and the dark theme). The invoices API (task 019) may not be merged when you work: develop and test against a mocked `fetch`, with the answers of the "Invoices and payments API" subsection of `docs/SPEC.md` (literal examples included).

## Goal

The home page (`/`, after login) is only a heading. Make it a "Resumen" that gives every role a quick picture of the data and a way into each list: a welcome line, and counters for customers, orders by state and invoices by state, each linking to the filtered list. It gives the owner's tests a page with many stable, numeric, data-dependent elements, and it must stay correct when the data changes (it reads live counts; nothing is hard coded).

## Read first

`docs/SPEC.md` sections 4, 5 and 6 (the list rules: `status` filters, `total` counts every match), `docs/TESTABILITY.md`, `frontend/src/app/(app)/page.tsx`, `frontend/src/features/customers/`, `frontend/src/features/orders/` and `frontend/src/features/invoices/` (the list hooks and the URL parsers: the filtered list URLs of each screen), `frontend/src/lib/`, `frontend/src/components/ui/`, `tools/audit/README.md`.

## Scope

You may create and edit files only under `frontend/`: `src/features/summary/`, `src/app/(app)/page.tsx` and its tests, and the README. You may add small read-only helpers to the data layers of customers, orders and invoices only if a count cannot be read with the existing hooks (add, never change behavior). No new dependencies. Do not change any existing `data-testid` (the heading `app-home-heading` keeps its id and the text "LabApp" becomes "Resumen"; if an existing test asserts the old text, update that test only).

## Requirements

1. **Data layer** (`src/features/summary/`): one hook `useSummary()` returning, for each group, a count and its own loading and error state, so that a failing request breaks only its card. The counts are the `total` of a list request: customers with `status=active` and with `status=inactive`; orders for each of the five states; invoices for `issued`, `paid` and `void`. Reuse the list API functions of the modules with their query keys where it makes sense, so that a visited list and the summary share the cache; every request is `GET` with the `status` filter and `page=1`. `retry: false`. A 401 behaves as in the other hooks (the shell redirects to login).
2. **Page** (`src/app/(app)/page.tsx`, client component, all text in Spanish): heading "Resumen"; a line "Hola, {name}" with the user's role label (from `useMe`); three sections with an `h2` each: "Clientes" (Activos, Inactivos), "Pedidos" (Borrador, Confirmado, Pagado, Enviado, Cancelado) and "Facturas" (Emitida, Pagada, Anulada). Each counter is a link (the number large, the label under it) to the filtered list: `/customers?status=active`, `/orders?status=confirmed`, `/invoices?status=issued`, and so on (check the URL parsers of the three list screens and use exactly the query they read). A counter that is loading shows a status "Cargando…" in place of the number; one that failed shows "—" and a small "Reintentar" button for that section; never a blank card. The numbers use `Intl.NumberFormat("es-US")` thousands separators. The labels come from the label helpers of each module (never retyped).
3. **Layout.** A responsive grid (one column on a phone, up to four on a wide screen), cards with the existing tokens only (no color literals), readable in both themes, no horizontal scroll at 390 pixels.
4. **Test ids** (the `{x}` are the status values, for example `confirmed`): `app-home-heading`, `app-home-greeting-text`, `home-customers-heading`, `home-orders-heading`, `home-invoices-heading`, `home-customers-{x}-link` and `home-customers-{x}-count-text`, `home-orders-{x}-link` and `home-orders-{x}-count-text`, `home-invoices-{x}-link` and `home-invoices-{x}-count-text`, `home-customers-loading-status`, `home-orders-loading-status`, `home-invoices-loading-status` (per counter instead: `home-{group}-{x}-loading-status`), `home-customers-retry-button`, `home-orders-retry-button`, `home-invoices-retry-button`. Every id passes `isValidTestId` and is unique on the page (a test checks them); the static audit must pass.
5. **Tests.** Mock `fetch`; no network. Cover: the exact requests (paths and query), every counter rendered from `total`, the links and their URLs, the number format, the loading state per counter, one failing group (the others still render), the retry button, the greeting for each role, a 401, and that the ids are valid and unique. Keep the existing tests passing.
6. **Docs.** A "Summary" section in `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
