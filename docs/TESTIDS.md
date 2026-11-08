# Test id catalog

Every `data-testid` found in each audited state, with the element that carries it (its tag, the type of an input and
an explicit `role`, not the implicit one). It is **generated**: `node tools/audit/browser-audit.mjs --catalog docs/TESTIDS.md`
against a freshly seeded application, and CI fails when the committed copy is out of date.

- Elements that are not visible but carry an id are included.
- A number at the end of an id is the id of a record of the seed data (`customers-list-row-3`), or a position in a list
  (`auth-login-demo-item-2`).
- Only the states of `tools/audit/states.json` are covered. An id that appears only after an interaction (a field error
  after a failed submit, a confirmation message) is not here until a state reaches it; the grammar still applies to it
  ([TESTABILITY.md](TESTABILITY.md)).
- The ids of the app shell that every logged-in state has are listed once, under "App shell".

## App shell

Present in every logged-in state.

| Test id | Element |
|---|---|
| `app-logout-button` | `button` |
| `app-nav-customers-link` | `a` |
| `app-nav-home-link` | `a` |
| `app-nav-invoices-link` | `a` |
| `app-nav-orders-link` | `a` |
| `app-nav-products-link` | `a` |
| `app-nav-settings-link` | `a` |
| `app-skip-link` | `a` |
| `app-theme-select` | `select` |
| `app-user-name-text` | `p` |
| `app-user-role-text` | `p` |

## login

`/login`, no session. Page title: `Iniciar sesión · LabApp`.

| Test id | Element |
|---|---|
| `auth-login-demo-item-1` | `li` |
| `auth-login-demo-item-2` | `li` |
| `auth-login-demo-item-3` | `li` |
| `auth-login-demo-item-4` | `li` |
| `auth-login-demo-list` | `ul` |
| `auth-login-demo-password-text` | `p` |
| `auth-login-demo-title-text` | `p` |
| `auth-login-email-input` | `input[type=email]` |
| `auth-login-form` | `form` |
| `auth-login-heading` | `h1` |
| `auth-login-notice-text` | `p` |
| `auth-login-password-input` | `input[type=password]` |
| `auth-login-skip-link` | `a` |
| `auth-login-submit-button` | `button` |
| `auth-login-tagline-text` | `p` |
| `auth-login-theme-select` | `select` |

## login-expired

`/login?expired=1`, no session. Page title: `Iniciar sesión · LabApp`.

| Test id | Element |
|---|---|
| `auth-login-demo-item-1` | `li` |
| `auth-login-demo-item-2` | `li` |
| `auth-login-demo-item-3` | `li` |
| `auth-login-demo-item-4` | `li` |
| `auth-login-demo-list` | `ul` |
| `auth-login-demo-password-text` | `p` |
| `auth-login-demo-title-text` | `p` |
| `auth-login-email-input` | `input[type=email]` |
| `auth-login-expired-alert` | `p[role=alert]` |
| `auth-login-form` | `form` |
| `auth-login-heading` | `h1` |
| `auth-login-notice-text` | `p` |
| `auth-login-password-input` | `input[type=password]` |
| `auth-login-skip-link` | `a` |
| `auth-login-submit-button` | `button` |
| `auth-login-tagline-text` | `p` |
| `auth-login-theme-select` | `select` |

## not-found

`/no-such-page`, no session. Page title: `Página no encontrada · LabApp`.

| Test id | Element |
|---|---|
| `app-notfound-heading` | `h1` |
| `app-notfound-home-link` | `a` |

## home

`/`, logged in as `sales@labapp.test`. Page title: `Resumen · LabApp`.

| Test id | Element |
|---|---|
| `app-home-greeting-text` | `p` |
| `app-home-heading` | `h1` |
| `home-customers-active-count-text` | `span` |
| `home-customers-active-link` | `a` |
| `home-customers-heading` | `h2` |
| `home-customers-inactive-count-text` | `span` |
| `home-customers-inactive-link` | `a` |
| `home-invoices-heading` | `h2` |
| `home-invoices-issued-count-text` | `span` |
| `home-invoices-issued-link` | `a` |
| `home-invoices-paid-count-text` | `span` |
| `home-invoices-paid-link` | `a` |
| `home-invoices-void-count-text` | `span` |
| `home-invoices-void-link` | `a` |
| `home-orders-cancelled-count-text` | `span` |
| `home-orders-cancelled-link` | `a` |
| `home-orders-confirmed-count-text` | `span` |
| `home-orders-confirmed-link` | `a` |
| `home-orders-draft-count-text` | `span` |
| `home-orders-draft-link` | `a` |
| `home-orders-heading` | `h2` |
| `home-orders-paid-count-text` | `span` |
| `home-orders-paid-link` | `a` |
| `home-orders-shipped-count-text` | `span` |
| `home-orders-shipped-link` | `a` |

## customers-list

`/customers`, logged in as `sales@labapp.test`. Page title: `Clientes · LabApp`.

| Test id | Element |
|---|---|
| `customers-list-email-cell-1` | `td` |
| `customers-list-email-cell-2` | `td` |
| `customers-list-email-cell-3` | `td` |
| `customers-list-email-cell-4` | `td` |
| `customers-list-email-cell-5` | `td` |
| `customers-list-email-cell-6` | `td` |
| `customers-list-email-cell-7` | `td` |
| `customers-list-email-cell-8` | `td` |
| `customers-list-email-cell-9` | `td` |
| `customers-list-email-cell-10` | `td` |
| `customers-list-footer-item` | `div` |
| `customers-list-heading` | `h1` |
| `customers-list-name-cell-1` | `td` |
| `customers-list-name-cell-2` | `td` |
| `customers-list-name-cell-3` | `td` |
| `customers-list-name-cell-4` | `td` |
| `customers-list-name-cell-5` | `td` |
| `customers-list-name-cell-6` | `td` |
| `customers-list-name-cell-7` | `td` |
| `customers-list-name-cell-8` | `td` |
| `customers-list-name-cell-9` | `td` |
| `customers-list-name-cell-10` | `td` |
| `customers-list-new-link` | `a` |
| `customers-list-next-button` | `button` |
| `customers-list-page-text` | `p` |
| `customers-list-prev-button` | `button` |
| `customers-list-row-1` | `tr` |
| `customers-list-row-2` | `tr` |
| `customers-list-row-3` | `tr` |
| `customers-list-row-4` | `tr` |
| `customers-list-row-5` | `tr` |
| `customers-list-row-6` | `tr` |
| `customers-list-row-7` | `tr` |
| `customers-list-row-8` | `tr` |
| `customers-list-row-9` | `tr` |
| `customers-list-row-10` | `tr` |
| `customers-list-scroll-region` | `div[role=region]` |
| `customers-list-search-button` | `button` |
| `customers-list-search-form` | `form` |
| `customers-list-search-input` | `input[type=text]` |
| `customers-list-state-cell-1` | `td` |
| `customers-list-state-cell-2` | `td` |
| `customers-list-state-cell-3` | `td` |
| `customers-list-state-cell-4` | `td` |
| `customers-list-state-cell-5` | `td` |
| `customers-list-state-cell-6` | `td` |
| `customers-list-state-cell-7` | `td` |
| `customers-list-state-cell-8` | `td` |
| `customers-list-state-cell-9` | `td` |
| `customers-list-state-cell-10` | `td` |
| `customers-list-status-select` | `select` |
| `customers-list-table` | `table` |
| `customers-list-taxid-cell-1` | `td` |
| `customers-list-taxid-cell-2` | `td` |
| `customers-list-taxid-cell-3` | `td` |
| `customers-list-taxid-cell-4` | `td` |
| `customers-list-taxid-cell-5` | `td` |
| `customers-list-taxid-cell-6` | `td` |
| `customers-list-taxid-cell-7` | `td` |
| `customers-list-taxid-cell-8` | `td` |
| `customers-list-taxid-cell-9` | `td` |
| `customers-list-taxid-cell-10` | `td` |
| `customers-list-total-text` | `p` |
| `customers-list-view-link-1` | `a` |
| `customers-list-view-link-2` | `a` |
| `customers-list-view-link-3` | `a` |
| `customers-list-view-link-4` | `a` |
| `customers-list-view-link-5` | `a` |
| `customers-list-view-link-6` | `a` |
| `customers-list-view-link-7` | `a` |
| `customers-list-view-link-8` | `a` |
| `customers-list-view-link-9` | `a` |
| `customers-list-view-link-10` | `a` |

## customers-list-readonly

`/customers`, logged in as `readonly@labapp.test`. Page title: `Clientes · LabApp`.

| Test id | Element |
|---|---|
| `customers-list-email-cell-1` | `td` |
| `customers-list-email-cell-2` | `td` |
| `customers-list-email-cell-3` | `td` |
| `customers-list-email-cell-4` | `td` |
| `customers-list-email-cell-5` | `td` |
| `customers-list-email-cell-6` | `td` |
| `customers-list-email-cell-7` | `td` |
| `customers-list-email-cell-8` | `td` |
| `customers-list-email-cell-9` | `td` |
| `customers-list-email-cell-10` | `td` |
| `customers-list-footer-item` | `div` |
| `customers-list-heading` | `h1` |
| `customers-list-name-cell-1` | `td` |
| `customers-list-name-cell-2` | `td` |
| `customers-list-name-cell-3` | `td` |
| `customers-list-name-cell-4` | `td` |
| `customers-list-name-cell-5` | `td` |
| `customers-list-name-cell-6` | `td` |
| `customers-list-name-cell-7` | `td` |
| `customers-list-name-cell-8` | `td` |
| `customers-list-name-cell-9` | `td` |
| `customers-list-name-cell-10` | `td` |
| `customers-list-next-button` | `button` |
| `customers-list-page-text` | `p` |
| `customers-list-prev-button` | `button` |
| `customers-list-row-1` | `tr` |
| `customers-list-row-2` | `tr` |
| `customers-list-row-3` | `tr` |
| `customers-list-row-4` | `tr` |
| `customers-list-row-5` | `tr` |
| `customers-list-row-6` | `tr` |
| `customers-list-row-7` | `tr` |
| `customers-list-row-8` | `tr` |
| `customers-list-row-9` | `tr` |
| `customers-list-row-10` | `tr` |
| `customers-list-scroll-region` | `div[role=region]` |
| `customers-list-search-button` | `button` |
| `customers-list-search-form` | `form` |
| `customers-list-search-input` | `input[type=text]` |
| `customers-list-state-cell-1` | `td` |
| `customers-list-state-cell-2` | `td` |
| `customers-list-state-cell-3` | `td` |
| `customers-list-state-cell-4` | `td` |
| `customers-list-state-cell-5` | `td` |
| `customers-list-state-cell-6` | `td` |
| `customers-list-state-cell-7` | `td` |
| `customers-list-state-cell-8` | `td` |
| `customers-list-state-cell-9` | `td` |
| `customers-list-state-cell-10` | `td` |
| `customers-list-status-select` | `select` |
| `customers-list-table` | `table` |
| `customers-list-taxid-cell-1` | `td` |
| `customers-list-taxid-cell-2` | `td` |
| `customers-list-taxid-cell-3` | `td` |
| `customers-list-taxid-cell-4` | `td` |
| `customers-list-taxid-cell-5` | `td` |
| `customers-list-taxid-cell-6` | `td` |
| `customers-list-taxid-cell-7` | `td` |
| `customers-list-taxid-cell-8` | `td` |
| `customers-list-taxid-cell-9` | `td` |
| `customers-list-taxid-cell-10` | `td` |
| `customers-list-total-text` | `p` |
| `customers-list-view-link-1` | `a` |
| `customers-list-view-link-2` | `a` |
| `customers-list-view-link-3` | `a` |
| `customers-list-view-link-4` | `a` |
| `customers-list-view-link-5` | `a` |
| `customers-list-view-link-6` | `a` |
| `customers-list-view-link-7` | `a` |
| `customers-list-view-link-8` | `a` |
| `customers-list-view-link-9` | `a` |
| `customers-list-view-link-10` | `a` |

## customers-detail

`/customers/2`, logged in as `sales@labapp.test`. Page title: `Cliente Beta Comercial Ltda. · LabApp`.

| Test id | Element |
|---|---|
| `customers-deactivate-back-button` | `button` |
| `customers-deactivate-confirm-button` | `button` |
| `customers-deactivate-confirm-dialog` | `dialog` |
| `customers-deactivate-message-text` | `p` |
| `customers-deactivate-title-heading` | `h2` |
| `customers-detail-address-text` | `dd` |
| `customers-detail-back-link` | `a` |
| `customers-detail-deactivate-button` | `button` |
| `customers-detail-edit-link` | `a` |
| `customers-detail-email-text` | `dd` |
| `customers-detail-heading` | `h1` |
| `customers-detail-name-text` | `dd` |
| `customers-detail-neworder-link` | `a` |
| `customers-detail-orders-heading` | `h2` |
| `customers-detail-orders-link` | `a` |
| `customers-detail-phone-text` | `dd` |
| `customers-detail-state-status` | `dd` |
| `customers-detail-taxid-text` | `dd` |

## customers-detail-inactive

`/customers/5`, logged in as `sales@labapp.test`. Page title: `Cliente Estudio Épsilon · LabApp`.

| Test id | Element |
|---|---|
| `customers-deactivate-back-button` | `button` |
| `customers-deactivate-confirm-button` | `button` |
| `customers-deactivate-confirm-dialog` | `dialog` |
| `customers-deactivate-message-text` | `p` |
| `customers-deactivate-title-heading` | `h2` |
| `customers-detail-address-text` | `dd` |
| `customers-detail-back-link` | `a` |
| `customers-detail-edit-link` | `a` |
| `customers-detail-email-text` | `dd` |
| `customers-detail-heading` | `h1` |
| `customers-detail-name-text` | `dd` |
| `customers-detail-orders-heading` | `h2` |
| `customers-detail-orders-link` | `a` |
| `customers-detail-phone-text` | `dd` |
| `customers-detail-reactivate-button` | `button` |
| `customers-detail-state-status` | `dd` |
| `customers-detail-taxid-text` | `dd` |

## customers-deactivate-dialog

`/customers/2`, logged in as `sales@labapp.test`. Page title: `Cliente Beta Comercial Ltda. · LabApp`.

| Test id | Element |
|---|---|
| `customers-deactivate-back-button` | `button` |
| `customers-deactivate-confirm-button` | `button` |
| `customers-deactivate-confirm-dialog` | `dialog` |
| `customers-deactivate-message-text` | `p` |
| `customers-deactivate-title-heading` | `h2` |
| `customers-detail-address-text` | `dd` |
| `customers-detail-back-link` | `a` |
| `customers-detail-deactivate-button` | `button` |
| `customers-detail-edit-link` | `a` |
| `customers-detail-email-text` | `dd` |
| `customers-detail-heading` | `h1` |
| `customers-detail-name-text` | `dd` |
| `customers-detail-neworder-link` | `a` |
| `customers-detail-orders-heading` | `h2` |
| `customers-detail-orders-link` | `a` |
| `customers-detail-phone-text` | `dd` |
| `customers-detail-state-status` | `dd` |
| `customers-detail-taxid-text` | `dd` |

## customers-new

`/customers/new`, logged in as `sales@labapp.test`. Page title: `Nuevo cliente · LabApp`.

| Test id | Element |
|---|---|
| `customers-customer-form` | `form` |
| `customers-form-address-textarea` | `textarea` |
| `customers-form-cancel-link` | `a` |
| `customers-form-email-input` | `input[type=email]` |
| `customers-form-heading` | `h1` |
| `customers-form-name-input` | `input[type=text]` |
| `customers-form-phone-input` | `input[type=text]` |
| `customers-form-submit-button` | `button` |
| `customers-form-taxid-input` | `input[type=text]` |

## customers-edit

`/customers/2/edit`, logged in as `sales@labapp.test`. Page title: `Editar cliente · LabApp`.

| Test id | Element |
|---|---|
| `customers-customer-form` | `form` |
| `customers-form-address-textarea` | `textarea` |
| `customers-form-cancel-link` | `a` |
| `customers-form-email-input` | `input[type=email]` |
| `customers-form-heading` | `h1` |
| `customers-form-name-input` | `input[type=text]` |
| `customers-form-phone-input` | `input[type=text]` |
| `customers-form-submit-button` | `button` |
| `customers-form-taxid-input` | `input[type=text]` |

## customers-not-found

`/customers/999`, logged in as `sales@labapp.test`. Page title: `Clientes · LabApp`.

| Test id | Element |
|---|---|
| `customers-detail-back-link` | `a` |
| `customers-detail-error-alert` | `p[role=alert]` |

## products-list

`/products`, logged in as `readonly@labapp.test`. Page title: `Productos · LabApp`.

| Test id | Element |
|---|---|
| `products-list-footer-item` | `p` |
| `products-list-heading` | `h1` |
| `products-list-name-cell-1` | `td` |
| `products-list-name-cell-2` | `td` |
| `products-list-name-cell-3` | `td` |
| `products-list-name-cell-4` | `td` |
| `products-list-name-cell-5` | `td` |
| `products-list-name-cell-6` | `td` |
| `products-list-name-cell-7` | `td` |
| `products-list-name-cell-8` | `td` |
| `products-list-name-cell-9` | `td` |
| `products-list-name-cell-10` | `td` |
| `products-list-name-cell-11` | `td` |
| `products-list-name-cell-12` | `td` |
| `products-list-name-cell-13` | `td` |
| `products-list-name-cell-14` | `td` |
| `products-list-name-cell-15` | `td` |
| `products-list-price-cell-1` | `td` |
| `products-list-price-cell-2` | `td` |
| `products-list-price-cell-3` | `td` |
| `products-list-price-cell-4` | `td` |
| `products-list-price-cell-5` | `td` |
| `products-list-price-cell-6` | `td` |
| `products-list-price-cell-7` | `td` |
| `products-list-price-cell-8` | `td` |
| `products-list-price-cell-9` | `td` |
| `products-list-price-cell-10` | `td` |
| `products-list-price-cell-11` | `td` |
| `products-list-price-cell-12` | `td` |
| `products-list-price-cell-13` | `td` |
| `products-list-price-cell-14` | `td` |
| `products-list-price-cell-15` | `td` |
| `products-list-row-1` | `tr` |
| `products-list-row-2` | `tr` |
| `products-list-row-3` | `tr` |
| `products-list-row-4` | `tr` |
| `products-list-row-5` | `tr` |
| `products-list-row-6` | `tr` |
| `products-list-row-7` | `tr` |
| `products-list-row-8` | `tr` |
| `products-list-row-9` | `tr` |
| `products-list-row-10` | `tr` |
| `products-list-row-11` | `tr` |
| `products-list-row-12` | `tr` |
| `products-list-row-13` | `tr` |
| `products-list-row-14` | `tr` |
| `products-list-row-15` | `tr` |
| `products-list-scroll-region` | `div[role=region]` |
| `products-list-search-button` | `button` |
| `products-list-search-form` | `form` |
| `products-list-search-input` | `input[type=text]` |
| `products-list-sku-cell-1` | `td` |
| `products-list-sku-cell-2` | `td` |
| `products-list-sku-cell-3` | `td` |
| `products-list-sku-cell-4` | `td` |
| `products-list-sku-cell-5` | `td` |
| `products-list-sku-cell-6` | `td` |
| `products-list-sku-cell-7` | `td` |
| `products-list-sku-cell-8` | `td` |
| `products-list-sku-cell-9` | `td` |
| `products-list-sku-cell-10` | `td` |
| `products-list-sku-cell-11` | `td` |
| `products-list-sku-cell-12` | `td` |
| `products-list-sku-cell-13` | `td` |
| `products-list-sku-cell-14` | `td` |
| `products-list-sku-cell-15` | `td` |
| `products-list-stock-cell-1` | `td` |
| `products-list-stock-cell-2` | `td` |
| `products-list-stock-cell-3` | `td` |
| `products-list-stock-cell-4` | `td` |
| `products-list-stock-cell-5` | `td` |
| `products-list-stock-cell-6` | `td` |
| `products-list-stock-cell-7` | `td` |
| `products-list-stock-cell-8` | `td` |
| `products-list-stock-cell-9` | `td` |
| `products-list-stock-cell-10` | `td` |
| `products-list-stock-cell-11` | `td` |
| `products-list-stock-cell-12` | `td` |
| `products-list-stock-cell-13` | `td` |
| `products-list-stock-cell-14` | `td` |
| `products-list-stock-cell-15` | `td` |
| `products-list-stockstate-status-7` | `span` |
| `products-list-stockstate-status-9` | `span` |
| `products-list-table` | `table` |

## products-search

`/products?q=cable`, logged in as `sales@labapp.test`. Page title: `Productos · LabApp`.

| Test id | Element |
|---|---|
| `products-list-footer-item` | `p` |
| `products-list-heading` | `h1` |
| `products-list-name-cell-6` | `td` |
| `products-list-price-cell-6` | `td` |
| `products-list-row-6` | `tr` |
| `products-list-scroll-region` | `div[role=region]` |
| `products-list-search-button` | `button` |
| `products-list-search-form` | `form` |
| `products-list-search-input` | `input[type=text]` |
| `products-list-sku-cell-6` | `td` |
| `products-list-stock-cell-6` | `td` |
| `products-list-table` | `table` |

## orders-list

`/orders`, logged in as `sales@labapp.test`. Page title: `Pedidos · LabApp`.

| Test id | Element |
|---|---|
| `orders-list-created-cell-1` | `td` |
| `orders-list-created-cell-2` | `td` |
| `orders-list-created-cell-3` | `td` |
| `orders-list-created-cell-4` | `td` |
| `orders-list-created-cell-5` | `td` |
| `orders-list-created-cell-6` | `td` |
| `orders-list-created-cell-7` | `td` |
| `orders-list-customer-cell-1` | `td` |
| `orders-list-customer-cell-2` | `td` |
| `orders-list-customer-cell-3` | `td` |
| `orders-list-customer-cell-4` | `td` |
| `orders-list-customer-cell-5` | `td` |
| `orders-list-customer-cell-6` | `td` |
| `orders-list-customer-cell-7` | `td` |
| `orders-list-footer-item` | `div` |
| `orders-list-heading` | `h1` |
| `orders-list-lines-cell-1` | `td` |
| `orders-list-lines-cell-2` | `td` |
| `orders-list-lines-cell-3` | `td` |
| `orders-list-lines-cell-4` | `td` |
| `orders-list-lines-cell-5` | `td` |
| `orders-list-lines-cell-6` | `td` |
| `orders-list-lines-cell-7` | `td` |
| `orders-list-new-link` | `a` |
| `orders-list-next-button` | `button` |
| `orders-list-number-cell-1` | `td` |
| `orders-list-number-cell-2` | `td` |
| `orders-list-number-cell-3` | `td` |
| `orders-list-number-cell-4` | `td` |
| `orders-list-number-cell-5` | `td` |
| `orders-list-number-cell-6` | `td` |
| `orders-list-number-cell-7` | `td` |
| `orders-list-page-text` | `p` |
| `orders-list-prev-button` | `button` |
| `orders-list-row-1` | `tr` |
| `orders-list-row-2` | `tr` |
| `orders-list-row-3` | `tr` |
| `orders-list-row-4` | `tr` |
| `orders-list-row-5` | `tr` |
| `orders-list-row-6` | `tr` |
| `orders-list-row-7` | `tr` |
| `orders-list-scroll-region` | `div[role=region]` |
| `orders-list-search-button` | `button` |
| `orders-list-search-form` | `form` |
| `orders-list-search-input` | `input[type=text]` |
| `orders-list-state-cell-1` | `td` |
| `orders-list-state-cell-2` | `td` |
| `orders-list-state-cell-3` | `td` |
| `orders-list-state-cell-4` | `td` |
| `orders-list-state-cell-5` | `td` |
| `orders-list-state-cell-6` | `td` |
| `orders-list-state-cell-7` | `td` |
| `orders-list-status-select` | `select` |
| `orders-list-table` | `table` |
| `orders-list-total-cell-1` | `td` |
| `orders-list-total-cell-2` | `td` |
| `orders-list-total-cell-3` | `td` |
| `orders-list-total-cell-4` | `td` |
| `orders-list-total-cell-5` | `td` |
| `orders-list-total-cell-6` | `td` |
| `orders-list-total-cell-7` | `td` |
| `orders-list-total-text` | `p` |
| `orders-list-view-link-1` | `a` |
| `orders-list-view-link-2` | `a` |
| `orders-list-view-link-3` | `a` |
| `orders-list-view-link-4` | `a` |
| `orders-list-view-link-5` | `a` |
| `orders-list-view-link-6` | `a` |
| `orders-list-view-link-7` | `a` |

## orders-new

`/orders/new`, logged in as `sales@labapp.test`. Page title: `Nuevo pedido · LabApp`.

| Test id | Element |
|---|---|
| `orders-customer-form` | `form` |
| `orders-form-cancel-link` | `a` |
| `orders-form-customer-select` | `select` |
| `orders-form-customer-text` | `p` |
| `orders-form-customersearch-button` | `button` |
| `orders-form-customersearch-form` | `form` |
| `orders-form-customersearch-input` | `input[type=text]` |
| `orders-form-heading` | `h1` |
| `orders-form-submit-button` | `button` |

## orders-detail-draft

`/orders/1`, logged in as `sales@labapp.test`. Page title: `Pedido PED-0001 · LabApp`.

| Test id | Element |
|---|---|
| `orders-cancel-back-button` | `button` |
| `orders-cancel-confirm-button` | `button` |
| `orders-cancel-confirm-dialog` | `dialog` |
| `orders-cancel-message-text` | `p` |
| `orders-cancel-title-heading` | `h2` |
| `orders-detail-addline-form` | `form` |
| `orders-detail-addline-heading` | `h2` |
| `orders-detail-addline-product-select` | `select` |
| `orders-detail-addline-quantity-input` | `input[type=number]` |
| `orders-detail-addline-submit-button` | `button` |
| `orders-detail-back-link` | `a` |
| `orders-detail-cancel-button` | `button` |
| `orders-detail-changecustomer-button` | `button` |
| `orders-detail-changecustomer-form` | `form` |
| `orders-detail-changecustomer-search-button` | `button` |
| `orders-detail-changecustomer-search-form` | `form` |
| `orders-detail-changecustomer-search-input` | `input[type=text]` |
| `orders-detail-changecustomer-select` | `select` |
| `orders-detail-changecustomer-submit-button` | `button` |
| `orders-detail-confirm-button` | `button` |
| `orders-detail-created-text` | `dd` |
| `orders-detail-customer-link` | `a` |
| `orders-detail-heading` | `h1` |
| `orders-detail-line-form-1` | `form` |
| `orders-detail-line-price-cell-1` | `td` |
| `orders-detail-line-product-cell-1` | `td` |
| `orders-detail-line-quantity-cell-1` | `td` |
| `orders-detail-line-quantity-input-1` | `input[type=number]` |
| `orders-detail-line-remove-button-1` | `button` |
| `orders-detail-line-row-1` | `tr` |
| `orders-detail-line-save-button-1` | `button` |
| `orders-detail-line-total-cell-1` | `td` |
| `orders-detail-lines-heading` | `h2` |
| `orders-detail-lines-scroll-region` | `div[role=region]` |
| `orders-detail-lines-table` | `table` |
| `orders-detail-preview-text` | `p` |
| `orders-detail-state-status` | `span` |
| `orders-detail-subtotal-text` | `span` |
| `orders-detail-tax-text` | `span` |
| `orders-detail-taxrate-text` | `span` |
| `orders-detail-total-text` | `span` |
| `orders-detail-updated-text` | `dd` |

## orders-cancel-dialog

`/orders/3`, logged in as `sales@labapp.test`. Page title: `Pedido PED-0003 · LabApp`.

| Test id | Element |
|---|---|
| `orders-cancel-back-button` | `button` |
| `orders-cancel-confirm-button` | `button` |
| `orders-cancel-confirm-dialog` | `dialog` |
| `orders-cancel-message-text` | `p` |
| `orders-cancel-title-heading` | `h2` |
| `orders-detail-back-link` | `a` |
| `orders-detail-cancel-button` | `button` |
| `orders-detail-created-text` | `dd` |
| `orders-detail-customer-link` | `a` |
| `orders-detail-heading` | `h1` |
| `orders-detail-invoice-link` | `a` |
| `orders-detail-line-price-cell-4` | `td` |
| `orders-detail-line-product-cell-4` | `td` |
| `orders-detail-line-quantity-cell-4` | `td` |
| `orders-detail-line-row-4` | `tr` |
| `orders-detail-line-total-cell-4` | `td` |
| `orders-detail-lines-heading` | `h2` |
| `orders-detail-lines-scroll-region` | `div[role=region]` |
| `orders-detail-lines-table` | `table` |
| `orders-detail-state-status` | `span` |
| `orders-detail-subtotal-text` | `span` |
| `orders-detail-tax-text` | `span` |
| `orders-detail-taxrate-text` | `span` |
| `orders-detail-total-text` | `span` |
| `orders-detail-updated-text` | `dd` |

## orders-detail-confirmed

`/orders/3`, logged in as `sales@labapp.test`. Page title: `Pedido PED-0003 · LabApp`.

| Test id | Element |
|---|---|
| `orders-cancel-back-button` | `button` |
| `orders-cancel-confirm-button` | `button` |
| `orders-cancel-confirm-dialog` | `dialog` |
| `orders-cancel-message-text` | `p` |
| `orders-cancel-title-heading` | `h2` |
| `orders-detail-back-link` | `a` |
| `orders-detail-cancel-button` | `button` |
| `orders-detail-created-text` | `dd` |
| `orders-detail-customer-link` | `a` |
| `orders-detail-heading` | `h1` |
| `orders-detail-invoice-link` | `a` |
| `orders-detail-line-price-cell-4` | `td` |
| `orders-detail-line-product-cell-4` | `td` |
| `orders-detail-line-quantity-cell-4` | `td` |
| `orders-detail-line-row-4` | `tr` |
| `orders-detail-line-total-cell-4` | `td` |
| `orders-detail-lines-heading` | `h2` |
| `orders-detail-lines-scroll-region` | `div[role=region]` |
| `orders-detail-lines-table` | `table` |
| `orders-detail-state-status` | `span` |
| `orders-detail-subtotal-text` | `span` |
| `orders-detail-tax-text` | `span` |
| `orders-detail-taxrate-text` | `span` |
| `orders-detail-total-text` | `span` |
| `orders-detail-updated-text` | `dd` |

## orders-detail-shipped

`/orders/5`, logged in as `sales@labapp.test`. Page title: `Pedido PED-0005 · LabApp`.

| Test id | Element |
|---|---|
| `orders-cancel-back-button` | `button` |
| `orders-cancel-confirm-button` | `button` |
| `orders-cancel-confirm-dialog` | `dialog` |
| `orders-cancel-message-text` | `p` |
| `orders-cancel-title-heading` | `h2` |
| `orders-detail-back-link` | `a` |
| `orders-detail-created-text` | `dd` |
| `orders-detail-customer-link` | `a` |
| `orders-detail-heading` | `h1` |
| `orders-detail-invoice-link` | `a` |
| `orders-detail-line-price-cell-6` | `td` |
| `orders-detail-line-product-cell-6` | `td` |
| `orders-detail-line-quantity-cell-6` | `td` |
| `orders-detail-line-row-6` | `tr` |
| `orders-detail-line-total-cell-6` | `td` |
| `orders-detail-lines-heading` | `h2` |
| `orders-detail-lines-scroll-region` | `div[role=region]` |
| `orders-detail-lines-table` | `table` |
| `orders-detail-state-status` | `span` |
| `orders-detail-subtotal-text` | `span` |
| `orders-detail-tax-text` | `span` |
| `orders-detail-taxrate-text` | `span` |
| `orders-detail-total-text` | `span` |
| `orders-detail-updated-text` | `dd` |

## orders-detail-cancelled

`/orders/6`, logged in as `sales@labapp.test`. Page title: `Pedido PED-0006 · LabApp`.

| Test id | Element |
|---|---|
| `orders-cancel-back-button` | `button` |
| `orders-cancel-confirm-button` | `button` |
| `orders-cancel-confirm-dialog` | `dialog` |
| `orders-cancel-message-text` | `p` |
| `orders-cancel-title-heading` | `h2` |
| `orders-detail-back-link` | `a` |
| `orders-detail-created-text` | `dd` |
| `orders-detail-customer-link` | `a` |
| `orders-detail-heading` | `h1` |
| `orders-detail-line-price-cell-7` | `td` |
| `orders-detail-line-product-cell-7` | `td` |
| `orders-detail-line-quantity-cell-7` | `td` |
| `orders-detail-line-row-7` | `tr` |
| `orders-detail-line-total-cell-7` | `td` |
| `orders-detail-lines-heading` | `h2` |
| `orders-detail-lines-scroll-region` | `div[role=region]` |
| `orders-detail-lines-table` | `table` |
| `orders-detail-state-status` | `span` |
| `orders-detail-subtotal-text` | `span` |
| `orders-detail-tax-text` | `span` |
| `orders-detail-taxrate-text` | `span` |
| `orders-detail-total-text` | `span` |
| `orders-detail-updated-text` | `dd` |

## invoices-list

`/invoices`, logged in as `finance@labapp.test`. Page title: `Facturas · LabApp`.

| Test id | Element |
|---|---|
| `invoices-list-created-cell-1` | `td` |
| `invoices-list-created-cell-2` | `td` |
| `invoices-list-created-cell-3` | `td` |
| `invoices-list-customer-cell-1` | `td` |
| `invoices-list-customer-cell-2` | `td` |
| `invoices-list-customer-cell-3` | `td` |
| `invoices-list-footer-item` | `div` |
| `invoices-list-heading` | `h1` |
| `invoices-list-next-button` | `button` |
| `invoices-list-number-cell-1` | `td` |
| `invoices-list-number-cell-2` | `td` |
| `invoices-list-number-cell-3` | `td` |
| `invoices-list-order-cell-1` | `td` |
| `invoices-list-order-cell-2` | `td` |
| `invoices-list-order-cell-3` | `td` |
| `invoices-list-order-link-1` | `a` |
| `invoices-list-order-link-2` | `a` |
| `invoices-list-order-link-3` | `a` |
| `invoices-list-page-text` | `p` |
| `invoices-list-prev-button` | `button` |
| `invoices-list-row-1` | `tr` |
| `invoices-list-row-2` | `tr` |
| `invoices-list-row-3` | `tr` |
| `invoices-list-scroll-region` | `div[role=region]` |
| `invoices-list-search-button` | `button` |
| `invoices-list-search-form` | `form` |
| `invoices-list-search-input` | `input[type=text]` |
| `invoices-list-state-cell-1` | `td` |
| `invoices-list-state-cell-2` | `td` |
| `invoices-list-state-cell-3` | `td` |
| `invoices-list-status-select` | `select` |
| `invoices-list-table` | `table` |
| `invoices-list-total-cell-1` | `td` |
| `invoices-list-total-cell-2` | `td` |
| `invoices-list-total-cell-3` | `td` |
| `invoices-list-total-text` | `p` |
| `invoices-list-view-link-1` | `a` |
| `invoices-list-view-link-2` | `a` |
| `invoices-list-view-link-3` | `a` |

## invoices-detail-issued

`/invoices/1`, logged in as `finance@labapp.test`. Page title: `Factura FAC-0001 · LabApp`.

| Test id | Element |
|---|---|
| `invoices-detail-address-text` | `dd` |
| `invoices-detail-back-link` | `a` |
| `invoices-detail-created-text` | `dd` |
| `invoices-detail-customer-text` | `dd` |
| `invoices-detail-heading` | `h1` |
| `invoices-detail-line-price-cell-1` | `td` |
| `invoices-detail-line-product-cell-1` | `td` |
| `invoices-detail-line-quantity-cell-1` | `td` |
| `invoices-detail-line-row-1` | `tr` |
| `invoices-detail-line-total-cell-1` | `td` |
| `invoices-detail-lines-heading` | `h2` |
| `invoices-detail-lines-scroll-region` | `div[role=region]` |
| `invoices-detail-lines-table` | `table` |
| `invoices-detail-order-link` | `a` |
| `invoices-detail-payment-amount-cell-1` | `td` |
| `invoices-detail-payment-amount-cell-2` | `td` |
| `invoices-detail-payment-detail-cell-1` | `td` |
| `invoices-detail-payment-detail-cell-2` | `td` |
| `invoices-detail-payment-method-cell-1` | `td` |
| `invoices-detail-payment-method-cell-2` | `td` |
| `invoices-detail-payment-row-1` | `tr` |
| `invoices-detail-payment-row-2` | `tr` |
| `invoices-detail-payment-state-cell-1` | `td` |
| `invoices-detail-payment-state-cell-2` | `td` |
| `invoices-detail-payments-heading` | `h2` |
| `invoices-detail-payments-scroll-region` | `div[role=region]` |
| `invoices-detail-payments-table` | `table` |
| `invoices-detail-state-status` | `span` |
| `invoices-detail-subtotal-text` | `span` |
| `invoices-detail-tax-text` | `span` |
| `invoices-detail-taxid-text` | `dd` |
| `invoices-detail-taxrate-text` | `span` |
| `invoices-detail-total-text` | `span` |
| `payments-register-amount-input` | `input[type=text]` |
| `payments-register-cardcvc-input` | `input[type=text]` |
| `payments-register-cardexpiry-input` | `input[type=text]` |
| `payments-register-cardnumber-input` | `input[type=text]` |
| `payments-register-form` | `form` |
| `payments-register-heading` | `h2` |
| `payments-register-method-select` | `select` |
| `payments-register-submit-button` | `button` |

## invoices-detail-paid

`/invoices/2`, logged in as `finance@labapp.test`. Page title: `Factura FAC-0002 · LabApp`.

| Test id | Element |
|---|---|
| `invoices-detail-address-text` | `dd` |
| `invoices-detail-back-link` | `a` |
| `invoices-detail-closed-text` | `p` |
| `invoices-detail-created-text` | `dd` |
| `invoices-detail-customer-text` | `dd` |
| `invoices-detail-heading` | `h1` |
| `invoices-detail-line-price-cell-2` | `td` |
| `invoices-detail-line-product-cell-2` | `td` |
| `invoices-detail-line-quantity-cell-2` | `td` |
| `invoices-detail-line-row-2` | `tr` |
| `invoices-detail-line-total-cell-2` | `td` |
| `invoices-detail-lines-heading` | `h2` |
| `invoices-detail-lines-scroll-region` | `div[role=region]` |
| `invoices-detail-lines-table` | `table` |
| `invoices-detail-order-link` | `a` |
| `invoices-detail-payment-amount-cell-3` | `td` |
| `invoices-detail-payment-detail-cell-3` | `td` |
| `invoices-detail-payment-method-cell-3` | `td` |
| `invoices-detail-payment-row-3` | `tr` |
| `invoices-detail-payment-state-cell-3` | `td` |
| `invoices-detail-payments-heading` | `h2` |
| `invoices-detail-payments-scroll-region` | `div[role=region]` |
| `invoices-detail-payments-table` | `table` |
| `invoices-detail-state-status` | `span` |
| `invoices-detail-subtotal-text` | `span` |
| `invoices-detail-tax-text` | `span` |
| `invoices-detail-taxid-text` | `dd` |
| `invoices-detail-taxrate-text` | `span` |
| `invoices-detail-total-text` | `span` |

## invoices-detail-readonly

`/invoices/1`, logged in as `readonly@labapp.test`. Page title: `Factura FAC-0001 · LabApp`.

| Test id | Element |
|---|---|
| `invoices-detail-address-text` | `dd` |
| `invoices-detail-back-link` | `a` |
| `invoices-detail-created-text` | `dd` |
| `invoices-detail-customer-text` | `dd` |
| `invoices-detail-heading` | `h1` |
| `invoices-detail-line-price-cell-1` | `td` |
| `invoices-detail-line-product-cell-1` | `td` |
| `invoices-detail-line-quantity-cell-1` | `td` |
| `invoices-detail-line-row-1` | `tr` |
| `invoices-detail-line-total-cell-1` | `td` |
| `invoices-detail-lines-heading` | `h2` |
| `invoices-detail-lines-scroll-region` | `div[role=region]` |
| `invoices-detail-lines-table` | `table` |
| `invoices-detail-order-link` | `a` |
| `invoices-detail-payment-amount-cell-1` | `td` |
| `invoices-detail-payment-amount-cell-2` | `td` |
| `invoices-detail-payment-detail-cell-1` | `td` |
| `invoices-detail-payment-detail-cell-2` | `td` |
| `invoices-detail-payment-method-cell-1` | `td` |
| `invoices-detail-payment-method-cell-2` | `td` |
| `invoices-detail-payment-row-1` | `tr` |
| `invoices-detail-payment-row-2` | `tr` |
| `invoices-detail-payment-state-cell-1` | `td` |
| `invoices-detail-payment-state-cell-2` | `td` |
| `invoices-detail-payments-heading` | `h2` |
| `invoices-detail-payments-scroll-region` | `div[role=region]` |
| `invoices-detail-payments-table` | `table` |
| `invoices-detail-state-status` | `span` |
| `invoices-detail-subtotal-text` | `span` |
| `invoices-detail-tax-text` | `span` |
| `invoices-detail-taxid-text` | `dd` |
| `invoices-detail-taxrate-text` | `span` |
| `invoices-detail-total-text` | `span` |

## settings-admin

`/settings`, logged in as `admin@labapp.test`. Page title: `Configuración · LabApp`.

| Test id | Element |
|---|---|
| `settings-page-heading` | `h1` |
| `settings-taxrate-current-text` | `p` |
| `settings-taxrate-form` | `form` |
| `settings-taxrate-heading` | `h2` |
| `settings-taxrate-input` | `input[type=text]` |
| `settings-taxrate-save-button` | `button` |

## settings-readonly

`/settings`, logged in as `sales@labapp.test`. Page title: `Configuración · LabApp`.

| Test id | Element |
|---|---|
| `settings-page-heading` | `h1` |
| `settings-taxrate-current-text` | `p` |
| `settings-taxrate-heading` | `h2` |
| `settings-taxrate-readonly-text` | `p` |
