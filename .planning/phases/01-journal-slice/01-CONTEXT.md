# Phase 1: Journal Slice - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the thinnest working vertical of contaplus-reader: raw `DIARIO.DBF`
bytes → a strict, validated journal reader → a styled `.xlsx` → a runnable CLI.

Success = a user runs `contaplus2xlsx DIARIO.DBF out.xlsx` and gets a styled
workbook with a journal sheet of validated rows; an invalid `.dbf` is rejected
with a structured error naming the offending row and column; `uv build` produces
a wheel that `uvx contaplus2xlsx` can install and run.

**In scope:** `DIARIO.DBF` reading only — INPUT-01, INPUT-03, JRNL-01/02/03,
API-01/02/04, XLSX-01/04, CLI-01/04, TEST-01/02, DIST-02.

**Explicitly NOT in scope (sequenced downstream by the roadmap):**
- `SUBCTA.DBF` + group tables (`grupos`, `usuarios`, `empresa`) → **Phase 2**
- Operational tables (`venci`, `prede`, `amoinv`, `nivel`) + `BALAN.DBF` → **Phase 3**
- ZIP input, lenient conversion path, multi-company → Phases 2–3
- PWA → Phase 5

</domain>

<decisions>
## Implementation Decisions

### Phase Scope
- **D-01:** Phase 1 stays strictly journal-only (`DIARIO.DBF`). The other ContaPlus
  tables were discussed and confirmed to belong to Phases 2–3 — the roadmap
  boundary is unchanged. No table readers beyond the journal land in this phase.
- **D-02:** A raw input that sniffs as a valid `.dbf` but is **not journal-shaped**
  (e.g. someone feeds `SUBCTA.DBF`) is detected and rejected with a structured
  error stating it is a non-journal table and that multi-table support is planned.
  The reader checks the DBF field signature *before* attempting journal parsing —
  it does not just fall through to a generic D-E1 "no debe/haber column" error.
  (Research must define the minimal "journal-shaped" field signature — see
  Open for Research below.)

### Read API
- **D-03:** `read()` returns a **`ContaPlusData` container object**, not the journal
  directly. Phase 1 populates `.journal` (a `ContaPlusJournal`); Phases 2–3 add
  sibling attributes (`.subcta`, `.balance`, …). The container return type is
  stable across all five phases — adding tables never breaks the API for the CLI,
  PWA, or tax-workbench.
- **D-04:** Strict-only in Phase 1. `read()` has **no** `strict`/`lenient`/`mode`
  parameter yet; it always raises `ContaPlusReadError` on invalid data. Phase 3
  (API-03) adds the lenient parameter with a strict default — additive, non-breaking.
- **D-05:** Input type is detected by **content magic-byte sniffing** — not a
  file suffix (the API is bytes-first) and not a caller-supplied hint. Phase 1
  accepts dBASE/FoxPro DBF signatures and rejects everything else — including ZIP
  (`PK\x03\x04`) — with a structured error. ZIP support is Phase 2.
- **D-06:** Signature is `read(data: bytes | BinaryIO, source_name: str | None = None)`.
  `source_name` is an optional caller-supplied provenance label (CLI passes the
  input filename; PWA will pass the dropped file's name). No filesystem-path
  argument ever exists — Phase 1 success criterion #5.

### Result Model
- **D-07:** `ContaPlusJournal.rows` is `list[JournalRow]` — frozen, fully static-typed
  dataclasses. **No pandas type appears in the public API surface.** The per-row
  field shape stays `{fecha, cuenta, subcuenta, debe, haber, concepto}` (SEED D-E3,
  unchanged so the future tax-workbench adapter port stays faithful).
- **D-08:** The XLSX renderer and the future tax-workbench `Diario` adapter convert
  `list[JournalRow]` → a DataFrame internally if/as they need one. The DataFrame is
  an implementation detail of those consumers, not part of the result type.
- **D-09:** `ContaPlusJournal` also carries the skipped-memo-line count (D-C3) and
  the optional `source_name`. No computed totals on the result in Phase 1.

### XLSX Rendering
- **D-10:** Polished-but-restrained styling — bold header row with a fill color,
  frozen header row, auto-sized columns, proper number/date cell formats.
  Professional accounting-export look, not decorative.
- **D-11:** `debe`/`haber` use an accounting number format — 2 decimals, thousands
  separators; **negative amounts rendered in red**. Negatives are real (reversal /
  correction rows per SEED D-C1) and the sign must stay visible.
- **D-12:** XLSX column headers are in **Spanish** — `Fecha, Cuenta, Subcuenta,
  Debe, Haber, Concepto`. This is a deliberate, documented exception to the
  project-wide "English everything" i18n rule: the headers label Spanish-statutory
  accounting data (Plan General de Contabilidad) and the audience is Spanish-speaking
  ContaPlus migrants. **All code, identifiers, docstrings, CLI `--help`, and error
  messages remain English.** Downstream agents must NOT "correct" these headers to
  English.
- **D-13:** The journal sheet contains data rows only — no footer/totals row. A
  clean rectangular block re-imports cleanly; totals and the trial balance are
  Phase 3 (BAL-02).

### CLI (`contaplus2xlsx`)
- **D-14:** Both arguments are **required positionals**: `contaplus2xlsx <input> <output>`.
  No auto-derived default output path.
- **D-15:** The CLI **refuses to overwrite** an existing output file; a `--force`
  flag (alias `--overwrite`) permits replacement. Never clobbers silently; stays
  script-safe.
- **D-16:** On success the CLI prints a **concise one-line summary** including the
  journal row count and the skipped-memo count — e.g.
  `out.xlsx — 3 journal rows (1 memo line skipped)`. The fuller row-count /
  problems report is Phase 4 (CLI-03).
- **D-17:** A `ContaPlusReadError` is presented as a **clean Rich error panel** —
  message + row index + column + context, **no Python traceback** — and the CLI
  exits with code 1. Rich is already in the locked tech stack.

### Claude's Discretion
- Exact class names (`ContaPlusData`, `ContaPlusJournal`, `JournalRow`,
  `ContaPlusReadError`), module/package layout, and the bytes→temp-path bridge
  mechanism for `dbfread` (which is path-only) are implementation choices for
  research/planning.
- Precise styling values — fill color, fonts, column-width algorithm, and the exact
  Excel number-format strings — are the planner's to choose within
  "polished but restrained" and "accounting format, red negatives".

### Open for Research
- **Journal field signature (D-02):** define the minimal set of DBF fields that
  reliably identifies a `DIARIO.DBF` and distinguishes it from `SUBCTA.DBF`,
  `BALAN.DBF`, and the group/operational tables — used by the detect-and-reject check.
- **Bytes→path bridge:** `dbfread` has no bytes/file-like API (path-only; upstream
  issue #25 never merged). STATE.md flags this as the foundational Phase 1 blocker —
  research the temp-file bridge (lifecycle, cleanup, `.cdx`/memo-sibling handling).
- **DBF magic bytes (D-05):** enumerate the dBASE/FoxPro version-byte values a
  ContaPlus DBF can present at offset 0, for the content sniffer.
- **Excel accounting format:** number-format codes for 2-decimal + thousands
  separators with red negatives, and how separator glyphs render across viewer locales.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Format, rules & test inventory (primary)
- `SEED.md` — **the primary reference for Phase 1.** Self-contained: the
  `DIARIO.DBF` format spec, encoding policy (cp850 unconditional), column-name
  variant resolution (§3), journal business rules D-A1…D-E3 + the structured
  error model, and the synthetic-fixture / test inventory to port verbatim
  (TEST-01/02). Read in full.

### Project specs
- `.planning/PROJECT.md` — project scope, constraints, and the Key Decisions table.
- `.planning/REQUIREMENTS.md` — full text of the Phase 1 requirements (INPUT-01,
  INPUT-03, JRNL-01/02/03, API-01/02/04, XLSX-01/04, CLI-01/04, TEST-01/02, DIST-02).
- `.planning/ROADMAP.md` §"Phase 1: Journal Slice" — phase goal and the five
  success criteria the verifier checks.
- `CLAUDE.md` (repo root) — locked tech stack (Python ≥3.13, uv + uv_build, Typer,
  Rich, dbfread, pandas, openpyxl) and the "What NOT to Use" list (e.g. never
  `latin-1`, never `dbfread(load=True)` on large journals).

### Porting source — fallback only, OUTSIDE this repo
SEED.md is self-contained; consult these only to cross-check:
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — current
  Qt-free reader implementation being ported.
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\params.py` — current params.
- `C:\dev\tax-workbench\packages\tw-contaplus\tests\` — existing reader tests +
  the synthetic-DBF fixture factory (`conftest.py`) to port.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None in this repository — Phase 1 is greenfield. The repo currently holds only
  `SEED.md`, `CLAUDE.md`, `.planning/`, and the git-ignored `pii-test-data/`.
- The porting source is the tax-workbench `tw-contaplus` package (see Canonical
  References). The reader logic, business rules, and synthetic-fixture factory are
  ported from there; their content is already embedded verbatim in `SEED.md`.

### Established Patterns
- None yet — CLAUDE.md notes "Conventions not yet established." Phase 1 sets the
  foundational conventions (package layout, error model, test approach).

### Integration Points
- Phase 1 is foundational: it creates the package, the `read()` entry point, the
  `ContaPlusData`/`ContaPlusJournal` result types, the `ContaPlusReadError` model,
  the shared XLSX renderer, and the `contaplus2xlsx` CLI. Every later phase builds
  on these seams — the container return type (D-03) is the key extension point.

</code_context>

<specifics>
## Specific Ideas

- **Spanish XLSX headers despite English-everything (D-12):** the user explicitly
  wants `Fecha/Cuenta/Subcuenta/Debe/Haber/Concepto` as the visible sheet headers
  because the sheet *is* a Spanish accounting journal — but everything else in the
  project (code, docs, CLI help, error text) stays English.
- **Honest scope-aware error for non-journal DBFs (D-02):** when a user feeds a
  non-journal table, the error should make clear it's the *wrong table* and that
  multi-table support is coming — not a cryptic column-resolution failure.
- **Negatives in red (D-11):** reversal/correction rows are unusual and the user
  wants them to visually stand out in the workbook.

</specifics>

<deferred>
## Deferred Ideas

None — the other ContaPlus tables (`SUBCTA`, `BALAN`, group and operational
tables), ZIP input, the lenient conversion path, and the PWA were all raised and
confirmed to sit in Phases 2–5 per the existing roadmap. No new out-of-phase
capabilities surfaced; the roadmap needs no amendment.

</deferred>

---

*Phase: 1-journal-slice*
*Context gathered: 2026-05-15*
