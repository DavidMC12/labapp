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
await page.getByTestId("customers-detail-heading").toHaveText(name);
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
await page.getByTestId("orders-detail-state-status").toHaveText("Borrador");
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
