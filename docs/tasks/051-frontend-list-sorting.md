# Task 051: sortable column headers on the four lists

Assignee: Worker 2. Branch: `w2/list-sorting-ui`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 050 (the backend sorting) is merged (the supervisor tells you).

## Goal

The API now sorts the lists (`sort` and `direction`, `docs/SPEC.md`, the **Sorting** sentences of the customers, orders and invoices list rules and the `GET /api/products` row). Make the column headers of the four tables clickable, the way a business application does, with the accessible markup that test automation can rely on: `aria-sort` on the header, a real `<button>` inside it, and an announcement of the new order.

## Read first

`docs/SPEC.md` (the sorting rules above), `docs/TESTABILITY.md` (the id grammar and the state attributes), `docs/TESTIDS.md` (the ids that exist), the four list pages `frontend/src/app/(app)/{customers,orders,invoices,products}/page.tsx` and their `features/*/params.ts` (the URL carries the list state: `?page=2&q=ana&status=active`), the API client of each feature and its types, `frontend/src/components/ui/TableScroll.tsx`, `frontend/src/lib/testid.ts`, the audit README (`tools/audit/README.md`) and `frontend/README.md`.

## Scope

You may edit under `frontend/` (the four list pages, their `features/*` params and API client, a new `src/components/ui/SortableHeader.tsx` with its test, the tests, the README), `tools/audit/states.json` (by text: add lines, keep the existing ones byte-identical), `docs/TESTIDS.md` (regenerated, not edited by hand), `tools/audit/README.md` (one sentence). No new dependency. Do not change an existing `data-testid` or text.

## Requirements

1. **The sortable columns** (the API fields in parentheses):
   - Customers: Nombre (`name`), Email (`email`) and a **new column** "Creado" (`created_at`, the date of creation formatted as the orders list formats its "Creado" column; reuse that formatter).
   - Orders: Número (`number`), Cliente (`customer`), Creado (`created_at`).
   - Invoices: Número (`number`), Cliente (`customer`), Total (`total`), Creada (`created_at`).
   - Products: SKU (`sku`), Producto (`name`), Precio (`price`), Stock (`stock`) (read the existing columns of the page and map them; if a column named like this does not exist, say so in the report).
   Every other column stays a plain header.
2. **A shared component** `SortableHeader` (in `src/components/ui/`, exported from `index.ts`) that renders a `<th scope="col">` with `aria-sort="ascending"` or `aria-sort="descending"` when it is the sorted column (no `aria-sort` attribute otherwise) and, inside it, a `<button type="button">` whose visible text is the column label (so the accessible name is the label) and a small arrow icon marked `aria-hidden="true"` that shows the direction of the sorted column (use inline SVG, like the other icons). The button carries `data-state="ascending" | "descending" | "none"` (the observable state of the contract) and its `data-testid` is required by the types like every other component. It needs a visible focus ring from the existing focus style, a target of at least 24 by 24 CSS pixels, and it must not break the table's reflow at 320 px (the audit checks it).
3. **The behavior.** Clicking the button of a column that is not the sorted one sorts by it with the default direction of that field (`created_at` descending, every other field ascending); clicking the sorted column flips the direction. There is no third "unsorted" state. Changing the sort goes back to page 1 and keeps the other filters (`q`, `status`, `customer_id`, `order_id`). The state lives in the URL: `?sort=name&direction=asc`; when the sort is the default (`created_at` descending) both parameters are left out of the URL, so the clean URL is the default list. Invalid values in the URL fall back to the default, as an invalid `status` does today (extend `parse*ListParams` and `listUrl`/the equivalent and their tests). The API calls carry the two parameters when they are not the default, and the query keys of TanStack Query include them.
4. **The ids.** `<module>-list-sort-<field>-button` with `<field>` in kebab case and `created_at` written `created`: `customers-list-sort-name-button`, `customers-list-sort-email-button`, `customers-list-sort-created-button`, `orders-list-sort-number-button`, `orders-list-sort-customer-button`, `orders-list-sort-created-button`, `invoices-list-sort-number-button`, `invoices-list-sort-customer-button`, `invoices-list-sort-total-button`, `invoices-list-sort-created-button`, `products-list-sort-sku-button`, `products-list-sort-name-button`, `products-list-sort-price-button`, `products-list-sort-stock-button`. The new customers "Creado" column header is the button above; do not add ids to the cells beyond what the other lists have.
5. **The announcement.** Each list has a visually hidden element with `role="status"` and the id `<module>-list-sort-text` (for example `customers-list-sort-text`) whose text is, for example, "Ordenado por Nombre, ascendente" (descendente for descending); it says "Ordenado por Creado, descendente" for the default; it updates when the sort changes. Read how the page already announces its results and follow that pattern if there is one.
6. **Tests** (Vitest and Testing Library, each page): the header of each sortable column has a button with the right id and text; the first click sorts ascending (descending for the created columns) and calls the router with the URL of the SPEC rule and the API with the parameters; the second click flips; `aria-sort` and `data-state` follow; the clean URL for the default; an invalid `sort` or `direction` in the URL falls back; the page returns to 1; the filters survive; the status text. The component has its own tests (keyboard activation by Enter and Space, the label in the accessible name, no `aria-sort` on an unsorted column).
7. **The audit.** Add four states to `tools/audit/states.json`: `customers-list-sorted` (`/customers?sort=name&direction=desc`), `orders-list-sorted` (`/orders?sort=customer&direction=asc`), `invoices-list-sorted` (`/invoices?sort=total&direction=desc`), `products-list-sorted` (`/products?sort=price&direction=desc`), each with the user, `waitFor` and `title` of its plain list state, `"catalog": false`; and one state that clicks a header: `customers-list-sort-click`, copy of `customers-list` with `"steps": [{ "click": "customers-list-sort-name-button", "waitFor": "customers-list-sort-text" }]`. Run the browser audit in both themes (`tools/audit/README.md`, in-memory API with `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`): all states pass, including the existing ones and the 320 px states. Regenerate `docs/TESTIDS.md` against a clean seed as `tools/audit/README.md` says (the new ids appear) and commit it.
8. **Check it against the real API**, not only the mocks: with the dev servers running, sort each list by each field in both directions through the UI (or a small script that calls the pages' API client) and confirm the rows come back in the order the SPEC defines. Put in the report one example per list (the first three values of the sorted column).
9. **README.** `frontend/README.md`: a short "Sorting" paragraph (the URL parameters, the ids, `aria-sort`).

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage` (the coverage floor holds), `pnpm build` pass. From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs`, `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs` and the browser audit in both themes (0 failures; the light run with `--catalog docs/TESTIDS.md` shows the catalog unchanged after you regenerated it).

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits: the component, then each page, then the audit states, the catalog and the README). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the four examples of requirement 8, and any deviation or open question.
