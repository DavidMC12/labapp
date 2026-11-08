# Task 048: the screens at 320 px (reflow)

Assignee: Worker 2. Branch: `w2/reflow-320`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 047 is merged (the supervisor tells you; until then branch from `w2/site-icon`).

## Goal

WCAG 2.1 criterion 1.4.10 (Reflow) asks that a page works at a width of 320 CSS pixels (a 1280 px window zoomed to 400 %) without sideways scrolling, except for the data tables themselves, which may scroll inside their own container. The browser audit already walks phone (390 px) and tablet states and fails a page that scrolls sideways. Extend it to 320 px, and fix what it finds. A person who tests accessibility with zoom should find nothing to report on this app.

## Read first

`tools/audit/README.md` (states, `viewport`, `catalog: false`, `steps`), `tools/audit/states.json` (the existing `*-phone` states are the templates), `frontend/README.md` (layout, `TableScroll`, the phone header), `frontend/src/components/ui/TableScroll.tsx`, `frontend/src/app/globals.css`.

## Scope

You may edit `tools/audit/states.json` (by text: add lines, keep the existing ones byte-identical; do not run it through a JSON formatter), the frontend source (class names and CSS only), its tests, `frontend/README.md`, `tools/audit/README.md` and any sentence in the docs that states the number of audited states (search for the old number with `grep -rn "39" docs README.md README.es.md frontend/README.md tools/audit/README.md` and update what it counts). No new dependency. Do **not** change any `data-testid`, text, DOM order or behavior; if a fix seems to need that, stop and write the question in the report.

## Requirements

1. **New states.** For each of these pages add one state named `<page>-narrow` (for example `home-narrow`, `customers-new-narrow`, `invoices-detail-issued-narrow`; drop a `-phone` suffix) with `"viewport": { "width": 320, "height": 568 }`, `"catalog": false`, and the same `path`, `user`, `waitFor`, `title` (and `steps` if any) as the existing phone or desktop state it copies: login, home, customers list, customers detail, customers new (create form), products list, orders list, orders new, orders detail (confirmed), invoices list, invoices detail (issued, with the payment form), settings. If a page has no phone state yet, copy its desktop state.
2. **Run the browser audit in both themes** (`tools/audit/README.md`, in-memory API with `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`). List every failure the new states produce (sideways scroll, axe violations such as `scrollable-region-focusable` or target size, missing ids).
3. **Fix every failure** with class names and CSS only. Typical causes to look for: a fixed `min-width` or `w-[...]`, a flex row that does not wrap, a long unbroken text (an email, a SKU, a reference, a number) without `break-words` or `min-w-0`, a form grid that keeps two columns, buttons in a row that do not wrap, a table that is not inside `TableScroll`. A data table may scroll sideways inside its own focusable container (that is what `TableScroll` is for); the page itself must not.
4. **Keep the other states passing.** The 39 existing states in both themes still pass; the light run with `--catalog docs/TESTIDS.md` shows the catalog unchanged.
5. **Tests** for every class change where a test already covers that component (Vitest); do not add tests that only restate a class name.
6. **Docs.** The audit README lists the new states or says how many there are; any sentence with the old count is corrected; one sentence in `frontend/README.md` says the pages are audited at 320 px.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` pass. From the repository root: the three audit test files (`node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs`), `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs` and the browser audit in both themes (all states, old and new, 0 failures; the light run with `--catalog docs/TESTIDS.md` unchanged).

## Rules for this task

- Commit as you go, in small real steps (about 6 to 10 commits: the states first, then one commit per kind of fix, then the docs). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the list of failures the new states found (before) and what you changed for each, the exact commands you ran with their exit codes, and any deviation or open question.
