# Task 025: frontend settings screen (tax rate)

Assignee: Worker 2. Branch: `w2/settings-ui`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 023 (dark theme) is merged. The backend already serves `GET /api/settings` and `PATCH /api/settings` (task 015, running today in memory and in PostgreSQL); you may check your calls against it, but the unit tests mock `fetch` as in tasks 011, 016 and 020.

## Goal

SPEC section 2 says that only an Admin can change the tax rate, and the API exists, but no screen uses it. Build a small "Configuración" screen: every role sees the current tax rate, and the Admin can change it. It is also the simplest example of a form with server-side validation for the owner's tests: the screen must show the server's answers exactly, without adding rules of its own.

## Read first

`docs/SPEC.md` section 2 (permissions), section 5 ("Orders API": the `Settings` rule and the settings rows of the table), section 7; `docs/TESTABILITY.md`; `frontend/src/features/customers/` and `frontend/src/features/orders/` (data layer, form and alert patterns), `frontend/src/app/(app)/customers/new/page.tsx` (a form page), `frontend/src/app/(app)/layout.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/testid.ts`, `frontend/src/components/ui/`, `tools/audit/README.md`.

## Scope

You may create and edit files only under `frontend/`: `src/features/settings/`, `src/app/(app)/settings/`, the shell layout `src/app/(app)/layout.tsx` and its tests (one new navigation link), and the README. No new dependencies. Do not change any existing `data-testid`. Do not touch `next.config.ts`.

## Requirements

1. **Data layer** (`src/features/settings/`): `types.ts` (`Settings = { tax_rate: string }`), `api.ts` and `hooks.ts`: `useSettings()` (key `["settings"]`, `GET /api/settings`, `retry: false`) and `useUpdateTaxRate()` (`PATCH /api/settings` with the JSON body `{"tax_rate": "<the string exactly as typed>"}`; on success `setQueryData(["settings"], answer)` and invalidate the queries whose key starts with `"orders"` so the preview rate of drafts is read again). Errors keep the `ApiProblem` of `src/lib/api.ts` with its `errors[]`. `permissions.ts`: `canChangeTaxRate(role)` is true only for `admin`.
2. **Page** (`src/app/(app)/settings/page.tsx`, a client component, all text in Spanish): heading "Configuración"; a section "Impuesto" that shows the current rate as "10.00 %" (the string as it comes plus " %"); for an Admin a form with one labelled input "Tasa de impuesto (%)" prefilled with the current rate and a button "Guardar"; for every other role no form, and a sentence "Solo un administrador puede cambiar el impuesto." The input is `type="text" inputMode="decimal"` with `noValidate` on the form and no `min`, `max` or `step`: the server decides what is valid. The raw value is sent as typed, not trimmed and not parsed (`" 7"`, `"1e1"` and `"10.123"` must reach the server and come back as errors). While the request runs the button is disabled and shows "Guardando…", the form has `aria-busy="true"`, and a second click does nothing. Show the server's answers next to the field: `INVALID_FORMAT` and `OUT_OF_RANGE` on `tax_rate` as the field error (use the `message` of the answer); any other problem (403, 500, network) in the form alert with its `detail`; focus goes to the first error. On success show "Impuesto actualizado a 7.00 %." in a status region (`role="status"`), keep the saved value in the input as the server returned it (`"7"` becomes `7.00`) and clear any error. Loading shows a status "Cargando configuración…"; a failed load shows an alert and a "Reintentar" button.
3. **Navigation.** A link "Configuración" in the shell (rail and phone layout, same pattern as the others) to `/settings`, visible to every role; the current-section highlighting works for it. Do not change the existing links.
4. **Test ids** (all pass `isValidTestId`, unique per page; the audit requires an id on every interactive element, form, heading, alert and status):

| Element | Test id |
|---|---|
| Shell link | `app-nav-settings-link` |
| Heading, section heading | `settings-page-heading`, `settings-taxrate-heading` |
| Current rate text, read-only sentence | `settings-taxrate-current-text`, `settings-taxrate-readonly-text` |
| Form, input, button, field error | `settings-taxrate-form`, `settings-taxrate-input`, `settings-taxrate-save-button`, `settings-taxrate-input-error` |
| Form alert, success status | `settings-taxrate-alert`, `settings-taxrate-success-status` |
| Load states | `settings-page-loading-status`, `settings-page-error-alert`, `settings-page-retry-button` |

   Check how `Field` builds the id of the field error (`errorId`) in the customers form and follow it; the table gives the intended name, adjust only if the existing pattern forces a different valid one and say so in the report.
5. **Tests.** Mock `fetch` and `next/navigation`; no network. Cover: the exact requests (path, method, headers, body for `"7"`, `" 7"`, `"1e1"`, `"10.123"`, `""`, `"100"`, `"100.01"`), the Admin view and the view of each other role (no form), the field error from a 422 `INVALID_FORMAT` and `OUT_OF_RANGE`, a 403 and a 500 in the form alert, success (status text, input shows the returned value, orders queries invalidated), the double-click guard, the load states, the navigation link for every role and the current-section highlight, and that every id of the table is valid and appears. Keep the existing tests passing.
6. **Docs.** A "Settings" section in `frontend/README.md`: the page, the permission rule and the rule that the screen adds no validation.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` all pass; from the repository root `node tools/audit/testid-audit.mjs` reports no problem.

## Rules for this task

- Commit as you go, in small real steps (about 10 to 14 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
