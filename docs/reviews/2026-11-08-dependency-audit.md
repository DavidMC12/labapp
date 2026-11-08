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

## Workflow actions

Every `uses:` of `.github/workflows/*.yml`:

| Workflow | Action | Version tag | Pinned to a full commit SHA? |
|---|---|---|---|
| `ci.yml` (backend job) | `actions/checkout` | `v7.0.1` | Yes: `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `ci.yml` (backend job) | `jdx/mise-action` | `v5.2.0` | Yes: `9b200bcecbfd6303e69a4a261b2e09e3757440a7` |
| `ci.yml` (frontend job) | `actions/checkout` | `v7.0.1` | Yes: `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `ci.yml` (frontend job) | `jdx/mise-action` | `v5.2.0` | Yes: `9b200bcecbfd6303e69a4a261b2e09e3757440a7` |
| `ci.yml` (browser-audit job) | `actions/checkout` | `v7.0.1` | Yes: `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `ci.yml` (browser-audit job) | `jdx/mise-action` | `v5.2.0` | Yes: `9b200bcecbfd6303e69a4a261b2e09e3757440a7` |
| `commit-standards.yml` | `actions/checkout` | `v4` | No: a movable tag. |
| `nightly-reset.yml` | — | — | No action is used (the job runs `curl` in a shell step). |

Recommendation: pin the remaining `actions/checkout@v4` to a full commit SHA as well, and keep every
pin current through the `github-actions` entry of Dependabot. The workflows were not changed in this
task, as the brief requires.

## Dependabot (`.github/dependabot.yml`)

The file declares `version: 2` and three entries: `npm` for `/frontend`, `uv` for `/backend` and
`github-actions` for `/`. The current Dependabot documentation lists `uv` as a supported ecosystem
(its supported-versions column says `v0.11`, while this repository pins uv 0.13.6 in `mise.toml`; the
lockfile format is the one Dependabot reads). If Dependabot ever rejects the `uv` entry, the fallback
is `pip` for `/backend`, at the cost of reading only the Python requirements and not the `uv` lock.

There is no root `package.json`, so no npm entry is needed for `/`; only `/frontend` has one.

Why each key is there:

| Key | Why |
|---|---|
| `version: 2` | The only configuration syntax Dependabot accepts. |
| `package-ecosystem` | One entry per manager: `npm`, `uv` and `github-actions`. |
| `directory` | The manifest and lockfile live in `frontend/` and `backend/`; the actions live in the repository root. |
| `schedule.interval: weekly` + `day: monday` | A weekly check on Monday, as the task requires; it keeps the pull-request volume low. |
| `open-pull-requests-limit: 5` | At most five open pull requests per ecosystem, so the board stays readable. |
| `groups` | `npm-minor-patch`, `uv-minor-patch` and `actions-minor-patch` collect every minor and patch update of an ecosystem into one pull request; major updates still arrive separately. |
| `commit-message.prefix: "build"` + `include: scope` | The bot writes `build(deps): ...` (or `build(deps-dev): ...` for development dependencies), which satisfies Conventional Commits and the subject check of `commit-standards.yml`. |

The YAML was validated with `python3 -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`,
which exited 0.
