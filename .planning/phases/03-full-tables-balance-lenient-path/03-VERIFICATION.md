---
phase: 03-full-tables-balance-lenient-path
verified: 2026-05-17T00:00:00Z
status: gaps_found
score: 4/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "A lenient conversion of a corrupt-DIARIO ZIP produces a workbook with other tables + problems sheet (D-03 end-to-end)"
    status: failed
    reason: "render() unconditionally calls _render_journal_sheet(wb.active, data.journal) without a None guard. When data.journal is None (D-03 path), _render_journal_sheet iterates journal.rows and raises AttributeError: 'NoneType' object has no attribute 'rows'. The lenient read() path correctly sets journal=None and collects a ProblemEntry, but the subsequent render() call crashes before producing the workbook. Confirmed by direct execution: ContaPlusData(journal=None) -> render() raises AttributeError."
    artifacts:
      - path: "src/contaplus_reader/xlsx.py"
        issue: "_render_journal_sheet(wb.active, data.journal) at line 87 has no None guard; type: ignore[arg-type] suppresses the type error but does not make the call safe"
    missing:
      - "Guard the journal sheet render: if data.journal is not None: _render_journal_sheet(ws, data.journal) else: ws.title = 'Diario'  # write headers only"
      - "Test: render(ContaPlusData(journal=None, subcta=...)) succeeds and returns valid workbook bytes"
---

# Phase 3: Full Tables, Balance & Lenient Path Verification Report

**Phase Goal:** A user running lenient conversion gets every readable table extracted — including operational tables and a recomputed trial balance — plus a problems sheet listing anything that was skipped
**Verified:** 2026-05-17
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A backup ZIP converted with `--lenient` produces sheets for venci, prede, amoinv, and nivel | VERIFIED | `_render_generic_sheet` called for all four; `render()` sheet-order confirmed in xlsx.py:103-110; `test_full_zip_all_tables_sheets_present` passes |
| 2 | The workbook contains a Problemas sheet listing every row the lenient path flagged, with row and column context | VERIFIED | `_render_problems_sheet` writes five columns (Tabla/Fila/Columna/Motivo/Valor); conditional only when `data.problems.entries` is non-empty (D-05); tested by `test_problems_sheet_present`, `test_problems_sheet_columns`, `test_problems_sheet_has_entries` |
| 3 | The BALAN sheet carries the descuadre disclaimer only when its own figures fail to balance; two recomputed trial-balance sheets are always present (D-07/D-09 refinements) | VERIFIED | `_render_balan_sheet` sums SDO_CIERRE with Decimal and injects banner only on non-zero sum; `test_balan_banner_on_descuadre` and `test_balan_no_banner_when_balanced` pass; `balance_cuenta`/`balance_subcuenta` computed from journal whenever it is not None |
| 4 | Field schemas for venci, prede, amoinv, and nivel are validated against pii-test-data/ before readers are committed | VERIFIED | 03-RESEARCH.md §Q1 documents schema enumeration across all 5 real archives (confirmed 2026-05-17); test fixtures use exact field schemas from that enumeration; synthetic fixtures do not use pii-test-data/ blobs |
| 5 | A lenient conversion of a corrupt-DIARIO ZIP produces a workbook containing all other readable tables plus a problems sheet (D-03 end-to-end) | FAILED | `render()` crashes with `AttributeError: 'NoneType' object has no attribute 'rows'` when `data.journal is None`. The `read()` path correctly implements D-03 (journal=None + ProblemEntry) and is tested by `test_lenient_corrupt_journal`. The `render()` path is not guarded and is not tested. End-to-end lenient conversion of a corrupt-DIARIO archive produces no workbook. |

**Score:** 4/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/contaplus_reader/models.py` | ProblemEntry, ProblemsReport, BalanceRow, BalanceTable, ContaPlusData Phase 3 attributes | VERIFIED | All types present; ContaPlusData has balan/venci/prede/amoinv/nivel/balance_cuenta/balance_subcuenta/problems |
| `src/contaplus_reader/_balance.py` | compute_balance() with Decimal accumulation | VERIFIED | Decimal(str(row.debe)) pattern used; defaultdict accumulators; sorted output |
| `src/contaplus_reader/_reader.py` | _build_journal_row helper + lenient/problems parameters | VERIFIED | Inner try/except ContaPlusReadError catches per-row errors and appends ProblemEntry when lenient; file-level errors re-raise |
| `src/contaplus_reader/__init__.py` | lenient param, 10-table catalogue, D-03/D-04/D-13 wiring | VERIFIED | _CATALOGUE frozenset; _read_secondary_table helper; D-03 try/except around journal read; D-13 uncatalogued scan |
| `src/contaplus_reader/xlsx.py` | Phase 3 renderers, render() sheet order, problems sheet | PARTIAL | _render_balan_sheet, _render_balance_sheet, _render_problems_sheet all implemented correctly; render() sheet order correct; BUT render() line 87 calls _render_journal_sheet unconditionally without a None guard (WR-06) |
| `src/contaplus_reader/cli.py` | --lenient flag | VERIFIED | Typer option wired to read(lenient=lenient) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `read()` | `_read_dbf_path()` | `lenient=True, problems=collected_problems` | VERIFIED | Both ZIP and raw-DBF paths pass lenient/problems through |
| `read()` | `compute_balance()` | Called after journal read when journal is not None | VERIFIED | Both cuenta and subcuenta levels computed; subcta_lookup reused |
| `render()` | `_render_journal_sheet()` | `wb.active, data.journal` — unconditional | BROKEN | No None guard; crashes when data.journal is None (WR-06) |
| `render()` | `_render_problems_sheet()` | Conditional: only when problems.entries non-empty | VERIFIED | D-05 honored |
| `render()` | `_render_balan_sheet()` | Conditional: only when data.balan is not None | VERIFIED | |
| `_read_dbf_path()` | inner `except ContaPlusReadError` | per-row lenient skip | PARTIAL | Only catches ContaPlusReadError; bare ValueError from dbfread mid-iteration escapes to outer handler (WR-05) |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `_render_balance_sheet` | `table.rows` | `compute_balance(journal)` | Yes — Decimal accumulation over real journal rows | FLOWING |
| `_render_balan_sheet` | `balan.rows` | `read_table_raw(balan_path)` | Yes — full DBF dump | FLOWING |
| `_render_problems_sheet` | `report.entries` | `collected_problems` list in `read()` | Yes — real error events from lenient path | FLOWING |
| `render()` Diario sheet | `data.journal` | `_read_dbf_path()` | Crashes when None — no data flows when journal is None | HOLLOW (WR-06) |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 120-test suite | `uv run pytest tests/ 2>&1 \| tail -3` | `120 passed in 1.71s` | PASS |
| render(ContaPlusData(journal=None)) | Direct Python execution | `AttributeError: 'NoneType' object has no attribute 'rows'` | FAIL |
| Lenient read + render of corrupt-DIARIO ZIP | End-to-end Python execution | read() succeeds (journal=None, subcta populated), render() crashes | FAIL |
| Decimal precision for N(16,2) amounts | `str(float(Decimal('99999999999999.99')))` | Round-trip fails at 100-trillion values; all realistic ContaPlus accounting amounts (up to ~10 billion) round-trip correctly | PASS (practical) |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TABL-03 | 03-01-PLAN | Typed readers for venci/prede/amoinv/nivel, schemas validated against pii-test-data/ | SATISFIED | read_table_raw reused; schemas from RESEARCH.md Q1; test_tables.py 12/12 green |
| TABL-04 | 03-01-PLAN | Reader extracts every recognized table from a ZIP in a single pass | SATISFIED | _CATALOGUE frozenset; 10 tables resolved via _find_sibling_dbf; zip_with_all_tables test passes |
| BAL-01 | 03-01-PLAN | Typed reader extracts raw BALAN.DBF trial-balance data | SATISFIED | BALAN read via read_table_raw as GenericTable; SDO_CIERRE column verified |
| BAL-02 | 03-01-PLAN | Tool computes authoritative trial balance from DIARIO.DBF | SATISFIED | compute_balance() in _balance.py; Decimal(str(float)) accumulation; test_balance.py 8/8 green |
| API-03 | 03-01-PLAN | Lenient conversion path extracts all readable data, collects problems, never aborts the whole file | PARTIALLY BLOCKED | read() path is correct; but render() crashes when journal=None — the "never aborts the whole file" contract is broken at render time |
| XLSX-02 | 03-01-PLAN | Renderer includes a problems sheet listing rows the lenient path skipped or flagged | SATISFIED | _render_problems_sheet with five Spanish columns; conditional on non-empty entries; test_problems_sheet_present passes |
| XLSX-03 | 03-01-PLAN | Renderer marks raw BALAN sheet with visible "derived — may be unreliable" disclaimer | SATISFIED | _render_balan_sheet with conditional SDO_CIERRE banner; D-09 refinement (conditional) implemented per CONTEXT.md; tests pass |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/contaplus_reader/xlsx.py` | 87 | `_render_journal_sheet(wb.active, data.journal)` — no None guard, `# type: ignore[arg-type]` suppresses type error | BLOCKER | render() crashes with AttributeError when called after a lenient read() that produced journal=None (WR-06 confirmed by execution) |
| `src/contaplus_reader/_reader.py` | 290-352 | Inner `except ContaPlusReadError` only; bare `ValueError` from dbfread mid-iteration escapes to outer `except (struct.error, ValueError, OSError)` which creates a file-level error (row_index=-1) | WARNING | A dbfread `ValueError` on a single corrupt record aborts the whole journal in lenient mode (D-03 behavior) instead of skipping the row (D-02 behavior). Contradicts D-02 guarantee but not exploitable from the test suite since all bad-row fixtures use application-level validation failures (ContaPlusReadError), not dbfread-level ValueError. |
| `src/contaplus_reader/__init__.py` | 89-98 | `ProblemEntry(table=table_name.lower(), ...)` vs line 249 `candidate.name.upper()` vs line 181/312 `table="DIARIO"` — inconsistent ProblemEntry.table casing | WARNING | Table name convention is self-contradictory: balan -> "balan.dbf", uncatalogued -> "EXTRA.DBF", journal -> "DIARIO". PWA/consumer code filtering by table name will need case-folding. Test_lenient.py uses `.table.lower() == "venci.dbf"` and `.table.upper() == "EXTRA.DBF"` to paper over this. |
| `src/contaplus_reader/cli.py` | 126-129 | `sheet_count` computed only from Phase 1/2 tables (journal/subcta/empresa/grupos/usuarios) | WARNING | Reports "5 sheet(s)" when a full Phase 3 workbook has 13+. User-facing summary is incorrect but does not affect extraction correctness. |

---

## Verification Override Notes

**CR-01 (float precision in trial balance):** The code review flags that `JournalRow.debe/haber` are `float` and `Decimal(str(float))` can fail for amounts > ~100 trillion. Direct measurement confirms the round-trip fails only at `N(16,2)` extreme values (99999999999999.99). ContaPlus is a small-business accounting system — no real archive will contain 100-trillion-euro amounts. The `Decimal(str(float))` pattern matches the pattern prescribed by RESEARCH.md §Q4 ("Why str() and not Decimal(float_value)") and is verified against the real MELO archive. This defect is a theoretical correctness concern for the docstring claim, not a practical failure for any real ContaPlus data. It is a WARNING (code quality), not a BLOCKER for the phase goal.

---

## Gaps Summary

One blocker prevents full phase goal achievement:

**WR-06 — render() crashes on journal=None (D-03 lenient path).**

The phase goal states "a user running lenient conversion gets every readable table extracted...plus a problems sheet." When the archive's DIARIO is corrupt, `read()` correctly produces `journal=None` with a ProblemEntry (D-03 implemented). But `render(data)` is called next and immediately crashes with `AttributeError: 'NoneType' object has no attribute 'rows'` at `xlsx.py:87`. The user gets no workbook.

The 120-test suite is green because `test_lenient_corrupt_journal` only asserts on the `ContaPlusData` returned by `read()` — it never calls `render()`. The test correctly validates D-03 at the data layer but leaves the render layer untested for this case.

**Fix required:**
1. In `xlsx.py` `render()`, guard the journal sheet: `if data.journal is not None: _render_journal_sheet(ws, data.journal)` else write "Diario" headers only.
2. Add test: `render(ContaPlusData(journal=None, subcta=<some_table>))` returns valid bytes containing a "Subcuentas" sheet and a "Problemas" sheet.

Secondary items (WR-05 / table-name casing / sheet-count undercount) are warnings that do not block the core conversion path for typical inputs but should be addressed before Phase 4.

---

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
