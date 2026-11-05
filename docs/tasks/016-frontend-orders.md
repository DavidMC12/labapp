# Task 016: frontend orders screens

Assignee: Worker 2. Branch: `w2/orders-ui`. Reviewer: Supervisor.

**Base.** Branch from `main` once task 013 (the "Libro mayor" theme) is merged, so the design tokens and the `Button`, `Link`, field and alert styles exist and are used by everything you build. The backend is built in parallel (task 015): develop and test with a mocked `fetch`, with the discipline of task 011: a mocked test must not pass where the real API would fail.

## Goal

Build the orders screens of flow 2 (list, create, detail with line editing and the confirm, cancel and ship transitions) against the "Orders API" subsection of `docs/SPEC.md`. Follow the layering of `src/features/customers/` and the behaviors of `docs/tasks/011-frontend-customers.md` (data layer on TanStack Query with `retry: false`, numeric ids parsed once with the strict pattern, URL as list state with fallbacks, `setQueryData` before navigating, a 401 clearing the session cache entry, guards against double submit, refetch after a failed mutation so the next click sends a fresh `version`, focus moving to the form-level alert or the first field with an error on every failed submit). Where this brief says "as in customers", copy that behavior.

## Read first

`docs/SPEC.md` sections 2, 5 (all of it, with "Orders API" and "Concurrency"), 7 and 8 (money and date formats); `docs/SEED.md` (products and orders as test data); `docs/TESTABILITY.md`; `docs/tasks/011-frontend-customers.md`; `frontend/src/features/customers/` and `frontend/src/app/(app)/customers/` (the pattern), `frontend/src/lib/api.ts`, `frontend/src/lib/testid.ts` and `frontend/src/components/ui/`.

## Scope

You may create and edit files only under `frontend/`: `src/features/orders/`, `src/app/(app)/orders/`, `src/lib/format.ts` (and its test), small additions to `src/features/customers/` only if a hook there must be reused (add, never change behavior) and the README. No new dependencies. Do not add an `/api` rewrite to `next.config.ts`. Do not change any existing `data-testid`.

## Requirements

### Shared formatting (`src/lib/format.ts`)

1. `formatMoney(value: string)` returns the amount as `$1,234.50` using `Intl.NumberFormat("es-US", { style: "currency", currency: "USD" })` (the value arrives as a string with 2 decimals; do not convert through a float for display more than the formatter needs). `formatDate(iso: string)` returns `31/10/2026` and `formatTime(iso)` returns `02:30`, both in UTC, produced with `Intl.DateTimeFormat("es-US", ...)` and the `2-digit` options of SPEC section 8; `formatDateTime(iso)` returns `31/10/2026 02:30 UTC`. Tests with fixed timestamps (including a date with a one-digit day and month, which must be zero-padded, and a time close to midnight UTC).

### Data layer (`src/features/orders/`)

2. `types.ts`: `OrderStatus` (`draft | confirmed | paid | shipped | cancelled`), `Product`, `OrderLine`, `OrderCustomer`, `Order`, `OrderSummary`, `OrderList`, `Shortage`, exactly as in the spec (money as `string`, ids as `number`, `invoice_id: number | null`), `orderStatusLabel(status)` returning the Spanish labels "Borrador", "Confirmado", "Pagado", "Enviado", "Cancelado".
3. `api.ts` and `hooks.ts`: `useOrders({ page, q, status })` (key `["orders","list",{page,q,status}]`; the request is built with `URLSearchParams`: `page` always, `q` and `status` only when set), `useOrder(id)` (key `["orders","detail",id]`, `id` a number), `useProducts()` (key `["products"]`, `GET /api/products`), `useCreateOrder()`, `useSetOrderCustomer()`, `useAddLine()`, `useSetLineQuantity()`, `useRemoveLine()` and `useOrderTransition()` (`confirm`, `cancel` or `ship`, with `If-Match: "<version>"`). Every body that carries `version` sends the version of the order on screen at click time. Every successful mutation writes the returned order with `setQueryData` on its detail key and invalidates `["orders","list"]`; confirm and cancel also invalidate `["products"]` (stock changed). A 401 on any call writes `null` into `["auth","me"]`. Line deletion is `DELETE` with the `If-Match` header and answers the new order. `permissions.ts`: `canEditOrders(role)` and `canTransitionOrders(role)`, both true for `admin` and `sales`.
4. `params.ts`: the strict id parser (`^[1-9][0-9]*$`, at most 2147483647) and the list URL parser (`?page=2&q=ped&status=confirmed`; an invalid `page`, including above 1000000, becomes 1; an invalid `status` becomes no status).

### Pages (under `src/app/(app)/orders/`), all text in Spanish

5. **List** (`page.tsx`, replaces the placeholder; keep the heading "Pedidos"). State in the URL as in customers, with the page clamped to the last one. Search form: field "Buscar" (placeholder "Número o cliente"), select "Estado" ("Todos" plus the five labels), button "Buscar". Table columns Número (a link to the detail), Cliente, Estado, Líneas, Total (right aligned, `formatMoney`) and Creado (`formatDate`). Below: "Anterior", "Siguiente", "Página X de Y" and the total as "N pedidos" ("1 pedido"). "Nuevo pedido" (a link to `/orders/new`) only when `canEditOrders`. Loading, empty ("No hay pedidos que coincidan.") and error states as in customers.
6. **Create** (`new/page.tsx`): heading "Nuevo pedido". A small search form (field "Buscar cliente", button "Buscar") and the form with a select "Cliente" listing the active customers returned by `useCustomers({ page: 1, q, status: "active" })` (at most 20; say so in a hint under the select: "Se muestran hasta 20 clientes activos; usa la búsqueda para encontrar otro."). The select starts with a disabled placeholder option "Elige un cliente"; when a new search changes the options and the chosen customer is no longer among them, the choice returns to the placeholder (the state never holds an id that the select does not show). While the customers load the select shows the status "Buscando clientes…" (`orders-form-customer-loading-status`), when none match it shows "No hay clientes activos que coincidan." (`orders-form-customer-empty-status`), and a failure shows the `detail` in `orders-form-error-alert` with `orders-form-retry-button`. The customer search is its own form (not nested in the creation form). The submit button "Crear pedido" is disabled until a customer is chosen; on success `router.replace` to the detail page of the new order. Errors as in the customers form (a 422 on `customer_id` shows on the select; `CUSTOMER_INACTIVE` shows its `detail` on the select; any other problem in the form-level alert with focus on it). Users who cannot edit orders see only the alert "No tienes permiso para realizar esta acción.".
7. **Detail** (`[id]/page.tsx`). Heading with the order number; the status label; the customer name as a link to `/customers/{id}` (with "(inactivo)" after it when the customer is inactive); the dates ("Creado" and "Actualizado", `formatDateTime`); when `invoice_id` is not null a link "Ver factura" to `/invoices/{invoice_id}`.
   - **Lines table** with Producto (name and SKU), Cantidad, Precio unitario, Subtotal. In a `draft`, for users who can edit: the quantity cell holds a number input with "Guardar" and "Quitar" buttons per row; otherwise it is plain text. A quantity (here and in the add form) is turned into the request as follows: empty means "Este campo es obligatorio." on that field with no request; text that fully matches `^[0-9]+$` is sent as a number; anything else (a decimal, a sign, letters) is sent as the typed string, so the server's `INVALID_FORMAT` message shows on the field. Do not add other client-side checks. An order with no lines shows "Este pedido aún no tiene líneas.".
   - **Totals:** Subtotal, "Impuesto (10.00 %)" using the order's `tax_rate`, and Total, all with `formatMoney`. A draft shows the note "Vista previa: la tasa se fija al confirmar.".
   - **Add a line** (draft, can edit): a select "Producto" (from `useProducts`, starting with a disabled placeholder "Elige un producto", option text `Name (SKU) — $price — stock N`, products already in the order disabled; while the products load the only option is "Cargando productos…", and a failure shows its `detail` in `orders-detail-products-error-alert` with `orders-detail-products-retry-button`), a number input "Cantidad" (default 1) and the button "Agregar". A 422 maps `product_id` and `quantity` to their fields; `ORDER_DUPLICATE_PRODUCT` and `ORDER_TOO_MANY_LINES` show their `detail` in the form-level alert.
   - **Change the customer** (draft, can edit): a button "Cambiar cliente" (`aria-expanded`, `aria-controls` pointing at the section, not a `<details>`) that shows or hides a section with the same customer search (its own form, never nested in the change form) and select as the create page, with the same loading, empty and error states (`orders-detail-changecustomer-loading-status`, `-empty-status`, `-error-alert`), and the button "Cambiar".
   - **Transitions** (users who can transition): "Confirmar" (draft), "Cancelar pedido" (draft or confirmed) and "Marcar como enviado" (paid), each with loading state and a guard against a second click. `INSUFFICIENT_STOCK` shows its `detail` in the alert and, under it, a list of the short products from `shortages` ("Teclado USB (KB-100): disponible 3, solicitado 5"). `ORDER_EMPTY`, `CUSTOMER_INACTIVE`, `INVALID_TRANSITION`, `ORDER_NOT_EDITABLE` and `VERSION_CONFLICT` show their `detail` in the alert. After any failed mutation, and always after a `VERSION_CONFLICT`, refetch the order so the next click sends a fresh version. While **any** mutation of the order is pending (a line change, an addition, a removal, the customer change or a transition), every control of the page that sends a mutation is disabled, not only the clicked one: all the mutations of one order share one `version`, so a second request sent before the first returns would carry a stale version and fail with a `VERSION_CONFLICT` of the user's own making.
   - Loading, 404 (the `detail` and the back link without "Reintentar"), other errors with "Reintentar", and an invalid id behave as in customers. A link "Volver a pedidos".
8. Pages are client components; wrap `useSearchParams` in `Suspense`.

### Test ids

9. Use exactly these (`{id}` is the order id and `{line}` the line id, `{product}` the product id; every id must pass `isValidTestId`; the error ids of fields are derived by the field components):

| Element | Test id |
|---|---|
| List: heading, new link | `orders-list-heading`, `orders-list-new-link` |
| List: search form, field, select, button | `orders-list-search-form`, `orders-list-search-input`, `orders-list-status-select`, `orders-list-search-button` |
| List: loading, empty, error, retry | `orders-list-loading-status`, `orders-list-empty-status`, `orders-list-error-alert`, `orders-list-retry-button` |
| List: table, row, cells | `orders-list-table`, `orders-list-row-{id}`, `orders-list-number-cell-{id}`, `orders-list-customer-cell-{id}`, `orders-list-state-cell-{id}`, `orders-list-lines-cell-{id}`, `orders-list-total-cell-{id}`, `orders-list-created-cell-{id}` |
| List: link in the number cell | `orders-list-view-link-{id}` |
| List: pagination | `orders-list-prev-button`, `orders-list-next-button`, `orders-list-page-text`, `orders-list-total-text` |
| Create: heading, form, customer search form, field, button | `orders-form-heading`, `orders-customer-form`, `orders-form-customersearch-form`, `orders-form-customersearch-input`, `orders-form-customersearch-button` |
| Create: select, hint, picker states, submit, cancel | `orders-form-customer-select`, `orders-form-customer-text`, `orders-form-customer-loading-status`, `orders-form-customer-empty-status`, `orders-form-submit-button`, `orders-form-cancel-link` |
| Create: alert, loading, forbidden, load error, retry | `orders-form-alert`, `orders-form-loading-status`, `orders-form-forbidden-alert`, `orders-form-error-alert`, `orders-form-retry-button` |
| Detail: heading, state, customer link, dates, invoice link | `orders-detail-heading`, `orders-detail-state-status`, `orders-detail-customer-link`, `orders-detail-created-text`, `orders-detail-updated-text`, `orders-detail-invoice-link` |
| Detail: lines table, row, cells | `orders-detail-lines-table`, `orders-detail-line-row-{line}`, `orders-detail-line-product-cell-{line}`, `orders-detail-line-quantity-cell-{line}`, `orders-detail-line-price-cell-{line}`, `orders-detail-line-total-cell-{line}`, `orders-detail-nolines-text` |
| Detail: line editing | `orders-detail-line-quantity-input-{line}`, `orders-detail-line-save-button-{line}`, `orders-detail-line-remove-button-{line}` |
| Detail: totals | `orders-detail-subtotal-text`, `orders-detail-taxrate-text`, `orders-detail-tax-text`, `orders-detail-total-text`, `orders-detail-preview-text` |
| Detail: add a line | `orders-detail-addline-form`, `orders-detail-addline-product-select`, `orders-detail-addline-quantity-input`, `orders-detail-addline-submit-button`, `orders-detail-products-error-alert`, `orders-detail-products-retry-button` |
| Detail: change the customer | `orders-detail-changecustomer-button`, `orders-detail-changecustomer-search-form`, `orders-detail-changecustomer-search-input`, `orders-detail-changecustomer-search-button`, `orders-detail-changecustomer-form`, `orders-detail-changecustomer-select`, `orders-detail-changecustomer-submit-button`, `orders-detail-changecustomer-loading-status`, `orders-detail-changecustomer-empty-status`, `orders-detail-changecustomer-error-alert` |
| Detail: transitions | `orders-detail-confirm-button`, `orders-detail-cancel-button`, `orders-detail-ship-button` |
| Detail: alert, shortages | `orders-detail-alert`, `orders-detail-shortages-list`, `orders-detail-shortage-item-{product}` |
| Detail: loading, load error, retry, back | `orders-detail-loading-status`, `orders-detail-error-alert`, `orders-detail-retry-button`, `orders-detail-back-link` |

### Tests and docs

10. **Tests.** Mock `fetch` and `next/navigation`; no network; `QueryClient` with `retry: false`. Cover: the exact requests (paths, methods, `If-Match`, JSON bodies, the list URL built with `URLSearchParams`, `q=R&D` encoded); `canEditOrders` and `canTransitionOrders`; the list (URL parsing with invalid values, search submit, pagination arithmetic and disabled buttons, the page beyond the last replaced, empty and error states, hiding "Nuevo pedido" per role); the create page (disabled submit, the customer search, the 422 and `CUSTOMER_INACTIVE` mappings, focus on every failed submit, the redirect, the forbidden message); the detail (every state of the order with the right controls for each role: draft shows line editing, add form, confirm and cancel; confirmed shows cancel only; paid shows ship only; shipped and cancelled show none; read-only and finance see none), adding, changing and removing a line with the version at click time, the totals formatting, `INSUFFICIENT_STOCK` with the shortages list, a failed mutation refetching the order, a stale version recovering after the refetch, every mutating control disabled while one mutation is pending (a second click on a different control sends nothing), the quantity parsing (empty, `5`, `5.5`, `-1`, letters), the customer pickers (placeholder, selection reset when the options change, loading, empty and error states, the toggle's `aria-expanded`), the products states, the numeric id in the keys (the detail updates without a reload), a 401 clearing the session, 404 and invalid id; and a test that every id of the table passes `isValidTestId` (derive the `{...}` ones with sample numbers).
11. **Docs.** An "Orders" section in `frontend/README.md`: the pages, the list parameters and the permission rule.

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

- Commit as you go, in small real steps (about 20 to 28 commits): the formatters, the types, each hook, each page, each group of tests, the README. Conventional Commits, in English, for example `feat(frontend): add the orders list page`.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question. You cannot see the result in a browser; say so.
