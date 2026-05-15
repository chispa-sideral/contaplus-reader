# Roadmap: contaplus-reader

## Overview

Five vertical slices, each thicker than the last. Phase 1 is the thinnest possible
working path: bytes in, journal reader, XLSX out, CLI runnable. Each subsequent phase
thickens the slice — ZIP inputs, secondary table readers, the lenient conversion path,
full CLI + PyPI publication, and finally the browser PWA (which depends on the published
wheel). Every phase delivers something a user can run and verify end-to-end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Journal Slice** - Thin working vertical: bytes → DIARIO.DBF reader → XLSX → CLI (completed 2026-05-15)
- [ ] **Phase 2: ZIP & Subaccounts** - ZIP input, SUBCTA reader, journal name enrichment, group-level tables
- [ ] **Phase 3: Full Tables, Balance & Lenient Path** - Operational-table readers, trial-balance computation, lenient conversion path, XLSX report sheet
- [ ] **Phase 4: Full CLI & PyPI Publication** - Multi-company flag, stdout reporting, wheel published to PyPI
- [ ] **Phase 5: Browser PWA** - Pyodide spike then full client-side PWA on Cloudflare Pages

## Phase Details

### Phase 1: Journal Slice
**Goal**: A user can convert a journal-only `DIARIO.DBF` to a styled `.xlsx` by running `contaplus2xlsx DIARIO.DBF out.xlsx`
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: INPUT-01, INPUT-03, JRNL-01, JRNL-02, JRNL-03, API-01, API-02, API-04, XLSX-01, XLSX-04, CLI-01, CLI-04, TEST-01, TEST-02, DIST-02
**Success Criteria** (what must be TRUE):
  1. Running `contaplus2xlsx DIARIO.DBF out.xlsx` produces a styled `.xlsx` with a journal sheet containing validated rows
  2. The CLI rejects an invalid `.dbf` with a structured error message naming the offending row and column
  3. `uv build` produces a wheel; `uvx contaplus2xlsx` installs and runs from that wheel
  4. The test suite uses synthetic blob-free fixtures and all ported `tw-contaplus` journal coverage passes
  5. The bytes-first API (`read(data: bytes | BinaryIO)`) is the only entry point — no filesystem-path argument
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Package scaffold, journal reader, models, bridge, sniffer, fixture factory, ~27 reader tests (completed 2026-05-15)
- [x] 01-02-PLAN.md — XLSX renderer (Spanish headers, accounting format), Typer CLI, XLSX tests, CLI tests
- [x] 01-03-PLAN.md — README, .gitignore, uv build wheel, uvx smoke test (human checkpoint)

### Phase 2: ZIP & Subaccounts
**Goal**: A user can convert a full ContaPlus backup `.zip` — including SUBCTA enrichment of the journal — to a multi-sheet `.xlsx`
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: INPUT-02, INPUT-04, INPUT-05, INPUT-06, TABL-01, TABL-02, API-05
**Success Criteria** (what must be TRUE):
  1. Running `contaplus2xlsx backup.zip out.xlsx` produces a `.xlsx` with a journal sheet where account names are populated from `SUBCTA.DBF`
  2. A multi-company ZIP passed without a `--company` flag exits with an error listing the available company names
  3. ZIP extraction rejects a path-traversal entry (zip-slip attack) with a structured error
  4. The `.xlsx` includes sheets for `SUBCTA`, `grupos`, `usuarios`, and `empresa` when those tables are present in the archive
**Plans**: TBD

### Phase 3: Full Tables, Balance & Lenient Path
**Goal**: A user running lenient conversion gets every readable table extracted — including operational tables and a recomputed trial balance — plus a problems sheet listing anything that was skipped
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: TABL-03, TABL-04, BAL-01, BAL-02, API-03, XLSX-02, XLSX-03
**Success Criteria** (what must be TRUE):
  1. A backup ZIP converted with the lenient flag produces a `.xlsx` that includes sheets for `venci`, `prede`, `amoinv`, and `nivel`
  2. The `.xlsx` contains a problems sheet listing every row the lenient path flagged or skipped, with row and column context
  3. The `BALAN` sheet carries a visible "derived — may be unreliable" disclaimer; the recomputed trial-balance sheet is presented as authoritative
  4. Field schemas for `venci`, `prede`, `amoinv`, and `nivel` are validated against `pii-test-data/` archives before typed readers are committed
**Plans**: TBD

### Phase 4: Full CLI & PyPI Publication
**Goal**: The tool is installable from PyPI, the CLI handles all v1 options, and the published wheel is ready for `micropip` consumption by the PWA
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: CLI-02, CLI-03, DIST-01
**Success Criteria** (what must be TRUE):
  1. `pip install contaplus-reader` installs the library and `contaplus2xlsx` CLI from PyPI
  2. `contaplus2xlsx backup.zip out.xlsx --company ACME` selects the correct company in a multi-company ZIP
  3. CLI stdout reports row counts, skipped-memo count, and any problem entries after every conversion
  4. The published wheel is installable via `micropip` in a Pyodide environment (validated locally before PWA phase begins)
**Plans**: TBD

### Phase 5: Browser PWA
**Goal**: Any user can drag-and-drop a ContaPlus file on a public URL, convert it entirely in the browser, and download the styled `.xlsx` — the file never leaves their machine
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: PWA-01, PWA-02, PWA-03, PWA-04, PWA-05
**Success Criteria** (what must be TRUE):
  1. A user on the public Cloudflare Pages URL can drag-drop a `.dbf` or `.zip` and download a styled `.xlsx` with no install and no upload
  2. The Pyodide/`micropip`/Web Worker spike is completed and COOP/COEP headers are confirmed working before the full shell is built
  3. Conversion errors and the problems report are surfaced clearly in the browser UI
  4. On a repeat visit the PWA loads without re-downloading the Python runtime (service worker caching verified)
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Journal Slice | 3/3 | Complete   | 2026-05-15 |
| 2. ZIP & Subaccounts | 0/TBD | Not started | - |
| 3. Full Tables, Balance & Lenient Path | 0/TBD | Not started | - |
| 4. Full CLI & PyPI Publication | 0/TBD | Not started | - |
| 5. Browser PWA | 0/TBD | Not started | - |
