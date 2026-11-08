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
