# Task 029: frontend products catalog screen

Assignee: Worker 2. Branch: `w2/products`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 028 is merged (the supervisor merges it first, or tells you to branch from `w2/error-pages`).

## Goal

The catalog of 15 products exists in the API (`GET /api/products`, every role, no paging) and in the order editor, but there is no screen for it. Stock is the number that changes when orders are confirmed or cancelled, so a read-only catalog is the natural place for a test to observe it. Build a "Productos" screen with the same discipline as the other list screens.

## Read first

`docs/SPEC.md` section 5 ("Orders API": the `Product` shape, `stock` is live, the catalog is ordered by `id`, no paging) and `docs/SEED.md` (the 15 products and their special cases: low stock and out of stock); `docs/TESTABILITY.md`; `frontend/src/features/orders/` (`useProducts`, the `Product` type, `fetchProducts`), `frontend/src/app/(app)/customers/page.tsx` and `frontend/src/app/(app)/orders/page.tsx` (list screens: table, footer, loading, empty and error states), `frontend/src/app/(app)/layout.tsx`, `frontend/src/lib/format.ts`, `frontend/src/lib/testid.ts`, `frontend/src/components/ui/`.

## Scope

You may create and edit files only under `frontend/`: `src/app/(app)/products/` (the page and its tests), `src/features/products/` (a thin module that re-exports or wraps the existing `useProducts` and `Product` of the orders feature; do not duplicate the fetch), the shell layout (one navigation link, between "Pedidos" and "Facturas", visible to every role) and its tests, and the README. No new dependencies. Do not change any existing `data-testid`, text or behavior.

## Requirements

1. **Page** (`/products`, client component, all text in Spanish): heading "Productos"; a table with the columns SKU, Producto, Precio (`formatMoney`, right aligned) and Stock (an integer, right aligned), ordered as the API returns (by `id`); a search field "Buscar por SKU o nombre" that filters **on the client** the rows already loaded (case and accent insensitive "contains" on SKU or name; no request) with a button "Buscar" and the same form behavior as the other lists (Enter submits; the search term is kept in the URL as `?q=`, parsed and trimmed like the other screens); the ledger footer "N productos" ("1 producto") that counts the **filtered** rows; states for loading, empty ("No hay productos que coincidan"), and error with a "Reintentar" button, as the other lists.
2. **Stock cue.** A stock of 0 shows the badge "Agotado" next to the number and a stock of 5 or less (and above 0) shows "Poco stock"; both with the existing badge styles and tokens, never color alone (the text is the cue). The thresholds are constants in one place, tested.
3. **Navigation.** A link "Productos" in the shell (rail and phone layout), same pattern as the others, with the current-section highlight.
4. **Test ids** (`{id}` is the product id): `products-list-heading`, `products-list-search-form`, `products-list-search-input`, `products-list-search-button`, `products-list-table`, `products-list-row-{id}`, `products-list-sku-cell-{id}`, `products-list-name-cell-{id}`, `products-list-price-cell-{id}`, `products-list-stock-cell-{id}`, `products-list-stockstate-status-{id}` (the badge, only when shown), `products-list-footer-item`, `products-list-loading-status`, `products-list-empty-status`, `products-list-error-alert`, `products-list-retry-button`, `app-nav-products-link`. All valid and unique; the static audit passes.
5. **Tests.** Mock `fetch` and `next/navigation`; no network. Cover: the request (`GET /api/products` once), every cell, the sort order, the money and integer format, the search (accents, case, no match, the URL parameter, Enter), the footer count with and without a filter, the stock thresholds at 0, 1, 5 and 6, each state, the navigation link for every role and the current-section highlight, and that the ids are valid and unique. Keep every existing test passing.
6. **Docs.** A "Products" section in `frontend/README.md`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
