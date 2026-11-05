# Task 020: frontend invoices and payments screens

Assignee: Worker 2. Branch: `w2/invoices-ui`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 016 (the orders screens) is merged. The backend is built in parallel (task 019): develop and test against a mocked `fetch` with the discipline of tasks 011 and 016, and make the mocked answers match the "Invoices and payments API" subsection of `docs/SPEC.md` literally.

## Goal

Build the screens of flow 3: the invoices list, the invoice detail with its payment history, the payment form with the three methods and every outcome of the fake gateway, and the "Facturar" action on the order detail. Follow `src/features/orders/` and `src/app/(app)/orders/` (data layer on TanStack Query with `retry: false`, numeric ids parsed once, URL as list state, `setQueryData` before navigating, 401 clearing the session entry, every mutating control disabled while one mutation is pending because they share one `version`, refetch after a failed mutation, focus on the form-level alert or the first field with an error on every failed submit, the design tokens and components of the Libro mayor theme, no literal colors) and the formatters of `src/lib/format.ts`. Read `docs/tasks/016-frontend-orders.md` and `docs/tasks/011-frontend-customers.md` first and copy their behaviors.

## Read first

`docs/SPEC.md` sections 2, 5 (Concurrency), 6 (all of it) and the **Invoices and payments API**, 7 and 8; `docs/SEED.md` (the invoices and payments as test data, the test cards); `docs/TESTABILITY.md`; `frontend/src/features/orders/`, `frontend/src/app/(app)/orders/`, `frontend/src/lib/` and `frontend/src/components/ui/`; `tools/audit/README.md`.

## Scope

You may create and edit files only under `frontend/`: `src/features/invoices/`, `src/app/(app)/invoices/`, the orders detail page and its tests for the "Facturar" action, small additions to `src/features/orders/` (add, never change behavior) and the README. No new dependencies. Do not touch `next.config.ts`. Do not change any existing `data-testid`.

## Requirements

### Data layer (`src/features/invoices/`)

1. `types.ts`: `InvoiceStatus` (`issued | paid | void`), `Invoice`, `InvoiceSummary`, `InvoiceLine`, `InvoiceCustomer`, `Payment`, `PaymentMethod`, `PaymentStatus`, `PaymentResult`, `PaymentProblem` (the problem document with `payment_id` and `reason`), exactly as in the spec (money as `string`, ids as `number`, nullable fields as `| null`); label helpers: invoice states "Emitida", "Pagada", "Anulada"; payment states "Aprobado", "Rechazado", "Fallido"; methods "Tarjeta", "Transferencia", "Efectivo"; the reasons "Tarjeta rechazada" (`CARD_DECLINED`) and "Pasarela no disponible" (`GATEWAY_UNAVAILABLE`).
2. `api.ts` and `hooks.ts`: `useInvoices({ page, q, status })` (key `["invoices","list",{page,q,status}]`, `URLSearchParams`, `page` always and the rest only when set), `useInvoice(id)` (key `["invoices","detail",id]`, numeric id), `useIssueInvoice()` (`POST /api/orders/{id}/invoice` with `If-Match: "<order version>"`; on success `setQueryData` the invoice detail, and invalidate `["orders","detail",orderId]`, `["orders","list"]` and `["invoices","list"]`) and `useRegisterPayment()` (`POST /api/invoices/{id}/payments` with `Idempotency-Key` and `If-Match: "<invoice version>"`; on **every** answer that carries a payment, a 201, a 402 or a 503, invalidate the invoice detail and the orders detail and lists; on a 201 `setQueryData` the invoice from `PaymentResult.invoice`). A 401 writes `null` into `["auth","me"]`. `permissions.ts`: `canManageInvoices(role)` true for `admin` and `finance` only.
3. **The idempotency key.** The payment form owns one key (`crypto.randomUUID()` in the shape `^[A-Za-z0-9._-]{1,64}$`). It keeps the same key after a network error (no answer arrived, so a retry is safe and replays or continues), and takes a **new** key after any HTTP answer (a retry after a decline or a failure is a new attempt, as the spec says) and whenever the user changes a field. Test each case, including that the header of the second request is the same or different accordingly.
4. `params.ts`: the strict id parser and the list URL parser (`?page=2&q=fac&status=paid`, invalid values fall back, a page above 1000000 becomes 1).

### Pages, all text in Spanish

5. **List** (`src/app/(app)/invoices/page.tsx`, replaces the placeholder; keep the heading "Facturas"): as the orders list, with the columns Número (a link to the detail), Pedido (a link to the order), Cliente, Estado (badge), Total (`formatMoney`, right aligned) and Creada, the ledger footer with "N facturas" ("1 factura") and the pagination, the search "Número o cliente", the status filter ("Todas", "Emitidas", "Pagadas", "Anuladas"), loading, empty ("No hay facturas que coincidan.") and error states. No "new invoice" button: invoices are issued from the order.
6. **Detail** (`[id]/page.tsx`): heading with the number; the state badge; the order as a link; the customer snapshot (name, ID fiscal, dirección, "—" for null) labelled "Cliente al emitir"; the lines table and the totals as in the order detail (with "Impuesto (10.00 %)"); the payments history table (Método, Estado, Monto, Detalle with the reference, "Tarjeta ···· 4242" or the reason, and the date and time; "Aún no hay pagos." when empty; a declined or failed attempt is shown with its badge and reason); the dates in UTC with the suffix; a back link. Loading, 404 and other errors, invalid id: as in orders.
7. **Payment form** on the detail, shown only when `canManageInvoices` and the invoice is `issued` (for a `paid` or `void` invoice the form is absent and the state says why). Fields: a select "Método" (Tarjeta, Transferencia, Efectivo; no placeholder), an input "Monto" prefilled with the invoice total (the string as it comes, `327.80`; editable so the mismatch error can be provoked), and, by method: for Tarjeta "Número de tarjeta", "Vencimiento (MM/AA)" and "CVC"; for Transferencia "Referencia"; for Efectivo nothing. The fields of the other methods are not rendered and their values are not sent. Client side only "Este campo es obligatorio." for an empty required field; every other rule is the server's (the card number is sent as typed, spaces and hyphens included). The submit "Pagar" shows "Pagando…" and the loading state, ignores a second submit, and disables every other mutating control while pending. Outcomes: **201** a success message (`role="status"`) "Pago aprobado." and the invoice and its history update without a reload, the form disappears because the invoice is `paid`; **402** the problem `detail` in the form-level alert (`role="alert"`) and the new attempt appears in the history after the refetch; **503** the same with its `detail`; **409** (`VERSION_CONFLICT`, `INVOICE_NOT_PAYABLE`) and **422** `PAYMENT_AMOUNT_MISMATCH` and `IDEMPOTENCY_KEY_REUSED` in the form-level alert, with a refetch of the invoice; a 422 with `errors[]` maps `method`, `amount`, `card.number` to the number field, `card.expiry`, `card.cvc` and `reference` to their fields; any other problem or a network error in the form-level alert. Focus goes to the alert or the first field with an error on every failed submit (a counter that every failure increments, as in the customers form). A card number is never written to the console, to storage or to the DOM outside its own input, and the input has `autocomplete="off"`. After a success the card fields are cleared.
8. **Order detail** (`src/app/(app)/orders/[id]/page.tsx`): for users who can manage invoices, an order that is `confirmed` and has no `invoice_id` shows a button "Facturar" (loading state, guarded against a second click, sends the order version); `ORDER_NOT_INVOICEABLE`, `CUSTOMER_TAX_ID_REQUIRED`, `INVOICE_ALREADY_EXISTS` and `VERSION_CONFLICT` show their `detail` in the existing order alert and refetch the order; on success `router.push` to the new invoice. An order with an `invoice_id` shows the link "Ver factura" (already in the orders brief).
9. Pages are client components; wrap `useSearchParams` in `Suspense`.

### Test ids (the `{id}` is the invoice id, `{line}` a line id, `{payment}` a payment id)

| Element | Test id |
|---|---|
| List: heading, search form, field, select, button | `invoices-list-heading`, `invoices-list-search-form`, `invoices-list-search-input`, `invoices-list-status-select`, `invoices-list-search-button` |
| List: loading, empty, error, retry | `invoices-list-loading-status`, `invoices-list-empty-status`, `invoices-list-error-alert`, `invoices-list-retry-button` |
| List: table, row, cells | `invoices-list-table`, `invoices-list-row-{id}`, `invoices-list-number-cell-{id}`, `invoices-list-order-cell-{id}`, `invoices-list-customer-cell-{id}`, `invoices-list-state-cell-{id}`, `invoices-list-total-cell-{id}`, `invoices-list-created-cell-{id}` |
| List: links | `invoices-list-view-link-{id}`, `invoices-list-order-link-{id}` |
| List: footer and pagination | `invoices-list-footer-item`, `invoices-list-prev-button`, `invoices-list-next-button`, `invoices-list-page-text`, `invoices-list-total-text` |
| Detail: heading, state, order link, customer, dates | `invoices-detail-heading`, `invoices-detail-state-status`, `invoices-detail-order-link`, `invoices-detail-customer-text`, `invoices-detail-taxid-text`, `invoices-detail-address-text`, `invoices-detail-created-text` |
| Detail: lines | `invoices-detail-lines-table`, `invoices-detail-line-row-{line}`, `invoices-detail-line-product-cell-{line}`, `invoices-detail-line-quantity-cell-{line}`, `invoices-detail-line-price-cell-{line}`, `invoices-detail-line-total-cell-{line}` |
| Detail: totals | `invoices-detail-subtotal-text`, `invoices-detail-taxrate-text`, `invoices-detail-tax-text`, `invoices-detail-total-text` |
| Detail: payments | `invoices-detail-payments-table`, `invoices-detail-payment-row-{payment}`, `invoices-detail-payment-method-cell-{payment}`, `invoices-detail-payment-state-cell-{payment}`, `invoices-detail-payment-amount-cell-{payment}`, `invoices-detail-payment-detail-cell-{payment}`, `invoices-detail-nopayments-text` |
| Detail: states | `invoices-detail-loading-status`, `invoices-detail-error-alert`, `invoices-detail-retry-button`, `invoices-detail-back-link`, `invoices-detail-closed-text` |
| Payment form | `payments-register-form`, `payments-register-method-select`, `payments-register-amount-input`, `payments-register-cardnumber-input`, `payments-register-cardexpiry-input`, `payments-register-cardcvc-input`, `payments-register-reference-input`, `payments-register-submit-button`, `payments-register-alert`, `payments-register-success-status` |
| Order detail | `orders-detail-invoice-button` |

Every id passes `isValidTestId` and is unique (a test checks the table with sample numbers); every element you add that the audit requires (`h2`, `h3`, forms, alerts, statuses) has an id from this table or one that follows the grammar.

### Tests and docs

10. **Tests.** Mock `fetch` and `next/navigation`; no network. Cover: the exact requests (paths, methods, `Idempotency-Key`, `If-Match`, JSON bodies per method with the other methods' fields absent, the list URL); `canManageInvoices`; the list (URL parsing, search, paging, empty and error states, the footer); the detail (every status with the right controls, the history with each payment status, "—" for null snapshot fields, the dates in UTC); the payment form for each method and each outcome (201, 402, 503, 409, the 422 shapes, a network error keeping the key, a new key after any answer and after a field change, double submit ignored, every other control disabled while pending, focus on every failed submit, the fields cleared after success, no card number anywhere but its input); "Facturar" (visibility per role and state, the errors, the redirect); a 401 clearing the session; and the table of ids.
11. **Docs.** An "Invoices and payments" section in `frontend/README.md`: the pages, the idempotency key rule and the permission rule.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 22 to 30 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question. You cannot see the result in a browser; say so and list what only a visual check can confirm.
