---
phase: 03-full-tables-balance-lenient-path
verified: 2026-05-18T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "A lenient conversion of a corrupt-DIARIO ZIP produces a workbook with other tables + problems sheet (D-03 end-to-end)"
    - "WR-05: per-row dbfread ValueError escapes inner handler to file-level abort"
    - "ProblemEntry.table casing inconsistent across call sites"
    - "CLI sheet_count undercount (only counted Phase 1/2 tables)"
  gaps_remaining: []
  regressions: []
---

# Phase 3: Full Tables, Balance & Lenient Path Verification Report

**Phase Goal:** A user running lenient conversion gets every readable table extracted — including operational tables and a recomputed trial balance — plus a problems sheet listing anything that was skipped
**Verified:** 2026-05-18
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 03-05)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A backup ZIP converted with `--lenient` produces sheets for venci, prede, amoinv, and nivel | VERIFIED | `_render_generic_sheet` called for all four in `render()` lines 108-115; `test_full_zip_all_tables_sheets_present` passes |
| 2 | The workbook contains a Problemas sheet listing every row the lenient path flagged, with row and column context | VERIFIED | `_render_problems_sheet` writes five columns (Tabla/Fila/Columna/Motivo/Valor); conditional on non-empty entries; `test_problems_sheet_present`, `test_problems_sheet_columns`, `test_problems_sheet_has_entries` all pass |
| 3 | The BALAN sheet carries the descuadre disclaimer only when its own figures fail to balance; two recomputed trial-balance sheets are always present | VERIFIED | `_render_balan_sheet` sums SDO_CIERRE with Decimal and injects banner only on non-zero sum; `balance_cuenta`/`balance_subcuenta` computed from journal when not None; `test_balan_banner_on_descuadre` and `test_balan_no_banner_when_balanced` pass |
| 4 | Field schemas for venci, prede, amoinv, and nivel are validated against pii-test-data/ before readers are committed | VERIFIED | 03-RESEARCH.md documents schema enumeration across all 5 real archives; test fixtures use exact field schemas from that enumeration; pii-test-data/ not committed |
| 5 | A lenient conversion of a corrupt-DIARIO ZIP produces a workbook containing all other readable tables plus a problems sheet (D-03 end-to-end) | VERIFIED | `xlsx.py:89` guards `if data.journal is not None`; `_write_diario_headers_only` writes headers-only Diario sheet when journal is None; `test_render_journal_none_produces_valid_workbook` and `test_render_lenient_end_to_end` both pass; `type: ignore[arg-type]` suppression removed |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/contaplus_reader/models.py` | ProblemEntry, ProblemsReport, BalanceRow, BalanceTable, ContaPlusData Phase 3 attributes | VERIFIED | All types present; ContaPlusData has balan/venci/prede/amoinv/nivel/balance_cuenta/balance_subcuenta/problems |
| `src/contaplus_reader/_balance.py` | compute_balance() with Decimal accumulation | VERIFIED | Decimal(str(row.debe)) pattern; defaultdict accumulators; sorted output |
| `src/contaplus_reader/_reader.py` | _build_journal_row helper + lenient/problems params + ValueError catch | VERIFIED | Inner `except (ContaPlusReadError, ValueError)` at line 296; isinstance discrimination; lenient skips, strict re-raises |
| `src/contaplus_reader/__init__.py` | lenient param, 10-table catalogue, D-03/D-04/D-13 wiring, canonical ProblemEntry.table | VERIFIED | `_CATALOGUE` frozenset; `_read_secondary_table` uses `Path(table_name).stem.upper()` (line 92); D-13 block uses `candidate.stem.upper()` (line 249) |
| `src/contaplus_reader/xlsx.py` | render() None guard for journal, _write_diario_headers_only, all Phase 3 renderers | VERIFIED | `if data.journal is not None` at line 89; `_write_diario_headers_only` at line 183; all six renderers present; no `type: ignore[arg-type]` |
| `src/contaplus_reader/cli.py` | --lenient flag; sheet_count from rendered workbook | VERIFIED | `lenient` Typer option wired to `read(lenient=lenient)`; `len(_load_wb(BytesIO(xlsx_bytes), read_only=True, data_only=True).sheetnames)` at line 129 |
| `tests/test_xlsx.py` | test_render_journal_none_produces_valid_workbook + test_render_lenient_end_to_end | VERIFIED | Both tests present and pass |
| `tests/test_lenient.py` | test_lenient_dbfread_valueerror_skipped + updated casing assertions | VERIFIED | `test_lenient_dbfread_valueerror_skipped` and `test_lenient_dbfread_valueerror_strict_raises` present; table casing assertions use canonical `== "VENCI"` / `== "EXTRA"` (no .lower()/.upper() workarounds) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `read()` | `_read_dbf_path()` | `lenient=True, problems=collected_problems` | VERIFIED | Both ZIP and raw-DBF paths pass lenient/problems through |
| `read()` | `compute_balance()` | Called after journal read when journal is not None | VERIFIED | Both cuenta and subcuenta levels computed |
| `render()` | `_render_journal_sheet()` | `if data.journal is not None` guard at line 89 | VERIFIED | None guard present; no crash on journal=None |
| `render()` | `_write_diario_headers_only()` | `else` branch when journal is None | VERIFIED | Writes "Diario" title + HEADERS + freeze_panes; max_row=1 confirmed by test |
| `render()` | `_render_problems_sheet()` | Conditional on non-empty problems.entries | VERIFIED | D-05 honored |
| `_read_dbf_path()` | inner `except (ContaPlusReadError, ValueError)` | per-row ValueError catch | VERIFIED | Line 296; lenient appends ProblemEntry and continues; strict re-raises to outer handler |
| `_read_secondary_table()` | `ProblemEntry.table` | `Path(table_name).stem.upper()` | VERIFIED | Line 92; consistent uppercase stem at this call site |
| D-13 uncatalogued block | `ProblemEntry.table` | `candidate.stem.upper()` | VERIFIED | Line 249; "EXTRA" not "EXTRA.DBF" |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `_render_balance_sheet` | `table.rows` | `compute_balance(journal)` | Yes — Decimal accumulation over real journal rows | FLOWING |
| `_render_balan_sheet` | `balan.rows` | `read_table_raw(balan_path)` | Yes — full DBF dump | FLOWING |
| `_render_problems_sheet` | `report.entries` | `collected_problems` list in `read()` | Yes — real error events from lenient path | FLOWING |
| `render()` Diario sheet — journal=None path | HEADERS tuple | `_write_diario_headers_only` | Static HEADERS tuple (correct: headers-only by design) | FLOWING (by design) |
| `render()` Diario sheet — journal present | `data.journal.rows` | `_read_dbf_path()` | Yes — validated journal rows | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 124-test suite | `uv run pytest tests/ 2>&1 \| tail -1` | `124 passed in 1.69s` | PASS |
| render(ContaPlusData(journal=None)) | `uv run pytest tests/test_xlsx.py::test_render_journal_none_produces_valid_workbook -v` | `1 passed` | PASS |
| D-03 end-to-end: lenient read + render of corrupt-DIARIO ZIP | `uv run pytest tests/test_xlsx.py::test_render_lenient_end_to_end -v` | `1 passed` | PASS |
| WR-05: dbfread ValueError skipped per-row in lenient mode | `uv run pytest tests/test_lenient.py::test_lenient_dbfread_valueerror_skipped -v` | `1 passed` | PASS |
| WR-05: strict mode propagates ValueError | `uv run pytest tests/test_lenient.py::test_lenient_dbfread_valueerror_strict_raises -v` | `1 passed` | PASS |
| ProblemEntry.table casing (VENCI canonical) | `uv run pytest tests/test_lenient.py::test_lenient_corrupt_table -v` | `1 passed` | PASS |
| ProblemEntry.table casing (EXTRA canonical) | `uv run pytest tests/test_lenient.py::test_lenient_uncatalogued_dbf -v` | `1 passed` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TABL-03 | 03-01-PLAN | Typed readers for venci/prede/amoinv/nivel, schemas validated against pii-test-data/ | SATISFIED | `read_table_raw` reused; schemas from RESEARCH.md Q1; test_tables.py green |
| TABL-04 | 03-01-PLAN | Reader extracts every recognized table from a ZIP in a single pass | SATISFIED | `_CATALOGUE` frozenset (10 tables); `_find_sibling_dbf` resolution; zip_with_all_tables test passes |
| BAL-01 | 03-01-PLAN | Typed reader extracts raw BALAN.DBF trial-balance data | SATISFIED | BALAN read via `read_table_raw` as GenericTable; SDO_CIERRE column verified |
| BAL-02 | 03-01-PLAN | Tool computes authoritative trial balance from DIARIO.DBF | SATISFIED | `compute_balance()` in `_balance.py`; Decimal(str(float)) accumulation; test_balance.py green |
| API-03 | 03-05-PLAN | Lenient conversion path extracts all readable data, collects problems, never aborts the whole file | SATISFIED | `read()` D-03 path sets journal=None + ProblemEntry; `render()` None guard produces headers-only Diario sheet; end-to-end test passes |
| XLSX-02 | 03-01-PLAN | Renderer includes a problems sheet listing rows the lenient path skipped or flagged | SATISFIED | `_render_problems_sheet` with five Spanish columns; conditional on non-empty entries |
| XLSX-03 | 03-01-PLAN | Renderer marks raw BALAN sheet with visible "derived — may be unreliable" disclaimer | SATISFIED | `_render_balan_sheet` with conditional SDO_CIERRE banner; D-09 refinement (conditional) |

---

### Anti-Patterns Found

These are residual code-quality findings from the 03-REVIEW.md code review of the gap-closure diff. None block the phase goal; all are advisory.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/contaplus_reader/xlsx.py` | 183, 367, 381 | `ws: Any` on `_write_diario_headers_only`, `_autosize_columns`, `_autosize_columns_from_offset` — violates CLAUDE.md no-any rule; `Worksheet` is already imported | WARNING | Disables type checker on new gap-fix code; `wb.active` is `Worksheet \| None` in openpyxl stubs; passing it into `Any`-typed param silences a legitimate None-safety warning (review WR-04) |
| `src/contaplus_reader/xlsx.py` | 183-201 vs 150-180 | `_write_diario_headers_only` duplicates `_render_journal_sheet` header block verbatim | INFO | Drift hazard if header styling changes; not a correctness issue (review WR-03) |
| `src/contaplus_reader/_reader.py` | 296-317 | `except (ContaPlusReadError, ValueError)` wraps entire `_build_journal_row` call including `float()` amount parsing — amount-parsing `ValueError` lands in generic branch with blank column/value | INFO | Less informative ProblemEntry for amount-parsing failures vs. ContaPlusReadError path; not a correctness blocker (review WR-01) |
| `src/contaplus_reader/__init__.py` | 214-237 | Call sites pass inconsistently-cased `table_name` to `_read_secondary_table` (e.g. `"BALAN.DBF"` vs `"venci.dbf"`) — casing fix normalised `ProblemEntry.table` but user-facing error message still reflects raw casing | INFO | Cosmetic inconsistency in error messages; does not affect extraction correctness (review WR-02) |
| `src/contaplus_reader/cli.py` | 129 | `data_only=True` passed to `load_workbook` for a sheet-name count — no-op and misleading | INFO | Does not affect sheet count correctness; misleads reader (review WR-05 in code review) |
| `src/contaplus_reader/cli.py` | 127-128 | `import io as _io` and `from openpyxl import load_workbook as _load_wb` placed mid-function after several statements | INFO | Inconsistent with deferred-import grouping pattern at top of `main()`; cosmetic (review IN-01) |

No BLOCKER anti-patterns. The `ws: Any` typing violation is the most significant residual issue (breaks strict-typing contract required by CLAUDE.md), but it does not affect runtime correctness or the phase goal.

---

### Human Verification Required

None. All must-haves are verified programmatically. The behavioral spot-checks and test suite execution confirm the D-03 end-to-end contract is satisfied.

---

## Gaps Summary

No gaps. All four gaps from the previous verification (WR-06 BLOCKER, WR-05 WARNING, ProblemEntry.table casing WARNING, CLI sheet_count WARNING) are closed.

**Gap closure evidence:**
1. **WR-06 (BLOCKER closed):** `xlsx.py:89` contains `if data.journal is not None`; `_write_diario_headers_only` helper exists at line 183; `test_render_journal_none_produces_valid_workbook` and `test_render_lenient_end_to_end` both pass; `type: ignore[arg-type]` suppression is absent from the file.
2. **WR-05 (WARNING closed):** `_reader.py:296` contains `except (ContaPlusReadError, ValueError) as exc`; `isinstance(exc, ValueError)` discrimination at line 297; `test_lenient_dbfread_valueerror_skipped` passes (2 rows returned, 1 ProblemEntry with row_index=1); `test_lenient_dbfread_valueerror_strict_raises` passes.
3. **Table casing (WARNING closed):** `__init__.py:92` uses `Path(table_name).stem.upper()`; line 249 uses `candidate.stem.upper()`; `test_lenient_corrupt_table` asserts `e.table == "VENCI"` without workaround; `test_lenient_uncatalogued_dbf` asserts `e.table == "EXTRA"` without workaround.
4. **CLI sheet_count (WARNING closed):** `cli.py:129` contains `load_workbook(_io.BytesIO(xlsx_bytes), read_only=True, data_only=True).sheetnames`; derived from rendered workbook.

**Residual quality items** (WR-01 through WR-05 from code review, IN-01 through IN-04) are advisory refinements to be addressed in a future pass or Phase 4 cleanup. None block the phase goal.

**Test suite:** 124 tests, 0 failures, 0 errors.

---

_Verified: 2026-05-18_
_Verifier: Claude (gsd-verifier)_
