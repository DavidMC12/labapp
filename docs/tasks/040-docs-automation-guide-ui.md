# Task 040: the automation guide, part 1 (the web UI)

Assignee: Worker 2. Branch: `w2/automation-guide`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

LabApp exists so that its owner, a QA engineer, can write test automation against it. The pieces are all there (stable `data-testid` on everything, a generated catalog of them, deterministic seed data, titles, states) but nothing tells a newcomer how to use them. Write the first half of a practical guide: how to drive the web UI. The second half (test controls and the HTTP API) comes after those parts are merged. The reader knows automation well and does not know this application: be concrete, short and exact; never describe a behavior you have not read in the repository.

## Read first

`docs/TESTABILITY.md`, `docs/TESTIDS.md` (the generated catalog: never copy it, link it), `docs/SEED.md`, `docs/SPEC.md` (sections 2 to 6 and 8), `frontend/README.md`, `docs/DEVELOPMENT.md`, `docs/DEPLOYMENT.md`, `tools/audit/README.md`, `tools/audit/states.json` (the audited screens and their users), the pages under `frontend/src/app/` and the feature folders (to read the real behavior: labels, messages, which role sees which control).

## Scope

You may create `docs/AUTOMATION_GUIDE.md` and edit `README.md` and `README.es.md` (one link line each, under "Where it stands" or "Getting started"). You may not edit any other file. No code.

## Requirements

The guide is in English, Markdown, with this structure (keep each section tight; tables and short lists, no padding):

1. **Start in five minutes.** How to run it locally (`mise run dev`, the URLs), the four demo users and their roles (a table with what each role can do, from SPEC section 2), and how to tell the online demo apart from local.
2. **Locators.** The test id grammar in three sentences, why `data-testid` and not `data-test`, the Playwright setting (`use: { testIdAttribute: 'data-testid' }`), how to find an id (the catalog), the rules for ids that end in a number (a record id or a position), and what the `region`, `status`, `alert` and `dialog` kinds mean.
3. **Screen map.** One table: screen, URL, who can open it, the document title, the id of its main heading, the id of its main table or form. Built from the code and `states.json`, covering login, the summary, customers (list, detail, new, edit), orders (list, detail, new), invoices (list, detail), products, settings, the 404 page and the expired-session notice.
4. **Seed data cheat sheet.** A table "I want to test X, use Y": the customer without a tax id (invoicing fails), the inactive customers, the draft, confirmed, paid, shipped and cancelled orders, the issued and paid invoices, the declined and the unavailable test cards, a product with low stock and one out of stock, the long customer name. From `docs/SEED.md`, with the ids and numbers exactly.
5. **The core flows, step by step.** Flow 1 (create a customer), flow 2 (build, confirm and cancel an order), flow 3 (invoice an order and pay it with a card, a transfer and cash, and the declined and unavailable outcomes). For each: the steps with the test ids that you click and read, the expected visible result, the errors a test can provoke and their messages (read the messages from the code, in Spanish, between quotes). Include one short Playwright (TypeScript) sketch per flow, clearly labelled "illustrative, not run in CI", using only ids that exist in `docs/TESTIDS.md`.
6. **Waiting and state.** What to wait for instead of timeouts: the loading `status` elements, `aria-busy`, the `data-hydrated` marker (read how it is set in the code), the confirmation dialogs, the success statuses, the redirects after create. The payment form's idempotency key rule in the UI (when it is kept, when it is renewed).
7. **Accessibility and titles.** How to run axe in a test, what the project's own audit checks (link to `tools/audit/README.md`), the document title convention, the skip link, the responsive widths the audit covers.
8. **Things that surprise a test author.** A short list, each item verified in the code: the rate limits online, the session lifetime and the expired-session notice, the optimistic concurrency messages, which controls disappear for which role, the order and invoice numbers that continue after the seed, the nightly reset online, the theme stored in the browser (`labapp-theme`) and how to pin it.
9. **What is next.** One sentence: part 2 (test controls: reset, seed, clock, faults; and the API contract) follows.

## Acceptance criteria

- Every test id, URL, label and message in the guide exists in the repository (the supervisor checks a sample against `docs/TESTIDS.md` and the code; a wrong id is a defect).
- No claim about behavior that you did not read in the code or the documents. When something is unknown, leave it out or say it is not verified.
- Markdown renders (tables aligned, code fences closed). The two READMEs link to the guide.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits, one per section). Conventional Commits, in English (`docs(guide): ...`).
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If something is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the sections you could not complete and why, and any deviation or open question.
