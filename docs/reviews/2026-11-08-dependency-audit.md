# Dependency audit (task 064, 2026-11-08)

- **Branch:** `w1/dependency-audit`, by Worker 1.
- **Scope:** the two ecosystems of the repository (`frontend/` and `backend/`), the versions of the
  workflow actions and Dependabot. No feature and no runtime dependency were added.
- **Result:** one moderate finding, in a development-only tool; nothing was upgraded because no finding
  met the upgrade rule; Dependabot is configured to watch the three ecosystems.

## Commands run (2026-11-08)

From `frontend/`, after `pnpm install --frozen-lockfile` (exit 0):

| Command | Exit code | Result |
|---|---|---|
| `pnpm audit --prod` | 0 | No findings in the production dependencies. |
| `pnpm audit` | 1 | One moderate finding (the table below). The command exits 1 when it reports anything. |

From `backend/`, without adding anything to the project:

```bash
uv export --frozen --no-hashes --output-file "$TMPDIR/labapp-requirements.txt"
uvx pip-audit -r "$TMPDIR/labapp-requirements.txt"
```

| Command | Exit code | Result |
|---|---|---|
| `uv export --frozen --no-hashes` | 0 | 46 pinned distributions (runtime and development groups), written outside the repository. |
| `uvx pip-audit -r ...` | 0 | No known vulnerabilities. `labapp-backend` itself is skipped because it is local and not published on PyPI; the skip is expected. |

`pip-audit` reached its advisory service from this machine (it downloaded its environment and audited
every distribution), so no alternative tool was needed and no result was inferred.

## Frontend findings

`pnpm audit --prod`: 0 findings. The table covers `pnpm audit` (all dependencies).

| Package | Installed | Advisory | Severity | Kind | Reachable in this app? | Fixed |
|---|---|---|---|---|---|---|
| `minimatch` | 10.2.6 | GHSA-g3hv-75wg-m249 (CVE-2026-118764) | Moderate | Build/dev only: `eslint-config-next` → `typescript-eslint` → `@typescript-eslint/typescript-estree` → `minimatch`. It is absent from the production install (`pnpm audit --prod` does not see it). | **No.** The advisory is a denial of service through a glob pattern controlled by the caller (`firstPhasePreProcess`). The only caller is ESLint, which runs on the developer machine and in CI over the static patterns of `eslint.config.mjs` and the ignore lists; no pattern comes from a request, and ESLint is not part of the deployed Next.js runtime. | 11.0.1 |

`minimatch` 3.1.5 also appears in the tree (through older ESLint internals); the advisory affects
`>= 7.0.0 < 11.0.1`, so 3.1.5 is not affected.

**Decision: not upgraded.** It is a development-only tool with no reachable path, and the fix requires a
major jump from 10 to 11 inside a transitive dependency; forcing it with a package-manager override
could break ESLint. Dependabot will open the update when `eslint-config-next` and
`typescript-eslint` adopt `minimatch` 11.

## Backend findings

`uvx pip-audit`: 0 findings. The locked set (`backend/uv.lock`) is therefore clean at the time of the
run; there is nothing to record in a table.

## What was upgraded

Nothing. No finding was a patch or minor upgrade of a runtime dependency, and no High or Critical
finding was reachable, so the upgrade rule of the task did not apply. Both lockfiles are untouched and
still install with `pnpm install --frozen-lockfile` and `uv sync --frozen`.

## Numbers

| Ecosystem | Before (all severities) | After | Upgraded |
|---|---|---|---|
| Frontend, production (`pnpm audit --prod`) | 0 | 0 | 0 |
| Frontend, all dependencies (`pnpm audit`) | 1 moderate | 1 moderate | 0 |
| Backend (`pip-audit`) | 0 | 0 | 0 |
