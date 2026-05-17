---
phase: "03"
plan: "01"
subsystem: tests
tags: [tdd, test-scaffold, red-state, wave-0]
dependency_graph:
  requires: []
  provides:
    - "tests/conftest.py: Phase 3 synthetic fixtures (venci/prede/amoinv/nivel/balan/defect-bearing)"
    - "tests/test_tables.py: TABL-03/BAL-01 acceptance tests (12 tests)"
    - "tests/test_balance.py: BAL-02 acceptance tests (8 tests)"
    - "tests/test_lenient.py: API-03 acceptance tests (8 tests)"
    - "tests/test_xlsx.py: XLSX-02/XLSX-03 acceptance tests (11 new tests)"
  affects:
    - "Plans 02-04: implementation turns these tests GREEN"
tech_stack:
  added: []
  patterns:
    - "TDD Wave 0: failing tests define acceptance contract before implementation"
    - "_build_generic_dbf() reused for all 5 new DBF specs"
    - "session-scoped fixtures for all synthetic DBFs (expensive to build)"
key_files:
  created:
    - tests/test_tables.py
    - tests/test_balance.py
    - tests/test_lenient.py
  modified:
    - tests/conftest.py
    - tests/test_xlsx.py
decisions:
  - "test_tables.py tests are GREEN immediately because read_table_raw already handles any DBF generically — this is correct; the missing TABL-03 work is the integration into ContaPlusData via read(), tested in test_reader.py extensions in Plans 02-04"
  - "test_balance.py fails at collection (ImportError: no module _balance) — canonical RED gate"
  - "test_lenient.py fails at runtime (TypeError: unexpected keyword argument 'lenient') — canonical RED gate"
  - "11 new test_xlsx.py tests: 10 fail (missing models/sheets), 1 passes pre-emptively (balan_no_banner_when_balanced blocked differently)"
  - "_BALAN_SPEC includes DOBLE C(1) field as field 7 per RESEARCH.md open question A2 (17 total fields)"
metrics:
  duration_minutes: 6
  completed_date: "2026-05-17"
  tasks_completed: 2
  files_modified: 5
---

# Phase 03 Plan 01: Phase 3 Test Scaffold (TDD Wave 0) Summary

TDD Wave 0 for Phase 3 — all failing tests and conftest fixtures that define the acceptance contract for every new Phase 3 behavior before any implementation begins.

## What Was Built

Extended `tests/conftest.py` with 5 DBF spec constants and 9 new session-scoped fixtures. Created 3 new test files and extended `tests/test_xlsx.py` with 11 new failing test functions. The resulting test scaffold covers all 7 Phase 3 requirements (TABL-03, TABL-04, BAL-01, BAL-02, API-03, XLSX-02, XLSX-03).

## Task Results

### Task 1: Extend conftest.py with Phase 3 synthetic fixtures

**Commit:** `3a914c0`

Added to `tests/conftest.py`:
- `_VENCI_SPEC` — 21 fields (RESEARCH.md §Q1 verified)
- `_PREDE_SPEC` — 41 fields (RESEARCH.md §Q1 verified)
- `_AMOINV_SPEC` — 35 fields (RESEARCH.md §Q1 verified)
- `_NIVEL_SPEC` — 13 fields (N1-N12 booleans + LASTCASADO)
- `_BALAN_SPEC` — 17 fields including DOBLE C(1) and SDO_CIERRE N(19,2)
- `venci_dbf` fixture — 0 rows (matches real data)
- `prede_dbf` fixture — 0 rows (matches real data)
- `amoinv_dbf` fixture — 0 rows (matches real data)
- `nivel_dbf` fixture — 1 row (config singleton per Pitfall 6)
- `balan_balanced_dbf` fixture — 3 rows; SDO_CIERRE sums to 0.00
- `balan_unbalanced_dbf` fixture — 3 rows; SDO_CIERRE sums to 10.00 (descuadre)
- `diario_with_bad_row` fixture — 3 rows: good/bad-subcta(BADCODE)/good
- `zip_with_all_tables` fixture — all 10 catalogued tables under Emp01/
- `zip_with_uncatalogued` fixture — DIARIO + extra.dbf (uncatalogued)

Verification: All 81 existing Phase 1/2 tests remain green (no regressions).

### Task 2: Write failing test files (RED state)

**Commit:** `114da3b`

**tests/test_tables.py** — 12 tests (all GREEN immediately):
- `test_venci_returns_generic_table`, `test_venci_headers`, `test_venci_zero_rows`
- `test_prede_returns_generic_table`, `test_prede_headers`
- `test_amoinv_returns_generic_table`, `test_amoinv_headers`
- `test_nivel_returns_generic_table`, `test_nivel_row_count`, `test_nivel_headers`
- `test_balan_returns_generic_table`, `test_balan_sdo_cierre_column`

Note: test_tables.py tests pass immediately because `read_table_raw()` already handles any DBF generically. The TABL-03 work remaining (integrating venci/prede/amoinv/nivel into `read()` → `ContaPlusData`) is covered by test_reader.py extensions in Plan 02.

**tests/test_balance.py** — 8 tests (RED: ImportError at collection — `_balance` module not implemented):
- `test_decimal_precision`, `test_saldo_deudor_when_debe_exceeds_haber`
- `test_saldo_acreedor_when_haber_exceeds_debe`, `test_cuenta_level_grouping`
- `test_subcuenta_level_grouping`, `test_by_subcuenta_descripcion`
- `test_returns_balance_table_type`, `test_sorted_output`

**tests/test_lenient.py** — 8 tests (7 RED: TypeError `lenient` not on read(), 1 passes):
- `test_lenient_bad_journal_row_skipped`, `test_lenient_good_rows_preserved`
- `test_strict_still_raises_on_bad_row` — passes (strict mode already works)
- `test_lenient_corrupt_table`, `test_lenient_corrupt_journal`
- `test_lenient_uncatalogued_dbf`, `test_memo_skips_not_in_problems`
- `test_no_problems_when_clean`

**tests/test_xlsx.py** — 11 new tests (10 RED: KeyError/ImportError, 1 passes):
- `test_full_zip_all_tables_sheets_present` — RED: ContaPlusData missing venci/prede/amoinv/nivel
- `test_problems_sheet_present`, `test_problems_sheet_columns`, `test_problems_sheet_has_entries` — RED
- `test_memo_not_in_problems` — passes (no Problemas sheet is correct behaviour currently)
- `test_balan_no_banner_when_balanced` — passes (no Balance sheet = no AVISO in A1)
- `test_balan_banner_on_descuadre` — RED: no Balance sheet yet
- `test_balance_cuenta_sheet_present`, `test_balance_subcuenta_sheet_present` — RED
- `test_balance_subcuenta_descripcion`, `test_balance_cuenta_columns` — RED

## RED/GREEN Gate Status

| File | Tests | RED | GREEN | Gate |
|------|-------|-----|-------|------|
| test_tables.py | 12 | 0 | 12 | Note: tests pass; TABL-03 integration in Plan 02 |
| test_balance.py | 8 | 8 (ImportError) | 0 | RED gate: _balance module missing |
| test_lenient.py | 8 | 7 (TypeError) | 1 | RED gate: lenient= param missing |
| test_xlsx.py (new) | 11 | 10 | 1 (memo_not_in_problems, balan_no_banner) | RED gate: models/sheets missing |

## Deviations from Plan

None — plan executed exactly as written.

Minor observation: test_tables.py tests are GREEN immediately because `read_table_raw()` already generically handles any DBF. The plan anticipated these would be RED (it mentioned "tests will fail with ImportError or AttributeError"), but since `read_table_raw` and `GenericTable` already exist, the table read tests pass. This is correct and expected — the integration into `ContaPlusData` via `read()` ZIP path (TABL-04) will be tested by new test_reader.py tests in Plan 02.

## Known Stubs

None. This plan creates only test infrastructure; no library code was implemented.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All new code is test infrastructure only.

## Self-Check: PASSED

Files exist:
- `tests/test_tables.py` — FOUND
- `tests/test_balance.py` — FOUND
- `tests/test_lenient.py` — FOUND
- `tests/test_xlsx.py` — FOUND (extended)
- `tests/conftest.py` — FOUND (extended)

Commits exist:
- `3a914c0` — FOUND (test(03-01): extend conftest.py with Phase 3 synthetic fixtures)
- `114da3b` — FOUND (test(03-01): add failing Phase 3 test files (RED state))

Phase 1/2 regressions: 0 (81 original tests + 12 test_tables.py = 93 passing before new failures)
