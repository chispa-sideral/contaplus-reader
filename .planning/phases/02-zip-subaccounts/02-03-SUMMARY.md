---
phase: "02-zip-subaccounts"
plan: "03"
subsystem: "library+cli"
tags: [xlsx, multi-sheet, descripcion, company-flag, render, tdd-green]
dependency_graph:
  requires: [zip-read-pipeline, subcta-enrichment, group-tables, ContaPlusData-model]
  provides: [multi-sheet-renderer, company-cli-flag, descripcion-column]
  affects:
    - src/contaplus_reader/xlsx.py
    - src/contaplus_reader/cli.py
    - tests/test_xlsx.py
    - tests/test_cli.py
tech_stack:
  added: []
  patterns:
    - data-driven multi-sheet renderer (one sheet per non-None ContaPlusData attribute)
    - render() primary entry point; render_journal() backward-compat alias pattern
    - private _render_*_sheet() helpers sharing _autosize_columns() utility
    - Typer Annotated[str | None, typer.Option()] pattern for optional string flags
    - multi-sheet success summary: "N journal rows, N sheet(s)"
key_files:
  created: []
  modified:
    - src/contaplus_reader/xlsx.py
    - src/contaplus_reader/cli.py
    - tests/test_xlsx.py
    - tests/test_cli.py
decisions:
  - "D-12 implemented: data-driven renderer emits one sheet per non-None ContaPlusData table"
  - "D-13 implemented: non-journal sheets use raw DBF field names as headers"
  - "D-14 implemented: sheet tabs are Spanish (Diario, Subcuentas, Empresa, Grupos, Usuarios)"
  - "D-15 implemented: Descripción column at index 4 in Diario; blank when subcuenta_nombre is None"
  - "D-07 implemented: --company Annotated[str | None, typer.Option()] added to CLI main()"
  - "D-08 confirmed: existing Rich ContaPlusReadError panel surfaces multi-company error transparently"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-16T09:20:00Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 03: Multi-Sheet XLSX Renderer + CLI --company Flag Summary

**One-liner:** Multi-sheet xlsx renderer with Descripción column and --company CLI flag — completing Phase 2 delivery by wiring ContaPlusData through to a styled workbook with one sheet per populated table.

## What Was Built

### Task 1: Generalized xlsx.py — render(ContaPlusData) + Descripción (commits 73da9e7, d3ec20c)

**TDD: RED commit (73da9e7):** Updated 8 Phase 1 xlsx tests to reflect new 7-column HEADERS (Descripción at index 4) and shifted column positions (Debe=5, Haber=6, Concepto=7). Removed xfail markers from `test_render_multi_sheet_names` and `test_render_descripcion_column_present`. All 8 confirmed failing before implementation.

**TDD: GREEN commit (d3ec20c):**

`xlsx.py` — rewritten with backward-compat alias pattern:

- `HEADERS` updated to 7 columns: `["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]` (D-15 Descripción at index 3, 1-based column 4).
- `render(data: ContaPlusData) -> bytes` is the new primary entry point (D-12). Sheet order: Diario (active), then Subcuentas/Empresa/Grupos/Usuarios only if non-None.
- `render_journal(journal: ContaPlusJournal) -> bytes` becomes a one-liner alias: `return render(ContaPlusData(journal=journal))`.
- `_render_journal_sheet(ws, journal)` private helper: writes 7-column HEADERS, freeze A2, data rows with col 4=subcuenta_nombre (None → blank cell), D-11 accounting formats on cols 5 and 6.
- `_render_subcta_sheet(ws, subcta)` private helper: extracts headers from first row's `fields` dict keys (insertion order, D-13), applies D-10 styling.
- `_render_generic_sheet(ws, table)` private helper: uses `table.headers` (raw DBF field names, D-13), applies D-10 styling.
- `_autosize_columns(ws)` shared utility extracted from original render_journal body.

### Task 2: CLI --company flag + render(data) wiring (commits dc28ba5, ae75d05)

**TDD: RED commit (dc28ba5):** Removed xfail markers from `test_cli_company_flag_accepted` (confirmed failing — typer rejects unknown --company) and `test_cli_multi_company_no_flag_exits_1` (was xpassed; confirmed passing via existing error panel).

**TDD: GREEN commit (ae75d05):**

`cli.py` — extended main() signature and call chain:

- `company: Annotated[str | None, typer.Option("--company", help="...")]  = None` inserted between `output_file` and `force` parameters (D-07).
- `input_file` help text updated to "Path to DIARIO.DBF file or backup .zip".
- Docstring updated to mention backup .zip.
- `read(raw_bytes, source_name=str(input_file), company=company)` — company passed through (D-04).
- `render(data)` replaces `render_journal(journal)` — multi-sheet output (D-12).
- Success summary: `f"{output_file} — {row_count} journal rows, {sheet_count} sheet(s){skip_msg}"` (D-16).
- Existing `except ContaPlusReadError` block handles D-08 transparently — multi-company error message surfaces via `exc.message` with no code change needed.

## Verification Results

```
72 passed in 1.10s
```

All Phase 2 success criteria verified:
1. `test_cli_company_flag_accepted` — GREEN (--company accepted, single-company ZIP with subcta enrichment works)
2. `test_cli_multi_company_no_flag_exits_1` — GREEN (exits 1 with "Emp01" in error output)
3. `test_reader.py -k zipslip` — GREEN (zip-slip guard still holds, no regression)
4. `test_render_multi_sheet_names` — GREEN (Diario + Subcuentas sheets in workbook)
5. `test_render_descripcion_column_present` — GREEN (Descripción header at column 4, value = "Cliente XYZ")

## Deviations from Plan

None — plan executed exactly as written. The backward-compat alias pattern and private helper extraction followed the PATTERNS.md §xlsx.py patterns exactly.

## Known Stubs

None — all data paths are wired end-to-end.
- `render(data)` consumes ContaPlusData with all attributes populated by the Phase 2 ZIP reader.
- `--company` is passed through to `read()` which dispatches correctly for single-company, multi-company, and DBF inputs.
- Descripción column populated from `subcuenta_nombre` (set by SUBCTA enrichment in Phase 2 ZIP reader).

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. T-02-04 (xlsx formula injection) and T-02-05 (usuarios credential fields) remain accepted per the plan's threat model.

## Self-Check: PASSED
