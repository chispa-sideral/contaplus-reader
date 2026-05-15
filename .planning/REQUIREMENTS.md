# Requirements: contaplus-reader

**Defined:** 2026-05-15
**Core Value:** Correctly extract ContaPlus accounting data — above all the journal, whose strict, validated reading tax-workbench depends on.

## v1 Requirements

Requirements for the initial release. Each maps to roadmap phases.

### Input Handling

- [ ] **INPUT-01**: Reader accepts a raw `.dbf` file as bytes or a file-like object (no filesystem path required)
- [ ] **INPUT-02**: Reader accepts a ContaPlus backup `.zip` as bytes or a file-like object
- [ ] **INPUT-03**: Reader sniffs the input type and rejects unsupported inputs with a structured error
- [ ] **INPUT-04**: ZIP extraction works from an in-memory buffer and is zip-slip-safe (rejects path-traversal entries)
- [ ] **INPUT-05**: Reader recursively locates ContaPlus tables inside a backup ZIP regardless of nesting depth
- [ ] **INPUT-06**: Multi-company ZIP is disambiguated by a caller-supplied company selector; ambiguous or missing selection fails listing the available company names

### Journal Reader (`DIARIO.DBF`)

- [ ] **JRNL-01**: Reader extracts validated journal rows (`fecha, cuenta, subcuenta, debe, haber, concepto`), porting the existing `tw-contaplus` business rules (D-A1…D-E3) including `cuenta = subcuenta[:4]`
- [ ] **JRNL-02**: Journal reader handles ContaPlus format quirks — cp850 decoding, trailing-whitespace stripping, deleted records, both-zero memo lines (with a surfaced skipped count), negative amounts (sign preserved), and case-insensitive debit/credit column-name variants
- [ ] **JRNL-03**: Journal reader rejects invalid rows (null `FECHA`, both-non-zero amounts, malformed `subcuenta`) with a structured per-row error carrying row and column context

### Other Table Readers

- [ ] **TABL-01**: Typed reader for `SUBCTA.DBF` (chart of subaccounts) with defensive field-name resolution (`CODIGO`/`COD`, `DESCRIP`/`TITULO`, `NIF`/`CIF`)
- [ ] **TABL-02**: Typed readers for the group-level tables (`grupos.dbf`, `usuarios.dbf`, `empresa.dbf`)
- [ ] **TABL-03**: Typed readers for the operational tables (`venci.dbf`, `prede.dbf`, `amoinv.dbf`, `nivel.dbf`), with field schemas validated against real `pii-test-data/` archives before implementation
- [ ] **TABL-04**: Reader extracts every recognized table from a backup ZIP in a single pass

### Trial Balance

- [ ] **BAL-01**: Typed reader extracts the raw `BALAN.DBF` trial-balance data
- [ ] **BAL-02**: Tool computes an authoritative trial balance (sumas y saldos) from `DIARIO.DBF` journal data

### Read API & Result Model

- [ ] **API-01**: Library exposes a single bytes-first read API used by all consumers (CLI, PWA, tax-workbench)
- [ ] **API-02**: Strict read path fails loudly on invalid data, raising `ContaPlusReadError` with row/column/context
- [ ] **API-03**: Lenient conversion path extracts all readable data, collects problems into a report, and never aborts the whole file
- [ ] **API-04**: Library returns self-contained result types (`ContaPlusJournal` and per-table siblings) with no `tw-domain` dependency
- [ ] **API-05**: Journal result is enriched with account/subaccount names when `SUBCTA.DBF` is present in the input

### XLSX Rendering

- [ ] **XLSX-01**: Shared, templated XLSX renderer produces a styled workbook with one sheet per extracted table
- [ ] **XLSX-02**: Renderer includes a problems/report sheet listing rows the lenient path skipped or flagged
- [ ] **XLSX-03**: Renderer marks the raw `BALAN` sheet with a visible "derived — may be unreliable" disclaimer
- [ ] **XLSX-04**: Renderer is callable identically from the CLI and the PWA, with no filesystem assumptions

### CLI (`contaplus2xlsx`)

- [ ] **CLI-01**: `contaplus2xlsx` converts a single `.dbf`/`.zip` file to a styled `.xlsx`
- [ ] **CLI-02**: CLI selects a company in a multi-company backup via a flag
- [ ] **CLI-03**: CLI reports row counts, skipped-memo count, and any problems to stdout
- [ ] **CLI-04**: CLI is installable and runnable via `uvx` / `pipx`

### PWA

- [ ] **PWA-01**: PWA converts a ContaPlus file to `.xlsx` entirely in the browser — the file never leaves the user's machine
- [ ] **PWA-02**: User drags-and-drops or selects a `.dbf`/`.zip` file and downloads the generated `.xlsx`
- [ ] **PWA-03**: PWA surfaces conversion errors and the problems report clearly to the user
- [ ] **PWA-04**: PWA caches the Python runtime via a service worker for fast repeat and offline visits
- [ ] **PWA-05**: PWA is deployed to a public Cloudflare Pages URL

### Distribution

- [ ] **DIST-01**: Library is published to PyPI as `contaplus-reader` under LGPL-3.0-or-later
- [ ] **DIST-02**: `uv build` produces a wheel usable for PyPI publish and for local dev (editable installs, `micropip` from a locally built wheel)

### Testing

- [ ] **TEST-01**: Test suite uses synthetic, blob-free `.dbf`/`.zip` fixtures generated at test-collection time
- [ ] **TEST-02**: Existing `tw-contaplus` journal-reader coverage is ported and passing

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Reader

- **ENC-01**: Encoding autodetection via the DBF header byte-29 codepage marker (v1 forces `cp850`)
- **VAL-01**: Two-pass "collect every bad row" validation in the strict API (v1 is first-fail)
- **SUB-01**: Support for alpha-prefixed subaccount codes (e.g. `A4300001`)

### PWA

- **PWA-V2-01**: In-browser multi-company picker UI (v1 surfaces the multi-company error listing companies)
- **PWA-V2-02**: In-page preview table of parsed rows before download

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| tax-workbench `tw-contaplus` rewrite as a thin adapter | Tracked in tax-workbench; triggered by the contaplus-reader v0.1 release |
| Qt GUI / `ReadDBFWidget` | The standalone GUI is the web PWA; nothing ports from `tests/qt/` |
| Batch / glob CLI input | v1 CLI is single-file by decision |
| FacturaPlus article tables (`articulo.dbf`, …) | Different product; not part of ContaPlus accounting data |
| Sage 50 CSV export | Different format and product; v1 is ContaPlus DBF only |
| Committing real ContaPlus data as test fixtures | Confidential; the suite uses synthetic blob-free fixtures (`pii-test-data/` is git-ignored) |

## Traceability

Which phases cover which requirements. **Populated during roadmap creation.**

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | TBD | Pending |
| INPUT-02 | TBD | Pending |
| INPUT-03 | TBD | Pending |
| INPUT-04 | TBD | Pending |
| INPUT-05 | TBD | Pending |
| INPUT-06 | TBD | Pending |
| JRNL-01 | TBD | Pending |
| JRNL-02 | TBD | Pending |
| JRNL-03 | TBD | Pending |
| TABL-01 | TBD | Pending |
| TABL-02 | TBD | Pending |
| TABL-03 | TBD | Pending |
| TABL-04 | TBD | Pending |
| BAL-01 | TBD | Pending |
| BAL-02 | TBD | Pending |
| API-01 | TBD | Pending |
| API-02 | TBD | Pending |
| API-03 | TBD | Pending |
| API-04 | TBD | Pending |
| API-05 | TBD | Pending |
| XLSX-01 | TBD | Pending |
| XLSX-02 | TBD | Pending |
| XLSX-03 | TBD | Pending |
| XLSX-04 | TBD | Pending |
| CLI-01 | TBD | Pending |
| CLI-02 | TBD | Pending |
| CLI-03 | TBD | Pending |
| CLI-04 | TBD | Pending |
| PWA-01 | TBD | Pending |
| PWA-02 | TBD | Pending |
| PWA-03 | TBD | Pending |
| PWA-04 | TBD | Pending |
| PWA-05 | TBD | Pending |
| DIST-01 | TBD | Pending |
| DIST-02 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 37 ⚠️

---
*Requirements defined: 2026-05-15*
*Last updated: 2026-05-15 after initial definition*
