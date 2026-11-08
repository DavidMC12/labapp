# Task 067: frontend fixes from the second-agent review of the new features

Assignee: Worker 2. Branch: `w2/review-fixes`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

A background reviewer read the import screen, the sort headers, the shared title hook and the security headers (`docs/reviews/2026-11-08-batch-security-review.md`). The supervisor confirmed three of its findings in the real application: the import form can be changed while a request is in flight, it keeps stale results when another file is chosen, and **keyboard focus falls to `<body>` after every sort click or page change on all four lists** (measured in Chromium: pressing Enter on a sort button leaves `document.activeElement` on `BODY`). Fix them, and one defect of the web security headers.

## Read first

`docs/reviews/2026-11-08-batch-security-review.md` (the findings that are yours are listed below), `frontend/src/features/customers/ImportForm.tsx` and its tests, the four list pages `frontend/src/app/(app)/{customers,orders,invoices,products}/page.tsx` and their data hooks (`frontend/src/features/*/hooks.ts`: the TanStack Query `useQuery` of each list and what the page renders while `isPending`), `frontend/src/components/ui/SortableHeader.tsx`, `frontend/next.config.ts` and `frontend/src/next-config.test.ts`, `docs/TESTABILITY.md` (`aria-busy`, `data-state`), `tools/audit/README.md`.

## Scope

Under `frontend/` (the import form, the four list pages and their hooks, `next.config.ts`, the tests, the README) and, if a state changes, `tools/audit/states.json` (by text) and `docs/TESTIDS.md` (regenerated). No new dependency. Do not change an existing `data-testid` or text.

## Requirements

1. **The import form during a request (Important).** While `formState` is `loading`: the file input is `disabled` and its `onChange` does nothing. (Today the input stays enabled and `onChange` unconditionally sets the form to `idle`: choosing file B while A is sent drops `aria-busy` early, re-enables the button, and when A's answer arrives the form reports A and `clearFile()` throws B away.) Tests: the input is disabled while sending (check the attribute through the test's pending promise), a change event during the request changes nothing, and the answer of A leaves the file input empty and the state `success` or `error` as before.
2. **Stale results (Minor).** Choosing another file clears the previous attempt completely: the result text with its "Ver clientes" link, the alert and the errors table disappear (clear `resultText`, `alertText` and `errorRows` as well as returning to `idle`). The comment of the `onChange` already says so. Tests for each of the three after a success and after a rejection.
3. **The focus must survive a sort, a page change and a filter (Important).** Sorting changes the query key, `isPending` becomes true and the page replaces the table, **including the button that has the focus**, by the loading text; the Tab-walk audit does not see it because it never activates anything. Keep the previous data on screen while the next arrives (TanStack Query v5: `placeholderData: keepPreviousData` on the list queries of the four lists, or the equivalent your version supports; read the version in `package.json`), so the table and its header buttons stay mounted; while the new data is fetching mark the table region `aria-busy="true"` (the existing observable state; do not invent a new attribute) and clear it when the data lands. The first load (no previous data) keeps today's loading text. The same fix covers the "Anterior" and "Siguiente" buttons and the search/status controls, which suffer the same loss: check them. Tests per list: after a sort click the header button is still the document's active element once the new data renders (Testing Library: `expect(button).toHaveFocus()`), `aria-busy` is `true` while the second request is pending and gone after, and the first load still shows the loading text. Then prove it **in a real browser**: with the dev servers (in-memory API; use `WEB_PORT=3200 API_PORT=8200`: other processes may hold 3000 and 8000), press Enter on each sort button through `Input.dispatchKeyEvent` and read `document.activeElement` (`data-testid`) after the data arrives, for the four lists, and for "Siguiente" on the customers list after creating 21 customers (or on a list with a second page); the report lists the observed active elements. Keep your script outside the repository.
4. **The CSP source is a prefix match (Minor).** `APP_HEADERS_SOURCE` is `/((?!api|__test__).*)`: `/apiary` or `/__test__x` would lose the headers although they are web pages. Make the lookahead match whole path segments: `/((?!(?:api|__test__)(?:/|$)).*)`. Update the comment, and the tests in `next-config.test.ts`: `/api`, `/api/docs`, `/api/openapi.json`, `/__test__/reset` and `/__test__` do **not** match; `/`, `/login`, `/orders/3`, `/apiary`, `/api-docs`, `/__test__x` and `/customers/api` **do**. Build and check the headers of `/apiary` with `curl -I` against `next start` (it is a 404 page, but it must carry the headers).
5. **Docs.** `frontend/README.md`: a sentence in the lists section that the previous data stays while a new sort or page loads, with `aria-busy`.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage` (the coverage floor holds), `pnpm build` pass. From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs tools/audit/keyboard.test.mjs`, `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs` and the browser audit in both themes (all states 0 failures, the light run with `--catalog docs/TESTIDS.md` unchanged). The supervisor repeats the focus check in a real browser.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause; a stuck test process at 100 % CPU is a loop in the code.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the observed active elements of requirement 3, and any deviation or open question.
