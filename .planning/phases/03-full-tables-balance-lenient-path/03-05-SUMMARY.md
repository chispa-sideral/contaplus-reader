---
phase: 03-full-tables-balance-lenient-path
plan: 05
subsystem: library
tags: [python, xlsx, openpyxl, lenient, dbfread, cli]

# Dependency graph
requires:
  - phase: 03-full-tables-balance-lenient-path
    provides: "Phase 3 plans 01-04: lenient reader, render(), ProblemsReport, secondary tables"
provides:
  - "render() None guard for journal=None: headers-only Diario sheet when journal is None (WR-06)"
  - "Per-row ValueError catch in lenient mode: dbfread ValueError skips row instead of aborting file (WR-05)"
  - "Canonical ProblemEntry.table convention: uppercase stem without extension at all call sites"
  - "CLI sheet_count derived from rendered workbook via load_workbook (always accurate)"
  - "D-03 end-to-end contract restored: lenient read(corrupt_zip) + render() produces valid workbook"
affects: [phase-04, pwa]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WR-06 None guard: guard journal render before calling _render_journal_sheet"
    - "WR-05 inner except broadened: (ContaPlusReadError, ValueError) with isinstance discrimination"
    - "ProblemEntry.table canonical form: Path(name).stem.upper() at all call sites"
    - "CLI sheet count from workbook: load_workbook(BytesIO(xlsx_bytes)).sheetnames"

key-files:
  created: []
  modified:
    - "src/contaplus_reader/xlsx.py"
    - "src/contaplus_reader/_reader.py"
    - "src/contaplus_reader/__init__.py"
    - "src/contaplus_reader/cli.py"
    - "tests/test_xlsx.py"
    - "tests/test_lenient.py"

key-decisions:
  - "_write_diario_headers_only() extracted as private helper (not inline in render()) to avoid duplicating D-10 styling logic"
  - "WR-05 ValueError in strict mode re-raises to outer file-level handler (unchanged strict behaviour); only lenient mode swallows per-row ValueError"
  - "CLI imports io and load_workbook inside main() body (consistent with existing pattern of importing read/render inside main())"

patterns-established:
  - "ProblemEntry.table must always be Path(name).stem.upper() — canonical uppercase stem, no extension"
  - "render() guards every nullable ContaPlusData attribute with 'if data.X is not None' before calling sheet renderers"

requirements-completed: [API-03]

# Metrics
duration: 25min
completed: 2026-05-17
---

# Phase 3 Plan 05: Gap-Closure (WR-06/WR-05/casing/sheet-count) Summary

**Four verified gaps closed: render() no longer crashes on journal=None, per-row dbfread ValueError is caught in lenient mode, ProblemEntry.table uses canonical uppercase stems, and CLI sheet count matches actual rendered output**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-17T22:00:00Z
- **Completed:** 2026-05-17T22:25:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- WR-06 (BLOCKER) fixed: `render()` guards `data.journal` with `if data.journal is not None`; new `_write_diario_headers_only()` helper writes headers-only Diario sheet for corrupt-journal case; D-03 end-to-end contract fully restored
- WR-05 fixed: inner `except (ContaPlusReadError, ValueError)` catches dbfread ValueErrors at the per-row level; lenient mode appends ProblemEntry and continues; strict mode re-raises to outer file-level handler
- ProblemEntry.table canonicalized: `_read_secondary_table` uses `Path(table_name).stem.upper()` and D-13 uncatalogued block uses `candidate.stem.upper()` — consistent with `"DIARIO"` literal already used elsewhere
- CLI sheet count accurate: `len(load_workbook(BytesIO(xlsx_bytes)).sheetnames)` replaces the manual 5-table sum that was wrong for Phase 3 workbooks

## Task Commits

Each task was committed atomically with TDD RED/GREEN commits:

1. **Task 1 RED: test_render_journal_none_produces_valid_workbook + test_render_lenient_end_to_end** - `0e36ea6` (test)
2. **Task 1 GREEN: xlsx.py None guard + _write_diario_headers_only** - `38cc316` (feat)
3. **Task 2 RED: test_lenient_dbfread_valueerror_skipped + test_lenient_dbfread_valueerror_strict_raises** - `9a2c2fb` (test)
4. **Task 2 GREEN: _reader.py ValueError catch, __init__.py casing, cli.py sheet count, test_lenient.py assertion updates** - `2d1a8f6` (feat)

## Files Created/Modified

- `src/contaplus_reader/xlsx.py` - Added `_write_diario_headers_only()`, added None guard in `render()`, removed `type: ignore[arg-type]` suppression
- `src/contaplus_reader/_reader.py` - Inner except broadened to `(ContaPlusReadError, ValueError)` with isinstance discrimination
- `src/contaplus_reader/__init__.py` - `_read_secondary_table` ProblemEntry.table uses `Path(table_name).stem.upper()`; D-13 block uses `candidate.stem.upper()`
- `src/contaplus_reader/cli.py` - sheet_count derived from `load_workbook(BytesIO(xlsx_bytes)).sheetnames`
- `tests/test_xlsx.py` - Added `test_render_journal_none_produces_valid_workbook` and `test_render_lenient_end_to_end`
- `tests/test_lenient.py` - Added `test_lenient_dbfread_valueerror_skipped` and `test_lenient_dbfread_valueerror_strict_raises`; updated table-casing assertions

## Decisions Made

- `_write_diario_headers_only()` extracted as a private helper (not inlined into `render()`) to keep the D-10 styling logic in one place — matches the style of all other `_render_*` helpers
- WR-05: in strict mode, a ValueError from `_build_journal_row` re-raises unchanged; the outer `except (struct.error, ValueError, OSError)` handler wraps it as a file-level `ContaPlusReadError(row_index=-1)` — existing strict behaviour is preserved exactly
- CLI: `io` and `load_workbook` imported inside `main()` body (not at module level) to keep startup fast and consistent with existing import-inside-function pattern for `read` and `render`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all four fixes were straightforward and the test suite remained green throughout.

## Known Stubs

None — all data flows are wired. The new `_write_diario_headers_only()` writes the fixed HEADERS tuple (not user-controlled data) and produces a valid headers-only sheet.

## Threat Flags

None — threat mitigations T-03-17 (ValueError catch scoped to inner per-row block only) and T-03-18 (None guard prevents iteration over None) are implemented as specified in the plan's threat register.

## Next Phase Readiness

- Phase 3 is now fully verified (4/4 must-haves + 5/5 observable truths): API-03, XLSX-02, XLSX-03, TABL-03, TABL-04, BAL-01, BAL-02 all satisfied
- Full test suite: 124 tests green (120 pre-existing + 4 new from this plan)
- Ready for Phase 4 (PWA / packaging) — no blocking issues remain in the reader or renderer

## Self-Check: PASSED

- `src/contaplus_reader/xlsx.py` — exists, contains `if data.journal is not None` and `def _write_diario_headers_only`
- `src/contaplus_reader/_reader.py` — exists, contains `except (ContaPlusReadError, ValueError)`
- `src/contaplus_reader/__init__.py` — exists, contains `stem.upper()` at both call sites
- `src/contaplus_reader/cli.py` — exists, contains `load_workbook`
- Commits `0e36ea6`, `38cc316`, `9a2c2fb`, `2d1a8f6` — all verified in git log
- 124 tests green: `uv run pytest tests/ 2>&1 | tail -1` → `124 passed in 1.73s`

---
*Phase: 03-full-tables-balance-lenient-path*
*Completed: 2026-05-17*
