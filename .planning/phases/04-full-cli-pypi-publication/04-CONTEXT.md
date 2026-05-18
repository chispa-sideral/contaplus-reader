# Phase 4: Full CLI & PyPI Publication - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 is mostly **delivery and distribution** — the reader and the CLI are
already functionally complete (Phases 1–3). It delivers the two remaining v1
requirements:

- **CLI-03** — a fuller stdout report after every conversion (row counts,
  skipped-memo count, problem entries).
- **DIST-01** — the library published to PyPI as `contaplus-reader` under
  LGPL-3.0-or-later, in a wheel that `micropip` can consume.

It also establishes the **micropip-readiness gate** for Phase 5: the published
wheel must be proven installable in a Pyodide environment *before* the PWA
phase begins (ROADMAP Phase 4 success criterion #4).

**Success = all four ROADMAP §"Phase 4" criteria hold:** `pip install
contaplus-reader` installs the library + `contaplus2xlsx` CLI from PyPI;
`--company` selects the right company in a multi-company ZIP (already shipped in
Phase 2 — see Carried Forward); the CLI stdout report covers row counts,
skipped-memo count, and problem entries after every conversion; the published
wheel is `micropip`-installable in Pyodide, validated locally before Phase 5.

**Explicitly NOT in scope (sequenced downstream by the roadmap):**
- The browser PWA itself — drag-drop UI, Cloudflare Pages deploy, service-worker
  caching → **Phase 5**. Phase 4 only proves the wheel is *micropip-ready*.
- Any new reader/table/XLSX capability — the reader is feature-complete after
  Phase 3.
- New CLI flags — the CLI surface is complete; Phase 4 only deepens the report
  body (see Carried Forward).

</domain>

<decisions>
## Implementation Decisions

Per-phase decision numbering — `D-NN` restarts at `D-01` for this phase. Phase
1/2/3 decisions referenced below are cited as "Phase-1 D-NN" etc.

### CLI stdout Report (CLI-03)
- **D-01:** The CLI prints a **multi-line report block on every conversion** —
  strict and lenient alike. This replaces the Phase-1 D-16 one-line summary.
  Realises ROADMAP criterion #3's "reports … after every conversion."
- **D-02:** The report shows **per-table row counts** — one line per extracted
  table with its row count (`Diario`, `Subcuentas`, the group tables,
  `venci`/`prede`/`amoinv`/`nivel`, raw `BALAN`, the two recomputed-balance
  sheets) — matching CLI-03's "row counts" (plural). The **skipped-memo count**
  is reported alongside.
- **D-03:** In lenient mode the report **lists every problem entry inline** on
  stdout — table, row index, column, plain-English reason (the Phase-3 D-06
  problems-entry shape). It is **not** a count-with-pointer-to-the-sheet. The
  user explicitly accepted that a messy archive will produce a long report —
  full detail on stdout was the deliberate choice.
- The report goes to **stdout** (it *is* a report — criterion #3 says "stdout
  reports"); `ContaPlusReadError` panels stay on the **stderr** Rich console
  (Phase-1 D-17). In **strict** mode there are no problem entries (strict aborts
  on the first defect), so the problems section is simply absent — the per-table
  counts and skipped-memo line still print. All report text is **English**
  (Phase-1 D-12 — only XLSX tabs/headers are Spanish).

### PyPI Publication (DIST-01)
- **D-04:** The first published version is **0.1.0** — `pyproject.toml` already
  says so. Pre-1.0 signals the public API may still evolve as the Phase-5 PWA
  and the tax-workbench adapter exercise it; matches PROJECT.md's "v0.1 release"
  wording.
- **D-05:** A **TestPyPI dry-run precedes the real publish** — 0.1.0 goes to
  test.pypi.org first; the project page rendering and an install are verified;
  then it is published to real PyPI. Catches README-rendering / metadata
  mistakes that are permanent once on real PyPI.
- **D-06:** Publishing uses **GitHub Actions trusted publishing (OIDC)** — no
  PyPI API token is stored anywhere. The publish runs in CI via PyPI's
  trusted-publisher mechanism. This requires a GitHub repo, a release workflow,
  and a trusted-publisher configuration on both PyPI and TestPyPI (the latter is
  a human step on the PyPI websites).
- **D-07:** A **public GitHub repository `marcfargas/contaplus-reader`** is
  created as part of this phase — `develop` + `main` pushed. Trusted publishing
  cannot work without it; a public repo is consistent with this being an
  external, public project (public PWA, public PyPI package). `pii-test-data/`,
  `dist/`, and `*.whl` are **already git-ignored** (`.gitignore` lines 4/13/22) —
  the planner must verify this holds before the first push.
- **D-08:** The release flow is **changeset-style, driven by a Python-native
  tool**. The changesets *model* is kept — explicit per-change entries
  accumulate; a **release step consumes them to bump the version, regenerate
  `CHANGELOG.md`, and cut a GitHub Release**; that Release triggers the
  trusted-publishing workflow. It is **not** `@changesets/cli` itself
  (npm-native — rejected to avoid bolting a JS toolchain onto a Python package)
  and **not** pure conventional-commit derivation. The exact tool is **Open for
  Research** (see below).
- The publish *authorization* is a **human action** — Marc creates the GitHub
  Release / approves the deployment environment. Claude never holds or handles a
  PyPI token (OIDC removes the token entirely); the trusted-publisher setup on
  (Test)PyPI is also a human step.

### micropip-Readiness Gate (Success criterion #4)
- **D-09:** Criterion #4 is validated by an **automated CI smoke test** — a
  GitHub Actions job boots Pyodide, `micropip.install`s the `contaplus-reader`
  wheel, imports `contaplus_reader`, and runs a tiny end-to-end conversion.
  Repeatable and regression-guarding; it exercises real dependency resolution,
  not just a static prediction. It leverages the GitHub Actions setup already
  being added for publishing (D-06).
- **Known wrinkle (research):** `contaplus-reader` depends on `pandas`, which
  Pyodide **pre-loads via `pyodide.loadPackage`** rather than micropip-resolving
  from PyPI. The smoke test must load `pandas`/`numpy` the Pyodide way *before*
  `micropip.install`-ing the wheel — see Open for Research.

### Package Metadata & PyPI Page (DIST-01)
- **D-10:** The **README is expanded into a proper PyPI landing page** — what
  the library and CLI do, install (`pip` + `uvx`), CLI usage examples for both
  `.dbf` and `.zip` (including `--company` and `--lenient`), the table coverage,
  the strict-vs-lenient distinction, and a forward link to the Phase-5 PWA. The
  README is the PyPI long description. **English** (Phase-1 D-12).
- **D-11:** A **full metadata pass** on `pyproject.toml`:
  - Add a **`LICENSE` file** containing the LGPL-3.0 text — **none exists in the
    repo today**; it is mandatory for an LGPL-3.0-or-later release.
  - Add PyPI **classifiers** (license, Python 3.13, accounting/financial topic,
    development status), **keywords** (`contaplus`, `sage`, `dbf`, `accounting`,
    `xlsx`, …), and **project URLs** (Repository, Issues).
  - **Modernize the license declaration** from the legacy
    `license = { text = "LGPL-3.0-or-later" }` form to the PEP 639 SPDX string +
    `license-files`.
- **D-12:** Fold in the **`typer[all]` → `typer` cleanup**. STATE flagged that
  `typer[all]` is no longer a published extra as of typer 0.25.1 (Rich is
  bundled by default) and it emits a `uvx` warning. Phase 4 owns the published
  dependency metadata, so it changes `pyproject.toml` to plain `typer`. Commit
  `pyproject.toml` **and** `uv.lock` together (lockfile discipline).
- **D-13:** `CHANGELOG.md` exists and is **generated/maintained by the D-08
  release tool** — not hand-written. Its initial 0.1.0 entry is produced by the
  first release run.

### Carried Forward (locked by earlier phases — not re-discussed)
- `read()` is the single bytes-first entry point; signature additive-only, no
  filesystem-path argument ever (Phase-1 D-06).
- The CLI surface is otherwise complete: `--company` (Phase-2 D-07, which
  reassigned **CLI-02 to Phase 2** — ROADMAP criterion #2 is already satisfied),
  `--force`/`--overwrite` (Phase-1 D-15), `--lenient` (Phase-3 D-01). Phase 4
  adds **no new flags** — only the report body.
- `ContaPlusReadError` is shown as a Rich error panel on **stderr**, no
  traceback, exit code 1 (Phase-1 D-17 / Phase-2 D-08).
- All code, identifiers, CLI `--help`, error text, and report text stay
  **English**; only XLSX sheet tabs/headers are Spanish (Phase-1 D-12,
  Phase-2 D-14).
- Problems-entry shape — table name, row index, column, plain-English reason,
  offending value; `row_index = -1` for file/table-level (Phase-3 D-06). D-03
  renders these.
- `uv build` produces a wheel + sdist; the Phase-1 wheel + `uvx` smoke test
  already proved the build works (Phase-1 DIST-02).
- `pii-test-data/` is confidential, git-ignored, never committed or quoted in
  output (PROJECT.md).

### Claude's Discretion
- Exact wording, layout, and column alignment of the multi-line stdout report;
  table ordering within it; section headers.
- The exact `LICENSE` filename and the precise classifier / keyword strings.
- README section ordering and example depth within "proper landing page."
- Whether the D-09 smoke test installs from a served local wheel or the
  published TestPyPI/PyPI artifact (subject to the pandas-pre-load research
  finding).
- GitHub Actions workflow file structure — one workflow vs. separate
  publish / micropip-smoke-test jobs.

### Open for Research
- **Changeset-style release tool (D-08):** evaluate Python-native tools that
  reproduce the changesets model (explicit per-change entries → a release step
  that bumps the version, regenerates `CHANGELOG.md`, and cuts a GitHub
  Release). Candidates: `release-please` (PR-based, language-agnostic,
  GitHub-Actions-native — closest to the changesets release-PR UX); `towncrier`
  (news-fragment changelog, Python-native); `python-semantic-release`. The tool
  must drive the single `pyproject.toml` version and dovetail with trusted
  publishing.
- **Trusted-publishing wiring (D-06):** the GitHub Actions workflow plus the
  PyPI / TestPyPI trusted-publisher setup — `pypa/gh-action-pypi-publish` vs
  `uv publish` with OIDC, the `id-token: write` permission, GitHub deployment
  environments, and how the TestPyPI dry-run (D-05) fits the same workflow
  (separate job vs manual `workflow_dispatch`).
- **micropip + pandas in Pyodide (D-09):** how the CI smoke test loads
  `pandas`/`numpy` via `pyodide.loadPackage` before `micropip.install`-ing the
  wheel; whether `dbfread` and `openpyxl` resolve cleanly from PyPI via
  micropip; the Pyodide-in-CI harness (node + the `pyodide` npm package, or
  `pytest-pyodide`).
- **PEP 639 license modernization (D-11):** the correct `license` /
  `license-files` form for the `uv_build` backend and current PyPI metadata
  version; confirm `uv_build` emits the SPDX expression correctly.
- **Report ↔ `render()` coupling (D-02):** the per-table row counts should match
  the sheets `render()` actually produces — confirm whether to derive counts
  from `ContaPlusData` attributes or from the rendered workbook (the CLI already
  loads the workbook to count sheets — WR-07).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — scope, constraints, Key Decisions table; note the
  Pyodide/`micropip` PWA dependency and the `pii-test-data/` confidentiality
  rule (relevant to the D-07 public-repo decision).
- `.planning/REQUIREMENTS.md` — Phase 4 requirements **CLI-03** and **DIST-01**;
  note CLI-02 was reassigned to Phase 2 (Phase-2 D-07).
- `.planning/ROADMAP.md` §"Phase 4: Full CLI & PyPI Publication" — phase goal
  and the four success criteria the verifier checks.
- `CLAUDE.md` (repo root) — locked tech stack (Python ≥3.13, uv + uv_build,
  Typer, Rich); the documented `uv build` + `uv publish` PyPI workflow and `uvx`
  consumption; the "What NOT to Use" list.

### Tech / PWA dependency
- `.planning/notes/pwa-lean-stack.md` — the lean PWA stack notes; relevant
  because the D-09 micropip-readiness gate is the Phase-5 dependency this phase
  must clear.
- `SEED.md` — the primary ContaPlus format reference. Less central to Phase 4
  than to Phases 1–3, but it documents the table inventory the D-02 per-table
  report enumerates and the still-open PWA research questions (`micropip`
  resolution, in-browser XLSX) that the D-09 gate touches.

### Prior phase context (carried-forward decisions)
- `.planning/phases/01-journal-slice/01-CONTEXT.md` — D-06 (`read()` signature),
  D-12 (English everywhere except Spanish XLSX headers), D-15 (`--force`),
  D-16 (the one-line summary D-01 now replaces), D-17 (Rich error panel).
- `.planning/phases/02-zip-subaccounts/02-CONTEXT.md` — D-07 (`--company`,
  CLI-02 → Phase 2), D-08 (Rich error panel for multi-company), D-14 (Spanish
  sheet tabs).
- `.planning/phases/03-full-tables-balance-lenient-path/03-CONTEXT.md` —
  D-01 (`--lenient` flag, strict default), D-05/D-06 (problems-report contents
  and entry shape — what D-03 lists on stdout).

### Local validation gate (CONFIDENTIAL — never committed, quoted, or read into output)
- `pii-test-data/` — 5 real ContaPlus backup archives. Not needed for Phase 4
  work (Phase 4 has no schema discovery), but called out because D-07 makes the
  repository **public** — the planner must confirm `.gitignore` keeps this
  directory out of every commit and push.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/contaplus_reader/cli.py`** — the Typer CLI. The closing `typer.echo`
  one-line summary (lines ~123–139) is exactly what D-01/D-02/D-03 replace with
  the multi-line report. It already loads the rendered workbook to count sheets
  (`load_workbook`, WR-07) — the per-table report can extend that pattern.
- **`src/contaplus_reader/models.py`** — `ContaPlusData` (the table container),
  `ContaPlusJournal.rows` / `.skipped_memo`, and the problems-report type with
  its `entries` (table / row / column / reason / value). D-02 and D-03 read
  these directly.
- **`pyproject.toml`** — `version = "0.1.0"`, `[project.scripts]`
  `contaplus2xlsx`, the legacy `license = { text = ... }` form (D-11
  modernizes), the `typer[all]` dependency (D-12 fixes), `uv_build` backend.
- **`README.md`** — minimal (~35 lines); D-10 expands it into the PyPI page.
- **`.gitignore`** — already excludes `pii-test-data/`, `dist/`, `*.whl`
  (lines 4 / 13 / 22) — verified, supports the D-07 public-repo push.

### Established Patterns
- Bytes-first `read()`; Rich error panels on stderr; no traceback on
  `ContaPlusReadError`; `from None` to suppress the traceback chain.
- Conventional-commit messages; per-phase `D-NN` decision numbering.
- `uv build` → wheel + sdist in `dist/` (Phase-1 DIST-02, proven).

### Integration Points
- `cli.py`, end of `main()` — the multi-line report replaces the `typer.echo`
  summary. No new flags, no signature change to `read()` or `render()`.
- **New files**: `.github/workflows/` (publish + micropip smoke-test jobs),
  `LICENSE`, `CHANGELOG.md`, and the changeset tool's config + fragments
  directory.
- `pyproject.toml` + `uv.lock` — metadata and dependency edits, committed
  together.

</code_context>

<specifics>
## Specific Ideas

- **"Changesets or similar" (D-08)** — the user explicitly wants the changesets
  *model* (deliberate per-change entries → a release step that bumps the
  version, regenerates the changelog, and publishes), not raw
  conventional-commit derivation. They are open on the exact Python-native tool,
  having rejected `@changesets/cli` itself as too npm-coupled for a Python
  package.
- **Every problem entry inline (D-03)** — the user chose to print the full
  problem list on stdout and explicitly accepted that a messy archive yields a
  long report, preferring complete detail over a terse count-and-pointer.
- **Trusted publishing over a token (D-06)** — the user explicitly preferred
  OIDC trusted publishing (no stored credential) over a local token-based
  `uv publish`, accepting the extra GitHub-Actions + PyPI-config setup.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 4 scope (CLI-03 + DIST-01). No new
out-of-phase capabilities surfaced; the browser PWA remains Phase 5 per the
existing roadmap.

</deferred>

---

*Phase: 4-full-cli-pypi-publication*
*Context gathered: 2026-05-18*
