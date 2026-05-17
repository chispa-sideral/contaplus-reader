# Phase 3: Full Tables, Balance & Lenient Path - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 thickens the reader to extract *every readable table* and introduces the
lenient conversion path. It delivers:

- **Operational-table readers** for `venci.dbf`, `prede.dbf`, `amoinv.dbf`,
  `nivel.dbf` — typed, undocumented, schema-discovered against `pii-test-data/`
  (TABL-03).
- **Single-pass extraction** of every recognized table from a backup ZIP
  (TABL-04).
- **Raw `BALAN.DBF` reader** — a full dump of ContaPlus's own trial-balance file
  (BAL-01).
- **Recomputed authoritative trial balance** (*sumas y saldos*) derived from
  `DIARIO.DBF` journal data (BAL-02).
- **Lenient conversion path** — extracts all readable data, collects problems
  into a report, and never aborts the whole file (API-03).
- A **problems sheet** in the XLSX listing every genuine defect with row/column
  context (XLSX-02).
- A **conditional "derived — may be unreliable" disclaimer** on the raw `BALAN`
  sheet (XLSX-03).

**Success = all four ROADMAP §"Phase 3" criteria hold** (see §"Decisions" for two
deliberate refinements of criterion #3): a lenient ZIP conversion produces sheets
for `venci`/`prede`/`amoinv`/`nivel`; the workbook has a problems sheet listing
every flagged/skipped row; the raw `BALAN` sheet is disclaimed and the recomputed
balance is authoritative; the operational-table schemas are validated against
`pii-test-data/` before the typed readers are committed.

**Explicitly NOT in scope (sequenced downstream by the roadmap):**
- Full CLI stdout reporting beyond the one-line summary (CLI-03) → **Phase 4**
- PyPI publication, `micropip` validation (DIST-01) → **Phase 4**
- The browser PWA → **Phase 5**

</domain>

<decisions>
## Implementation Decisions

Per-phase decision numbering — `D-NN` restarts at `D-01` for this phase. Phase 1
and Phase 2 decisions referenced below are cited as "Phase-1 D-NN" / "Phase-2 D-NN".

### Lenient Conversion Path
- **D-01:** The lenient path is a **parameter on `read()` with a strict default**
  — carried forward and now realised from Phase-1 D-04 ("Phase 3 (API-03) adds
  the lenient parameter with a strict default — additive, non-breaking"). The
  library `read()` defaults to strict. The CLI exposes it as a **`--lenient`
  flag, strict by default**. ROADMAP criterion #1 references "the lenient flag",
  consistent with opt-in. Exact parameter name is planner discretion.
- **D-02:** In **lenient mode the journal also goes best-effort.** Bad journal
  rows (null `FECHA`, both-non-zero amounts, malformed `subcuenta`) are skipped
  and diverted into the problems report; the `Diario` sheet keeps the good rows.
  This does **not** compromise the project core value: tax-workbench always calls
  the **strict** path, where the journal stays fail-loud — its contract is
  untouched. Lenient is the migration-user path.
- **D-03:** In lenient mode, a journal that is **unreadable as a whole** —
  truncated/corrupt `DIARIO.DBF`, no resolvable debe/haber column, or no
  `DIARIO.DBF` in the ZIP at all — becomes a **single problems-report entry**;
  the conversion **continues** and still produces a sheet for every other
  readable table. No `Diario` sheet is produced (or an empty one). This makes
  API-03's "never aborts the whole file" literally true.
- **D-04:** In lenient mode, a **secondary table that is present but unreadable**
  (corrupt, or a schema the typed reader cannot resolve) — which aborts the
  whole conversion under Phase-2 D-06 *uniform strict* — instead becomes a
  problems-report entry and is skipped. Relaxing exactly this is the purpose of
  API-03. Strict mode is unchanged: Phase-2 D-06 still aborts.

### Problems Report
- **D-05:** The problems sheet (XLSX-02) lists **genuine defects only** —
  skipped bad journal rows, present-but-unreadable tables, flagged anomalies.
  **By-design both-zero memo-line skips do NOT appear** in the problems sheet;
  they remain a separate surfaced count (`ContaPlusJournal.skipped_memo`, already
  shown in the CLI one-line summary). Rationale: a clean multi-year archive has
  thousands of memo lines — folding them into a "problems" sheet would bury the
  real defects under expected noise.
- **D-06:** Each problems entry carries: **table name, row index, column,
  plain-English reason, and the offending value.** The offending value (e.g. the
  actual malformed `subcuenta` string) lets a migrating user locate and fix the
  bad record back in ContaPlus. Whole-table / file-level failures use **row index
  `-1`** and a **blank column** — consistent with the existing `ContaPlusReadError`
  `row_index = -1` file-level convention.

### Trial Balance & BALAN
- **D-07:** BAL-02 produces **two recomputed trial-balance sheets** — one grouped
  at **4-digit `cuenta`** level, one at **full `subcuenta`** level. This is a
  deliberate **refinement of ROADMAP criterion #3**, which says "the recomputed
  trial-balance *sheet*" (singular): the deliverable is the same BAL-02 recomputed
  balance, presented at both granularities. Both sheets are flat, re-importable
  tables.
- **D-08:** Trial-balance sheet columns: **account code, Suma Debe, Suma Haber,
  Saldo Deudor, Saldo Acreedor, and a signed Saldo column** (positive = deudor,
  negative = acreedor). The user explicitly wanted *both* the classic
  split-saldo form *and* the convenience signed column. The **subcuenta-level
  sheet adds a `Descripción` column** populated from SUBCTA enrichment (blank
  when unresolved); the **cuenta-level sheet stays code-only** — there is no
  honest cuenta-name source (carried forward Phase-2 D-10).
- **D-09:** The raw `BALAN.DBF` sheet (BAL-01) carries the
  "derived — may be unreliable" disclaimer **conditionally**: a visible warning
  banner row is shown **only when `BALAN`'s own figures fail to balance** (a
  *descuadre*). When `BALAN` balances cleanly, **no banner** — the sheet looks
  normal. This **narrows ROADMAP criterion #3's** literal "carries a visible
  disclaimer" (unconditional) to "carries the disclaimer when it is actually
  unbalanced." Recorded as a deliberate, user-chosen criterion refinement — the
  verifier should reconcile against this intent, not the literal wording.
- **D-10:** The descuadre check compares **`BALAN` against itself** (its own
  total debit vs total credit / saldo columns) — **not** `BALAN` against the
  recomputed balance.
- **D-11:** The raw-balance sheet **tab name stays plain `Balance`** (no
  descuadre signal in the tab strip); the in-sheet conditional banner (D-09) is
  the only signal. The two recomputed *Sumas y Saldos* sheets are **always
  present and always trusted** — no banner of any kind.

### Table Extraction Scope
- **D-12:** TABL-04 single-pass extraction covers the **known 10-table catalogue
  only**: `DIARIO`, `SUBCTA`, `BALAN`, `grupos`, `usuarios`, `empresa`, `venci`,
  `prede`, `amoinv`, `nivel`. An **uncatalogued `.dbf`** found in the archive
  does **not** produce a sheet. Only `.dbf` files are tables — `.cdx` indexes and
  `.fpt`/`.dbt` memo siblings are never treated as tables.
- **D-13:** In **lenient mode**, an uncatalogued `.dbf` produces **one
  informational problems-sheet entry** (e.g. "table FOO.DBF found but not
  extracted — unrecognized table"). In **strict mode** this is **silent** — an
  unknown table is not an error. So the catalogue-only output is never quietly
  lossy when the user has opted into lenient.

### Operational Table Readers
- **D-14:** TABL-03 delivers typed readers for `venci.dbf`, `prede.dbf`,
  `amoinv.dbf`, `nivel.dbf`. These tables are **undocumented** — they go through
  the same `pii-test-data/` **schema-discovery gate** as the Phase-2 group tables
  (Phase-2 D-17 / ROADMAP criterion #4): enumerate field schemas across all 5
  real archives **before** the readers are committed. The committed test suite
  uses only synthetic, blob-free fixtures.
- **D-15:** Full-dump policy applies (carried forward Phase-2 D-13) — every
  field, in DBF field order, **raw DBF field names** as headers. Spanish sheet
  tab names (carried forward Phase-2 D-14). Exact Spanish tab labels for the new
  sheets are planner/research discretion.

### Carried Forward (locked by earlier phases — not re-discussed)
- `ContaPlusData` is the stable container extension seam — new tables become new
  attributes; adding tables never breaks CLI/PWA/tax-workbench callers
  (Phase-1 D-03).
- `read()` signature is additive-only — no filesystem-path argument ever
  (Phase-1 D-06).
- Spanish sheet tabs and headers; **all code, identifiers, CLI `--help`, and
  error/problem-reason text stay English** (Phase-1 D-12, Phase-2 D-14).
- Defensive, case-insensitive field-name resolution via ordered candidate lists
  (`_pick_column`) (Phase-2 D-16).
- In **strict** mode, a present-but-unreadable table aborts the whole conversion
  (Phase-2 D-06, *uniform strict*). Lenient mode (D-04) is the only thing that
  relaxes this.
- `ContaPlusReadError(message, row_index, column, original)` structured error;
  `row_index = -1` marks a file-level error.

### Claude's Discretion
- Exact new type names and `ContaPlusData` attribute names for the operational
  tables, the raw balance, and the recomputed balance results; module/package
  layout.
- The `lenient` parameter's exact name and the lenient result/report type shape
  (how the problems list is carried back from `read()`).
- Exact Spanish sheet-tab labels and overall sheet ordering for the new sheets;
  the problems-sheet tab name (Spanish, consistent with the D-15 convention) and
  its column headers.
- How the recomputed trial balance is computed internally (grouping mechanics,
  `Decimal` vs `float` accumulation).
- Whether `venci`/`prede`/`amoinv`/`nivel` need anything beyond a `GenericTable`
  full dump — for an undocumented table, a "typed reader" is in practice
  defensive full-dump plus any field-name resolution discovery surfaces.

### Open for Research
- **Operational-table schemas (D-14):** field schemas of `venci.dbf`,
  `prede.dbf`, `amoinv.dbf`, `nivel.dbf` — enumerate from `pii-test-data/` across
  all 5 real archives before the typed readers exist.
- **`BALAN.DBF` schema:** SEED documents `BALAN` only as "derived/temporary,
  unreliable" — its field layout is undocumented. Enumerate from `pii-test-data/`
  so BAL-01 (raw reader) and the D-10 descuadre check know which fields hold the
  debit/credit/saldo totals.
- **Descuadre tolerance (D-09/D-10):** the user deferred this to research —
  decide what is feasible and practical: exact-zero comparison vs a fixed small
  tolerance vs a configurable `--precision`-style CLI flag. Real-world rounding
  in ContaPlus data and `Decimal`-sum behaviour inform the choice.
- **Trial-balance computation from the journal (BAL-02):** confirm the
  *sumas y saldos* formula (saldo deudor / saldo acreedor derivation from summed
  debe/haber) and whether opening-balance / *apertura* journal entries need any
  special handling vs being plain summed.
- **Lenient-mode mechanics:** how per-row journal best-effort interacts with the
  existing first-fail `D-C5` reader loop in `_reader.py`; how a
  present-but-unreadable secondary table is caught and converted into a problems
  entry without aborting.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Format, rules & ContaPlus tables (primary)
- `SEED.md` — **the primary reference.** Read in full; for Phase 3 especially:
  §1 "Related ContaPlus files" (`BALAN.DBF` is a derived/temporary file, *known
  to develop descuadres*, must not be treated as source of truth — recompute
  from `DIARIO.DBF`), §3 "Column-name variants (defensive resolution)", §5 "DBF
  reader invocation specifics", §6 "Format gotchas" (gotcha #10 multi-exercise
  trees, gotcha #11 big files / lazy iteration). Note: `venci`/`prede`/`amoinv`/
  `nivel` are **not documented in SEED** — schema discovery is required (D-14).

### Project specs
- `.planning/PROJECT.md` — scope, constraints, Key Decisions table; note the
  `pii-test-data/` description and "research must enumerate and spec the
  non-journal tables".
- `.planning/REQUIREMENTS.md` — Phase 3 requirements TABL-03, TABL-04, BAL-01,
  BAL-02, API-03, XLSX-02, XLSX-03.
- `.planning/ROADMAP.md` §"Phase 3: Full Tables, Balance & Lenient Path" — phase
  goal and the four success criteria the verifier checks. **Two refinements**
  recorded in this CONTEXT: criterion #3's singular "trial-balance sheet" becomes
  two sheets (D-07); criterion #3's unconditional `BALAN` disclaimer becomes
  conditional on a descuadre (D-09).
- `.planning/phases/01-journal-slice/01-CONTEXT.md` — Phase 1 decisions carried
  forward: D-03 (`ContaPlusData` container = extension seam), D-04 (strict-only;
  Phase 3 adds the lenient parameter), D-06 (`read()` signature), D-07
  (`JournalRow` shape), D-12 (Spanish headers).
- `.planning/phases/02-zip-subaccounts/02-CONTEXT.md` — Phase 2 decisions carried
  forward: D-06 (uniform strict — abort on present-but-unreadable table; Phase 3
  lenient relaxes this), D-13 (full-dump, raw field-name headers), D-14 (Spanish
  sheet tabs), D-16 (defensive field-name resolution), D-17 (`pii-test-data/`
  schema-discovery gate — reapplied to the Phase 3 operational tables + `BALAN`).
- `CLAUDE.md` (repo root) — locked tech stack (Python ≥3.13, uv/uv_build, Typer,
  Rich, dbfread, pandas, openpyxl) and the "What NOT to Use" list (never
  `latin-1`, never `dbfread(load=True)` on large journals).

### Local validation gate (CONFIDENTIAL — never read into output or commit)
- `pii-test-data/` — 5 real ContaPlus backup `.zip` archives (4 single-company,
  1 multi-company). The schema-discovery gate for the `venci`/`prede`/`amoinv`/
  `nivel` typed readers and the `BALAN.DBF` raw reader (D-14, Open for Research).
  **Git-ignored, internal-only — its contents must never be committed, quoted in
  output, or read into any public artifact.** The committed test suite uses only
  synthetic, blob-free fixtures generated at collection time.

### Porting source — fallback only, OUTSIDE this repo
SEED.md is self-contained; consult these only to cross-check ported logic:
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — current
  reader; cross-check only if a journal rule is ambiguous.
- `C:\dev\tax-workbench\packages\tw-contaplus\tests\` — existing tests and the
  synthetic-DBF/ZIP fixture factory (`conftest.py`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`src/contaplus_reader/__init__.py`** — `read()`, the single public entry
  point. Phase 3 adds the `lenient` parameter (D-01) and threads the
  problems-collection through both the ZIP and DBF branches.
- **`src/contaplus_reader/models.py`** — `ContaPlusData` (deliberately *not*
  frozen — the extension seam), `ContaPlusJournal`, `JournalRow`,
  `ContaPlusReadError`, `GenericTable`, `SubctaTable`/`SubctaRow`. Phase 3 adds
  sibling table types + the recomputed-balance and raw-`BALAN` types, and a
  problems-report type. `GenericTable` is likely reusable for the operational
  tables and raw `BALAN` (full-dump, schema-driven headers via `headers` tuple).
- **`src/contaplus_reader/_subcta.py`** — `read_table_raw()` builds a
  `GenericTable` (full dump, `lowernames=False`, schema-driven headers,
  `ContaPlusReadError`-wrapped). This is the model for the operational-table and
  raw-`BALAN` readers. `_pick_column` (via `_reader.py`) is the defensive
  field-name resolver if any operational table needs it.
- **`src/contaplus_reader/_reader.py`** — `_read_dbf_path()`, `_pick_column()`,
  the first-fail journal validation loop (D-C5). Phase 3's lenient journal mode
  (D-02) must add a best-effort variant of this loop — skip+collect instead of
  raise-on-first.
- **`src/contaplus_reader/_zip.py`** — `_safe_extract_zip()`,
  `_resolve_company_diario()`, `_find_sibling_dbf()`. The sibling-DBF discovery
  pattern extends to locating `venci`/`prede`/`amoinv`/`nivel`/`BALAN` alongside
  the selected `DIARIO.DBF`.
- **`src/contaplus_reader/xlsx.py`** — `render()` is already data-driven
  (one sheet per non-None table on `ContaPlusData`), with reusable styling
  constants (`HEADER_FILL`, `HEADER_FONT`, `ACCOUNTING_FMT`, `DATE_FMT`,
  `_autosize_columns`) and `_render_generic_sheet()`. Phase 3 adds sheet
  renderers for the operational tables, the two balance sheets, the conditional
  `BALAN` banner, and the problems sheet — reusing the styling template verbatim.
- **`src/contaplus_reader/cli.py`** — the Typer CLI. Phase 3 adds the
  `--lenient` flag; the Rich error-panel pattern and the one-line summary already
  exist.
- **`tests/conftest.py`** — the synthetic-fixture factory. Phase 3 extends it
  with synthetic `venci`/`prede`/`amoinv`/`nivel`/`BALAN` DBFs and
  defect-bearing fixtures for the lenient/problems-sheet tests.

### Established Patterns
- Full-dump table reads via `DBF(..., lowernames=False, ...)` → `GenericTable`
  with a schema-captured `headers` tuple (WR-05 — schema from the DBF, not row 0).
- `ContaPlusReadError` wrapping of `struct.error`/`ValueError`/`OSError`/
  `UnicodeDecodeError` at every reader boundary; `row_index = -1` for file-level.
- Data-driven `render()` — one sheet per populated table; styling applied
  uniformly via shared constants and `_autosize_columns`.
- Per-phase `D-NN` decision numbering in CONTEXT.md.

### Integration Points
- `read()` — gains the `lenient` parameter and the problems-collection plumbing
  (D-01).
- `ContaPlusData` — gains `venci`/`prede`/`amoinv`/`nivel` table attributes, a
  raw-`BALAN` attribute, two recomputed-balance attributes, and a problems-report
  attribute (D-05/D-07/D-14).
- `render()` — gains operational-table sheets, two balance sheets, the
  conditional `BALAN` banner, and the problems sheet.
- `cli.py` — gains the `--lenient` flag (D-01).

</code_context>

<specifics>
## Specific Ideas

- **Conditional `BALAN` disclaimer (D-09)** — the user explicitly rejected an
  always-on disclaimer: "If the Balance Sheet sums to zero, then it's fine. Only
  when the balance sheet does not add up to zero we show the banner row." The
  banner is a *descuadre detector*, not a blanket warning.
- **Two trial-balance sheets, both levels (D-07)** — the user explicitly wanted
  both the 4-digit `cuenta` rollup and the full `subcuenta` detail as separate
  sheets, not one combined sheet.
- **Both saldo forms (D-08)** — the user explicitly wanted the classic Spanish
  split (`Saldo Deudor` / `Saldo Acreedor`) *and* a convenience signed `Saldo`
  column, not one or the other.
- **Strict stays the default everywhere (D-01)** — the user chose strict as the
  CLI default despite the migration audience; `--lenient` is the deliberate
  opt-in. The journal's strict reading remains the project's core value.
- **Descuadre tolerance is a research call** — the user has "no idea" what's
  practical and explicitly delegated it: "let research decide what is feasible
  and practical in this context."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No new out-of-phase capabilities
surfaced.

**ROADMAP criterion refinements noted during discussion** (not new scope —
clarifications of *how* Phase 3 delivers what is already scoped):
- ROADMAP Phase 3 criterion #3's singular "recomputed trial-balance sheet"
  becomes **two sheets** — cuenta-level and subcuenta-level (D-07).
- ROADMAP Phase 3 criterion #3's unconditional `BALAN` "visible disclaimer"
  becomes **conditional** — shown only on a detected descuadre (D-09).

The verifier should reconcile against these documented refinements.

</deferred>

---

*Phase: 3-full-tables-balance-lenient-path*
*Context gathered: 2026-05-17*
