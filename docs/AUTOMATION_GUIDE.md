# Automation guide

LabApp is a small order-to-cash ERP (customers, orders, invoices, payments) built to be automated: it is the application a QA engineer drives with Playwright when learning the suite. This is **part 1: the web UI** — how to start it, how to locate everything, what the screens contain, and how the three core flows behave. Part 2 (the test controls — reset, seed, clock, faults — and the HTTP API contract) follows after those parts exist.

Every id, URL, label and message here was read from the code and the documents ([TESTABILITY](TESTABILITY.md), [TESTIDS](TESTIDS.md), [SEED](SEED.md), [SPEC section 2–6 and 8](SPEC.md)). The generated catalog [TESTIDS.md](TESTIDS.md) is the source for ids; this guide links it instead of copying it.

## 1. Start in five minutes

```bash
mise install    # once: Node, pnpm and uv at the pinned versions
mise run dev    # API on 127.0.0.1:8000, web on http://localhost:3000
```

The script ([docs/DEVELOPMENT.md](DEVELOPMENT.md)) installs dependencies if needed and starts both processes. For UI tests point Playwright at **`http://localhost:3000`**: the web dev server forwards `/api/*` and `/__test__/*` to the API, so the browser sees one origin, as it does online. By default the data lives in memory: it is the seed below, and it is lost when the processes restart.

Log in at `/login` with one of the four seeded users. The login screen lists them with the shared password (demo list `auth-login-demo-list`, items `auth-login-demo-item-1` to `auth-login-demo-item-4`, password line `auth-login-demo-password-text`).

| Email | Role |
|---|---|
| `admin@labapp.test` | Admin |
| `sales@labapp.test` | Sales |
| `finance@labapp.test` | Finance |
| `readonly@labapp.test` | Read-only |

Password for all four: `Demo-LabApp-2026!`. What each role can do ([SPEC section 2](SPEC.md); the server enforces every rule, the UI only hides controls):

| Action | Admin | Sales | Finance | Read-only |
|---|---|---|---|---|
| View customers, products, orders, invoices, payments | yes | yes | yes | yes |
| Create, edit, deactivate and reactivate customers | yes | yes | no | no |
| Create and edit Draft orders; confirm, cancel, ship | yes | yes | no | no |
| Create invoices and register payments | yes | no | yes | no |
| Change the tax rate | yes | no | no | no |

**Online demo vs local.** There is no deployed demo yet (see [docs/DEPLOYMENT.md](DEPLOYMENT.md) — configured, not deployed); when it exists it lives on the project's Vercel URL. Tell them apart by the hostname, `localhost:3000` versus the `https://` deployment URL, and by the data:

- **Local:** in-memory data, restored from the seed on every start; `TEST_MODE=1`, so the request rate limits are off.
- **Online:** one shared dataset (strangers may move it between your runs), rate limits active — 120 requests per minute and 10 login attempts per minute per client IP; exceeding one answers HTTP 429 with code `RATE_LIMITED` and the message `Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.` ([SPEC section 3](SPEC.md)). A nightly reset workflow at 03:17 UTC restores the seed, but it only works once the test controls are deployed (task 022, part 2 of this guide).

## 2. Locators

Every screen stakes its locators up front, in [docs/TESTABILITY.md](TESTABILITY.md).

**The grammar in three sentences.** An id is `<module>-<name>-<kind>` in kebab-case, where `module` is one of `app`, `auth`, `home`, `customers`, `orders`, `products`, `invoices`, `payments`, `settings`, and `kind` is one of `button`, `input`, `select`, `textarea`, `checkbox`, `radio`, `switch`, `link`, `tab`, `menuitem`, `form`, `table`, `row`, `cell`, `list`, `item`, `dialog`, `alert`, `error`, `status`, `text`, `heading`, `region`. The `name` is one or more kebab-case words describing the element (`form-email`, `list`, `cancel-confirm`). A numeric id can appear only as the **final** segment: a record id appended after the kind (`customers-list-row-42`); `customers-list-row-42-view-button` and `orders-line-7-quantity-input` are invalid — write `orders-line-quantity-input-7`.

**Why `data-testid` and not `data-test`.** `data-testid` is the attribute Playwright looks for by default, so it needs no selector magic; LabApp emits it on every interactive element, every field error, every heading and every value a test would assert on. Pin it explicitly anyway in your own config so the suite does not depend on the default:

```ts
// playwright.config.ts
export default defineConfig({ use: { testIdAttribute: 'data-testid' } });
```

**Finding an id.** The generated catalog [docs/TESTIDS.md](TESTIDS.md) lists every id of every audited state with its element — grep it, link it, do not copy from the code by hand. The browser audit regenerates it (`node tools/audit/browser-audit.mjs --catalog docs/TESTIDS.md`) and CI fails when the committed copy is stale. An id that only appears after an interaction (a field error after a failed submit, a success message) is not in the catalog until an audited state reaches it; grep the source (`data-testid` in `frontend/src`) for those.

**What a trailing number means.** Two cases, per the catalog's own notes: a **record id** — `customers-list-row-4` is the row of customer 4, `orders-detail-line-quantity-input-10` the quantity editor of order line 10 — or a **position in a list** — `auth-login-demo-item-2` is the second entry of the login demo box. The record-id case dominates; the login demo box is a position.

**The four special kinds.**

| Kind | What it marks | Example |
|---|---|---|
| `region` | The scrollable wrapper of a wide table ([TableScroll](../frontend/src/components/ui/TableScroll.tsx), keyboard-focusable) | `customers-list-scroll-region` |
| `status` | An element with `role="status"`: loading announcements (`Cargando…`, busy) and success announcements | `customers-list-loading-status`, `settings-taxrate-success-status` |
| `alert` / `error` | Messages from the API. `error` is a field-level message next to its input (`customers-form-email-error`); `alert` is a form- or page-level one (`customers-form-alert`, `customers-detail-error-alert`) | both in `role="alert"` |
| `dialog` | A confirmation on the native `<dialog>`. There are exactly two in the app: cancelling an order and deactivating a customer; every other action runs at the first click | `orders-cancel-confirm-dialog`, `customers-deactivate-confirm-dialog` |

## 3. Screen map

One row per screen. "Who" is who gets the screen's main function; every logged-in role can open the routes of the shell — reading is open to all roles — but the write controls disappear for the roles without the permission ([SPEC section 2](SPEC.md)). Titles and ids read from the code and [states.json](../tools/audit/states.json).

| Screen | URL | Who | Document title | Main heading id | Main table or form id |
|---|---|---|---|---|---|
| Login | `/login` | no session | `Iniciar sesión · LabApp` | `auth-login-heading` | `auth-login-form` |
| Expired-session notice | `/login?expired=1` | no session | `Iniciar sesión · LabApp` | `auth-login-heading` | `auth-login-form` (alert `auth-login-expired-alert`) |
| Summary (home) | `/` | all roles | `Resumen · LabApp` | `app-home-heading` | — (counter cards, no table) |
| Customers list | `/customers` | view: all; write: Admin, Sales | `Clientes · LabApp` | `customers-list-heading` | `customers-list-table` |
| Customer detail | `/customers/{id}` | view: all; deactivate/reactivate: Admin, Sales | `Cliente {name} · LabApp` | `customers-detail-heading` | — (definition card) |
| Customer new | `/customers/new` | Admin, Sales (others get the permission alert) | `Nuevo cliente · LabApp` | `customers-form-heading` | `customers-customer-form` |
| Customer edit | `/customers/{id}/edit` | Admin, Sales (others get the permission alert) | `Editar cliente · LabApp` | `customers-form-heading` | `customers-customer-form` |
| Orders list | `/orders` | view: all; create: Admin, Sales | `Pedidos · LabApp` | `orders-list-heading` | `orders-list-table` |
| Order new | `/orders/new` | Admin, Sales (others get the permission alert) | `Nuevo pedido · LabApp` | `orders-form-heading` | `orders-customer-form` |
| Order detail | `/orders/{id}` | view: all; transitions: Admin, Sales; invoice: Admin, Finance | `Pedido {number} · LabApp` | `orders-detail-heading` | `orders-detail-lines-table` |
| Invoices list | `/invoices` | view: all (no create button here) | `Facturas · LabApp` | `invoices-list-heading` | `invoices-list-table` |
| Invoice detail | `/invoices/{id}` | view: all; pay: Admin, Finance, only while issued | `Factura {number} · LabApp` | `invoices-detail-heading` | `invoices-detail-lines-table` (issued: payment form `payments-register-form`) |
| Products list | `/products` | all roles, read-only | `Productos · LabApp` | `products-list-heading` | `products-list-table` |
| Settings | `/settings` | view: all; tax rate form: Admin only | `Configuración · LabApp` | `settings-page-heading` | `settings-taxrate-form` (Admin) |
| Not found (404) | any unmatched route | no session needed | `Página no encontrada · LabApp` | `app-notfound-heading` | — |

Notes a test can rely on:

- Detail titles carry the record only after it loads: until then the tab shows the section title (`Clientes`, `Pedidos`, `Facturas`), per the `useDocumentTitle` hook of the frontend. The state list of `states.json` asserts the loaded title (for example `Pedido PED-0003 · LabApp`).
- `app-nav-home-link` is the brand "LabApp" in the rail; the section links are `app-nav-customers-link`, `app-nav-orders-link`, `app-nav-products-link`, `app-nav-invoices-link`, `app-nav-settings-link` — visible to every role.
- Every shell page shares the skip link (`app-skip-link`) and the logout button (`app-logout-button`); "Salir" goes to `/login`.
- Unknown customer, order or invoice ids render their section's error alert (for example `customers-detail-error-alert` with `No se encontró el recurso solicitado.`) and keep the section title, not a 404 page ([states.json](../tools/audit/states.json) `customers-not-found`).

## 4. Seed data cheat sheet

The exact data ([docs/SEED.md](SEED.md)) is a contract. "I want to test X, use Y":

| I want to test… | Use | Facts |
|---|---|---|
| A customer that cannot be invoiced | Customer 3, `Cafetería La Esquina` (`cafe@example.test`) | Active but no tax ID; order `PED-0007` is confirmed and issuing its invoice fails with `CUSTOMER_TAX_ID_REQUIRED` |
| Inactive customers | Customer 5 `Estudio Épsilon`, customer 8 `Hotel Horizonte` (also without tax ID) | Deactivated: no new orders ([detail state](../tools/audit/states.json) `/customers/5`) |
| An active customer with a very long name | Customer 7 `Grupo Gamma Servicios Profesionales y Consultoría Internacional de Latinoamérica Sociedad por Acciones Simplificada` | 115 of the 120 allowed characters |
| A draft order | `PED-0001` (order id 1), customer 1, line `KB-100` x 2, total `$43.78` | Drafts reserve no stock |
| A confirmed order with no invoice | `PED-0002` (id 2), customer 2, total `$121.00` | Ready to invoice as Finance |
| An invoice already issued, with failed payment attempts | `PED-0003` (id 3) → invoice `FAC-0001` (id 1), customer 4, total `$327.80` | Payment history: card ···· 0002 declined, card ···· 0003 gateway unavailable |
| A paid order (then ship it) | `PED-0004` (id 4), customer 6, total `$197.97` → invoice `FAC-0002` (id 2), paid by transfer (`TRF-2026-0001`) | Shipping is the only transition left |
| A paid invoice paid in cash | `PED-0005` (id 5) → invoice `FAC-0003` (id 3), customer 9, `$768.90` | Shipped; the history shows the cash approval |
| A cancelled order | `PED-0006` (id 6), customer 10 | Cancelled draft; its stock never left: `SW-8P` shows stock 25 |
| A low-stock product | Product 7, `Cámara web HD` (`WC-720`), stock 3, `$34.50` | The Stock cell shows the badge `Poco stock` (stock 1–5) |
| An out-of-stock product | Product 9, `Impresora láser` (`PR-400`), stock 0, `$189.90` | Badge `Agotado` |
| A declined card | `4000 0000 0000 0002` | Ends in 0002 → HTTP 402 `PAYMENT_DECLINED` |
| The gateway unavailable by card | `4000 0000 0009 0003` | Ends in 0003 → HTTP 503 `PAYMENT_GATEWAY_UNAVAILABLE` |
| A card that always approves | `4242 4242 4242 4242` | Any valid expiry not in the past, any 3-digit CVC |

All three test cards pass the Luhn check, so the gateway outcome alone decides ([SPEC section 6](SPEC.md)). Tax rate in the seed: 10.00 %; the totals above assume it. User password: `Demo-LabApp-2026!`. After a fresh start the next numbers are order `PED-0008`, invoice `FAC-0004`, payment id 5.

## 5. The core flows, step by step

The UI is in Spanish; the steps cite the ids you click and read. Error messages are quoted exactly as the code writes them. The Playwright sketches are **illustrative, not run in CI**, and use only ids of the catalog.

### Flow 1 — create a customer (Admin or Sales)

| Step | Id | Expected result |
|---|---|---|
| Log in | `auth-login-email-input`, `auth-login-password-input`, `auth-login-submit-button` | Redirect to `/`, the `Resumen` heading `app-home-heading` |
| Open the module | `app-nav-customers-link` | `/customers`, heading `customers-list-heading`, table `customers-list-table` |
| Start the form | `customers-list-new-link` | `/customers/new`, heading `customers-form-heading`, form `customers-customer-form` |
| Fill and save | `customers-form-name-input`, `customers-form-email-input`, `customers-form-phone-input`, `customers-form-taxid-input`, `customers-form-address-textarea`, then `customers-form-submit-button` ("Guardar") | Redirect to `/customers/{id}`; the detail heading is the new name (`customers-detail-heading`), the state badge `customers-detail-state-status` reads `Activo` |

Errors a test can provoke, and where they appear:

- Empty name or email (the email is trimmed first): the field error `Este campo es obligatorio.`, in the `<p role="alert">` under the input; focus moves to the first field with an error.
- Email already used (409 `CUSTOMER_EMAIL_TAKEN`): the error `Ya existe un cliente con ese email.` on the email field.
- Server field rules (422 `VALIDATION_ERROR`): the answer's `message` under each field, for example `Debe tener al menos 2 caracteres.` on a one-letter name.

```ts
// Illustrative, not run in CI.
const name = "Prueba Uno";
await page.getByTestId("customers-list-new-link").click();
await page.getByTestId("customers-form-name-input").fill(name);
await page.getByTestId("customers-form-email-input").fill("prueba@example.test");
await page.getByTestId("customers-form-submit-button").click();
await expect(page.getByTestId("customers-detail-heading")).toHaveText(name);
await expect(page.getByTestId("customers-detail-state-status")).toHaveText("Activo");
```

### Flow 2 — build, confirm and cancel an order (Admin or Sales)

| Step | Id | Expected result |
|---|---|---|
| Start a draft | `orders-list-new-link` | `/orders/new`; the picker `orders-form-customer-select` lists up to 20 active customers ("Elige un cliente" placeholder); search it with `orders-form-customersearch-input` + `orders-form-customersearch-button` |
| Create the draft | `orders-form-submit-button` ("Crear pedido") | Redirect to `/orders/{id}`; the badge `orders-detail-state-status` reads `Borrador`; the totals (`orders-detail-subtotal-text`, `orders-detail-tax-text`, `orders-detail-total-text`) read `$0.00`; the note `orders-detail-preview-text` says `Vista previa: la tasa se fija al confirmar.` |
| Add a line | `orders-detail-addline-product-select` (option text `Teclado USB (KB-100) — $19.90 — stock 120`; products already in the order are disabled), `orders-detail-addline-quantity-input` (a number input, default 1), `orders-detail-addline-submit-button` ("Agregar") | A row in `orders-detail-lines-table` (row `orders-detail-line-row-{line_id}`) and recomputed totals |
| Confirm | `orders-detail-confirm-button` ("Confirmar") | The badge changes to `Confirmado`; stock is decremented and the totals freeze |
| Cancel | `orders-detail-cancel-button` ("Cancelar pedido") → dialog `orders-cancel-confirm-dialog` ("¿Cancelar el pedido {number}?") → `orders-cancel-confirm-button` ("Sí, cancelar pedido") | The badge changes to `Cancelado`; cancelling a draft frees nothing, cancelling a confirmed order returns the stock |

Errors a test can provoke:

- Confirm a draft without lines: the page alert gets `El pedido debe tener al menos una línea.`
- Quantity out of range (1–999): the field error `El valor debe estar entre 1 y 999.` under the quantity input (`addline` or the per-line editor `orders-detail-line-quantity-input-{line_id}`; empty reads `Este campo es obligatorio.` without a request).
- Not enough stock on confirm (409 `INSUFFICIENT_STOCK`): the page alert gets `No hay stock suficiente de {product}: disponible {available}, solicitado {requested}.` and the list `orders-detail-shortages-list` shows one line per short product, `{name} ({sku}): disponible {available}, solicitado {requested}`.
- The customer was deactivated after the draft was made: confirming fails with `El cliente está desactivado y no puede recibir pedidos.`
- A failed mutation refetches the order, so the next click sends a fresh version; a genuinely stale version answers 409 with `El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.` in the same alert.

```ts
// Illustrative, not run in CI.
await page.getByTestId("orders-list-new-link").click();
await page.getByTestId("orders-form-customer-select").selectOption({ label: "Acme Industrial S.A." });
await page.getByTestId("orders-form-submit-button").click();
await expect(page.getByTestId("orders-detail-state-status")).toHaveText("Borrador");
await page.getByTestId("orders-detail-addline-product-select").selectOption({ label: "Teclado USB (KB-100) — $19.90 — stock 120" });
await page.getByTestId("orders-detail-addline-quantity-input").fill("2");
await page.getByTestId("orders-detail-addline-submit-button").click();
await expect(page.getByTestId("orders-detail-total-text")).toHaveText("$43.78");
await page.getByTestId("orders-detail-confirm-button").click();
await expect(page.getByTestId("orders-detail-state-status")).toHaveText("Confirmado");
await page.getByTestId("orders-detail-cancel-button").click();
await page.getByTestId("orders-cancel-confirm-dialog").waitFor();
await page.getByTestId("orders-cancel-confirm-button").click();
await expect(page.getByTestId("orders-detail-state-status")).toHaveText("Cancelado");
```

### Flow 3 — invoice an order and pay it (Admin or Finance)

Issuing happens on the order detail; there is no "new invoice" button on the list.

| Step | Id | Expected result |
|---|---|---|
| Issue the invoice of a confirmed order | on `/orders/{id}`, `orders-detail-invoice-button` ("Facturar", rendered for Admin and Finance only while the order is confirmed without an invoice) | Navigation to `/invoices/{id}`; the badge `invoices-detail-state-status` reads `Emitida` |
| Open a seeded issued invoice | `/invoices/1` (`FAC-0001`, total `$327.80`), reached from the list via `invoices-list-view-link-1` or from the order via `orders-detail-invoice-link` | The form `payments-register-form` with `payments-register-heading` ("Registrar un pago") |
| Pay by card | `payments-register-method-select` ("Tarjeta", "Transferencia", "Efectivo"), `payments-register-amount-input` (prefilled with the total), `payments-register-cardnumber-input`, `payments-register-cardexpiry-input` ("Vencimiento (MM/AA)"), `payments-register-cardcvc-input`, then `payments-register-submit-button` ("Pagar") | Approved: the state region "Pago aprobado.", the badge turns `Pagada` and the form is replaced by `invoices-detail-closed-text` ("Esta factura está pagada."); the order becomes `Pagado` |
| Pay by transfer | switch the method, use `payments-register-reference-input` ("Referencia", 4–40 characters) | Always approved; the history shows the reference |
| Pay in cash | switch the method; no extra fields | Always approved |

Errors a test can provoke:

- Amount edited so it differs from the total: the form alert gets `El monto debe ser igual al total de la factura.`
- Card number that fails the Luhn check or is not 16 digits: the field error `El número de tarjeta no es válido.`
- Expiry in the past: `La tarjeta está vencida.`; expiry not in `MM/AA` shape: `El formato no es válido.`; CVC not 3 digits: `El código de seguridad no es válido.`
- Card ending `0002` (declined, HTTP 402): the form alert gets `La pasarela rechazó el pago. Prueba con otra tarjeta.`, and the attempt is kept in the history (`invoices-detail-payment-row-{payment_id}`) with the badge `Rechazado` and the detail `Tarjeta rechazada`. The invoice stays `Emitida`.
- Card ending `0003` (HTTP 503): the alert `La pasarela de pago no está disponible. Inténtalo de nuevo.`; history badge `Fallido`, detail `Pasarela no disponible`.
- Invoicing a customer without a tax ID: the order alert gets `El cliente necesita un ID fiscal para poder facturar.` (seed: `Cafetería La Esquina`, order `PED-0007`).
- On a paid or void invoice the form is not rendered; the closed note explains it: `Esta factura está pagada.` or `Esta factura fue anulada.`

```ts
// Illustrative, not run in CI. FAC-0001 carries two failed attempts; a new approval changes history.
await page.getByTestId("invoices-list-view-link-1").click();
await page.getByTestId("payments-register-cardnumber-input").fill("4242 4242 4242 4242");
await page.getByTestId("payments-register-cardexpiry-input").fill("12/30");
await page.getByTestId("payments-register-cardcvc-input").fill("123");
await page.getByTestId("payments-register-submit-button").click();
await expect(page.getByTestId("invoices-detail-state-status")).toHaveText("Pagada");
await expect(page.getByTestId("invoices-detail-closed-text")).toHaveText("Esta factura está pagada.");
```

## 6. Waiting and state

Wait for observable markers instead of fixed timeouts; every one is in the code.

**Hydration first.** The `<body>` gets `data-hydrated="true"` once the React client has hydrated ([HydrationMarker](../frontend/src/components/HydrationMarker.tsx) sets it in an effect). A test should never interact with the server-only render; wait for `body[data-hydrated="true"]` before the first click.

**Loading instead of sleeping.** Every screen renders a `role="status"` region with `aria-busy="true"` and the text `Cargando…` while its data is in flight, under a `*-loading-status` id (`customers-list-loading-status`, `orders-detail-loading-status`, `invoices-detail-loading-status`, the shell's `app-shell-loading-status`, the summary's `home-{group}-{status}-loading-status`). Wait for such an element to appear and disappear, or wait directly for the data you assert on. The pickers say `Buscando clientes…` (`orders-form-customer-loading-status`, `orders-detail-changecustomer-loading-status`).

**Busy controls.** While a request runs, `Button` renders `data-state` of `idle`/`loading` with `aria-busy`, disables itself, and swaps its label (`Ingresando…`, `Guardando…`, `Pagando…`). A second click during `aria-busy="true"` is ignored — don't double-click in tests.

**Confirmation dialogs.** Only two actions confirm: cancel order and deactivate customer. Click the trigger (`orders-detail-cancel-button` / `customers-detail-deactivate-button`), wait for `orders-cancel-confirm-dialog` / `customers-deactivate-confirm-dialog`, then click `orders-cancel-confirm-button` ("Sí, cancelar pedido") / `customers-deactivate-confirm-button` ("Sí, desactivar"). The dialog closes when the request ends, failure or success; Escape and the backdrop never act on their own.

**Success statuses.** `role="status"` regions announce outcomes: `settings-taxrate-success-status` (`Impuesto actualizado a {rate} %.`) and `payments-register-success-status` (`Pago aprobado.`) — these two are not yet reached by an audited state, so they are in the code but not in the catalog; the same grammar still applies.

**Redirects after create.** Navigation happens through the router after the cache write: creating or editing a customer replaces the URL with `/customers/{id}`, creating an order with `/orders/{id}`, issuing the invoice navigates to `/invoices/{id}`, a successful login goes to `/`. Waiting for the destination heading id is enough.

**List state lives in the URL.** `/customers?page=1&q=beta&status=active`, `/orders?…&customer_id=4`, `/invoices?status=paid`, `/products?q=cable`. Submitting a search returns to page 1; a page beyond the last is corrected in the URL (`Página {page} de {last}`, `*-page-text`). Tests can deep-link a filtered list.

**The idempotency key of the payment form.** The form sends an `Idempotency-Key` header with `POST /api/invoices/{id}/payments`. In the UI it is **kept** after a network error or a 429 or a 5xx other than the gateway's 503 (the outcome is unknown, a retry replays or continues), and **renewed** after any other HTTP answer — a decline (402), a gateway failure (503 `PAYMENT_GATEWAY_UNAVAILABLE`), a 409 or a 422 — and whenever any field changes. So a test that retries after a decline is a genuinely new attempt; do not expect a second decline to be a replay ([SPEC section 6](SPEC.md), [frontend/README.md](../frontend/README.md)).

## 7. Accessibility and titles

**Running axe yourself.** In a Playwright test, run `@axe-core/playwright`'s `AxeBuilder` on a rendered page and pass only serious and critical violations, the rule the project enforces:

```ts
// Illustrative, not run in CI.
import AxeBuilder from "@axe-core/playwright";
const results = await new AxeBuilder({ page }).analyze();
const serious = results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
expect(serious).toEqual([]);
```

**What the project's own audit checks.** The browser audit ([tools/audit/README.md](../tools/audit/README.md)) opens every screen and scripted state of [`states.json`](../tools/audit/states.json), logs in as the state's user, and fails when a visible interactive element lacks a valid `data-testid`, when an id is used twice on the page or breaks the grammar, when axe-core reports a **serious or critical** WCAG 2.0/2.1 A or AA violation, or when the page scrolls sideways. It covers phone (390×844) and tablet (768×1024) states, and CI runs it twice, once per theme (`--theme light` and `--theme dark`). The static audit `testid-audit.mjs` additionally fails the build on any source element without an id. Add a state to `states.json` for every new screen you automate against, or a gap is invisible to CI.

**The document title.** Every screen names itself `{page} · LabApp` (the root metadata template `%s · LabApp`, applied by the `useDocumentTitle` hook or a `metadata` export). Detail pages keep the section title until the record arrives, then switch to the record (`Pedido PED-0003 · LabApp`); the error boundary of a crash names itself `Algo salió mal`. Assert titles as part of navigation checks — the audit asserts all of them.

**The skip link.** The first focusable element of every page is `Saltar al contenido` (`app-skip-link` in the shell, `auth-login-skip-link` on the login), which jumps to the `main` landmark at `#main-content`; it is visually hidden until focused. Keyboard-reachable tables are likewise wrapped in focusable `region` elements (`*-scroll-region`), which is what the phone-width audit states verify.

## 8. Things that surprise a test author

Each item below was verified in the code and the documents.

- **Rate limits exist only online.** They apply when `TEST_MODE=0` (the deployment; local runs `TEST_MODE=1` and has none): 120 requests per minute and 10 login attempts per minute per client IP; the answer is HTTP 429 `RATE_LIMITED`, `Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.`, with a `Retry-After` header ([SPEC section 3](SPEC.md)).
- **Sessions last 8 hours of activity, sliding.** After an expiry the shell redirects to `/login?expired=1`, where the login shows the alert `Tu sesión expiró. Inicia sesión de nuevo.` (`auth-login-expired-alert`); any other lost session goes to `/login` plain. The login page is never left in the history (`router.replace`).
- **Optimistic concurrency shows a reload affordance.** Every versioned record carries `version`; a stale one answers 409 `VERSION_CONFLICT` with `El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.` The customer edit form offers a `Recargar datos` button (`customers-form-reload-button`) and the order detail simply refetches the order, so the page's next click always sends a fresh version.
- **Controls disappear per role, but the server decides.** Finance and Read-only get no `customers-list-new-link`, no edit/deactivate controls and no order edges; Sales gets no invoice controls (`orders-detail-invoice-button`, the payment form); only Admin sees the tax-rate form (`settings-taxrate-readonly-text` for the rest: `Solo un administrador puede cambiar el impuesto.`). A role that reaches a write URL anyway sees the alert `No tienes permiso para realizar esta acción.` (for example `customers-form-forbidden-alert`), and the API itself answers the same with 403 `FORBIDDEN`.
- **Numbers keep growing after the seed.** The next order is `PED-0008`, the next invoice `FAC-0004`, the next payment id 5. Seeded numbers have no gaps, but later ones can skip one: a rolled-back transaction still consumed its number (part 2 covers a reset to go back).
- **The nightly reset online.** A GitHub Actions workflow calls the reset every day at 03:17 UTC ([docs/DEPLOYMENT.md](DEPLOYMENT.md)); it needs the test controls of part 2 deployed and a token, so until then nothing resets the online data — which means the shared demo dataset drifts with every visitor.
- **The theme is remembered per browser.** The selector choice lives in `localStorage` under `labapp-theme` with the values `light` or `dark` (no key: the app follows the system preference); an inline script applies it before the first paint. Pin a theme for a deterministic run with `localStorage.setItem("labapp-theme", "dark")` before load, or run the project audit with `--theme dark` ([tools/audit/README.md](../tools/audit/README.md)).
- **Local data is memory.** `mise run dev` keeps data in memory: restart the processes and every created record is gone and the seed numbers restart. A suite that assumes persistence will drift between runs; a suite that assumes the seed should reset it (part 2) or tolerate both.
- **Dates are UTC, money is dollars.** Timestamps show as `01/01/2026 10:00 UTC` (order `PED-0001` was created then), never converted to the viewer's time zone; totals show as `$327.80` ([SPEC section 8](SPEC.md)). Assert the rendered strings, not recomputed dates.

## 9. What is next

Part 1 covered the web UI; this guide continues below with **part 2**: the HTTP API and the test-only controls (reset, seed, the controllable clock and fault injection).

---

# Part 2: the HTTP API and the test controls

Driving the UI is only half of what makes LabApp easy to automate. The other half is HTTP: every screenshot has an endpoint behind it, and the seed, reset, clock and faults exist so a test can arrange the world it needs. These sections cover the base path and authentication, the committed contract, the seven test-control endpoints with recipes, the three core flows over `curl`, the versioning and idempotency machinery, and how to isolate a run from other visitors of the demo.

Every endpoint, status code, header, field and message below was read from the backend code, [SPEC.md](SPEC.md) and the committed contract [openapi.json](openapi.json); each `curl` recipe was verified against the local server that `mise run dev` starts.

## 10. Where the API is

**One origin, two path roots.** The web app and the API are served from the same origin: locally the Next.js dev server on `http://localhost:3000` forwards `/api/*` and `/__test__/*` to the FastAPI process ([docs/DEVELOPMENT.md](DEVELOPMENT.md)); online, the Vercel project routes the same two prefixes to the API service ([docs/ARCHITECTURE.md](ARCHITECTURE.md)). Point `curl` and Playwright `request` contexts at `http://localhost:3000` (or directly at the API, `http://127.0.0.1:8000`, from a script that does not need cookie-sharing with the browser). Endpoints live under `/api`; the test controls live under `/__test__`, at the root of the API, never under `/api`.

**Logging in with a request.** `POST /api/auth/login` takes `{"email", "password"}` (the email is trimmed and lowercased before the lookup) and answers 200 with the user plus a `Set-Cookie` header. Keep the cookie in a jar; the cookie name is `labapp_session`, and it is `HttpOnly` and `SameSite=Lax` (`Secure` too whenever the origin starts with `https://`):

```bash
BASE=http://localhost:3000
curl -s -c /tmp/labapp-cookies -H 'Content-Type: application/json' \
  -d '{"email":"sales@labapp.test","password":"Demo-LabApp-2026!"}' \
  "$BASE/api/auth/login"
# {"id":2,"name":"Ventas Demo","email":"sales@labapp.test","role":"sales"}
```

`GET /api/auth/me` returns the current user; `POST /api/auth/logout` ends the session and answers 204, and is idempotent: it answers 204 with or without a session. What an API suite can meet on the way in:

| Situation | HTTP | Code | Message |
|---|---|---|---|
| Wrong email or password | 401 | `INVALID_CREDENTIALS` | `Email o contraseña incorrectos.` |
| No session on a protected route | 401 | `UNAUTHENTICATED` | `Inicia sesión para continuar.` |
| Session idle for more than 8 hours | 401 | `SESSION_EXPIRED` | `Tu sesión expiró. Inicia sesión de nuevo.` |

The same error shape for both wrong email and wrong password is deliberate: accounts cannot be enumerated. Only `POST /api/auth/login`, `POST /api/auth/logout` and `GET /api/health` work without a session.

**The `Origin` rule (CSRF).** State-changing requests — `POST`, `PUT`, `PATCH`, `DELETE` — that carry an `Origin` header must match the application origin; a mismatch answers 403 `CSRF_ORIGIN_MISMATCH` with `La solicitud no proviene de la aplicación.` ([SPEC section 3](SPEC.md#3-authentication-and-sessions)). The comparison is against `APP_ORIGIN` (locally `http://localhost:3000`); online it also accepts the Vercel preview origins built from the platform variables, so a test against a preview URL works. Two details a test suite cares about:

- A request **without** an `Origin` header is always allowed — API clients and test suites send none, because the cookie is `SameSite=Lax` and cannot be sent cross-site in the harmful direction. Do not add `Origin` to your requests unless you are testing this rule.
- The rule applies to `/api/*` paths only; it is a global guard, and it runs before the route's own checks ([SPEC section 7](SPEC.md#7-errors-and-validation-order)), so a bad `Origin` answers 403 even before authentication could answer 401.

**The contract file.** [docs/openapi.json](openapi.json) is the committed OpenAPI 3 document of every `/api` route: request bodies, query parameters, response shapes and every error answer each operation can give (the `/__test__` controls are deliberately left out of it). FastAPI generates it; the command `cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json` regenerates it, CI fails when the committed file and the application disagree ([backend/README.md](../backend/README.md)), and the running API serves the same document at `/openapi.json` of its own origin. Import `docs/openapi.json` into Postman, Insomnia or any OpenAPI client to get every request pre-built; it is also what code generators consume.

**The error format.** Every error answer is `application/problem+json` ([SPEC section 8](SPEC.md#8-formats-and-conventions)) with `type`, `title` (HTTP status name), `status`, `code` (stable), `detail` (Spanish message) and, when the problem is field-level, `errors[]` with one entry per field:

```json
{"type": "about:blank", "title": "Unprocessable Content", "status": 422,
 "code": "VALIDATION_ERROR", "detail": "Revisa los datos ingresados.",
 "errors": [{"field": "quantity", "code": "OUT_OF_RANGE",
             "message": "El valor debe estar entre 1 y 999."}]}
```

Other problem bodies carry extra members at the top level: `shortages[]` on a 409 `INSUFFICIENT_STOCK`, `payment_id` and `reason` on a 402 `PAYMENT_DECLINED` or a 503 `PAYMENT_GATEWAY_UNAVAILABLE`, and `retry_after` on a 429 `RATE_LIMITED` (the same seconds the `Retry-After` header carries). The stable codes and their messages are catalogued in [SPEC section 7](SPEC.md#7-errors-and-validation-order); a test should assert the `code`, not the wording, which may change. Every response — success or error — carries an `X-Request-Id` header; send your own (1–64 characters of `[A-Za-z0-9._-]`) to have it echoed into logs.

## 11. The test controls

Seven endpoints under `/__test__` let a script arrange the world instead of assuming it: reset and seed own the data, the clock owns time, the faults own failure. They answer without a session, they are not in [openapi.json](openapi.json), and they are guarded by the test token.

| Method | Path | Body | Answer |
|---|---|---|---|
| `POST` | `/__test__/reset` | none | 200 `{"status": "ok"}` |
| `POST` | `/__test__/seed` | `{"dataset": "default" \| "empty"}` | 200 `{"dataset": "<value>"}` |
| `GET` | `/__test__/clock` | none | 200 `{"now": "<ISO 8601 UTC>", "offset_seconds": <number>}` |
| `POST` | `/__test__/clock` | exactly one of `{"offset_seconds": <number>}` or `{"advance_seconds": <number>}` | the same shape as `GET` |
| `POST` | `/__test__/faults` | a fault rule (below) | 201, the stored rule with its `id` |
| `GET` | `/__test__/faults` | none | 200, the list of non-exhausted rules |
| `DELETE` | `/__test__/faults` | none | 204, no body |

**The token.** Every answer depends on the guard:

| `TEST_MODE` | `X-Test-Token` header | Result |
|---|---|---|
| `1` | any | Allowed. |
| `0` | equals a non-empty `TEST_TOKEN` | Allowed. |
| `0` | missing or different | 404 `NOT_FOUND`, as if the route did not exist. |
| `0` with an empty `TEST_TOKEN` | any / missing | 404 `NOT_FOUND`. |

The local start script sets `TEST_MODE=1`, so local runs need no header at all; a public deployment keeps `TEST_MODE=0` and reveals the controls only to a request that sends `X-Test-Token: <TEST_TOKEN>` ([docs/DEPLOYMENT.md](DEPLOYMENT.md) names the variable). The guard runs twice: as a middleware before routing and again inside the router, and the token is compared in constant time. The 404 answer is a problem document, `application/problem+json` with `code: "NOT_FOUND"` and `No se encontró el recurso solicitado.`, so an unguarded probe looks exactly like a mistyped path.

**The token and the rate limits.** The request rate limits (120 requests per minute and 10 login attempts per minute per client IP) apply only when `TEST_MODE=0`, and a request with a valid `X-Test-Token` is exempt from them even then — so adding the token header to every request of an online suite removes the risk of 429 entirely (it does nothing locally, where the limits are always off). Exceeding a limit answers 429 `RATE_LIMITED` with a `Retry-After` header and a `retry_after` member with the same seconds.

All three of the following have been verified against the local server: `BASE=http://127.0.0.1:8000` for the direct API (with `TEST_MODE=1` from `mise run dev`; the same paths also work through the web origin).

### Reset before a suite

```bash
BASE=http://127.0.0.1:8000
curl -s -X POST "$BASE/__test__/reset"   # {"status":"ok"}
```

A reset restores exactly what [docs/SEED.md](SEED.md) and [SPEC section 9](SPEC.md#9-seed-data) list: the ten customers, the fifteen products, the seven orders with their invoices and payments, the number sequences (the next order is `PED-0008`, the next invoice `FAC-0004`, the next payment id 5, the next customer id 11), the tax rate back to `DEFAULT_TAX_RATE`, the clock offset to 0, every fault rule deleted, and the stored idempotency keys and the rate-limit counters of the instance that served the reset.

Two things a suite relies on, verified against the code and the live server:

- **Sessions survive.** The reset upserts the four users without touching `sessions`, so a cookie saved from a login keeps working: a suite can log in once, keep the cookie jar, and reset between tests without logging in again.
- **A reset is meant for a quiet system.** It runs as one transaction in PostgreSQL, but a request that happens to be in flight can make it answer 409 `RESET_CONFLICT` (`No se pudo reiniciar porque hay una operación en curso. Inténtalo de nuevo.`) or 503 `LOCK_TIMEOUT`; the recipe is to retry once ([backend/README.md](../backend/README.md)).

### Seed a named dataset

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"dataset": "empty"}' "$BASE/__test__/seed"    # {"dataset":"empty"}
curl -s -H 'Content-Type: application/json' \
  -d '{"dataset": "default"}' "$BASE/__test__/seed"  # {"dataset":"default"}
```

`default` loads the data of [SEED.md](SEED.md) without touching the clock, the faults or the rate-limit counters; `empty` keeps only the four users and the settings — every other table is emptied (a `GET /api/customers` right after it lists `{"items": [], "page": 1, "page_size": 20, "total": 0}`), the sequences restart and the tax rate is restored. Both answer `{"dataset": "<value>"}` with the requested name. An unknown `dataset`, an unknown extra field or a wrong type is a 422 `VALIDATION_ERROR` naming the offending field (`dataset`).

### Move the clock

```bash
curl -s "$BASE/__test__/clock"
# {"now":"2026-11-08T16:47:24.206680Z","offset_seconds":0.0}
curl -s -H 'Content-Type: application/json' \
  -d '{"advance_seconds": 3600}' "$BASE/__test__/clock"
```

The application time is the system clock plus an offset in seconds. `POST` takes **exactly one** of `{"offset_seconds": <number>}` (replace the offset) or `{"advance_seconds": <number>}` (add to it); neither or both is a 422 `VALIDATION_ERROR` with the field `body`, a string where a number belongs is a 422 on that field, and the offset must stay within ±315,360,000 seconds (± ten years: `El valor debe estar entre -315360000 y 315360000.`). The returned `now` and `offset_seconds` show the result, so a test can assert the state it just set.

**Provoke `SESSION_EXPIRED`.** A session expires after **8 hours without activity** (a sliding window; every request extends it), measured with the application clock: advance past the idle time, then use the session once and watch it die ([SPEC section 3](SPEC.md#3-authentication-and-sessions)):

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"advance_seconds": 28801}' "$BASE/__test__/clock"   # 8 h plus a second
curl -s -b /tmp/labapp-cookies "$BASE/api/auth/me"
# 401 {"code":"SESSION_EXPIRED","detail":"Tu sesión expiró. Inicia sesión de nuevo.", ...}
curl -s -H 'Content-Type: application/json' \
  -d '{"offset_seconds": 0}' "$BASE/__test__/clock"        # put the clock back
```

In the browser, the same advance ends with the UI redirecting to `/login?expired=1`, where the login shows the notice `Tu sesión expiró. Inicia sesión de nuevo.` (part 1, section 8). Moving the clock that far also expires every other session of the demo, so log in again afterwards; setting the offset back to 0 does not restore sessions that already expired.

**Provoke `CARD_EXPIRED`.** A card's `MM/YY` expiry month is valid through its last day, compared against the application clock. The expiry `12/30` therefore means December **2030**:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"advance_seconds": 4752000}' "$BASE/__test__/clock"
# the application date is now early January 2027: an expiry of "12/30" is still valid,
# so a card payment with it is accepted as usual.
curl -s -H 'Content-Type: application/json' \
  -d '{"advance_seconds": 136248000}' "$BASE/__test__/clock"
# the advance is cumulative; the date is now past December 2030, and the same card
# payment now answers:
# 422 {"code":"VALIDATION_ERROR","errors":[{"field":"card.expiry","code":"CARD_EXPIRED",
#       "message":"La tarjeta está vencida."}], ...}
```

As with the session recipe, an advance this large expires the sessions, so log in after moving the clock and set the offset back to 0 at the end.

### Inject faults

A fault rule tells the server to delay a request and/or to answer it with a configured status before the application runs. `POST /__test__/faults` stores the rule and answers 201 with it; `GET /__test__/faults` lists the rules that are not exhausted; `DELETE /__test__/faults` removes every rule and answers 204. A rule is consumed once per matching request: with `times` it stops matching after that many, and an exhausted rule disappears from the list.

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"target": "route", "method": "GET", "path": "/api/customers", "status": 500, "times": 2}' \
  "$BASE/__test__/faults"
# 201 {"id":2,"target":"route","method":"GET","path":"/api/customers",
#      "latency_ms":0,"status":500,"remaining":2}
curl -s -b /tmp/labapp-cookies "$BASE/api/customers"     # 500 INJECTED_FAULT
curl -s -b /tmp/labapp-cookies "$BASE/api/customers"     # 500 INJECTED_FAULT (last one)
curl -s -b /tmp/labapp-cookies "$BASE/api/customers"     # 200, the rule is exhausted
curl -s "$BASE/__test__/faults"                          # []
curl -s -X DELETE "$BASE/__test__/faults"                # 204
```

The two failed requests answer the problem document `{"status": 500, "code": "INJECTED_FAULT", "detail": "Falla inyectada para pruebas."}` — the fault is decided before the route runs, so it needs no data and works on any method and path.

**Latency.** A rule with `latency_ms` and no `status` only delays the request:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"target": "route", "method": "GET", "path": "/api/customers", "latency_ms": 1000, "times": 1}' \
  "$BASE/__test__/faults"
time curl -s -b /tmp/labapp-cookies "$BASE/api/customers"   # real 1.0s
```

The wait happens in the middleware, before the application — even a request that only ends in a 401 pays the delay. This is how slow-network behaviour (spinners, `aria-busy`, disabled buttons) is tested deterministically; combine it with a `times` count to hit only one request.

**Make the gateway unavailable.** A `gateway` rule targets the payment gateway instead of a route: the next payment call — any method — waits the rule's latency and fails with 503 `PAYMENT_GATEWAY_UNAVAILABLE` (`La pasarela de pago no está disponible. Inténtalo de nuevo.`) without reaching the fake gateway. The body carries the extra members `payment_id` and `reason: "GATEWAY_UNAVAILABLE"`, and the attempt is kept in the invoice history with the `failed` status, exactly like the seed's `PED-0003` ([docs/SEED.md](SEED.md)):

```bash
curl -s -H 'Content-Type: application/json' -d '{"target": "gateway", "times": 1}' \
  "$BASE/__test__/faults"
# then, as Finance, with an Idempotency-Key of your choice:
curl -s -i -b /tmp/labapp-cookies -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: gw-1' \
  -d '{"method": "card", "amount": "327.80", "card": {"number": "4242 4242 4242 4242", "expiry": "12/30", "cvc": "123"}}' \
  "$BASE/api/invoices/1/payments"
# 503 {"code":"PAYMENT_GATEWAY_UNAVAILABLE","detail":"La pasarela de pago no está disponible. Inténtalo de nuevo.",
#      "payment_id":7,"reason":"GATEWAY_UNAVAILABLE"}
```

`payment_id` is the id of the stored attempt and depends on what exists: after a fresh reset the next payment id is 5 ([docs/SEED.md](SEED.md)).

A golden rule of the idempotency machinery applies here (section 13): the failed attempt consumed the key, so a retry of this payment needs a **new** key.

**What a rule can and cannot.** A `route` rule matches one HTTP method (any method when `method` is absent) and an **exact path**: no prefixes, no patterns, no query strings (`/api/customers` does not match `/api/customers/11`, and the query parameters are not part of the path). A `gateway` rule takes none of `method`, `path` or `status` — sending any of them is a 422 on that field. The rule fields and their limits, validated before the rule is stored (each problem is a 422 `VALIDATION_ERROR` entry):

| Field | Rule |
|---|---|
| `target` | `route` or `gateway` (anything else: `INVALID_FORMAT`). |
| `method` | optional, one of `GET`, `POST`, `PUT`, `PATCH`, `DELETE`; only for a `route` rule. |
| `path` | required for `route`, must start with `/`, at most 2048 characters, no control characters, never starting with `/__test__`, and `/api/health` is rejected by name (`La ruta /api/health no puede tener una falla inyectada.`). |
| `latency_ms` | 0 to 10000; a `route` rule needs a positive latency or a status (`La regla necesita latencia o un estado.`). |
| `status` | optional, 400 to 599, `route` only; the injected answer uses it verbatim. |
| `times` | optional, 1 to 1000 (`El valor debe estar entre 1 y 1000.`); without it the rule stays until `DELETE /__test__/faults` or a reset removes it. |

At most **50 non-exhausted rules** exist; when they are full the answer is a 422 on `target` reading `Ya hay 50 reglas activas. Elimina alguna con DELETE /__test__/faults.` — clear first, then add. The `/__test__/*` routes themselves and `GET /api/health` are never affected by a fault, so a test cannot lock itself out. A reset also deletes every rule, moves the clock back to 0, and is the cheapest way to start a scenario from a clean slate.

**The same recipes in Playwright.** For API-level tests the `request` fixture plays the role of curl (illustrative, not run in CI):

```ts
// Illustrative, not run in CI. Local: TEST_MODE=1, no token needed.
const base = "http://127.0.0.1:8000";
const controls = await request.newContext();           // no cookie jar needed
await controls.post(`${base}/__test__/reset`);
await controls.post(`${base}/__test__/clock`, { data: { advance_seconds: 28801 } });
const me = await request.get(`${base}/api/auth/me`);   // your existing logged-in context
expect(me.status()).toBe(401);
expect((await me.json()).code).toBe("SESSION_EXPIRED");
```

## 12. Orders and invoices through the API

The standard path of a test run: log in, create the customer, build and confirm the order, issue the invoice, pay. After a reset the ids are deterministic — the first new customer is 11, the first new order `PED-0008`, the first new invoice `FAC-0004`, the first new payment id 5 — so a suite can assert on them.

```bash
BASE=http://127.0.0.1:8000
J=/tmp/labapp-cookies

# 1. Log in as Sales (Admin works too): create customers and orders.
curl -s -c $J -H 'Content-Type: application/json' \
  -d '{"email":"sales@labapp.test","password":"Demo-LabApp-2026!"}' "$BASE/api/auth/login"

# 2. Create the customer. 201, Location: /api/customers/11, ETag: "1".
curl -s -i -b $J -H 'Content-Type: application/json' \
  -d '{"name":"Cliente de Prueba","email":"prueba-api@example.test","tax_id":"PRUE-123"}' \
  "$BASE/api/customers"

# 3. Create a draft order for it. 201, Location: /api/orders/8, ETag: "1",
#    number "PED-0008", empty lines, totals "0.00", tax_rate preview "10.00".
curl -s -i -b $J -H 'Content-Type: application/json' -d '{"customer_id": 11}' "$BASE/api/orders"

# 4. Add two units of product 1 (KB-100). 201, ETag: "2", total "43.78" (10% tax).
curl -s -i -b $J -H 'Content-Type: application/json' \
  -d '{"product_id": 1, "quantity": 2, "version": 1}' "$BASE/api/orders/8/lines"

# 5. Confirm. 200, ETag: "3", status "confirmed"; the stock of KB-100 drops by 2
#    and the totals and the tax rate freeze.
curl -s -i -b $J -X POST -H 'If-Match: "2"' "$BASE/api/orders/8/confirm"

# 6. Log in as Finance (Admin works too): issue invoices and pay.
curl -s -c $J -H 'Content-Type: application/json' \
  -d '{"email":"finance@labapp.test","password":"Demo-LabApp-2026!"}' "$BASE/api/auth/login"

# 7. Issue the invoice. 201, Location: /api/invoices/4, ETag: "1", number "FAC-0004";
#    the order is linked (its invoice_id set and its version bumped to 4), the issue
#    email ("Factura FAC-0004 emitida") is only written to the log.
curl -s -i -b $J -X POST "$BASE/api/orders/8/invoice"

# 8. Pay with the always-approved card. 201 with a PaymentResult:
#    {"payment": {"id": 5, "method": "card", "status": "approved", "amount": "43.78",
#                 "reference": null, "card_last4": "4242", "reason": null, ...},
#     "invoice": {"status": "paid", "version": 2, ...}}
#    ETag: "2" (the invoice's new version); the order is "paid" as well.
curl -s -i -b $J -H 'Content-Type: application/json' -H 'Idempotency-Key: pay-0001' \
  -d '{"method":"card","amount":"43.78",
       "card":{"number":"4242 4242 4242 4242","expiry":"12/30","cvc":"123"}}' \
  "$BASE/api/invoices/4/payments"
```

The guards a test meets on the way ([SPEC sections 4–6](SPEC.md)): every route needs a session; creating customers, orders and lines, editing them, and confirming/cancelling/shipping are for Admin and Sales (`403 FORBIDDEN` otherwise); issuing an invoice and registering a payment are for Admin and Finance. Money is always a JSON string with exactly two decimals (`"43.78"`), never a number; the tax rate is `"10.00"` too.

- Stable codes pointer… (placeholder)
