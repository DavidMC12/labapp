# Review: customers contract and briefs (2026-11-04)

- **Scope:** the "Customers API" subsection of `docs/SPEC.md`, the briefs `docs/tasks/010-backend-customers.md` and `docs/tasks/011-frontend-customers.md`, the CI brief and two review records.
- **Reviewer:** a second agent, read-only, run in the background at the same effort level as the author.
- **Verdict:** With fixes. No Critical findings. The reviewer checked all test ids against the pattern, the consistency of the contract with the seed data, the permission matrix and the concurrency rules, and read the existing error handler to confirm which codes the briefs would really produce.

## Important findings and what happened to them

| # | Finding | Disposition |
|---|---|---|
| 1 | Brief 010 depended on code not yet on `main` and did not say how to build the test application or reset customers between tests. | Fixed: a base line, the test recipe, module-scoped logins and a reachable repository in `app.state`. |
| 2 | The order of checks contradicted the spec: validation was reached before the 404. | Fixed: a dependency after the permission check loads the customer; the order inside the port is fixed; tests for each case. |
| 3 | The port contract was too loose for PostgreSQL (untyped arguments, atomicity only for update, LIKE wildcards in `q`, search normalization, numeric bounds, NUL characters, sequence reset). | Fixed: typed arguments with absent versus null, atomic `add` and `update`, literal `q`, a normative normalization stored at write time, bounds, NUL rule and sequence reset. |
| 4 | Undefined cases (empty required fields, several errors per field, character sets, email shape, `page` errors, unknown fields, path parameter name, create body typing). | Fixed in the spec and the brief. |
| 5 | The edit form could send a newer version than the values it showed and silently overwrite another user's change. | Fixed: the version is captured when the form is initialized or reset. |
| 6 | The list request URL was undefined and an empty `status=` would be a 422 from the real API. | Fixed: `URLSearchParams`, with empty parameters omitted. |
| 7 | A page beyond the last showed an empty state next to "Página 99 de 3". | Fixed: the URL is replaced by the last page. |
| 8 | After a 409 on the detail page every click repeated the stale `If-Match`. | Fixed: refetch after a failed status change. |
| 9 | The query key used a string id in some places and a number in others. | Fixed: one numeric id parsed with a strict pattern. |

Minor findings applied: the permission and invalid-id alerts have test ids, `Textarea` forwards a `ref`, a 401 clears the session entry, the `Z` timestamp suffix is tested, and the null rule for create bodies is stated. Deferred: keeping the list filters when returning from the detail page, and the deployment documents that still mention Render.
