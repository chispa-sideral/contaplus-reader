---
phase: "03"
plan: "04"
subsystem: xlsx-cli
tags: [xlsx-renderer, cli, lenient-path, balance, tdd-green, phase3-complete]
dependency_graph:
  requires:
    - "03-03: ContaPlusData fully populated with balan, venci, prede, amoinv, nivel, balance_cuenta, balance_subcuenta, problems"
    - "Phase 2: render(), _render_generic_sheet(), _autosize_columns() patterns"
  provides:
    - "xlsx.py: _render_balan_sheet (conditional SDO_CIERRE descuadre banner)"
    - "xlsx.py: _render_balance_sheet (cuenta + subcuenta variants, D-08 columns)"
    - "xlsx.py: _render_problems_sheet (D-06 five Spanish columns)"
    - "xlsx.py: _autosize_columns_from_offset (Pitfall 5 banner-width guard)"
    - "xlsx.py: render() full Phase 3 sheet order (13-sheet catalogue)"
    - "cli.py: --lenient flag wired to read(lenient=lenient)"
    - "cli.py: problems count in one-line success summary"
  affects:
    - "All callers of render() — sheet order changed (Empresa/Grupos/Usuarios moved after Niveles)"
tech_stack:
  added:
    - "openpyxl.utils.get_column_letter — used in _autosize_columns_from_offset to avoid MergedCell.column_letter AttributeError"
  patterns:
    - "_render_balan_sheet: SDO_CIERRE None guard (T-03-13); merge_cells A1:C1 for banner"
    - "_autosize_columns_from_offset: col_idx enumeration + get_column_letter avoids MergedCell issue"
    - "_render_balance_sheet: float(Decimal) for openpyxl cells + ACCOUNTING_FMT per D-08"
    - "render() conditional Problemas sheet: only when problems is not None and entries non-empty (D-05)"
key_files:
  created: []
  modified:
    - src/contaplus_reader/xlsx.py
    - src/contaplus_reader/cli.py
decisions:
  - "Used get_column_letter(col_idx) enumeration in _autosize_columns_from_offset instead of col_cells[0].column_letter — MergedCell objects returned by ws.columns when the banner merge is present do not have column_letter attribute"
  - "Empresa/Grupos/Usuarios reordered to after Niveles in render() to match documented Phase 3 sheet order (D-11/D-15)"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-17"
  tasks_completed: 2
  files_modified: 2
---

# Phase 03 Plan 04: Phase 3 Sheet Renderers and --lenient CLI Flag Summary

Added all Phase 3 XLSX sheet renderers to xlsx.py and the --lenient flag to cli.py, completing the vertical slice: `contaplus2xlsx backup.zip out.xlsx --lenient` now produces a full workbook with all operational-table sheets, trial-balance sheets, a conditional BALAN descuadre banner, and a Problemas sheet for any defects.

## What Was Built

### Task 1: Phase 3 sheet renderers + render() sheet order

**Commit:** `8267582`

Extended `src/contaplus_reader/xlsx.py`:

**New imports:**
- `from decimal import Decimal` — for SDO_CIERRE sum accumulation
- `BalanceTable`, `ProblemsReport` added to models import
- `from openpyxl.utils import get_column_letter` — used in _autosize_columns_from_offset

**New styling constants:**
- `BANNER_FILL = PatternFill(fill_type="solid", fgColor="FF0000")` — red fill for descuadre banner
- `BANNER_FONT = Font(bold=True, color="FFFFFF")`
- `_BALANCE_HEADERS_CUENTA` — 6-column Spanish headers for cuenta-level sheet
- `_BALANCE_HEADERS_SUBCUENTA` — 7-column Spanish headers including Descripción for subcuenta-level
- `_PROBLEMS_HEADERS` — ["Tabla", "Fila", "Columna", "Motivo", "Valor"]

**`_render_balan_sheet(ws, balan)`:**
- Finds SDO_CIERRE column index via `next(...)` with `StopIteration` fallback to `None`
- Sums SDO_CIERRE with Decimal accumulation and explicit None guard (T-03-13)
- When sum != 0: writes AVISO banner at row 1, merges A1:C1, sets header_row_offset=2
- Writes field-name headers at header_row_offset; data rows at header_row_offset+1
- Calls `_autosize_columns_from_offset(ws, start_row=header_row_offset)` (Pitfall 5)

**`_render_balance_sheet(ws, table)`:**
- Uses `_BALANCE_HEADERS_SUBCUENTA` when `table.level == "subcuenta"`, else `_BALANCE_HEADERS_CUENTA`
- Writes code in col 1; subcuenta level also writes `br.descripcion` in col 2 (may be None)
- Converts all six Decimal columns to float with ACCOUNTING_FMT number_format
- Correct column offset (2 for subcuenta, 1 for cuenta)

**`_render_problems_sheet(ws, report)`:**
- Five Spanish headers in A-E with HEADER_FILL/HEADER_FONT
- Writes `entry.table`, `entry.row_index`, `entry.column`, `entry.reason`, `entry.value`

**`_autosize_columns_from_offset(ws, start_row)`:**
- Iterates `ws.columns` with explicit `col_idx` enumeration
- Uses `get_column_letter(col_idx)` instead of `col_cells[0].column_letter` — avoids MergedCell AttributeError when the A1:C3 banner merge is present

**`render()` sheet order updated:**
Diario → Subcuentas → Balance (_render_balan_sheet) → Sumas y Saldos (Cuentas) → Sumas y Saldos (Subcuentas) → Vencimientos → Predefinidos → Amortizaciones → Niveles → Empresa → Grupos → Usuarios → Problemas (conditional: only when `data.problems.entries` non-empty, D-05)

### Task 2: --lenient flag and problems count in CLI

**Commit:** `132e046`

Extended `src/contaplus_reader/cli.py`:

- Added `lenient: Annotated[bool, typer.Option("--lenient", help="...")]` parameter after `force`
- Updated `read()` call: `data = read(raw_bytes, source_name=str(input_file), company=company, lenient=lenient)`
- Added `problems_count` local variable; appends `", {N} problem(s)"` to echo only when > 0
- `--help` now lists `--lenient` in the Options section
- Strict mode (default `lenient=False`): behavior identical to before — no new code paths

## Test Results

All 120 tests pass — 0 regressions:

| Test file | Before | After |
|-----------|--------|-------|
| test_xlsx.py | 25/35 (10 RED) | 35/35 |
| test_cli.py | 17/17 | 17/17 |
| test_balance.py | 8/8 | 8/8 |
| test_lenient.py | 8/8 | 8/8 |
| test_reader.py | 40/40 | 40/40 |
| test_tables.py | 12/12 | 12/12 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MergedCell AttributeError in _autosize_columns_from_offset**
- **Found during:** Task 1 initial test run
- **Issue:** `ws.columns` returns `MergedCell` objects for the A1:C1 banner merge region. `MergedCell` has no `column_letter` attribute, so `col_cells[0].column_letter` raised `AttributeError: 'MergedCell' object has no attribute 'column_letter'` in `test_balan_banner_on_descuadre`.
- **Fix:** Changed `_autosize_columns_from_offset` to enumerate `ws.columns` with an explicit `col_idx` counter and use `get_column_letter(col_idx)` (imported from `openpyxl.utils`) rather than accessing `.column_letter` on the first cell of each column tuple.
- **Files modified:** `src/contaplus_reader/xlsx.py`
- **Commit:** `8267582` (included in the same task commit)

## Known Stubs

None. All renderers write actual model data. No placeholder text or hardcoded empty values in rendered output.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes beyond what the plan's threat model covers.

- T-03-12 (DoS via column width): `_autosize_columns_from_offset` caps at 50 chars — same guard as `_autosize_columns`
- T-03-13 (None in Decimal sum): `if row[sdo_idx] is not None` guard verified by `test_balan_no_banner_when_balanced`

## Self-Check: PASSED

Files exist:
- `src/contaplus_reader/xlsx.py` — FOUND (modified)
- `src/contaplus_reader/cli.py` — FOUND (modified)

Commits exist:
- `8267582` — feat(03-04): add Phase 3 sheet renderers and update render() sheet order
- `132e046` — feat(03-04): add --lenient flag to CLI and problems count to one-line summary

Test results:
- `tests/test_xlsx.py`: 35/35 GREEN (all 10 previously RED now GREEN)
- `tests/test_cli.py`: 17/17 GREEN
- Full suite: 120/120 GREEN
