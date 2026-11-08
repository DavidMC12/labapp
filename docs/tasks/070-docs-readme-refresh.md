# Task 070: refresh the READMEs and the screenshots

Assignee: Worker 2. Branch: `w2/readme-refresh`. Reviewer: Supervisor.

**Base.** Branch from `main` after task 067 (`w2/review-fixes`) is merged (the supervisor tells you).

## Goal

`README.md` and `README.es.md` are the front door of a public portfolio repository. They were last written when the application had three flows, and they say little about what was added afterwards: sortable lists, CSV export and import, the keyboard and 320 px audits, the practice catalog, the smoke test and Dependabot. The screenshots show seven screens from before the sorting, the import and the final fixes. Bring both READMEs and the screenshots up to date, truthfully.

## Read first

`README.md` and `README.es.md` (the sections: Screenshots, Why, What it does, Stack, Where it stands, Roadmap, Demo users, Repository layout, Getting started), `docs/DEPLOYMENT.md` (the application is **not deployed yet**: the READMEs must not claim a live URL), `docs/AUTOMATION_GUIDE.md`, `docs/PRACTICE.md` (how many areas and rows there are: count them, do not copy an old number), `docs/TESTABILITY.md`, `tools/audit/README.md`, `docs/screenshots/` (the existing images and how big they are), `docs/DEVELOPMENT.md` (to start the stack).

## Scope

`README.md`, `README.es.md` and `docs/screenshots/` only. No code, no other document. English and Spanish say the same things (the Spanish one in natural Spanish, not a word-for-word copy); every link works (the documentation linter checks links and anchors).

## Requirements

1. **"What it does"**: still short. Name the three flows, then one compact list of the rest, each item one line, all true today: the four roles, sortable and filterable lists, CSV export and CSV import of customers (file download and file upload), test-only controls (reset, seed, clock, fault injection), idempotent payments with a fake gateway, a contract served at `/api/docs`, light and dark themes, the screen language Spanish.
2. **"Where it stands"**: bring the table up to date. Keep one row per area, each `Done` or the real state, and add the missing ones: sorting, CSV export and import, the keyboard audit (visible focus and no keyboard trap) and the 320 px audits, the automation guide and the practice catalog (say "about N scenarios in M areas" with the numbers you count in `docs/PRACTICE.md`), the smoke test for the online demo if its task is merged by then (check `tools/smoke/`), Dependabot and the dependency audit, and the test numbers only if you read them from a fresh run (do not copy numbers from an older README). The row about the online deployment stays honest: configured, not deployed.
3. **"Roadmap"**: what is really left (the first online deployment, the nightly reset secrets, a first Dependabot round, more practice material), in the same voice as now.
4. **Screenshots.** Replace the set with about 9 images that show the application as it is now, taken from a **production build** (`pnpm build` and `next start`, with `API_URL` set at build time as `frontend/README.md` explains) over the in-memory API with the seed, with headless Chromium over the DevTools protocol: login (light), customers list sorted by name (the header arrow visible), customers list in the dark theme, an order detail, an invoice detail in the dark theme, the import screen with its table of errors after a rejected file, the products list, the home summary and the orders list on a phone (390 px). Real data only (the seed), no browser chrome, a 1280 px wide window for desktop shots. Each file well under 120 KB (crop to the content, use a deviceScaleFactor of 1; the whole set under 900 KB), a descriptive file name and an `alt` text that says what the image shows. Your script stays **outside** the repository. Remove the images that are no longer used and check no link points to them (`git grep` the names).
5. **Layout.** The images keep the current `<p>` / `<img>` layout (a table with an empty header fails the linter), a few per row at a sensible width, nothing that scrolls the page sideways in GitHub's renderer.
6. **Do not invent.** Every sentence must be checkable in the repository; if you are not sure a feature behaves as you write it, open the screen or read the SPEC. If something in the README is already false, fix it and say so in the report.

## Acceptance criteria

`node tools/audit/docs-lint.mjs` exits 0 (links, anchors, the ids cited); from `backend/` `uv run pytest -q tests/docs` passes; the image sizes are as required (list them). The supervisor reads both READMEs and opens every image.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 8 commits: the text first, then the images in two or three commits). Conventional Commits, in English (`docs(readme): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them). Never read `backend/.env` or any file outside your working directory.
- Ports: use `WEB_PORT=3200 API_PORT=8200` (other processes may hold 3000 and 8000) and do not kill processes you did not start.
- If a command runs more than 3 minutes, interrupt it (esc) and look for the cause.
- If something is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the list of images with their sizes, the numbers you counted in the practice catalog, what you found false in the old README, and any deviation or open question.
