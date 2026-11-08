# Task 042: a documentation linter in CI

Assignee: Worker 2. Branch: `w2/docs-lint`. Reviewer: Supervisor.

**Base.** Branch from `main` after the automation guide (task 040) is merged (the supervisor tells you), or on top of your current branch until then.

## Goal

The documents are part of the product (the owner's tests rely on them), and they rot silently: a renamed test id, a moved file, a broken link. Add a small Node tool that checks the Markdown of the repository for the mistakes that can be found mechanically, and run it in CI. It reads files only; it needs no application and no browser.

## Read first

`tools/audit/README.md`, `tools/audit/testid-audit.mjs` (how it reads the grammar from `frontend/src/lib/testid.ts` and how the tests of the tool are written: `tools/audit/testid-audit.test.mjs`), `docs/TESTIDS.md`, `docs/AUTOMATION_GUIDE.md`, `.github/workflows/ci.yml` (the frontend job, where the other audits run).

## Scope

You may create `tools/audit/docs-lint.mjs` and `tools/audit/docs-lint.test.mjs`, edit `tools/audit/README.md` and `.github/workflows/ci.yml` (only to add the step in the frontend job next to the test id audit, and the new test file to the existing `node --test` line), and fix **only broken links and wrong ids inside the Markdown files** that the linter finds (each fix in its own commit; do not rewrite prose). No new dependencies: Node's standard library only.

## Requirements

1. **What it checks**, over every `*.md` under the repository root except `node_modules`, `.git`, `.next`, `docs/reviews/` and `docs/tasks/` (those are historical records and briefs):
   - **Links.** Every relative Markdown link `[text](path)` and `[text](path#anchor)` points to an existing file or directory; when there is an anchor and the target is a Markdown file, the anchor matches a heading of that file (GitHub's slug rule: lower case, spaces to hyphens, punctuation removed). Absolute URLs and `mailto:` are not fetched; a link to a path outside the repository is an error.
   - **Test ids.** Every inline code span that matches the test id grammar (the pattern is read from `frontend/src/lib/testid.ts`, one definition) is either present in `docs/TESTIDS.md` or in a literal id of the frontend source (the same set the static audit knows), or is a documented template (it contains `{` and `}`, or ends with `-N`). A span that matches the grammar but exists nowhere is an error with the file and line.
   - **Code fences.** Every fence that is opened is closed.
   - **Tables.** Every row of a table has the same number of cells as its header (escaped pipes aside).
2. **Output.** One line per problem (`file:line message`), a summary, exit code 1 when there is any problem, 0 otherwise. `--json` prints the list.
3. **Tests** (`docs-lint.test.mjs`, `node --test`): run the linter on small temporary directories (the tool takes `--root <dir>`): a good tree passes; a broken link, a broken anchor, an unknown test id, an unclosed fence and a ragged table each fail with the right message; a template id and an id of the catalog pass; the excluded folders are skipped.
4. **CI.** A step "Documentation lint" in the frontend job: `node tools/audit/docs-lint.mjs`. The repository must pass it: run it, fix what it finds in the documents (separate commits), and report the number of problems found and fixed.
5. **Docs.** A "Documentation lint" section in `tools/audit/README.md`.

## Acceptance criteria

From the repository root: `node --test tools/audit/testid-audit.test.mjs tools/audit/browser-audit.test.mjs tools/audit/docs-lint.test.mjs`, `node tools/audit/testid-audit.mjs` and `node tools/audit/docs-lint.mjs` all exit 0; from `frontend/`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` pass.

## Rules for this task

- Commit as you go, in small real steps (about 8 to 12 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, the problems the linter found in the existing documents and what you did about each, and any deviation or open question.
