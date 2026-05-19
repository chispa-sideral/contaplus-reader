---
phase: 04-full-cli-pypi-publication
plan: "03"
subsystem: ci
tags: [ci, github-actions, trusted-publishing, pyodide, micropip, oidc]

# Dependency graph
requires:
  - phase: 04-full-cli-pypi-publication
    plan: "02"
    provides: "pyproject.toml with [[tool.uv.index]] testpypi block — required by uv publish --index testpypi"
provides:
  - ".github/workflows/release.yml — trusted-publishing CI pipeline triggered on GitHub Release"
  - "ci/smoke.mjs — Pyodide Node.js micropip smoke test"
  - "ci/package.json — pyodide@0.29.4 pinned dependency"
affects: [04-04]

# Tech tracking
tech-stack:
  added:
    - "pyodide@0.29.4 (npm, CI only) — Node.js Pyodide runtime for micropip smoke test"
  patterns:
    - "OIDC trusted publishing: id-token: write at job level only (testpypi + pypi jobs)"
    - "Four-job sequential pipeline: build -> testpypi -> pypi -> micropip-smoke"
    - "smoke.mjs WHEEL_URL fallback: process.env.WHEEL_URL || 'contaplus-reader' for pre/post PyPI publish"
    - "PSR invoked via uvx (NOT uv run) — PSR is not a project dependency per 04-02 deviation"

key-files:
  created:
    - .github/workflows/release.yml
    - ci/smoke.mjs
    - ci/package.json

key-decisions:
  - "D-06 satisfied: OIDC trusted publishing with id-token:write at job level; environment gating for testpypi and pypi; no stored token"
  - "D-09 partially satisfied: ci/smoke.mjs + ci/package.json committed; full gate fires after real PyPI publish in Plan 04-04"
  - "PSR release step (if added to workflow) must use uvx python-semantic-release, not uv run semantic-release"

patterns-established:
  - "release.yml micropip-smoke job uses npm install + node smoke.mjs in ci/ working-directory"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-05-19
---

# Phase 04 Plan 03: CI Infrastructure — Release Workflow & Micropip Smoke Test

**Created the GitHub Actions trusted-publishing release pipeline (`.github/workflows/release.yml`) and the Pyodide Node.js micropip smoke test (`ci/smoke.mjs` + `ci/package.json`), implementing D-06 (OIDC trusted publishing) and D-09 (micropip-readiness CI gate).**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-05-19
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- `.github/workflows/release.yml`: four-job pipeline (build → testpypi → pypi → micropip-smoke); `id-token: write` at job level only on `testpypi` and `pypi` jobs; no workflow-level `permissions:` block; triggers on `release: types: [created]`; testpypi job uses `uv publish --index testpypi --trusted-publishing always` with `environment: name: testpypi`; pypi job uses `uv publish --trusted-publishing always` with `environment: name: pypi`; micropip-smoke uses `actions/setup-node@v4 node-version: '22'`, `npm install pyodide@0.29.4` and `node smoke.mjs` both in `working-directory: ci/`
- `ci/package.json`: private=true, type=module, pyodide pinned to "0.29.4"
- `ci/smoke.mjs`: ES module; loads micropip via `pyodide.loadPackage("micropip")`; reads `process.env.WHEEL_URL` with fallback to `"contaplus-reader"` (supports both local pre-publish and CI post-publish scenarios); imports `contaplus_reader`, `read`, `ContaPlusReadError`; `.catch((e) => { console.error(e); process.exit(1); })`
- `uv run pytest -q`: 128 tests pass — no regressions

## Task Commits

1. **Task 1: Create .github/workflows/release.yml** — `3c5cdb0`
2. **Task 2: Create ci/smoke.mjs and ci/package.json** — `96d49a7`

## Decisions Made

- D-06 implemented: OIDC trusted publishing pipeline committed and ready for the GitHub push in Plan 04-04.
- D-09 infrastructure committed: smoke test will run automatically after each PyPI publish. Full D-09 gate validation occurs in Plan 04-04.
- Pipeline structure implements D-05 TestPyPI dry-run gate: testpypi job must succeed before pypi job runs.

## Deviations from Plan

None — plan executed exactly as written.

The critical deviation carried from 04-02 (PSR not a project dependency; use `uvx python-semantic-release`) was already accounted for in the plan. The release.yml as written does NOT invoke PSR — that step is in Plan 04-04 (human-triggered release). No PSR invocation was needed in this plan's files.

## Known Stubs

None. Both files are complete and functional. ci/smoke.mjs requires a live PyPI publish to run end-to-end (expected — D-09 full gate is Plan 04-04).

## Threat Flags

None. The workflow implements T-04-07 (OIDC, no stored token) and T-04-09 (id-token:write at job level only) mitigations exactly as specified in the threat model.

## Self-Check: PASSED

- `.github/workflows/release.yml`: EXISTS
- `ci/smoke.mjs`: EXISTS
- `ci/package.json`: EXISTS
- Commit `3c5cdb0`: verified
- Commit `96d49a7`: verified
- 128 tests pass
