# Task 027: frontend customer orders filter and layout polish

Assignee: Worker 2. Branch: `w2/customer-orders`. Reviewer: Supervisor.

**Base.** Branch from `main` (it has the customers, orders, invoices, settings and summary screens and both themes).

## Goal

Two things. (1) Connect customers and orders: the API already filters the order list by `customer_id`, but no screen uses it, so from a customer there is no way to see their orders. (2) Three layout nits found while reviewing the screens in a browser.

## Read first

`docs/SPEC.md` section 5 ("Orders API": the **List** rule, `customer_id` is an integer from 1 to 2147483647, a non-integer is 422 `INVALID_FORMAT`, any other value is 422 `OUT_OF_RANGE`), `docs/TESTABILITY.md`, `frontend/src/features/orders/` (`params.ts`, `api.ts`, `hooks.ts`), `frontend/src/app/(app)/orders/page.tsx`, `frontend/src/features/customers/` (the `useCustomer` hook), `frontend/src/app/(app)/customers/[id]/page.tsx`, `frontend/src/app/(app)/page.tsx`, `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/(app)/orders/[id]/page.tsx`.

## Scope

You may edit files only under `frontend/`: the orders list, its params, api and hooks and their tests; the customer detail page and its tests; the shell layout (only the navigation row classes) and the home page grid classes, with their tests; and the README. No new dependencies. Do not change any existing `data-testid`, any existing text or any existing behavior of the lists except what is described here.

## Requirements

1. **Orders list filter by customer.** The list URL accepts `customer_id` (`/orders?customer_id=4`): the parser reads a strict positive integer up to 2147483647 and ignores any other value (as it does for the other parameters); the list request adds `customer_id` only when the parameter is valid; the query key includes it; searching, filtering by status and paging keep it in the URL (and changing the search or the status still resets the page to 1). When it is set, a line under the page heading says "Pedidos de {customer name}" (the name through `useCustomer`; while it loads or when the customer is not found it says "Pedidos del cliente #{id}") with a "Quitar filtro" link that goes to the list without `customer_id` and keeps the other parameters. The empty and error states work as today.
2. **Customer detail.** A section "Pedidos" (an `h2`) with a link "Ver pedidos de este cliente" to `/orders?customer_id={id}`, visible to every role, for active and inactive customers alike.
3. **Test ids.** Orders list: `orders-list-customerfilter-text`, `orders-list-customerfilter-clear-link`. Customer detail: `customers-detail-orders-heading`, `customers-detail-orders-link`. All valid and unique; the static audit passes.
4. **Layout nits** (classes only, no new behavior, tokens only):
   - On a phone the shell navigation row has four links and scrolls sideways inside its own row, hiding "Configuración". Make the links wrap onto a second row instead of scrolling (keep the desktop rail as it is).
   - The five order counters of the home summary sit on a four column grid and leave "Cancelado" alone on a second row. Give the orders group a grid that holds five on a wide screen (`lg:grid-cols-5`) and keep the other groups as they are.
   - The "Facturar" button of the order detail touches the card above it. Give it the same vertical spacing as the other action rows of that page.
5. **Tests.** Mock `fetch` and `next/navigation`; no network. Cover: the parser (valid, zero, negative, decimal, letters, above the limit, repeated), the request (with and without the parameter, together with `q`, `status` and `page`), the URL kept when searching, filtering and paging, the filter line with a loaded name, while loading and with an unknown customer, the "Quitar filtro" link keeping the other parameters, the new section and link on the customer detail for an active and an inactive customer, and that the new ids are valid. Keep every existing test passing. The layout nits are class changes: assert them in the existing layout tests where those tests already assert classes, otherwise explain in the report what only a visual check can confirm.
6. **Docs.** Add a sentence to the orders and customers sections of `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
