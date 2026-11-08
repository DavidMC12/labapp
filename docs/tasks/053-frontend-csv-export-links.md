# Task 053: "Exportar CSV" links on the lists

Assignee: Worker 2. Branch: `w2/csv-export-ui`. Reviewer: Supervisor.

**Base.** Branch from the branch of task 051 (`w2/list-sorting-ui`) if it is not merged yet, otherwise from `main`. The backend routes (task 052) are in `main`.

## Goal

The API can now export the customers, orders and invoices of the list filters as a CSV file (`GET /api/<resource>/export`, `docs/SPEC.md` section 8, "CSV export"). Give each of the three lists a download link, so that a person (and a test) can download exactly what the list shows. Downloading a file and checking its content is a classic automation exercise; the link must be a real, plain download.

## Read first

`docs/SPEC.md` section 8 ("CSV export": the parameters, the file name, the columns), the three list pages `frontend/src/app/(app)/{customers,orders,invoices}/page.tsx` and their `features/*/params.ts` (the list state lives in the URL: `page`, `q`, `status`, `sort`, `direction`, `customer_id`, `order_id`), `frontend/src/components/ui/Link.tsx`, `frontend/src/lib/testid.ts`, `docs/TESTABILITY.md`, `tools/audit/README.md`, `frontend/README.md`.

## Scope

You may edit under `frontend/` (the three list pages, their `features/*` helpers, tests, README), `tools/audit/states.json` (by text: add lines, keep the existing ones byte-identical), `docs/TESTIDS.md` (regenerated, not edited by hand), `tools/audit/README.md` (one sentence). No new dependency. Do not change an existing `data-testid` or text.

## Requirements

1. **The link.** On each of the three lists, next to the search and filter controls, a link with the visible text "Exportar CSV" and the ids `customers-list-export-link`, `orders-list-export-link` and `invoices-list-export-link`. It is a plain `<a>` (not the Next.js client router: the target is served by the API and it is a download) with the `download` attribute (no value: the server's `Content-Disposition` names the file) and an `href` of `/api/<resource>/export` followed by the query string of the **applied** list state: `q`, `status`, `sort`, `direction`, plus `customer_id` on the orders list and `order_id` on the invoices list, exactly the parameters the SPEC says the export accepts, each only when it has a value and is not the default (the same rule the list URL follows), and **never** `page`. It is built from the parsed URL state (what the list shows), not from text typed in the search box and not yet applied. Reuse the helpers that build the list URL where it is natural; add a small pure function per feature (`exportUrl(params)`) with unit tests.
2. **The look.** The same quiet link style as the other secondary links of the page (use the `Link` component's style through a variant or the same classes if `Link` forces the router: check and say which in the report); keyboard reachable in the DOM order right after the filter controls; visible focus; it must not break the layout at 320 px (the audit checks it).
3. **Behavior to preserve.** The links appear for every role (reading is open to everyone), also when the list is empty or in error (the export of an empty filter is a file with only the header). Nothing else on the page changes.
4. **Tests** (Vitest and Testing Library, each page): the link exists with the right text, id, `download` attribute and `href` for the default list; the `href` follows `q`, `status`, `sort` and `direction`, `customer_id` (orders) and `order_id` (invoices); it never carries `page`; a parameter that is the default is left out; it changes when the URL state changes; text typed in the search box but not applied does not change it; it is a plain anchor (clicking does not call the mocked router). The pure `exportUrl` functions have their own tests (encoding of `q` with spaces, accents and `&`).
5. **The audit.** The three lists are already audited states, so the new ids appear in them: run the browser audit in both themes (`tools/audit/README.md`, in-memory API with `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`): all states pass, including the 320 px ones. Regenerate `docs/TESTIDS.md` against a clean seed as `tools/audit/README.md` says and commit it. Add one state `customers-list-filtered-export` with the path `/customers?q=a&status=active` (user, `waitFor` and `title` of the plain customers list) and `"catalog": false`.
6. **Check it for real.** With the dev servers running and a session, take the `href` of each link from the rendered page (not from your test), fetch it with the session cookie and parse the answer with a CSV reader: the status, the `Content-Type`, the `Content-Disposition` name and the header line are the SPEC's, and the number of data rows equals the `total` of the list the page shows for the same filters. Put the three results (resource, `href`, row count, list total) in the report.
7. **README.** `frontend/README.md`: a short "CSV export" paragraph (the ids, what the `href` carries).

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage` (the coverage floor holds), `pnpm build` pass. From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs`, `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs` and the browser audit in both themes (0 failures; the light run with `--catalog docs/TESTIDS.md` shows the catalog unchanged after you regenerated it).

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the three results of requirement 6, and any deviation or open question.
