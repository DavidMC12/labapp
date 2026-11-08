# Review: dependency audit and Dependabot (task 064, 2026-11-08)

- **Branch:** `w1/dependency-audit`, by Worker 1 (4 commits: `.github/dependabot.yml`, the audit record `docs/reviews/2026-11-08-dependency-audit.md`, the inventory of the workflow actions and a paragraph in `docs/DEVELOPMENT.md`).
- **Reviewer:** Supervisor.
- **Verdict:** Ready to merge. No Critical or Important findings.
- **Result of the audit:** the production dependencies of the web app: no known vulnerabilities; the backend (46 pinned distributions): no known vulnerabilities; one **moderate** advisory in a development-only tool (`minimatch` 10.2.6 through `eslint-config-next`, GHSA-g3hv-75wg-m249: it never reaches the deployed application, and the fix needs a major version of a transitive dependency). Nothing was upgraded because no finding met the upgrade rule of the brief; the decision and the reason are in the record.
- **Verified by the supervisor:** both audits were re-run and gave the same numbers (`pnpm audit --prod` clean, `pnpm audit` one moderate, `pip-audit` on the locked set clean); `dependabot.yml` parses and declares `npm` for `/frontend`, `uv` for `/backend` and `github-actions`, weekly on Monday, grouped minor and patch updates, at most 5 pull requests per ecosystem and the commit prefix `build` with the scope, so a bot commit such as `build(deps): ...` matches the Conventional Commits check of the CI; the record has no local path or secret.

## Findings and what happened to them

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Note | The root of the repository has no `package.json`, so Dependabot has a single npm entry. | Accepted. |
| 2 | Note | The `uv` ecosystem of Dependabot is recent; if GitHub rejected it, the fallback is `pip` for `/backend`. | Accepted; the first Dependabot run will show it. |
| 3 | Note | The workflow actions are referenced by version tag, not by commit SHA. | Left for Dependabot, which keeps a pinned reference up to date; recorded in the audit. |
