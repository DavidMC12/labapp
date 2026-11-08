# Task 044: links to the API documentation on the login screen

Assignee: Worker 2. Branch: `w2/api-links`. Reviewer: Supervisor.

**Base.** Branch from `main`.

## Goal

The API now serves its contract at `/api/openapi.json` and an interactive Swagger page at `/api/docs` (task 041), on the same origin as the web app. A person who opens the demo to practice API automation should find them without reading the repository. The login screen already shows the demo users, so add the two links there, in the same quiet style.

## Read first

`frontend/src/app/login/page.tsx` (the demo users box under the form), its tests (`page.test.tsx`, `page.theme.test.tsx`, `page.expired.test.tsx`), `frontend/src/components/ui/Link.tsx`, `frontend/src/lib/testid.ts`, `docs/AUTOMATION_GUIDE.md` (part 2, where the API is described), `frontend/next.config.ts` (the `/api` rewrite).

## Scope

You may edit files only under `frontend/`: the login page, its tests, the README. No new dependencies. Do not change any existing `data-testid` or text.

## Requirements

1. Under the demo users box (inside the same column, after the box), a short paragraph "Para probar la API:" with two links: "Documentación interactiva" to `/api/docs` and "Contrato OpenAPI" to `/api/openapi.json`. They are plain anchors (not the Next.js client router: the targets are served by the API, so a client-side navigation would 404), opened in the same tab, with the existing link style (`Link` variant or an `<a>` with the same classes if `Link` forces the router: check and say which in the report). Ids: `auth-login-api-docs-link`, `auth-login-api-contract-link`; the paragraph `auth-login-api-text`.
2. The skip link, the heading, the form and every existing id and text stay exactly as they are; the new block is after the demo users box in the DOM order (so the tab order of the form does not change).
3. Tests: both links with their `href`, their text and ids, their position after the demo box, that they are plain anchors (no `data-nextjs-router` behavior: assert the `href` attribute and that clicking does not call the mocked router), and every existing login test still passes.
4. The static audit and the browser audit pass in both themes (the login state is audited: the supervisor regenerates the catalog afterwards, tell him that it changes).
5. README: one sentence in the login notes.

## Acceptance criteria

From `frontend/`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage`, `pnpm build` all pass (the coverage floor must hold); from the repository root `node tools/audit/testid-audit.mjs` and `node tools/audit/docs-lint.mjs` report no problem.

## Rules for this task

- Commit as you go, in small real steps (about 4 to 6 commits). Conventional Commits, in English.
- Do not add `Co-Authored-By` or any tool-attribution line. Do not change the git identity.
- Do not push. Do not merge. Do not touch `main`.
- Use paths relative to your working directory. Your copies of the project documents are in `.context/` (ignored by git; never stage them).
- If the spec is ambiguous, do not guess: write the question in your report.
- When done, reply with: the branch, the commit range, the exact commands you ran with their exit codes, and any deviation or open question.
