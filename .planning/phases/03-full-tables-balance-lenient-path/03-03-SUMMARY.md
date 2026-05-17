---
phase: "03"
plan: "03"
subsystem: library
tags: [integration, lenient-path, balance, 10-table-catalogue, tdd-green]
dependency_graph:
  requires:
    - "03-02: ProblemEntry, ProblemsReport, BalanceTable models; compute_balance; _reader.py lenient loop"
    - "Phase 2: ZIP pipeline, _find_sibling_dbf, _read_secondary_table, read_table_raw"
  provides:
    - "__init__.py: lenient parameter fully wired through ZIP and DBF paths"
    - "__init__.py: 10-table CATALOGUE constant + single-pass extraction"
    - "__init__.py: D-03 journal-level try/except (journal=None in lenient)"
    - "__init__.py: D-04 secondary table try/except via _read_secondary_table helper"
    - "__init__.py: D-13 uncatalogued .dbf scan in lenient mode"
    - "__init__.py: BAL-02 balance_cuenta and balance_subcuenta computed from journal"
  affects:
    - "Plan 03-04: xlsx renderer receives fully populated ContaPlusData"
tech_stack:
  added: []
  patterns:
    - "_read_secondary_table() helper: strict mode propagates, lenient catches D-04"
    - "D-03: try/except around _read_dbf_path, catch -> journal=None + ProblemEntry"
    - "Reuse existing `lookup` dict (built via build_subcta_lookup) for balance subcuenta descriptions"
    - "CATALOGUE frozenset for D-13 uncatalogued scan iteration"
key_files:
  created: []
  modified:
    - src/contaplus_reader/__init__.py
decisions:
  - "Reuse existing `lookup` dict (already built via build_subcta_lookup/lowernames=True) for balance_subcuenta descriptions — avoids duplicating field-resolution logic from SubctaRow.fields which uses lowernames=False keys"
  - "_read_secondary_table() extracted as module-level helper to avoid per-table try/except repetition across 8 optional tables"
  - "CATALOGUE frozenset defined at module level (not inside read()) so it is computed once and visible to tests if needed"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-17"
  tasks_completed: 1
  files_modified: 1
---

# Phase 03 Plan 03: 10-Table Catalogue, Lenient Wiring, and Balance Computation Summary

Completed the integration layer for Phase 3: wired the full 10-table catalogue extraction, the D-03/D-04/D-13 lenient error-collection paths, and the BAL-02 trial balance computation into the single public `read()` entry point. All 3 remaining RED tests from the lenient test file are now GREEN.

## What Was Built

### Task 1: Extend read() with 10-table catalogue, lenient path, balance computation

**Commit:** `9843c81`

Extended `src/contaplus_reader/__init__.py`:

**Imports added:**
- `from contaplus_reader._balance import compute_balance`
- `BalanceTable`, `GenericTable` added to models import

**Module-level constant:**
- `_CATALOGUE: frozenset[str]` — 10 lowercase DBF names for D-12 and D-13 uncatalogued scan

**`_read_secondary_table()` helper:**
- `path: Path | None, table_name: str, *, lenient: bool, problems: list[ProblemEntry]`
- Strict mode: delegates to `read_table_raw()`, any error propagates (D-06 unchanged)
- Lenient mode: wraps `read_table_raw()` in try/except; on error appends `ProblemEntry(table=table_name.lower(), row_index=-1, ...)` and returns `None` (D-04)

**D-03 journal try/except in ZIP path:**
- `lenient=True`: wraps `_read_dbf_path()` call; on `ContaPlusReadError` appends `ProblemEntry(table="DIARIO", row_index=-1)` and sets `journal=None`; continues to extract all secondary tables
- `lenient=False`: `_read_dbf_path()` called without try/except (strict, unchanged)

**Phase 3 table extraction in ZIP path:**
- `balan_path`, `venci_path`, `prede_path`, `amoinv_path`, `nivel_path` resolved via `_find_sibling_dbf()`
- Each read via `_read_secondary_table()` with lenient/problems threading

**D-13 uncatalogued DBF scan:**
- After all catalogue reads, when `lenient=True`: iterates `diario_path.parent.iterdir()`
- Any `.dbf` file whose lowercased name is not in `_CATALOGUE` produces `ProblemEntry(table=candidate.name.upper(), reason="unrecognized table — not extracted")`

**BAL-02 balance computation:**
- When `journal is not None`: calls `compute_balance(journal, by_subcuenta=False)` for `balance_cuenta`
- Calls `compute_balance(journal, by_subcuenta=True, subcta_lookup=lookup)` for `balance_subcuenta`
- Reuses the `lookup` dict already built by `build_subcta_lookup()` (avoids re-reading SUBCTA)
- Raw-DBF path also computes balance when journal is not None (without subcta_lookup)

**ContaPlusData return extended:**
- All 8 new Phase 3 attributes populated: `balan`, `venci`, `prede`, `amoinv`, `nivel`, `balance_cuenta`, `balance_subcuenta`, `problems`

## Test Results

Before this plan:
- `test_lenient_corrupt_table` — RED (D-04: venci=None but problems=None)
- `test_lenient_corrupt_journal` — RED (D-03: ContaPlusReadError propagated instead of being caught)
- `test_lenient_uncatalogued_dbf` — RED (D-13: no scan, problems=None)
- 17 tests already GREEN (test_tables.py TABL-03/BAL-01 + 5 lenient tests from Plan 02)

After this plan:
- All 20 `test_lenient.py` + `test_tables.py` tests GREEN
- 85 tests across test_reader.py, test_balance.py, test_cli.py, test_tables.py, test_lenient.py GREEN
- 10 test_xlsx.py failures remain — these are Plan 04 scope (Vencimientos/Balance/Problemas sheets)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] KeyError('cod') in subcta_lookup_for_balance**
- **Found during:** Full test suite regression run (test_cli.py::test_cli_company_flag_accepted)
- **Issue:** Initial implementation of balance_subcuenta lookup built a dict from `SubctaRow.fields["cod"]` — but `read_subcta_table` uses `lowernames=False`, so field key case depends on the DBF header (could be `"cod"` or `"COD"` or `"Cod"`). The `SubctaRow.fields` dict uses the verbatim DBF field name.
- **Fix:** Replaced the manual `SubctaRow.fields` dict construction with the existing `lookup` dict already built by `build_subcta_lookup()` which uses `lowernames=True` and `_pick_column()` for robust field resolution.
- **Files modified:** `src/contaplus_reader/__init__.py`
- **Commit:** included in `9843c81`

## Known Stubs

None. All ContaPlusData attributes populated or explicitly None when source DBF absent.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's threat model covers.

- T-03-07: `_read_secondary_table()` routes through `read_table_raw()` which wraps errors in `ContaPlusReadError`
- T-03-08: D-03 outer try/except catches `ContaPlusReadError` from `_read_dbf_path()`; verified by `test_lenient_corrupt_journal`
- T-03-11: Uncatalogued scan iterates `diario_path.parent.iterdir()` — already within the safe extraction directory from `_safe_extract_zip()`

## Self-Check: PASSED

Files exist:
- `src/contaplus_reader/__init__.py` — FOUND (modified)
- `src/contaplus_reader/_balance.py` — FOUND (dependency, unchanged)

Commits exist:
- `9843c81` — feat(03-03): wire full 10-table catalogue, lenient path, and balance into read()

Test results:
- `tests/test_tables.py`: 12/12 GREEN
- `tests/test_lenient.py`: 8/8 GREEN
- `tests/test_reader.py`: 40/40 GREEN
- `tests/test_balance.py`: 8/8 GREEN
- `tests/test_cli.py`: 17/17 GREEN (no regressions including test_cli_company_flag_accepted)
- `tests/test_xlsx.py`: 10 RED — Plan 04 scope only
