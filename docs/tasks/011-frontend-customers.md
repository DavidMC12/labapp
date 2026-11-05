# Task 011: frontend customers screens

Assignee: Worker 2. Branch: `w2/customers`. Reviewer: Supervisor.

## Goal

Build the customers screens of flow 1 (list, create, detail, edit, deactivate and reactivate) against the "Customers API" subsection of `docs/SPEC.md`. The backend endpoints are being built in parallel (task 010), so everything is developed and tested with a mocked `fetch`, with the same discipline as the login screen: a mocked test must not pass where the real API would fail.

## Read first

- `docs/SPEC.md`: section 4 (customers: fields, rules, errors and the "Customers API"), section 5 "Concurrency" (`version`, `If-Match`), section 7 (error catalog, field codes and messages) and section 8 (formats and list rules).
- `docs/SEED.md`: the ten seeded customers (useful as test data).
- `docs/TESTABILITY.md`: the whole file. Every test id below follows its grammar.
- `frontend/src/lib/api.ts`, `frontend/src/features/auth/`, `frontend/src/app/login/page.tsx`, `frontend/src/app/(app)/layout.tsx` and `frontend/src/components/ui/`: the patterns and components you must reuse (the form handling of the login page is the model for the form behavior below).

## Scope

You may create and edit files only under `frontend/`. You may not add dependencies. Do not add an `/api` rewrite to `next.config.ts`.

## Requirements

### Data layer (`src/features/customers/`)

1. `types.ts`: `CustomerStatus` (`"active" | "inactive"`), `Customer`, `CustomerList` exactly as in the spec (`id: number`; `phone`, `tax_id` and `address` are `string | null`; timestamps are strings), and a `statusLabel(status)` helper returning "Activo" or "Inactivo".
2. `api.ts` and `hooks.ts` on TanStack Query, all with `retry: false`: `useCustomers({ page, q, status })`, `useCustomer(id)`, `useCreateCustomer()`, `useUpdateCustomer()` and `useSetCustomerStatus()`. Keys: `["customers", "list", { page, q, status }]` and `["customers", "detail", id]`. The id in the keys is always a **number**: parse the route parameter once, accepting only the pattern `^[1-9][0-9]*$` and at most 2147483647 (so `"1e3"`, `"0"` and `"007"` are rejected), otherwise `["customers", "detail", "7"]` and `["customers", "detail", 7]` would be two different entries and the screen would not update. A successful create, update or status change writes the returned customer with `setQueryData` on its detail key **before** the page navigates, and invalidates `["customers", "list"]`. A 401 on any customers call also writes `null` into the `["auth", "me"]` cache entry, so the shell redirects to the login instead of showing "Reintentar" for ever. `useSetCustomerStatus` sends `POST /api/customers/{id}/deactivate` or `/reactivate` with the header `If-Match: "<version>"` (the version of the customer on screen). The update sends `PATCH /api/customers/{id}` with all five editable fields and the `version` **captured when the form was initialized or last reset** (never the version of a later background refetch), so a refetch while the form is open cannot silently overwrite another user's change; the captured version changes only through "Recargar datos" or a successful save. In a create or an update body, an empty optional field is sent as `null`. The list request is built with `URLSearchParams`: `page` is always present and `q` and `status` are present only when they have a value (an empty `status=` would be a 422 from the real API), so `q=R&D` is encoded correctly.
3. `permissions.ts`: `canManageCustomers(role)` is true for `admin` and `sales` only. The UI hides write controls for the other roles; the server remains the authority.

### Pages (under `src/app/(app)/customers/`), all text in Spanish

4. **List** (`page.tsx`, replaces the placeholder; keep the heading "Clientes"). State lives in the URL (`?page=2&q=ana&status=active`) so links can be shared; invalid values in the URL fall back to page 1 and no status. If the page in the URL is beyond the last one (the last page is `Y = max(1, ceil(total / 20))`), replace the URL with page `Y` instead of showing an empty page next to "Página 99 de 3"; the same applies after a status change leaves the current page empty. Wrap the part that calls `useSearchParams` in a `Suspense` boundary, otherwise `pnpm build` fails.
   - A search form with the field "Buscar", a select "Estado" (options "Todos", "Activos", "Inactivos") and the button "Buscar". Nothing is applied while typing; submitting the form sets `q` (trimmed) and `status` in the URL and goes back to page 1.
   - A table with the columns Nombre, Email, ID fiscal and Estado (use `<th scope="col">`); the name is a link to the detail page; empty values show "—". Below it: the buttons "Anterior" and "Siguiente" (disabled at the first and the last page), the text "Página X de Y" (Y is at least 1) and the total as "N clientes" ("1 cliente" for one).
   - "Nuevo cliente" (a link to `/customers/new`) is shown only when `canManageCustomers`.
   - States: loading shows "Cargando…" with `aria-busy="true"`; no results show "No hay clientes que coincidan."; any error shows the problem's `detail` (or the INTERNAL_ERROR text for non-API errors) in a `role="alert"` element with a "Reintentar" button that refetches.
5. **Create** (`new/page.tsx`) and **edit** (`[id]/edit/page.tsx`) share one form component. Heading "Nuevo cliente" or "Editar cliente". Fields: "Nombre", "Email" (`type="email"`), "Teléfono", "ID fiscal" and "Dirección" (a textarea). The form has `noValidate`.
   - Before sending: an empty (after trimming) name or email shows "Este campo es obligatorio." on that field and nothing is sent. Every other rule is the server's: do not duplicate length or format checks on the client.
   - Each submit clears the errors of the previous one; a second submit while one is pending is ignored (guard in the handler); the button "Guardar" shows "Guardando…" and the loading state.
   - A 422 answer maps `errors[].field` (`name`, `email`, `phone`, `tax_id`, `address`) to the matching field (`tax_id` shows on the "ID fiscal" field). A 409 `CUSTOMER_EMAIL_TAKEN` shows its `detail` on the email field. A 409 `VERSION_CONFLICT` shows its `detail` in the form-level alert together with a button "Recargar datos" that refetches the customer and resets the form to the server values. Any other problem, including a network error, shows its `detail` in the form-level alert (`role="alert"`).
   - After a failed submit, focus goes to the form-level alert when it is shown, otherwise to the first field with an error.
   - On success, `router.replace` to the detail page of the saved customer. "Cancelar" is a link back to the list (create) or to the detail page (edit).
   - The edit page shows "Cargando…" while the customer loads and an error alert (with "Reintentar" except for a 404) if it fails. If the user cannot manage customers, show only the alert "No tienes permiso para realizar esta acción." (test id `customers-form-forbidden-alert`) instead of the form. `Textarea` does not forward a `ref` yet while `Input` does: add it to `Textarea` (with a test) so focus can reach the address field.
6. **Detail** (`[id]/page.tsx`). Heading with the customer's name; then the labeled values name, email, phone, tax ID, address ("—" when `null`) and the status label. For users who can manage customers: a link "Editar" and, depending on the status, a button "Desactivar" or "Reactivar" (loading state, ignored second click; on success the cache is updated so the screen changes without reloading; on failure, including `VERSION_CONFLICT`, the `detail` appears in an alert and nothing changes). A link "Volver a clientes". Loading and load errors behave as in the list; a 404 shows its `detail` and the back link, without "Reintentar". After any failed status change, and always after a `VERSION_CONFLICT`, refetch the customer so that the next click sends the fresh version instead of repeating the stale one.
7. Pages are client components. Read the id with `useParams` and parse it as described for the keys; an id that does not match shows the alert `customers-detail-error-alert` (or `customers-form-error-alert` on the edit page) with the text "No se encontró el recurso solicitado." and the back link, without calling the API.

### Test ids

8. Use exactly these (the id of each customer appears where `{id}` is written):

| Element | Test id |
|---|---|
| List heading | `customers-list-heading` |
| "Nuevo cliente" link | `customers-list-new-link` |
| Search form, field, select, button | `customers-list-search-form`, `customers-list-search-input`, `customers-list-status-select`, `customers-list-search-button` |
| Loading status, empty status | `customers-list-loading-status`, `customers-list-empty-status` |
| Error alert and retry button | `customers-list-error-alert`, `customers-list-retry-button` |
| Table | `customers-list-table` |
| Row and cells of one customer | `customers-list-row-{id}`, `customers-list-name-cell-{id}`, `customers-list-email-cell-{id}`, `customers-list-taxid-cell-{id}`, `customers-list-state-cell-{id}` |
| Name link inside the name cell | `customers-list-view-link-{id}` |
| Pagination | `customers-list-prev-button`, `customers-list-next-button`, `customers-list-page-text`, `customers-list-total-text` |
| Form heading, form | `customers-form-heading`, `customers-customer-form` |
| Form fields (errors derive from them) | `customers-form-name-input`, `customers-form-email-input`, `customers-form-phone-input`, `customers-form-taxid-input`, `customers-form-address-textarea` |
| Submit, cancel, alert, reload, loading | `customers-form-submit-button`, `customers-form-cancel-link`, `customers-form-alert`, `customers-form-reload-button`, `customers-form-loading-status` |
| Form load error, retry, permission message | `customers-form-error-alert`, `customers-form-retry-button`, `customers-form-forbidden-alert` |
| Detail heading | `customers-detail-heading` |
| Detail values | `customers-detail-name-text`, `customers-detail-email-text`, `customers-detail-phone-text`, `customers-detail-taxid-text`, `customers-detail-address-text`, `customers-detail-state-status` |
| Detail actions | `customers-detail-edit-link`, `customers-detail-deactivate-button`, `customers-detail-reactivate-button`, `customers-detail-back-link` |
| Detail alert, loading, load error, retry | `customers-detail-alert`, `customers-detail-loading-status`, `customers-detail-error-alert`, `customers-detail-retry-button` |

### Tests and docs

9. **Tests.** Mock `fetch` and `next/navigation` (stable router object, `useSearchParams`, `useParams`); no network. Test `QueryClient` instances use `retry: false`. Cover: the hooks and the exact requests (paths, methods, headers including `If-Match`, JSON bodies, `null` for empty optionals); `canManageCustomers`; the list (URL parsing with invalid values, search submit, the pagination arithmetic and disabled buttons, the empty and error states with retry, hiding "Nuevo cliente" per role, 20-row page of seed-like data); the form (client-side required checks, field errors from a 422, the email-taken error, the version conflict with reload, a network error, the ignored second submit, focus after failure, the redirect on success, prefilled edit values, the permission message); the detail (values, "—" for nulls, the two status buttons, success and failure of a status change, 404 and invalid id, hidden controls per role); and the version captured by the edit form (a background refetch to a newer version while the form is open does not change the version that is sent, and "Recargar datos" does), the exact list request URL (`page` always, `q` and `status` only when set, `q=R&D` encoded), a page beyond the last being replaced by the last one, a refetch after a failed status change, a numeric id in the query keys (the detail updates without a reload after a status change), a 401 clearing the session cache entry, and that every id in the table passes `isValidTestId` (derive the `{id}` ones with a sample number).
10. **Docs.** A short "Customers" section in `frontend/README.md`: the pages, the URL parameters of the list, and the permission rule.

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

- Commit as you go, in small real steps (about 14 to 20 commits): for example the types and the API layer, each hook, the form component, each page, then tests next to each piece and the README. Messages follow Conventional Commits, in English, for example `feat(frontend): add the customers list page`.
- Do not add `Co-Authored-By` or any tool-attribution line to a commit. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory; never ask for access outside it.
- If the spec is ambiguous or contradicts itself, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their results, and any deviation or open question.
