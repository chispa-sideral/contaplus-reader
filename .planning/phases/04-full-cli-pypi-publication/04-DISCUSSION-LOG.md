# Phase 4: Full CLI & PyPI Publication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 4-full-cli-pypi-publication
**Areas discussed:** stdout report depth, PyPI publish flow, micropip validation, PyPI page & metadata

---

## stdout Report Depth

### What should the CLI print on success?

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-line block, always | A short block every run: per-table row counts, skipped-memo count, problem count | ✓ |
| One line normally, expand on problems | Keep the one-liner for clean conversions; expand only on skips/problems | |
| Keep the one-line summary | Current behavior, lightly extended | |

### How should problem entries appear on stdout?

| Option | Description | Selected |
|--------|-------------|----------|
| Count + pointer to Problemas sheet | e.g. "12 problems — see the Problemas sheet" | |
| First few inline, then "… and N more" | Capped preview of ~5 entries | |
| List every problem entry inline | table/row/column/reason for every problem on stdout | ✓ |

### Row counts — journal only, or every extracted table?

| Option | Description | Selected |
|--------|-------------|----------|
| Every extracted table | One line per extracted table with its row count | ✓ |
| Journal rows + sheet count only | Journal row count + total sheet count, as today | |

**User's choice:** Multi-line block always; every problem entry inline; per-table row counts.
**Notes:** The user accepted that listing every problem entry can make the report long on a messy archive — full detail on stdout was the deliberate choice over a terse count-and-pointer.

---

## PyPI Publish Flow

### Before the real PyPI publish, do a TestPyPI dry-run?

| Option | Description | Selected |
|--------|-------------|----------|
| TestPyPI dry-run first | Upload to test.pypi.org, verify page + install, then publish for real | ✓ |
| Publish straight to PyPI | Skip the test index | |

### How is the package pushed to PyPI?

| Option | Description | Selected |
|--------|-------------|----------|
| Local `uv publish` with a token | Marc runs uv build + uv publish with a PyPI token | |
| GitHub Actions trusted publishing (OIDC) | CI publishes via PyPI trusted-publisher — no stored token | ✓ |

### Confirm the first published version

| Option | Description | Selected |
|--------|-------------|----------|
| 0.1.0 | Keep pyproject.toml; pre-1.0; matches PROJECT.md "v0.1 release" | ✓ |
| 1.0.0 | Signals a stable committed public API from day one | |

### What triggers the publish workflow?

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Release published | Creating a Release fires the workflow | |
| Manual workflow_dispatch | Click "Run workflow" in the Actions tab | |
| Version tag push (v0.1.0) | Pushing a `v*` tag triggers publish | |
| Other (free text) | "We shall adopt changesets or similar" | ✓ |

### How literal should "changesets" be for this Python/PyPI project?

| Option | Description | Selected |
|--------|-------------|----------|
| Changeset-style, Python-native tool | Keep the changesets model; research picks the best PyPI-fit tool | ✓ |
| @changesets/cli itself | Add a Node devtool layer to drive a Python package | |
| Conventional-commit-driven | Derive version + changelog from commit history, no fragment files | |

### This repo has no GitHub remote — create the GitHub repo this phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — public repo | Public repo marcfargas/contaplus-reader, push develop + main | ✓ |
| Yes — private for now | Private repo, flip to public before/at release | |
| No — handle separately | Repo creation/push out of this phase | |

**User's choice:** TestPyPI dry-run → GitHub Actions trusted publishing (OIDC); version 0.1.0; changeset-style release flow driven by a Python-native tool (tool TBD by research); a new public GitHub repo created this phase.
**Notes:** The user answered the trigger question with "We shall adopt changesets or similar" — a release-fragment-driven flow. Clarified to mean the changesets *model* (deliberate per-change entries → release step bumps version + regenerates CHANGELOG + cuts a GitHub Release that triggers the publish), with the exact Python-native tool left to research. Trusted publishing (OIDC, no token) was explicitly preferred over local token-based `uv publish`.

---

## micropip Validation

### How rigorous should the micropip-readiness validation be?

| Option | Description | Selected |
|--------|-------------|----------|
| Automated CI smoke test | GitHub Actions job boots Pyodide, micropip-installs the wheel, imports + runs a tiny conversion | ✓ |
| One-off manual Pyodide check | Load Pyodide once, micropip-install, confirm, record the result | |
| Static check only | Assert wheel is py3-none-any with pure-Python deps; never runs micropip | |

**User's choice:** Automated CI smoke test.
**Notes:** Flagged that contaplus-reader depends on pandas, which Pyodide pre-loads via `pyodide.loadPackage` rather than micropip-resolving — a real run catches this, a static check would not. The smoke-test job leverages the GitHub Actions setup already being added for publishing.

---

## PyPI Page & Metadata

### How far do we take the README?

| Option | Description | Selected |
|--------|-------------|----------|
| Proper PyPI landing page | Full project page: what it does, install, CLI examples, table coverage, strict-vs-lenient, PWA link | ✓ |
| Light touch-up | Fix accuracy, add a couple of examples, no restructure | |
| Leave as-is | Current README is enough to publish | |

### How much package metadata work?

| Option | Description | Selected |
|--------|-------------|----------|
| Full metadata pass | LICENSE file, classifiers, keywords, project URLs, PEP 639 SPDX license form | ✓ |
| LICENSE + URLs only | LICENSE file + project URLs; skip classifiers/keywords | |
| LICENSE file only | Just the LICENSE file; leave pyproject.toml as-is | |

**User's choice:** README expanded to a proper PyPI landing page; full metadata pass.
**Notes:** Flagged that no LICENSE file exists in the repo — non-negotiable for the LGPL-3.0 release regardless of choice. The `typer[all]→typer` cleanup (flagged in STATE) is folded in as a known fix. CHANGELOG.md is generated by the changeset tool from the publish-flow discussion, not hand-written.

## Claude's Discretion

- Exact wording / layout / column alignment of the multi-line stdout report.
- The exact LICENSE filename and the precise classifier / keyword strings.
- README section ordering and example depth.
- Whether the micropip smoke test installs from a local wheel or the published artifact.
- GitHub Actions workflow file structure (one workflow vs separate jobs).

## Deferred Ideas

None — discussion stayed within Phase 4 scope (CLI-03 + DIST-01).
