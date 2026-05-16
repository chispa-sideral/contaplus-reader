# Phase 2: ZIP & Subaccounts - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 thickens the reader from a single `DIARIO.DBF` to a full ContaPlus backup
`.zip`. It delivers:

- **ZIP input** — sniffed by magic bytes, zip-slip-safe, extracted from an
  in-memory buffer (INPUT-02, INPUT-04).
- **Recursive table discovery** inside the archive, regardless of nesting depth
  (INPUT-05).
- **Multi-company disambiguation** by a caller-supplied company selector (INPUT-06).
- **Typed readers** for `SUBCTA.DBF` and the group-level tables `grupos.dbf`,
  `usuarios.dbf`, `empresa.dbf` (TABL-01, TABL-02).
- **Journal name enrichment** — the journal carries subaccount names from
  `SUBCTA.DBF` when present (API-05).
- A **multi-sheet `.xlsx`** with one sheet per extracted table.
- A `--company` CLI flag (CLI-02, reassigned from Phase 4 — see D-07).

**Success = all four ROADMAP §"Phase 2" criteria hold:** `contaplus2xlsx backup.zip
out.xlsx` produces a workbook whose journal sheet has SUBCTA-populated names; a
multi-company ZIP without `--company` errors listing the company directory names;
a zip-slip entry is rejected with a structured error; the workbook has sheets for
`SUBCTA`/`grupos`/`usuarios`/`empresa` when present.

**Explicitly NOT in scope (sequenced downstream by the roadmap):**
- Operational tables (`venci`, `prede`, `amoinv`, `nivel`) + `BALAN.DBF` → **Phase 3**
- The lenient conversion path + problems sheet (API-03, XLSX-02/03) → **Phase 3**
- `BAL-02` recomputed trial balance → **Phase 3**
- CLI stdout reporting beyond the one-line summary (CLI-03) → **Phase 4**
- PyPI publication (DIST-01) → **Phase 4**
- PWA → **Phase 5**

</domain>

<decisions>
## Implementation Decisions

Per-phase decision numbering — `D-NN` restarts at `D-01` for this phase (Phase 1's
CONTEXT used D-01…D-17 independently). Phase 1 decisions referenced below are
cited as "Phase-1 D-NN".

### ZIP Input & Discovery
- **D-01:** ZIP input is detected by **magic-byte sniffing** — the carry-forward
  Phase-1 D-05 mechanism, unchanged. `src/contaplus_reader/_sniffer.py` already
  detects the ZIP `PK` signature (`0x50`) and currently rejects it with a
  "future phase" hint; Phase 2 flips that branch to **accept** ZIP. The DBF
  version-byte set is untouched. Input type is never decided by file suffix.
- **D-02:** A multi-company backup is disambiguated by the **raw company
  directory name** (`Emp01`, `Emp02`, …) — both as the value the caller passes
  and as the names listed in the error. Matching is **case-insensitive**
  (archives present `EmpNN`/`EMPNN`). Single-company ZIP with no selector → use
  the one company. Multi-company ZIP with no selector → `ContaPlusReadError`
  listing the available directory names (Success Criterion #2). No human-readable
  company name from `empresa.dbf` is used for selection or in the error.
- **D-03:** Company-selector edge behavior: a selector supplied against a
  **single-company** ZIP is validated against that company — a mismatch raises an
  error (catches typos) rather than being silently ignored. A selector supplied
  against a **raw `.dbf`** input raises an error ("selector not applicable").

### Read API & Result Model
- **D-04:** `read()` gains a **company-selector parameter** — the Phase-1 D-06
  signature `read(data, source_name=None)` is extended additively with a
  `company: str | None = None` parameter. Exact parameter name is planner
  discretion; `company` is the working name. No filesystem-path argument is ever
  added (Phase-1 success criterion #5 stands).
- **D-05:** The result model grows by **adding sibling attributes to the existing
  `ContaPlusData` container** — the Phase-1 D-03 extension seam. Phase 2 adds
  attributes for `SUBCTA` and the three group tables (working names `.subcta`,
  `.empresa`, `.grupos`, `.usuarios`), each its own typed result type. Exact type
  names and attribute names are planner discretion. The container return type
  stays stable — adding tables never breaks the CLI/PWA/tax-workbench callers.
- **D-06:** **Uniform strict.** Any table that is *present in the archive but
  unreadable* (corrupt, or a schema the typed reader cannot resolve) raises
  `ContaPlusReadError` and **aborts the whole conversion** — consistent with
  Phase-1 D-04 (strict-only until Phase 3). Phase 2 has **no** partial-success or
  table-level skip behavior. A table simply *absent* from the archive is fine —
  no sheet, no error (Success Criterion #4 says sheets appear "when present").

### CLI
- **D-07:** The `--company` flag is **pulled into Phase 2**:
  `contaplus2xlsx backup.zip out.xlsx --company Emp01`. This resolves an
  inconsistency — ROADMAP Phase 2 Success Criterion #2 references a `--company`
  flag, but REQUIREMENTS mapped `CLI-02` to Phase 4. **`CLI-02` is reassigned
  Phase 4 → Phase 2** in the REQUIREMENTS traceability table; Phase 4 retains
  only `CLI-03` (full stdout reporting). Rationale: without the flag the Phase 2
  CLI could not convert any multi-company backup at all.
- **D-08:** A multi-company ZIP passed to the CLI without `--company` is surfaced
  as a **Rich error panel** (the Phase-1 D-17 pattern — no traceback) listing the
  available company directory names; the CLI exits with code 1.

### Journal Name Enrichment
- **D-09:** `JournalRow` gains an **optional field `subcuenta_nombre: str | None
  = None`**. This is an additive, defaulted field — a **documented extension of
  Phase-1 D-07** (which locked the six-field row shape `{fecha, cuenta,
  subcuenta, debe, haber, concepto}`). The future tax-workbench adapter reads the
  original six fields and is unaffected by the extra optional field.
- **D-10:** Enrichment is **subcuenta-level only.** A name is resolved for the
  full subaccount code; the 4-digit `cuenta` stays code-only. `SUBCTA.DBF` holds
  subaccount-level codes, not the higher PGC `cuenta` level — there is no honest
  source for a `cuenta` name.
- **D-11:** Enrichment is **best-effort at the row/lookup level** and never an
  error: a journal `subcuenta` with no matching `SUBCTA` row → `subcuenta_nombre
  = None`; `SUBCTA.DBF` absent from the input (raw `.dbf`, or a ZIP with no
  SUBCTA) → all `subcuenta_nombre` values `None`. This is **distinct from D-06** —
  a `SUBCTA.DBF` that is *present but unreadable* still aborts under uniform
  strict; only a *missing lookup key* or a *missing table* is tolerated silently.

### Multi-Sheet XLSX
- **D-12:** The renderer becomes **data-driven** — it emits one sheet per
  populated table on `ContaPlusData`. The current single-sheet `render_journal()`
  generalizes; exact function name/signature is planner discretion. The Phase-1
  D-10/D-12 styling (bold filled header, freeze panes, accounting format, red
  negatives) is the template, applied consistently across all sheets. Note: no
  XLSX-numbered requirement is mapped to Phase 2, but Success Criterion #4
  *requires* this renderer extension.
- **D-13:** **Full dump** — each sheet reproduces **every field its table
  contains**, in DBF field order. The project core value is "extract *all* their
  data"; a curated subset would silently drop data. Headers for the non-journal
  sheets are the **raw DBF field names** (these tables are undocumented — no
  reliable human-friendly labels exist).
- **D-14:** Sheet tabs use **Spanish names**: `Diario`, `Subcuentas`, `Empresa`,
  `Grupos`, `Usuarios`. Consistent with the existing `Diario` tab and Phase-1
  D-12 (these label Spanish statutory accounting data for a Spanish-speaking
  ContaPlus-migrant audience). All code, identifiers, CLI `--help`, and error
  messages stay English. Only tables actually present produce a sheet.
- **D-15:** The `Diario` sheet gains a **name column populated from
  `subcuenta_nombre`**, placed immediately after the `Subcuenta` column, with a
  Spanish header (e.g. `Descripción`). Blank when the name is unresolved. Exact
  header text and overall sheet ordering are planner discretion.

### Table Readers
- **D-16:** **Typed readers for all four tables** (`SUBCTA`, `grupos`,
  `usuarios`, `empresa`), each with **defensive field-name resolution** — the
  `SUBCTA` `CODIGO`/`COD`, `DESCRIP`/`TITULO` pattern from SEED §1, extended to
  the group tables, modelled on the existing `_pick_column` candidate-list
  pattern in `_reader.py`. `SUBCTA` is partially documented in SEED; the three
  group tables are undocumented.
- **D-17:** Because the group tables are undocumented, **Phase 2 research MUST
  include a `pii-test-data/` schema-discovery step** — enumerate the field
  schemas of `grupos.dbf`, `usuarios.dbf`, `empresa.dbf` (and `SUBCTA`/`XSUBCTA`
  variants) across all 5 real archives **before** the typed readers are
  committed. This is the same gate the roadmap applies to Phase 3's operational
  tables (TABL-03); STATE.md's init note only anticipated it for Phase 3, so
  this expands Phase 2's research scope. **Consequence:** typed readers + uniform
  strict (D-06) means a real-world archive whose group-table schema differs from
  the discovered set is a *hard failure* — thorough variant enumeration across
  all archives and defensive field resolution are the mitigation.
- **D-18:** `usuarios.dbf` is **extracted in full**, including any
  credential/password fields — consistent with the full-dump policy (D-13) and
  the "extract *all* their data" core value. Justified because conversion is
  **fully local**: the CLI runs on the user's own machine and the PWA is
  client-side by locked constraint — no data ever leaves the machine, and a
  migrating user may legitimately want their user list. `usuarios` is named
  explicitly in Success Criterion #4, so it must produce a sheet regardless.

### Claude's Discretion
- Exact new type names and attribute names on `ContaPlusData`, the
  company-selector parameter name, and module/package layout.
- The **ZIP extraction mechanism** — extract-the-whole-archive-to-a-temp-dir vs.
  read entries from an in-memory `BytesIO` and bridge each DBF to a temp path via
  the existing `_bridge.bytes_to_tmppath` pattern. `dbfread` is path-only, so
  *some* temp-file bridging is unavoidable; lifecycle, cleanup, and memo-sibling
  handling are research + planning concerns.
- Exact journal name-column header text (`D-15`) and the multi-sheet ordering.
- The CLI one-line summary format for a multi-sheet conversion (the Phase-1 D-16
  summary extends; full row-count/problems reporting is Phase 4 CLI-03).

### Open for Research
- **Group-table schemas (D-17):** field schemas of `grupos.dbf`, `usuarios.dbf`,
  `empresa.dbf` — enumerate from `pii-test-data/` before the typed readers exist.
- **SUBCTA field-name variants:** SEED §1/§3 note `CODIGO`/`COD`,
  `DESCRIP`/`TITULO`, and the `XSUBCTA.DBF` filename variant — validate against
  `pii-test-data/`.
- **ZIP layout variance:** `EmpNN/` vs `EMPNN/` vs `Datos\EmpNN\` nesting
  (SEED §4); recursive case-insensitive table discovery; how per-company
  `SUBCTA.DBF` is scoped to the *selected* company directory while group-level
  tables (`grupos`, `usuarios`) live at the archive root.
- **zip-slip-safe extraction from an in-memory buffer (INPUT-04):**
  `zipfile.extractall` has no `filter=` safety knob — the entry-name path-traversal
  validation pattern to apply before extraction.
- **Memo-sibling / `.cdx` handling** for the extracted non-journal DBFs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Format, rules & ZIP structure (primary)
- `SEED.md` — **the primary reference.** Read in full; for Phase 2 especially:
  §1 "Related ContaPlus files" (`SUBCTA.DBF`/`XSUBCTA.DBF` key fields,
  `BALAN.DBF` unreliability), §3 "Column-name variants (defensive resolution)",
  §4 "ZIP backup archive structure" (on-disk + ZIP company layout, recursive
  `DIARIO.DBF` discovery, zip-slip warning, rules D-A1/D-A2), §5 "DBF reader
  invocation specifics", §6 "Format gotchas".

### Project specs
- `.planning/PROJECT.md` — scope, constraints, Key Decisions table; note
  "research must enumerate and spec the non-journal tables" and the
  `pii-test-data/` description.
- `.planning/REQUIREMENTS.md` — Phase 2 requirements INPUT-02, INPUT-04,
  INPUT-05, INPUT-06, TABL-01, TABL-02, API-05 — **plus CLI-02, reassigned
  Phase 4 → Phase 2 per D-07**.
- `.planning/ROADMAP.md` §"Phase 2: ZIP & Subaccounts" — phase goal and the four
  success criteria the verifier checks.
- `.planning/phases/01-journal-slice/01-CONTEXT.md` — Phase 1 decisions carried
  forward: D-03 (`ContaPlusData` container = extension seam), D-04 (strict-only),
  D-05 (magic-byte sniffing), D-06 (`read()` signature), D-07 (`JournalRow`
  shape), D-10/D-12 (XLSX styling, Spanish headers).
- `CLAUDE.md` (repo root) — locked tech stack (Python ≥3.13, uv/uv_build, Typer,
  Rich, dbfread, pandas, openpyxl) and the "What NOT to Use" list (never
  `latin-1`, never `dbfread(load=True)` on large journals).

### Local validation gate (CONFIDENTIAL — never read into output or commit)
- `pii-test-data/` — 5 real ContaPlus backup `.zip` archives (4 single-company,
  1 multi-company). The schema-discovery gate for the SUBCTA/group-table typed
  readers (D-16/D-17). **Git-ignored, internal-only — its contents must never be
  committed, quoted in output, or read into any public artifact.** The committed
  test suite uses only synthetic, blob-free fixtures generated at collection time.

### Porting source — fallback only, OUTSIDE this repo
SEED.md is self-contained; consult these only to cross-check the ZIP / multi-company
logic being ported:
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — current
  reader, including the `.zip` extraction and multi-company D-A1/D-A2 logic.
- `C:\dev\tax-workbench\packages\tw-contaplus\tests\` — existing tests and the
  synthetic-DBF/ZIP fixture factory (`conftest.py`), including the
  `single_company_zip` / `multi_company_zip` fixtures (SEED §"Existing tests").

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/contaplus_reader/_sniffer.py`** — `sniff()` already detects the ZIP `PK`
  magic byte (`0x50`) and currently rejects it with a "future phase" hint.
  Phase 2 flips this branch to *accept* ZIP; the DBF version-byte set is unchanged.
- **`src/contaplus_reader/_bridge.py`** — `bytes_to_tmppath()` writes bytes to a
  temp `.dbf` (Windows-safe) for path-only `dbfread`. Phase 2 reuses this pattern
  per-DBF when reading tables out of an extracted ZIP.
- **`src/contaplus_reader/_reader.py`** — `_read_dbf_path()`, `_pick_column()`
  (case-insensitive ordered-candidate field resolution), `_assert_journal_shaped()`.
  The journal reader is reused unchanged; `_pick_column` / the candidate-list
  pattern is the model for SUBCTA and group-table defensive field resolution (D-16).
- **`src/contaplus_reader/models.py`** — `ContaPlusData` (deliberately *not*
  frozen — designed to grow attributes), `ContaPlusJournal`, `JournalRow` (frozen
  — gains `subcuenta_nombre` per D-09), `ContaPlusReadError`. The container
  extension seam (Phase-1 D-03) is exactly what Phase 2 builds on.
- **`src/contaplus_reader/xlsx.py`** — `render_journal()` plus the
  `HEADERS`/`ACCOUNTING_FMT`/`DATE_FMT`/`HEADER_FILL`/`HEADER_FONT` styling
  constants. Phase 2 generalizes the renderer to multi-sheet; the styling
  template is reused verbatim.
- **`src/contaplus_reader/cli.py`** — the Typer CLI. Phase 2 adds the `--company`
  option and ZIP-input handling; the Rich error-panel pattern (D-08) already exists.
- **`tests/conftest.py`** — the synthetic-fixture factory. Phase 2 extends it with
  synthetic `.zip` archives (single- and multi-company) and synthetic SUBCTA /
  group-table DBFs — no real files enter the repo.

### Established Patterns
- Defensive, case-insensitive field-name resolution via ordered candidate lists
  (`_pick_column`, `_DEBE_COL_CANDIDATES`) — extend to SUBCTA/group tables.
- `ContaPlusReadError(message, row_index, column, original)` structured error —
  every Phase 2 failure (zip-slip, multi-company ambiguity, unreadable table)
  raises this; `row_index = -1` marks a file-level error.
- Bytes-first public API, no filesystem path; path-only `dbfread` bridged via
  `NamedTemporaryFile` (`delete=False` + explicit unlink — Windows-safe).
- Per-phase `D-NN` decision numbering in CONTEXT.md.

### Integration Points
- `read()` in `__init__.py` — the single public entry point; gains ZIP handling
  and the company selector (D-04).
- `ContaPlusData` — the extension point; gains `.subcta`/`.empresa`/`.grupos`/
  `.usuarios` attributes (D-05).
- The renderer and the CLI both consume `ContaPlusData`; both must handle the
  multi-table shape (D-12, D-07).

</code_context>

<specifics>
## Specific Ideas

- **Spanish sheet tabs (D-14)** continue the Phase-1 D-12 reasoning explicitly:
  the workbook labels Spanish statutory accounting data for a Spanish-speaking
  ContaPlus-migrant audience — everything else (code, CLI help, errors) stays
  English. Downstream agents must not "correct" `Diario`/`Subcuentas`/etc. to
  English.
- **`usuarios.dbf` extracted in full including credentials (D-18)** — the user
  explicitly accepted this, on the stated grounds that conversion never leaves
  the user's machine (local CLI / client-side PWA).
- **Uniform strict over a softer skip (D-06)** — the user explicitly chose to
  reject any table-level partial-success behavior in Phase 2: a present-but-
  unreadable table fails the whole conversion. All leniency waits for Phase 3.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No new out-of-phase capabilities
surfaced; the operational tables, `BALAN.DBF`, the lenient path, and the PWA
remain in Phases 3–5 per the existing roadmap.

**Roadmap/requirements adjustments noted during discussion** (not new scope —
corrections within existing scope):
- `CLI-02` should move from Phase 4 to Phase 2 in `REQUIREMENTS.md` traceability
  (D-07).
- Phase 2 research scope expands to include `pii-test-data/` schema discovery for
  the group tables — STATE.md's init note only anticipated this for Phase 3 (D-17).

</deferred>

---

*Phase: 2-zip-subaccounts*
*Context gathered: 2026-05-16*
