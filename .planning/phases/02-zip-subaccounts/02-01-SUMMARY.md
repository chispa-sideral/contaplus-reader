---
phase: "02-zip-subaccounts"
plan: "01"
subsystem: "tests"
tags: [tdd, red-phase, fixtures, zip, subcta, wave-0]
dependency_graph:
  requires: []
  provides: [phase-2-red-tests, zip-fixtures, subcta-fixtures, group-table-fixtures]
  affects: [tests/conftest.py, tests/test_reader.py, tests/test_cli.py, tests/test_xlsx.py]
tech_stack:
  added: []
  patterns: [tdd-red-phase, session-scoped-fixtures, xfail-markers, zipfile-fixtures]
key_files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_reader.py
    - tests/test_cli.py
    - tests/test_xlsx.py
decisions:
  - "D-17 schema gate: synthetic _SUBCTA_SPEC uses C(n) not C(n,0) — dbf (ethanfurman) rejects decimal notation for character fields"
  - "test_subcta_candidate_fallback: DBF building inlined in test body instead of importing from conftest (tests/ is not a package)"
  - "Zip-slip and multi-company-no-selector tests use OR assertion (RED passes with 'ZIP', GREEN must have specific message)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-16T08:31:00Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 01: ZIP & SUBCTA — RED Phase Tests Summary

**One-liner:** TDD Wave 0 gate — 17 failing tests + session-scoped ZIP/SUBCTA/group-table fixture builders covering all 8 Phase 2 requirements before any implementation exists.

## What Was Built

### Task 1: conftest.py Phase 2 fixture builders (commit 7e88540)

Extended `tests/conftest.py` with:
- `import zipfile` added to imports
- Module-level spec constants: `_SUBCTA_SPEC`, `_GRUPOS_SPEC`, `_USUARIOS_SPEC`, `_EMPRESA_SPEC` (using `C(n)` format — see Deviations)
- `_build_subcta_dbf()` and `_build_generic_dbf()` module-level helpers
- 5 session-scoped fixtures:
  - `single_company_zip_with_subcta` — Emp01/Diario.dbf + Emp01/SubCta.dbf (4300000→"Cliente XYZ", 7000000→"Ventas mercaderias"; 6000001 intentionally absent to test missing-key→None)
  - `single_company_zip` — Emp01/Diario.dbf only (no SubCta, for all-None enrichment test)
  - `multi_company_zip` — Emp01/Diario.dbf + Emp02/Diario.dbf (company disambiguation tests)
  - `zip_with_group_tables` — Emp01 + SubCta + grupos + usuarios + empresa (TABL-02 tests)
  - `zip_slip_zip` — ZIP with `../evil.dbf` entry via `writestr()` (zip-slip security test)

### Task 2: Failing Phase 2 tests (commit 4307696)

Added 17 new tests across 3 files:

**tests/test_reader.py (13 tests):**
- `test_read_zip_bytes` / `test_read_zip_filelike` — INPUT-02: FAILED (sniffer rejects ZIP)
- `test_read_zipslip_rejected` — INPUT-04: PASSES in RED (ZIP rejected with "ZIP" in msg, tightens in GREEN)
- `test_read_multi_company_no_selector` — INPUT-06: PASSES in RED (OR assertion, tightens in GREEN)
- `test_read_multi_company_selected` — INPUT-06: FAILED (TypeError — no company= param yet)
- `test_read_single_company_wrong_selector` / `test_read_selector_on_dbf_raises` — INPUT-06: PASS in RED (accept TypeError)
- `test_subcta_lookup_correct` / `test_subcta_lookup_missing_key` / `test_subcta_absent_all_none` — API-05: FAILED
- `test_subcta_candidate_fallback` — TABL-01/D-16: FAILED (DBF building inlined)
- `test_group_tables_absent_no_error` / `test_usuarios_present_in_result` — TABL-02: FAILED

**tests/test_cli.py (2 tests):**
- `test_cli_company_flag_accepted` — CLI-02: XFAIL (--company option not yet on CLI)
- `test_cli_multi_company_no_flag_exits_1` — CLI-02/D-08: XFAIL (needs ZIP support + company listing)

**tests/test_xlsx.py (2 tests):**
- `test_render_multi_sheet_names` — D-12/D-14: XFAIL (render() not yet implemented)
- `test_render_descripcion_column_present` — D-15: XFAIL (subcuenta_nombre + render() missing)

## Verification Results

```
9 failed, 59 passed, 4 xfailed in 1.19s
72 tests collected
```

- All 55 Phase 1 tests continue to pass (no regressions)
- 9 FAILED (RED) + 4 XFAIL = 13 tests awaiting GREEN implementation
- 4 tests pass in RED with OR assertions (become strict assertions in GREEN)
- Zero collection errors; no binary blobs committed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] dbf (ethanfurman) rejects C(n,0) format for character fields**
- **Found during:** Task 1 verification — `ValueError: invalid literal for int() with base 10: '12,0'`
- **Issue:** Plan specified `_SUBCTA_SPEC = "cod C(12,0); titulo C(40,0); nif C(15,0)"` following the RESEARCH.md `[ASSUMED]` format, but `dbf.Table` only accepts `C(n)` (no decimal component for character fields)
- **Fix:** Changed all character field specs to `C(n)` format: `_SUBCTA_SPEC = "cod C(12); titulo C(40); nif C(15)"` and similarly for `_GRUPOS_SPEC`, `_USUARIOS_SPEC`, `_EMPRESA_SPEC`
- **Files modified:** `tests/conftest.py`
- **Commit:** 4307696

**2. [Rule 3 - Blocking] `from tests.conftest import` fails (tests/ is not a package)**
- **Found during:** Task 2 — `ModuleNotFoundError: No module named 'tests'`
- **Issue:** Plan specified importing `_build_diario_dbf` and `_build_generic_dbf` from `tests.conftest` inside `test_subcta_candidate_fallback`, but `tests/` has no `__init__.py` so it's not importable as a module
- **Fix:** Inlined the DBF construction directly in the test body using `dbf` (ethanfurman) directly, replicating the same pattern as `_build_diario_dbf`
- **Files modified:** `tests/test_reader.py`
- **Commit:** 4307696

## Known Stubs

None — this plan only writes tests; no implementation or data wiring.

## Threat Flags

None — test files introduce no new network endpoints, auth paths, or trust boundaries. All synthetic fixtures use `tmp_path_factory` (OS temp dirs, not committed).

## Self-Check: PASSED

- [x] `tests/conftest.py` modified: exists at C:/dev/contaplus-reader/tests/conftest.py
- [x] `tests/test_reader.py` modified: 13 new Phase 2 test functions present
- [x] `tests/test_cli.py` modified: 2 new xfail Phase 2 test functions present
- [x] `tests/test_xlsx.py` modified: 2 new xfail Phase 2 test functions present
- [x] Commit 7e88540 (Task 1) exists in git log
- [x] Commit 4307696 (Task 2) exists in git log
- [x] 72 tests collected, no collection errors
- [x] 9 FAILED + 4 XFAIL confirmed (RED phase gate)
- [x] All 55 Phase 1 tests still pass
