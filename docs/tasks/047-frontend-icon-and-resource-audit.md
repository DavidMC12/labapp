# Task 047: a site icon, and an audit check for resources that fail to load

Assignee: Worker 2. Branch: `w2/site-icon`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

Every page makes the browser ask for `/favicon.ico`, and the answer is 404 (seen in the browser console on every page). A site that is built to be audited should not have a failing request of its own. Add a small icon in the "Libro mayor" look, and teach the browser audit to fail when a page loads a document, script, stylesheet, image or font that answers 4xx or 5xx, so this class of defect cannot come back.

## Read first

`frontend/src/app/layout.tsx` (metadata), `frontend/src/app/globals.css` (the light palette tokens, the accent), `frontend/README.md` (the theme section), `tools/audit/browser-audit.mjs`, `tools/audit/browser-audit.test.mjs` (or the test file that covers the audit helpers), `tools/audit/README.md`, the Next.js documentation for file-based metadata icons in `frontend/node_modules/next/dist/docs/` (read it for the installed version: `icon.svg` in `src/app/`).

## Scope

You may edit `frontend/src/app/icon.svg` (new) and a test for it, `frontend/README.md`, `tools/audit/browser-audit.mjs` and its tests, `tools/audit/README.md`, and `docs/TESTABILITY.md` (one sentence) if the audit's checks are listed there. No new dependency. Do not change any `data-testid`, text or page.

## Requirements

1. **The icon.** `frontend/src/app/icon.svg`: a 32 by 32 viewBox mark that suits a ledger: a rounded square in the accent color of the light palette with a pale double rule (two horizontal lines, the second one thicker) or the letter "L" cut out. Plain SVG, no script, no external reference, no font (draw shapes, do not use `<text>`), under 1 KB. It must read on a light and on a dark tab bar: use a filled square, not a thin outline. Next.js serves it at `/icon.svg` and adds the `<link rel="icon">` by itself; confirm that in the built HTML.
2. **Tests.** A Vitest test that reads the file and checks: it parses as XML with a root `svg` and a `viewBox`, it has no `<script`, no `href=`/`xlink:href`, no `<text`, no `url(http`, and is smaller than 1024 bytes.
3. **The audit check.** In `tools/audit/browser-audit.mjs`, collect the network responses of each state of the audit with the DevTools `Network` domain, and add one failure per response whose `type` is `Document`, `Stylesheet`, `Script`, `Image` or `Font` and whose status is 400 or more, with the state name and the URL. Responses of type `Fetch` and `XHR` are ignored (the API answers 4xx on purpose in error states). A state that is expected to be a 404 page (the state `not-found` of `states.json`, path `/no-such-page`, is one: its page answers 404 on purpose; the other "not found" states are client-rendered pages whose main document is 200) may declare it with a new optional field `expectStatus` on the state (default 200 for the main document) so the page itself does not fail the check; document the field in `tools/audit/README.md`. Cover the new logic with unit tests in the same style as the existing audit tests (extract the pure part into an exported function so it can be tested without a browser).
4. **Prove it both ways.** Run the browser audit (see `tools/audit/README.md`, in-memory API with `DATABASE_URL= DATABASE_URL_UNPOOLED= scripts/dev.sh`) in both themes: it must pass with the icon in place. Then temporarily rename `icon.svg`, run one theme again and confirm the audit fails on `/favicon.ico` or `/icon.svg` before you restore the file. Put both outcomes in the report. Do not commit the rename.
5. **README.** One sentence in the frontend README about the icon and one in the audit README about the new check.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` all pass. From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs`, `node tools/audit/testid-audit.mjs`, `node tools/audit/docs-lint.mjs`, and the browser audit in both themes (`--theme light`, `--theme dark`, the light run with `--catalog docs/TESTIDS.md` unchanged) all pass.

## Rules for this task

- Commit as you go, in small real steps (about 6 to 8 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the two outcomes of requirement 4, and any deviation or open question.
