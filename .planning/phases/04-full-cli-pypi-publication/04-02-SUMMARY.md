---
phase: 04-full-cli-pypi-publication
plan: "02"
subsystem: packaging
tags: [pyproject, pep639, license, readme, semantic-release, packaging]

# Dependency graph
requires:
  - phase: 04-full-cli-pypi-publication
    provides: nothing — 04-02 is independent of 04-01 (Wave 1, disjoint files)
provides:
  - pyproject.toml at v1 publication quality (PEP 639 license, classifiers, keywords, URLs, TestPyPI index, [tool.semantic_release] config)
  - LICENSE file (LGPL-3.0-or-later full text)
  - README.md expanded into a PyPI landing page
  - uv.lock in sync with the typer[all]->typer dependency change
affects: [04-03, 04-04]

# Tech tracking
tech-stack:
  added: []
  removed: ["typer[all] extra (-> plain typer)"]
  patterns:
    - "python-semantic-release consumed via uvx, NOT a project dependency (avoids its click~=8.1 cap)"
    - "PEP 639: license = SPDX string + license-files = [\"LICENSE\"] (legacy dict form removed)"

key-files:
  created:
    - LICENSE
  modified:
    - pyproject.toml
    - uv.lock
    - README.md

key-decisions:
  - "D-04: first published version stays 0.1.0 (unchanged in pyproject.toml)"
  - "D-08: [tool.semantic_release] config added to pyproject.toml; PSR runs via uvx, not as a dep"
  - "D-10: README.md expanded into a 7-section PyPI landing page"
  - "D-11: PEP 639 SPDX license + license-files + classifiers/keywords/URLs; LICENSE file added; no License:: classifier"
  - "D-12: typer[all] changed to plain typer; pyproject.toml + uv.lock committed together"

patterns-established:
  - "Release tooling (PSR) is isolated via uvx so it cannot constrain the library's runtime dependency tree"

requirements-completed: [DIST-01]

# Metrics
duration: 12min
completed: 2026-05-19
---

# Phase 04 Plan 02: Package Metadata Pass Summary

**Brought pyproject.toml to v1 publication quality (PEP 639 license, classifiers, keywords, URLs, TestPyPI index, semantic-release config), added the LGPL-3.0 LICENSE file, and expanded README.md into a proper PyPI landing page.**

## Performance

- **Duration:** ~12 min (including recovery from two content-filtered subagent attempts)
- **Completed:** 2026-05-19
- **Tasks:** 2
- **Files modified:** 3, created: 1

## Accomplishments

- `pyproject.toml`: legacy `license = { text = ... }` replaced with PEP 639 `license = "LGPL-3.0-or-later"` + `license-files = ["LICENSE"]`; added 7 classifiers (no `License ::`), keywords, `[project.urls]`, `[[tool.uv.index]]` for TestPyPI, and `[tool.semantic_release]` config
- `typer[all]>=0.13` → `typer>=0.13` (D-12 — the `[all]` extra is no longer published); `uv.lock` regenerated and committed in the same commit
- `LICENSE` file created with the full LGPL-3.0-or-later text (304 lines, fetched from the SPDX license-list-data repository); verified to land in the built wheel at `dist-info/licenses/LICENSE`
- `README.md` expanded from 35 lines into a 7-section PyPI landing page: description, Installation, CLI Usage (4 examples), Table Coverage (10-row table), Strict vs. Lenient, Browser PWA, License
- `.gitignore` security gate confirmed — `pii-test-data/`, `dist/`, `*.whl` all present before any public push (D-07)

## Task Commits

1. **Task 1: pyproject.toml metadata pass + uv.lock sync** — `93e1ca6` (chore)
2. **Task 2: LICENSE + README expansion + .gitignore verify** — `3997aa3` (docs)

## Decisions Made

- D-04 / D-10 / D-11 / D-12 satisfied as specified.
- D-08: PSR config lives in `pyproject.toml` but PSR is **not** a project dependency — see Deviations.

## Deviations from Plan

### Significant — affects downstream plans

**1. python-semantic-release removed from the dev dependency group; consumed via `uvx` instead.**
- **Found during:** Task 1 — after `uv lock` included `python-semantic-release>=10.5`, 6 CLI tests in `tests/test_cli.py` failed with `ValueError: stderr not separately captured`.
- **Root cause:** `python-semantic-release 10.5.3` pins `click~=8.1.0`. Declaring PSR as a project dep forced the whole resolved environment down to `click 8.1.8`. The Phase 1–3 CLI test suite uses the click 8.2+ `result.stderr` API, which raises `ValueError` on click 8.1.
- **Fix:** Removed `"python-semantic-release>=10.5"` from `[dependency-groups] dev`. The `[tool.semantic_release]` config block remains in `pyproject.toml` (PSR reads it regardless of how it is launched). `uv lock --upgrade-package click` restored `click 8.4.0`; all 128 tests pass.
- **Why this is correct:** A release-time tool must not constrain the library's runtime dependency tree. `uvx python-semantic-release` runs PSR in an isolated ephemeral environment with its own `click 8.1` — the project keeps `click 8.4`. This matches CLAUDE.md's stack guidance ("uvx is the modern pipx replacement for CLI tool consumption").
- **Downstream impact:** Plan 04-03 (`release.yml`) and Plan 04-04 (Task 3, the PSR release run) MUST invoke PSR via `uvx python-semantic-release ...` (or `uv tool run`), **not** `uv run semantic-release ...` — `uv run` would not find PSR since it is no longer a project dep.
- **must_haves note:** This violates the literal 04-02 truth "python-semantic-release>=10.5 is in the dev dependency group". That truth, as written, is unimplementable without breaking the CLI test suite; the intent (PSR available for releases, config in pyproject.toml) is fully met via uvx.

**Total deviations:** 1 significant (dependency-architecture correction, documented above).

## Issues Encountered

- Two `gsd-executor` subagents were terminated by an `API Error: Output blocked by content filtering policy` on their final return message after doing partial work. Their uncommitted partial edits were discarded and 04-02 was completed via inline execution by the orchestrator.
- `gnu.org` is unreachable from this environment; the LGPL-3.0 text was fetched from the SPDX `license-list-data` GitHub mirror instead (canonical, identical text).

## User Setup Required

None for this plan. (Trusted-publisher registration and the GitHub repo are handled in Plan 04-04.)

## Next Phase Readiness

- DIST-01 packaging metadata is publication-ready: `uv build` produces a valid wheel + sdist with PEP 639 license metadata and the LICENSE file included.
- Plan 04-03 can proceed — but its `release.yml` must call PSR via `uvx` (see Deviation 1).

---
*Phase: 04-full-cli-pypi-publication*
*Completed: 2026-05-19*
