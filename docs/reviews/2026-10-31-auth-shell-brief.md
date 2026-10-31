# Review: auth shell brief (2026-10-31)

- **Scope:** three documentation commits: the API role values in `docs/SPEC.md`, the record of the test id contract review, and the brief `docs/tasks/005-frontend-auth-shell.md`.
- **Reviewer:** a second agent, read-only, run in the background at the same effort level as the author.
- **Verdict:** With fixes. No Critical findings. The reviewer checked all 26 test ids against the pattern (valid, unique, right kinds), the consistency of the brief with SPEC sections 2, 3, 7 and 8, and the feasibility of the proposed route structure in the existing code base.

## Important findings and what happened to them

| # | Finding | Disposition |
|---|---|---|
| 1 | "Refreshes `me` on login" invites a login bounce: after a first 401 the cache holds `null`, and the shell reads it before the refetch ends. | Fixed in the brief: the login writes the user with `setQueryData` before navigating, logout clears the cache, and a test drives the whole sequence. |
| 2 | Failure paths other than a 401 on `useMe` (other errors, failed logout, network errors, an unmatched 422) were undefined. | Fixed: one rule for each, `retry: false`, and no `/api` rewrite in this task. |
| 3 | The `apiFetch` contract omitted `Content-Type: application/json`, so real logins would fail with 422 while mocked tests passed; its options and the "is a problem document" criterion were open. | Fixed: headers, options and the criterion are defined and tested. |
| 4 | The login form behavior was left to guesswork (native validation, double submit, error clearing, trimming, focus, `replace`, alert role, autocomplete). | Fixed: a behavior list in the brief. |

## Minor findings

Applied: the demo box title and its test id, the order of the demo entries, the single `<main>` owned by the shell, the placeholder page paths, the exact dependency command, the file that holds the auth types, the decision that an expired session redirects silently for now, the stable router mock and `retry: false` in tests, and the punctuation of the SPEC sentence. The `Role` values used by task 003 were checked against the API values and match.

Declined to judge by the reviewer: running the acceptance commands (read-only review), the header layout at phone width, and the choice of mocked `fetch` over a mock server.
