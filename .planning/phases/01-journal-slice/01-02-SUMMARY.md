---
phase: "01-journal-slice"
plan: 2
subsystem: "xlsx-renderer + cli"
tags: ["python", "xlsx", "openpyxl", "typer", "cli", "renderer"]
dependency_graph:
  requires:
    - "contaplus_reader.read() bytes-first API (01-01)"
    - "ContaPlusJournal / JournalRow types (01-01)"
    - "ContaPlusReadError (01-01)"
    - "synthetic DBF fixture factory conftest.py (01-01)"
  provides:
    - "render_journal(ContaPlusJournal) -> bytes"
    - "HEADERS / ACCOUNTING_FMT / DATE_FMT constants"
    - "contaplus2xlsx Typer CLI app"
    - "19-test XLSX renderer suite"
    - "13-test CLI suite"
  affects:
    - "PWA XLSX renderer (Phase 5) -- same render_journal() signature"
    - "tax-workbench thin adapter -- will import render_journal via PyPI wheel"
tech_stack:
  added: []
  patterns:
    - "openpyxl direct Workbook (no pandas ExcelWriter) for per-cell format control"
    - "D-12 Spanish headers exception to English-everything convention (statutory data)"
    - "Typer two-alias option pattern: typer.Option('--force', '--overwrite')"
    - "raise typer.Exit(1) from None -- suppresses traceback chain (D-17)"
    - "Console(stderr=True) for error output to avoid polluting stdout"
key_files:
  created:
    - "src/contaplus_reader/xlsx.py"
    - "src/contaplus_reader/cli.py"
    - "tests/test_xlsx.py"
    - "tests/test_cli.py"
  modified: []
decisions:
  - "render_journal() uses openpyxl Workbook directly (not pandas ExcelWriter) -- gives per-cell number_format control without DataFrame overhead at the API boundary"
  - "CLI Console(stderr=True) keeps stdout clean (D-16 echo goes to stdout; errors go to stderr)"
  - "raise typer.Exit(1) from None used to suppress traceback chain completely (D-17)"
metrics:
  duration: "12 minutes"
  completed_date: "2026-05-15"
  tasks_completed: 2
  files_created: 4
---

# Phase 01 Plan 02: XLSX Renderer + CLI Entry Point Summary

**One-liner:** openpyxl-based render_journal() with Spanish headers, accounting format, and freeze_panes; Typer CLI with overwrite guard and Rich error panel — 50/50 tests green on Python 3.14.5.

## What Was Built

Completed the walking skeleton. A user can now run `contaplus2xlsx DIARIO.DBF out.xlsx` end to end.

### 1. XLSX Renderer (`src/contaplus_reader/xlsx.py`)

`render_journal(journal: ContaPlusJournal) -> bytes` converts validated journal data to a polished `.xlsx` workbook:

- **Spanish headers** (D-12 MANDATORY): `Fecha / Cuenta / Subcuenta / Debe / Haber / Concepto`
- **Header styling** (D-10): bold white font + `4472C4` Office Blue `PatternFill`
- **Freeze panes**: `ws.freeze_panes = "A2"` — header always visible on scroll
- **Accounting format** (D-11): `#,##0.00_);[Red](#,##0.00)` on debe/haber columns — red negatives, 2 decimals, thousands separator
- **Date format**: `DD/MM/YYYY` on fecha column
- **Auto-sized columns**: `col_cells[0].column_letter` pattern (avoids Pitfall 4 AttributeError); capped at 50 chars
- **No footer row** (D-13): data rows only
- **Returns bytes** (XLSX-04): `buf.getvalue()` — no filesystem assumption

### 2. CLI Entry Point (`src/contaplus_reader/cli.py`)

`contaplus2xlsx` Typer command:

- **Two required positional args** (D-14): `input_file` and `output_file` — no auto-derived default path
- **Overwrite guard** (D-15): exits 1 with error message if output exists unless `--force` / `--overwrite`
- **Bytes-first call**: `read(input_file.read_bytes(), source_name=str(input_file))`
- **Rich error panel** (D-17): `ContaPlusReadError` → `Panel(..., title="ContaPlus Read Error", border_style="red")` to stderr; `raise typer.Exit(1) from None` (no traceback)
- **Success summary** (D-16): `"{output_file} — {N} journal rows{skip_msg}"` to stdout

### 3. Test Suites

- `tests/test_xlsx.py`: 19 tests — output type, sheet title, Spanish headers, bold/fill styling, freeze_panes, accounting/date formats, negative value storage, empty journal, no footer row, column widths, data round-trip
- `tests/test_cli.py`: 13 tests — happy path, XLSX validity, success output format/filename, overwrite guard, `--force`, `--overwrite` alias, error exit code, Rich panel, no traceback, missing args, `--help`

**Full suite: 50/50 tests green** (`test_reader.py` + `test_xlsx.py` + `test_cli.py`)

## Deviations from Plan

None — plan executed exactly as written. Implementation follows PATTERNS.md §xlsx.py and §cli.py verbatim. All D-08/10/11/12/13/14/15/16/17 constraints implemented; all threat mitigations (T-02-02, T-02-03) applied.

## Known Stubs

None — all functionality is wired. `render_journal` produces real openpyxl output; CLI calls real `read()` and `render_journal()`. No placeholder values.

## Threat Surface Scan

No new threat surface beyond what was documented in the plan's `<threat_model>`. All mitigations applied:
- T-02-02: `if output_file.exists() and not force:` guard implemented in cli.py
- T-02-03: `raise typer.Exit(1) from None` suppresses traceback; Rich Panel is the only output for errors

## TDD Gate Compliance

Both tasks followed TDD RED/GREEN pattern:

**Task 1:**
- RED commit: `363e74f` — `test(01-02): add failing tests for XLSX renderer (RED)` (19 failing tests)
- GREEN commit: `ba250d0` — `feat(01-02): implement XLSX renderer ...` (19 passing tests)

**Task 2:**
- RED commit: `1d3d326` — `test(01-02): add failing tests for CLI entry point (RED)` (13 failing tests)
- GREEN commit: `2427c38` — `feat(01-02): implement Typer CLI entry point ...` (13 passing tests)

## Self-Check: PASSED

All created files exist:
- FOUND: src/contaplus_reader/xlsx.py
- FOUND: src/contaplus_reader/cli.py
- FOUND: tests/test_xlsx.py
- FOUND: tests/test_cli.py

All commits exist:
- FOUND: 363e74f (test: RED XLSX tests)
- FOUND: ba250d0 (feat: xlsx.py implementation)
- FOUND: 1d3d326 (test: RED CLI tests)
- FOUND: 2427c38 (feat: cli.py implementation)

Test suite: 50/50 passed (`uv run pytest tests/ -v`)
