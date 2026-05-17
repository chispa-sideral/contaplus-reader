---
phase: "03"
plan: "02"
subsystem: library
tags: [models, balance, lenient-path, decimal, tdd-green]
dependency_graph:
  requires:
    - "03-01: test scaffold (test_balance.py, test_lenient.py)"
    - "Phase 1/2: ContaPlusData, ContaPlusJournal, JournalRow, _reader.py D-C5 loop"
  provides:
    - "models.py: ProblemEntry, ProblemsReport, BalanceRow, BalanceTable types"
    - "models.py: ContaPlusData gains 8 new Phase 3 attributes"
    - "_balance.py: compute_balance() Decimal trial balance computation"
    - "_reader.py: _build_journal_row() helper, lenient/problems parameters"
    - "__init__.py: read() gains lenient=False keyword parameter"
  affects:
    - "Plans 03-04: build on BalanceTable/ProblemEntry types and lenient read() path"
tech_stack:
  added:
    - "decimal.Decimal: used in BalanceRow fields and _balance.py accumulation (BAL-02)"
  patterns:
    - "Decimal(str(float)) accumulation — BAL-02 mandated pattern"
    - "enrichment_misses_ref single-element list as mutable reference in helper function"
    - "ProblemEntry frozen dataclass carries table/row_index/column/reason/value"
    - "lenient mode: per-row ContaPlusReadError -> ProblemEntry + skip; file-level always propagates"
key_files:
  created:
    - src/contaplus_reader/_balance.py
  modified:
    - src/contaplus_reader/models.py
    - src/contaplus_reader/_reader.py
    - src/contaplus_reader/__init__.py
decisions:
  - "Decimal(str(float)) over Decimal(float_value): mandatory per BAL-02/Pitfall 2 — avoids binary float representation errors"
  - "enrichment_misses_ref=[0] passed to _build_journal_row instead of nonlocal: keeps helper self-contained and testable"
  - "lenient param is keyword-only in read() (using * separator) to prevent positional misuse"
  - "D-03 handling (journal=None for file-level DIARIO error in lenient mode) deferred to Plans 03-04 as it requires _read_dbf_path caller-level error recovery not in scope for plan 02"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-17"
  tasks_completed: 3
  files_modified: 4
---

# Phase 03 Plan 02: Core Models, Balance Computation, and Lenient Journal Loop Summary

Implemented the data-contract and core-logic layer for Phase 3: new model types (ProblemEntry, ProblemsReport, BalanceRow, BalanceTable), Decimal-based trial balance computation in `_balance.py`, and the lenient journal loop in `_reader.py` with extracted `_build_journal_row` helper.

## What Was Built

### Task 1: Extend models.py — Phase 3 types and ContaPlusData attributes

**Commit:** `df99913`

Added to `src/contaplus_reader/models.py`:
- `from decimal import Decimal` import
- `ProblemEntry` frozen dataclass (table, row_index, column, reason, value)
- `ProblemsReport` frozen dataclass (entries: tuple[ProblemEntry, ...])
- `BalanceRow` frozen dataclass (code, suma_debe, suma_haber, saldo_deudor, saldo_acreedor, saldo, descripcion=None — all Decimal fields)
- `BalanceTable` frozen dataclass (rows: tuple[BalanceRow, ...], level: str)
- `ContaPlusData` extended with 8 new None-defaulted attributes: balan, venci, prede, amoinv, nivel (GenericTable | None), balance_cuenta, balance_subcuenta (BalanceTable | None), problems (ProblemsReport | None)

### Task 2: Create _balance.py — compute_balance with Decimal accumulation

**Commit:** `3f73a7c`

Created `src/contaplus_reader/_balance.py`:
- `compute_balance(journal, *, by_subcuenta=False, subcta_lookup=None) -> BalanceTable`
- Uses `defaultdict(lambda: Decimal("0"))` for debe/haber accumulators
- `Decimal(str(row.debe))` and `Decimal(str(row.haber))` per BAL-02 mandated pattern
- `saldo_deudor = max(sd - sh, ZERO)`, `saldo_acreedor = max(sh - sd, ZERO)`, `saldo = sd - sh` per D-08
- Rows sorted ascending by key (alphabetic string sort)
- `level="cuenta"` when `by_subcuenta=False`, `level="subcuenta"` when True
- `descripcion` populated from `subcta_lookup.get(key)` at subcuenta level when lookup provided

All 8 `test_balance.py` tests pass (GREEN gate confirmed).

### Task 3: Extend _reader.py — _build_journal_row helper + lenient/problems parameters

**Commit:** `dec8433`

Extended `src/contaplus_reader/_reader.py`:
- Added `ProblemEntry` to model imports
- Extracted `_build_journal_row(record, idx, debe_col, haber_col, subcta_lookup, enrichment_misses_ref)` private helper: contains the complete D-C4/D-C2/D-C3/D-E3/D-B2/D-09 validation logic; raises `ContaPlusReadError` on validation failures; returns `None` for both-zero memo rows; returns `JournalRow` on success
- Added `_raw_value(record, column)` helper for capturing raw field values in ProblemEntry
- Extended `_read_dbf_path()` signature: `lenient: bool = False, problems: list[ProblemEntry] | None = None`
- Lenient loop: per-row `ContaPlusReadError` (row_index >= 0) appends `ProblemEntry` to problems and continues; file-level errors (row_index == -1) always re-raise regardless of lenient flag (D-02/Pitfall 3)
- Memo skips (row=None from helper) increment `skipped_memo` only — no ProblemEntry (D-05)

Extended `src/contaplus_reader/__init__.py`:
- `read()` gains `lenient: bool = False` as keyword-only parameter
- Plumbed through to `_read_dbf_path()` for both DBF and ZIP paths
- `ProblemsReport` built from collected entries at the end of conversion; `None` if no problems

`test_lenient_bad_journal_row_skipped` and `test_strict_still_raises_on_bad_row` GREEN. All 40 `test_reader.py` tests still GREEN.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Scope Notes

`test_lenient_corrupt_journal` (D-03: file-level DIARIO error → `journal=None` in lenient mode) remains RED. The plan's must_haves explicitly state that file-level errors in `_read_dbf_path` always propagate. D-03 handling requires caller-level error recovery in `read()` (catch `ContaPlusReadError(row_index=-1)` from journal read, set `journal=None`, continue). This is out of scope for plan 02 and will be addressed in Plans 03-04. The test was RED before (TypeError) and remains RED (ContaPlusReadError propagates) — no regression, just a different failure mode.

`test_lenient_corrupt_table` and `test_lenient_uncatalogued_dbf` require secondary table error collection and uncatalogued DBF detection — Plans 03-04 work. Both remain RED.

`test_xlsx.py` Phase 3 tests (Vencimientos/Balance/Problemas sheets) remain RED — Plans 03-04 work.

## Known Stubs

None. All implemented behavior is complete and wired. `ContaPlusData` attributes added in this plan (balan/venci/prede/amoinv/nivel) are structural additions — they default to `None` and will be populated by Plans 03-04 ZIP reader extensions.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what the plan's threat model covers.

- T-03-03: `_build_journal_row` preserves all existing D-E3/D-C4/D-C2 validation — extraction did not relax any constraint
- T-03-04: Explicit `if exc.row_index == -1: raise` in lenient catch correctly propagates file-level errors

## Self-Check: PASSED

Files exist:
- `src/contaplus_reader/models.py` — FOUND (modified)
- `src/contaplus_reader/_balance.py` — FOUND (created)
- `src/contaplus_reader/_reader.py` — FOUND (modified)
- `src/contaplus_reader/__init__.py` — FOUND (modified)

Commits exist:
- `df99913` — feat(03-02): extend models.py with Phase 3 types and ContaPlusData attributes
- `3f73a7c` — feat(03-02): create _balance.py with compute_balance Decimal accumulation
- `dec8433` — feat(03-02): extend _reader.py and read() with lenient journal loop

Test results:
- `test_balance.py`: 8/8 GREEN
- `test_lenient.py::test_lenient_bad_journal_row_skipped`: GREEN
- `test_lenient.py::test_strict_still_raises_on_bad_row`: GREEN
- `test_reader.py`: 40/40 GREEN
- Phase 1/2 regressions: 0
