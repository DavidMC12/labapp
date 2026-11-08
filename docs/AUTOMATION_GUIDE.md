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

### Sort the four lists

Every sortable column header of the four lists is a real `<button>` inside `aria-sort`-carrying `<th>` corners, and the 14 buttons share one id shape, `<module>-list-sort-<field>-button` (`created_at` is written `created`). The list's other filters and the export link sit around the table; the columns that nothing sorts by (`ID fiscal`, `Estado`, …) are plain `<th>` without a button.

| List | Sort buttons and field each one sorts by |
|---|---|
| `/customers` | `customers-list-sort-name-button` (name), `customers-list-sort-email-button` (email), `customers-list-sort-created-button` (`created_at`) |
| `/orders` | `orders-list-sort-number-button` (number), `orders-list-sort-customer-button` (customer name), `orders-list-sort-created-button` (`created_at`) |
| `/invoices` | `invoices-list-sort-number-button` (number), `invoices-list-sort-customer-button` (customer name), `invoices-list-sort-total-button` (total), `invoices-list-sort-created-button` (`created_at`) |
| `/products` | `products-list-sort-sku-button` (sku), `products-list-sort-name-button` (name), `products-list-sort-price-button` (price), `products-list-sort-stock-button` (stock) |

**What a click does.** The first click sorts the column with the default direction of its field (`created_at` descending, every other field ascending — the API's defaults, section 12), and a second click on the sorted column flips the direction. There is **no unsorted state**: the plain list *is* the default sort (`created_at` descending; the products catalog, `id` ascending), and both URL parameters are left out of it. Either kind of click returns the list to page 1 and keeps every other filter.

**What to assert.** Three places carry the sort state, and the click is over when the data lands:

| Where | Attribute | Values |
|---|---|---|
| the `<th>` (`aria-sort`) | `aria-sort` | `ascending` / `descending` while the table is sorted by it, **no attribute otherwise** |
| the button | `data-state` | `ascending` / `descending` when sorted, **the literal `none` otherwise** — it never disappears |
| the hidden status | text | `Ordenado por {label}, {ascendente\|descendente}` (e.g. `Ordenado por Nombre, ascendente`) in `*-list-sort-text`, a visually hidden `role="status"` paragraph |

The sort lives in the URL next to the filters: `?page=1&sort=name&direction=asc`. A list loaded directly from that URL arrives sorted (the API request carries the parameters), and an invalid `sort` or `direction` in the URL falls back to the default, like an invalid `status` does. Every change updates the URL, the `aria-sort`, the `data-state` and the hidden status together; only the `aria-sort` of the `<th>` vanishes when the column is not the sorted one — the button's `data-state="none"` is always there.

```ts
// Illustrative, not run in CI.
const th = page.getByTestId("customers-list-sort-name-button").locator("..");
const otherTh = page.getByTestId("customers-list-sort-email-button").locator("..");
await page.getByTestId("customers-list-sort-name-button").click();
await expect(th).toHaveAttribute("aria-sort", "ascending");
await expect(th.getByTestId("customers-list-sort-name-button"))
  .toHaveAttribute("data-state", "ascending");
await expect(page).toHaveURL(/sort=name&direction=asc/);
await expect(page.getByTestId("customers-list-sort-text"))
  .toHaveText("Ordenado por Nombre, ascendente");
// a column nothing sorts by: no aria-sort on its th, data-state "none" on its button
await expect(otherTh).not.toHaveAttribute("aria-sort", /.*/);
await expect(otherTh.getByTestId("customers-list-sort-email-button"))
  .toHaveAttribute("data-state", "none");
```

**The order of the rows.** The attribute says which column is sorted; a test that wants to be sure about the array order reads one column's cells and compares with the expected order. Every cell carries the record id as its suffix (`customers-list-name-cell-1` is customer 1), so a locator prefix reaches all the rows:

```ts
// Illustrative, not run in CI. On ten seeded customers, names ascend and
// the accents ignore themselves: `Ferretería Fénix` lands in the F position.
await page.getByTestId("customers-list-sort-name-button").click();
const names = await page.locator('[data-testid^="customers-list-name-cell-"]').allTextContents();
expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, "es")));
```

**The traps.** Sorting silently resets the page (`?page=` goes back to 1) while surviving filters (`q`, `status`, …) keep travelling in the URL; because the sort is a URL parameter, a test can skip the clicks and open the sorted list directly, and it must not expect an unsorted state to come back. Text columns compare the **normalized** text — accents and upper case are ignored, so `Álvaro` sorts with `A` (section 12 explains the normalization) — and `number` sorts `PED-0009` after `PED-0002` because it compares the numeric part as an integer.

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

Part 1 covered the web UI; **part 2** (the next sections of this document) covers the other half: the HTTP API under `/api` (section 10) and the test-only controls — reset, seed, clock, faults (section 11) — with recipes for the three flows over `curl` (section 12), how to isolate a run (section 13) and the online demo (section 14). The same sections teach the machinery the four lists gained since part 1 was drafted: their `sort` and `direction` parameters and their CSV downloads (section 12) and the headers every API answer carries (section 10). Before writing API tests, read in this order: [SPEC.md](SPEC.md) sections 2–3 (roles, sessions, the origin rule), 5–6 (orders, invoices and payments) and 7–9 (errors, formats, the seed contract); [openapi.json](openapi.json), the committed contract of every endpoint; and [backend/README.md](../backend/README.md) if you want the controls explained from the server side.

---

# Part 2: the HTTP API and the test controls

Driving the UI is only half of what makes LabApp easy to automate. The other half is HTTP: every screenshot has an endpoint behind it, and the seed, reset, clock and faults exist so a test can arrange the world it needs. These sections cover the base path and authentication (with the headers every API answer carries), the committed contract, the seven test-control endpoints with recipes, the three core flows over `curl`, the `sort` and `direction` parameters and the CSV downloads of the four lists, the versioning and idempotency machinery, and how to isolate a run from other visitors of the demo.

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

**The contract file.** [docs/openapi.json](openapi.json) is the committed OpenAPI 3 document of every `/api` route: request bodies, query parameters, response shapes and every error answer each operation can give (the `/__test__` controls are deliberately left out of it). FastAPI generates it; the command `cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json` regenerates it, CI fails when the committed file and the application disagree ([backend/README.md](../backend/README.md)), and the running API serves the same document at `/api/openapi.json` of its own origin, with an interactive Swagger UI at `/api/docs` (log in on the web app first: "Try it out" sends the session cookie). Import `docs/openapi.json` into Postman, Insomnia or any OpenAPI client to get every request pre-built; it is also what code generators consume.

**The error format.** Every error answer is `application/problem+json` ([SPEC section 8](SPEC.md#8-formats-and-conventions)) with `type`, `title` (HTTP status name), `status`, `code` (stable), `detail` (Spanish message) and, when the problem is field-level, `errors[]` with one entry per field:

```json
{"type": "about:blank", "title": "Unprocessable Content", "status": 422,
 "code": "VALIDATION_ERROR", "detail": "Revisa los datos ingresados.",
 "errors": [{"field": "quantity", "code": "OUT_OF_RANGE",
             "message": "El valor debe estar entre 1 y 999."}]}
```

Other problem bodies carry extra members at the top level: `shortages[]` on a 409 `INSUFFICIENT_STOCK`, `payment_id` and `reason` on a 402 `PAYMENT_DECLINED` or a 503 `PAYMENT_GATEWAY_UNAVAILABLE`, and `retry_after` on a 429 `RATE_LIMITED` (the same seconds the `Retry-After` header carries). The stable codes and their messages are catalogued in [SPEC section 7](SPEC.md#7-errors-and-validation-order); a test should assert the `code`, not the wording, which may change. Every response — success or error — carries an `X-Request-Id` header; send your own (1–64 characters of `[A-Za-z0-9._-]`) to have it echoed into logs.

### The headers of every API answer

Two headers travel on **every** response of the API — a request whose path starts with `/api/` or `/__test__/` — whatever its status: the guards' problem answers, the 404 of an unknown path, a 413 body-too-large and a 429 rate-limit answer included ([SPEC section 8](SPEC.md#8-formats-and-conventions)):

| Header | Value | Why a test can lean on it |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | no answer is ever sniffed into a different type |
| `Cache-Control` | `no-store` | the API's answers depend on the session or the data, so a shared cache must never keep them |

One exception with two paths: `GET /api/openapi.json` (the committed contract) and `GET /api/docs` (the Swagger page) carry **only** `nosniff`, without `no-store` — they are static documents a cache may keep. `GET /api/health` follows the general rule (it carries both), and a response that sets its own `Cache-Control` keeps it (today every route that sets one says `no-store`). The export files add `Content-Disposition` to this base, [section 12](#12-orders-and-invoices-through-the-api).

The full set, asserted on a success (200) and on a 401, run against a local API:

```bash
BASE=http://127.0.0.1:8000; J=/tmp/labapp-cookies
curl -s -i -b $J "$BASE/api/customers" | grep -iE '^(HTTP|x-content-type|cache-control|content-type)'
# 200: content-type: application/json, plus nosniff and no-store
curl -s -i        "$BASE/api/customers" | grep -iE '^(HTTP|x-content-type|cache-control)'
# 401 (no cookie jar): the guards answer through the same middleware, same two headers
curl -s -i -b $J "$BASE/api/openapi.json" | grep -iE '^(HTTP|x-content-type|cache-control)'
# 200: nosniff, and no cache-control — the second exception is /api/docs, same shape
```

```ts
// Illustrative, not run in CI. The browser context of the suite is logged in
// (section 10); a fresh API request context is not.
import { request as pwRequest } from "@playwright/test";

const base = "http://127.0.0.1:8000";
const ok = await request.get(`${base}/api/customers`);
expect(ok.status()).toBe(200);
expect(ok.headers()["x-content-type-options"]).toBe("nosniff");
expect(ok.headers()["cache-control"]).toBe("no-store");

const anon = await pwRequest.newContext();          // no cookie jar
const denied = await anon.get(`${base}/api/customers`);
expect(denied.status()).toBe(401);
expect(denied.headers()["x-content-type-options"]).toBe("nosniff");
expect(denied.headers()["cache-control"]).toBe("no-store");
await anon.dispose();
```

The web pages have their own set — `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` and `Cross-Origin-Opener-Policy: same-origin`, plus `Content-Security-Policy` in production only — applied by `frontend/next.config.ts`. The API paths take no part in it: the pattern that applies those headers explicitly excludes `/api/*` and `/__test__/*`, so an API answer never carries the web app's policy, and the browser never mixes the two.

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

The recipes below were verified request by request against the local server: `BASE=http://127.0.0.1:8000` for the direct API (with `TEST_MODE=1` from `mise run dev`; the same paths also work through the web origin).

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

In the browser, the same advance ends with the UI redirecting to `/login?expired=1`, where the login shows the notice `Tu sesión expiró. Inicia sesión de nuevo.` (part 1, section 8). The expiry is only a comparison of the application clock against the session's idle window — the session itself is not deleted, and a cookie that answered `SESSION_EXPIRED` works again once the offset is back below the window (verified against the server; a login purges only sessions idle for more than 32 hours). Moving the clock as this recipe does expires every other session of the demo for as long as the offset stays up, so log in again after moving it and set the offset back to 0 at the end.

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

A golden rule of the idempotency machinery applies here (section 12): the failed attempt consumed the key, so a retry of this payment needs a **new** key.

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

### Optimistic concurrency: `version`, `ETag`, `If-Match`

Every customer, order and invoice carries an integer `version` starting at 1, +1 on every change, and every response that returns one of them carries `ETag: "<version>"` — including create, update and transition answers. Use it to assert *how many* changes happened, and to send a conditional request the next time. Which route takes the version, and how:

| Route | Where the version goes |
|---|---|
| `PATCH /api/customers/{id}` | `version` in the JSON body (required there) |
| `POST /api/customers/{id}/deactivate`, `/reactivate` | optional `If-Match: "<version>"` header |
| `PATCH /api/orders/{id}` (change the customer of a draft) | `version` in the body |
| `POST /api/orders/{id}/lines` | `version` in the body |
| `PATCH /api/orders/{id}/lines/{line_id}` | `version` in the body |
| `DELETE /api/orders/{id}/lines/{line_id}` | optional `If-Match` (the order's) |
| `POST` `/api/orders/{id}/confirm`, `/cancel`, `/ship` | optional `If-Match` (the order's) |
| `POST /api/orders/{id}/invoice` | optional `If-Match` (the **order's**) |
| `POST /api/invoices/{id}/payments` | optional `If-Match` (the **invoice's**) |

A stale version answers 409 `VERSION_CONFLICT` with `El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo.`; no version sent skips the check (then a repeated transition answers the business conflict instead — `INVALID_TRANSITION` or `INVOICE_NOT_PAYABLE`). A malformed header — an unnecessary pair of quotes, non-digits, or anything outside 1–2147483647 — is a 422 `VALIDATION_ERROR` with `{"field": "If-Match", "code": "INVALID_FORMAT"}`. Requests that change nothing do not bump the version: an update with identical values, for example, answers 200 leaving `version` and `updated_at` untouched ([SPEC section 4](SPEC.md#4-customers-flow-1)).

### The idempotency key of a payment

`POST /api/invoices/{id}/payments` requires a header `Idempotency-Key` of 1–64 characters from `[A-Za-z0-9._-]` — missing is 422 `IDEMPOTENCY_KEY_REQUIRED` (`Falta la cabecera Idempotency-Key.`); a malformed one is 422 `VALIDATION_ERROR` with the field `Idempotency-Key`. The rules, all from [SPEC section 6](SPEC.md#6-invoices-and-payments-flow-3) and verified in the adapter code:

- The key is scoped to one invoice and remembered for 24 hours. Two requests with the same key and the same body produce **one** payment: the second gets the stored status and body back, plus the response header `Idempotency-Replayed: true`. This covers error answers too — a replay of a declined (402) or gateway-unavailable (503) payment replays that same 402/503 problem.
- Only an outcome that created a payment row consumes the key: `approved`, `declined`, `failed`. A request rejected earlier — no session, permission, unknown invoice, replay lookup, body validation, stale `version`, not payable, amount mismatch — does **not** consume it, so a corrected retry with the same key works.
- The same key with a **different** body is 422 `IDEMPOTENCY_KEY_REUSED` (`Esa clave de idempotencia ya se usó con otros datos.`). The comparison is an HMAC over the canonical body with the card number reduced to its last 4 digits and the CVC dropped — neither is ever stored or returned.
- Therefore: a retry after a decline (402) or a gateway failure (503) is a genuinely **new** attempt and must use a **new** key. Expecting a second decline with the same key to "replay" is a bug in the test; the UI renews its key after exactly those answers (part 1, section 6).

```bash
curl -s -b $J -H 'Content-Type: application/json' -H 'Idempotency-Key: pay-0001' \
  -d '{"method":"card","amount":"43.78",
       "card":{"number":"4242 4242 4242 4242","expiry":"12/30","cvc":"123"}}' \
  "$BASE/api/invoices/4/payments"      # 201 PaymentResult
curl -s -i -b $J -H 'Content-Type: application/json' -H 'Idempotency-Key: pay-0001' \
  -d '{"method":"card","amount":"43.78",
       "card":{"number":"4242 4242 4242 4242","expiry":"12/30","cvc":"123"}}' \
  "$BASE/api/invoices/4/payments"      # same 201 body, Idempotency-Replayed: true
```

The declined and unavailable outcomes do not change the invoice or the order. `4000 0000 0000 0002` (or a gateway fault) answers 402 with extra `payment_id` and `reason`, the attempt is stored and appears in the invoice's `payments` array; `4000 0000 0009 0003` answers 503 the same way with `reason: "GATEWAY_UNAVAILABLE"` ([SPEC section 6](SPEC.md#6-invoices-and-payments-flow-3) lists both problems verbatim).

### The lists: paging, search and filters

All four list endpoints share one shape ([SPEC section 8](SPEC.md#8-formats-and-conventions)): `{"items": [...], "page", "page_size": 20, "total"}`. The page size is fixed at 20 — the client cannot change it — `total` counts every match and not only the current page, the **default** order is `created_at` descending then `id` descending (every list can sort, next subsection), and asking for a page beyond the last one answers 200 with an empty `items` array. `page` is an integer from 1 to 1000000: a non-integer is 422 `INVALID_FORMAT` on `page`, any other value 422 `OUT_OF_RANGE`.

The search parameter `q` is the same on the three modules: trimmed, ignored when empty, at most 100 characters, no control characters, and **literal** — `%`, `_` and `\` mean themselves, there is no pattern syntax. The match is a "contains" that ignores case and accents (verified: `?q=ferreteria` finds the invoice of `Ferretería Fénix`):

| Endpoint | `q` matches | Filters |
|---|---|---|
| `GET /api/customers` | the name or the email | `status=active\|inactive` |
| `GET /api/orders` | the order number or the customer's name | `status=` one of `draft, confirmed, paid, shipped, cancelled`; `customer_id=` an integer id |
| `GET /api/invoices` | the invoice number or the snapshot customer name | `status=` one of `issued, paid, void`; `order_id=` an integer id |

A wrongly shaped filter value is a 422 too: `status` outside its list is `INVALID_FORMAT` on `status`; a non-integer `customer_id`/`order_id` is `INVALID_FORMAT`, and one outside 1–2147483647 is `OUT_OF_RANGE`. An id that simply does not exist is not an error: it matches nothing. Finally, `GET /api/products` is the whole read-only catalog in one answer (`{"items": [...]}`, ordered by `id` unless `sort` says otherwise, no paging) and `GET /api/settings` answers `{"tax_rate": "10.00"}`.

### Sorting the lists: `sort` and `direction`

Every list takes `sort` and `direction` on top of its filters, each optional:

| Endpoint | Allowed `sort` | Note |
|---|---|---|
| `GET /api/customers` | `created_at` (the default), `name`, `email` | `name` and `email` compare the normalized text below |
| `GET /api/orders` | `created_at` (the default), `number`, `customer` | `number` is the numeric part of the order number, compared as an integer; `customer` is the normalized customer's name |
| `GET /api/invoices` | `created_at` (the default), `number`, `customer`, `total` | `total` is the frozen total, compared as a number |
| `GET /api/products` | `id` (the default), `sku`, `name`, `price`, `stock` | `price` and `stock` compare as numbers |

The rules are one shape ([SPEC section 4](SPEC.md#4-customers-flow-1), and the same sentences for [orders](SPEC.md#5-orders-flow-2), [invoices](SPEC.md#6-invoices-and-payments-flow-3) and [products](SPEC.md#5-orders-flow-2)):

- `direction` is `asc` or `desc`; it defaults to `desc` for `created_at` and to `asc` for every other field (and it applies to `created_at` when `sort` is absent). Any other value of either parameter is 422 `VALIDATION_ERROR` with `INVALID_FORMAT` naming the field (`sort` or `direction`) — like every other bad query parameter.
- Ties break by `id`, in the same direction as the sort.
- Text fields compare the **normalized** text the same way `q` does (Unicode NFKD, combining marks removed, case-folded), so `Álvaro` sorts with `A` and upper case does not matter.
- The sort is applied after the filters and before the paging, so page 2 of a sorted list continues page 1, and the export routes validate these parameters the exact same way (the downloads give the files already sorted).

The first three values you get on the seed (verified against a local run of the API):

```bash
BASE=http://127.0.0.1:8000; J=/tmp/labapp-cookies
curl -s -b $J "$BASE/api/customers?sort=name&direction=asc"
# Acme Industrial S.A., Beta Comercial Ltda., Cafetería La Esquina
curl -s -b $J "$BASE/api/orders?sort=customer&direction=asc"
# PED-0001 (Acme Industrial S.A.), PED-0002 (Beta Comercial Ltda.), PED-0007 (Cafetería La Esquina)
curl -s -b $J "$BASE/api/invoices?sort=total&direction=asc"
# FAC-0002 (197.97), FAC-0001 (327.80), FAC-0003 (768.90)
curl -s -b $J "$BASE/api/products?sort=price&direction=asc"
# Cable HDMI 2 m (CB-010, 6.25), Mouse óptico (MS-200, 9.50), Tarjeta SD 128 GB (SD-128, 14.99)
curl -s -b $J "$BASE/api/customers?sort=surname"
# 422 {"code":"VALIDATION_ERROR", "errors":[{"field":"sort","code":"INVALID_FORMAT", ...}]}
```

### Download the lists as CSV

The three lists (customers, orders, invoices) download their whole result — every row the filters select, never one page — as a CSV file.

**In the UI.** An `Exportar CSV` link sits next to the filter controls of each list (`customers-list-export-link`, `orders-list-export-link`, `invoices-list-export-link`, `<a>` per [TESTIDS](TESTIDS.md)), and it renders in every state of the request, empty file included. It is a plain download link — `<a download>` to `/api/<resource>/export`, the client router is not involved — so `waitForEvent('download')` is the way a test digs in. Its `href` mirrors the applied state: `q`, `status`, and `sort` with `direction` whenever the sort is not the plain-list one (the orders list adds `customer_id`); **`page` never travels**, because the export answers every matching row.

```ts
// Illustrative, not run in CI.
const [download] = await Promise.all([
  page.waitForEvent("download"),
  page.getByTestId("customers-list-export-link").click(),
]);
expect(download.suggestedFilename()).toMatch(/^customers-\d{8}\.csv$/);
// The date in the file name is the UTC date of the application clock: move
// the clock with POST /__test__/clock (section 11) and the name moves too.
await download.saveAs("customers.csv");
```

**Over the API.** Same parameters as the list (`q`, `status`, `sort`, `direction`, plus `customer_id` for orders and `order_id` for invoices) with exactly the same validation — including the 422s of the previous subsection — and **no `page`**: sending one changes nothing, like any other unknown query parameter. Every signed-in role may export; without a session it is the usual 401. The answer is the file itself:

| Header | Value |
|---|---|
| `Content-Type` | `text/csv; charset=utf-8` |
| `Content-Disposition` | `attachment; filename="<resource>-<YYYYMMDD>.csv"` (`customers`, `orders` or `invoices`; the date is the UTC date of the **application clock**) |
| `Cache-Control` | `no-store` (plus the usual `nosniff` and `X-Request-Id`, section 10) |

The file is UTF-8 without a byte order mark; every line ends with CRLF, the last line included; the first line is the header, one of the three:

```text
id,name,email,phone,tax_id,address,status,created_at,updated_at
id,number,status,customer_id,customer_name,subtotal,tax_rate,tax,total,invoice_id,created_at,updated_at
id,number,status,order_id,order_number,customer_name,tax_id,subtotal,tax_rate,tax,total,created_at,updated_at
```

Money is a plain number with two decimals (`110.00`), the tax rate `10.00`, timestamps ISO 8601 UTC with a trailing `Z`, and the rows are in the order the list gives for the same `sort` and `direction` ([SPEC section 8](SPEC.md#8-formats-and-conventions)). The export of a filter that matches nothing is a file with the header only.

**The formula guard.** A text field that starts with `=`, `+`, `-`, `@`, a tab or a carriage return is written with a single quote in front (`'=1+1`), so a spreadsheet that opens the file never evaluates it as a formula. The seed gives one: Acme's phone `+1 555 010 0001` exports as `'+1 555 010 0001`. The quoting itself is RFC 4180: fields containing commas, double quotes or line breaks are wrapped in double quotes and a double quote inside is doubled.

**The recipe.** With the cookie jar of section 10:

```bash
BASE=http://127.0.0.1:8000; J=/tmp/labapp-cookies
curl -s -b $J -o customers.csv "$BASE/api/customers/export"
curl -s -b $J -o orders.csv    "$BASE/api/orders/export"
curl -s -b $J -o invoices.csv  "$BASE/api/invoices/export"
```

What lands (verified): `customers.csv` holds the header, then the ten customers in `created_at` descending order (so `Joyería Júpiter` first), the phone of Acme quoted as `'+1 555 010 0001`, and nothing else — no BOM, no page limit. Reading it back in a test:

```ts
// Illustrative, not run in CI. A minimal RFC 4180 parser: doubled quotes,
// commas, CRLF and LF. For real suites prefer a library, e.g. csv-parse.
import fs from "node:fs";

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += c;
  }
  if (cell !== "" || row.length > 0) { row.push(cell); rows.push(row); }
  return rows;
}

const lines = parseCsv(fs.readFileSync("customers.csv", "utf8"));
const [header, ...data] = lines;
expect(header).toEqual(
  ["id","name","email","phone","tax_id","address","status","created_at","updated_at"]);
expect(data.length).toBe(10);         // the list's total, not one page
expect(data[0][1]).toBe("Joyería Júpiter"); // the same order the UI shows
```

## 13. Isolating tests

A test that assumes a clean world will eventually meet someone else's data. The reset controls give three patterns; choose one per project and keep it.

**1. Reset before each suite (the local default).** One `POST /__test__/reset` in the suite setup, one cookie login after it, and the world is back to the seed even in the middle of a day of runs. The seed is a contract, so assertions can be exact: `PED-0002` confirmed with total `$121.00`, `FAC-0001` carrying one declined and one failed attempt. Trade-offs: you own the environment, because a reset is a bad neighbour online; and the reset wants a quiet system — a request that is still in flight can make the reset answer 409 `RESET_CONFLICT` (retry once) or 503 `LOCK_TIMEOUT`.

**2. Reset per worker against the shared online demo — unsafe.** The online dataset is one and shared: every visitor works on the same customers and orders (part 1, section 1). A reset from your worker erases the strangers' data in the middle of their run, and their writes erase your assumptions right back; between your reset and your next request, someone else's click can deactivate the very customer you just asserted on. If a suite needs resets online, it must be the only user of the demo — a staging URL, or the production URL outside public hours. Never assume a reset stays true for more than a request.

**3. Create your own data with unique names (the polite pattern for the shared demo).** Instead of relying on seed rows, log in once and create everything a test needs, with names and emails that cannot collide — a prefix per project plus a timestamp (`Contoso 1731…`, `prueba-1731099@example.test`). Find your rows again with the literal, accent-insensitive `q` (section 12) or by the ids the create answers give, and assert only on your own records. Trade-offs: the data accumulates until the nightly reset, your rows age down the list (the default ordering is `created_at` descending, section 12), and you still cannot stop others from touching *their* records — but yours are safe.

**Parallel runs and the per-IP rate limit.** Locally (`TEST_MODE=1`) there are no limits and each `mise run dev` process has its own memory, so parallel suites on different ports do not even share data. Online, the limits are per client IP: 120 requests per minute and 10 login attempts per minute shared by everything that runs from one machine — parallel workers count together and the group gets 429 `RATE_LIMITED` with a `Retry-After` header (the body member `retry_after` carries the same seconds). Two outs: spread the workers' requests below the limits, or add a valid `X-Test-Token` header to every request of an online suite — a token-bearing request is exempt from the limits even then (section 11).

## 14. The online demo

Everything above describes the local server. The demo lives on the project's Vercel URL and **is not deployed yet**: the configuration exists ([docs/DEPLOYMENT.md](DEPLOYMENT.md)) but the first deployment is still pending, so until it happens there is no online URL to automate against. When it arrives, this changes from local:

| Aspect | Local | Online |
|---|---|---|
| Controls guard | `TEST_MODE=1`: no token needed | `TEST_MODE=0`: 404 without `X-Test-Token: <TEST_TOKEN>` |
| Data | in memory, from the seed, lost on restart | PostgreSQL, **one shared dataset** all visitors move |
| Rate limits | off | on: 120 requests/min and 10 logins/min per client IP (429 `RATE_LIMITED`) |
| Nightly state | `mise run dev` restarts clean | a GitHub Actions workflow resets at **03:17 UTC** |
| Cold starts | none | possible: the first request after a quiet period can be slow (warm it with `GET /api/health`) |

Three extra facts about the online world ([docs/DEPLOYMENT.md](DEPLOYMENT.md)):

- The nightly reset workflow ([`nightly-reset.yml`](../.github/workflows/nightly-reset.yml)) can only run once the test controls are deployed; it needs the repository settings `DEMO_URL` (variable) and `TEST_TOKEN` (secret), counts only an exact HTTP 200 of `POST /__test__/reset` as success (a redirect fails and is never followed, so the token cannot leave the configured host), and can be started by hand from the Actions tab. Note for a long-lived repo: GitHub disables scheduled workflows after 60 days of inactivity — the nightly reset then stops silently until the next push or a re-enable.
- Preview deployments get a URL of their own and answer the same API; they share the production database unless the Neon integration carves a branch per preview, so treat preview data as even less stable.
- The origin check accepts each preview's Vercel origin automatically, so API or UI tests against a preview URL need no extra header handling — requests without an `Origin` never raise the 403 at all.

## 15. What to read next

- [openapi.json](openapi.json) — the committed contract; import it into your HTTP client instead of re-typing requests. The command that regenerates it when the API changes is `cd backend && uv run python -m app.cli openapi --output ../docs/openapi.json`.
- [SPEC.md](SPEC.md) — sections [3](SPEC.md#3-authentication-and-sessions) (sessions, the origin rule, the rate limits), [5](SPEC.md#5-orders-flow-2) (orders and concurrency), [6](SPEC.md#6-invoices-and-payments-flow-3) (invoices, payments, idempotency), [7](SPEC.md#7-errors-and-validation-order) (the stable error codes) and [9](SPEC.md#9-seed-data) (what a reset and a seed restore).
- In this guide, the machinery of the four lists: [Sort the four lists](#sort-the-four-lists) (the UI side); [Sorting the lists: sort and direction](#sorting-the-lists-sort-and-direction) and [Download the lists as CSV](#download-the-lists-as-csv) in section 12, and [The headers of every API answer](#the-headers-of-every-api-answer) in section 10.
- [SEED.md](SEED.md) — the exact data every recipe above leans on.
- [backend/README.md](../backend/README.md) — the same controls from the implementer's side ("Test controls", "Request controls", "OpenAPI contract").
- [DEPLOYMENT.md](DEPLOYMENT.md) and [DEVELOPMENT.md](DEVELOPMENT.md) — where the demo lives and how to start the stack locally.
- Part 1 of this guide, for the UI side of the same flows.

- [PRACTICE.md](PRACTICE.md) — the catalog of practice scenarios: what to test, row by row, with the exact expected result from the specification, so every recipe of this guide has a scenario to land on.
