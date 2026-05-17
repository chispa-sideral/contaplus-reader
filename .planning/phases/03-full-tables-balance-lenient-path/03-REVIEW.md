---
phase: 03-full-tables-balance-lenient-path
reviewed: 2026-05-17T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/contaplus_reader/__init__.py
  - src/contaplus_reader/_balance.py
  - src/contaplus_reader/_reader.py
  - src/contaplus_reader/cli.py
  - src/contaplus_reader/models.py
  - src/contaplus_reader/xlsx.py
  - tests/conftest.py
  - tests/test_balance.py
  - tests/test_lenient.py
  - tests/test_tables.py
  - tests/test_xlsx.py
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-05-17
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 3 adds operational-table readers (`venci`/`prede`/`amoinv`/`nivel`/`balan`),
a recomputed trial balance (`_balance.py`), the lenient conversion path, and new
XLSX sheets. The structural shape is sound and the security posture of
`_safe_extract_zip` (zip-slip, symlink, zip-bomb guards) is good. However, two
correctness defects affect the lenient path and one affects the BALAN descuadre
check — both touch the project's stated core value ("correct extraction cannot
fail"). The trial-balance computation has a precision defect that contradicts the
file's own BAL-02 docstring claim.

Most serious: the lenient secondary-table reader records a `ProblemEntry.table`
that is inconsistent with how the same table is matched downstream, and
`compute_balance` widens `Decimal` correctness claims it does not actually keep.

## Critical Issues

### CR-01: `compute_balance` re-introduces float error it claims to avoid

**File:** `src/contaplus_reader/_balance.py:56-57`
**Issue:** The module docstring and inline comments state Decimal accumulation is
"mandatory" to avoid float binary-representation error (Pitfall 2), and the test
`test_decimal_precision` asserts `suma_debe == Decimal("0.3")` for inputs
`0.1 + 0.2`. The conversion `Decimal(str(row.debe))` only produces a clean
`Decimal("0.1")` because `str(0.1)` is `"0.1"` — but `row.debe` is a `float`
sourced from `float(record.get(debe_col) or 0)` in `_reader.py:166`. For any DBF
amount that does not round-trip cleanly through `repr()` (e.g. a value stored as
`123456789012.34` in an `N(16,2)` field, or any value with >15 significant
digits), `str(float)` yields a rounded/imprecise decimal string and the
accumulator silently carries that error. The journal feeds tax filings; a
cent-level drift on a large account is a correctness failure, not a style issue.
The root cause is that `debe`/`haber` are stored as `float` on `JournalRow`
(`models.py:107-108`) — the precision is already lost before `_balance.py` runs.
**Fix:** Capture the amount as `Decimal` at read time and keep it `Decimal`
end-to-end. In `_reader.py`, dbfread already decodes `N`-type fields to
`Decimal`; do not collapse them to `float`:
```python
# _reader.py — keep the Decimal dbfread returns
raw_debe = record.get(debe_col)
debe = raw_debe if isinstance(raw_debe, Decimal) else Decimal(str(raw_debe or 0))
```
and change `JournalRow.debe/haber` to `Decimal`. Then `_balance.py` accumulates
`Decimal` directly with no `str()` round-trip. If `float` on `JournalRow` must be
kept for API reasons, document explicitly that balance precision is bounded by
float53 and drop the "avoids float error" claim from the docstring.

### CR-02: lenient `ProblemEntry.table` for secondary tables is inconsistent and breaks downstream matching

**File:** `src/contaplus_reader/__init__.py:90-98` and `:223-225`
**Issue:** `_read_secondary_table` builds `ProblemEntry(table=table_name.lower(), ...)`.
The `balan` call passes `table_name="BALAN.DBF"` (`__init__.py:224`) while every
other secondary table passes a lowercase name. After `.lower()` the balan entry
becomes `"balan.dbf"`, which happens to work, but the convention is
self-contradictory in the same function: the file-level DIARIO error uses
`table="DIARIO"` (uppercase, `:182` and `:312`), the uncatalogued scan uses
`candidate.name.upper()` (`:249`), and secondary tables use lowercase. The
`test_lenient.py` suite papers over this by matching case-insensitively
(`test_lenient_corrupt_table` uses `e.table.lower() == "venci.dbf"`), so the
inconsistency is untested and will surface the moment any consumer (the PWA, or
tax-workbench) filters problems by table name. A `ProblemEntry.table` value that
depends on which call site produced it is a data-correctness defect in the
public `ProblemsReport` contract.
**Fix:** Normalise once. Decide a single canonical form (recommend uppercase
basename, matching the uncatalogued scan and DIARIO) and apply it in every
construction site:
```python
def _problem_table_name(name: str) -> str:
    return name.upper()
# in _read_secondary_table:
table=_problem_table_name(table_name)
# DIARIO entries already use "DIARIO"; pass "DIARIO.DBF" if basename form is chosen
```
Add a test that asserts the exact `entry.table` string for a corrupt secondary
table rather than a case-folded substring.

## Warnings

### WR-01: BALAN descuadre banner crashes on a non-numeric `SDO_CIERRE` cell

**File:** `src/contaplus_reader/xlsx.py:238-245`
**Issue:** `_render_balan_sheet` sums `SDO_CIERRE` via
`Decimal(str(row[sdo_idx])) for row in balan.rows if row[sdo_idx] is not None`.
The `None` guard is present (T-03-13), but `BALAN.DBF` is read by
`read_table_raw` which performs no type validation — a `SDO_CIERRE` cell holding
an empty string `""` (common in DBF character/blank fields) or any non-numeric
text passes the `is not None` check and reaches `Decimal(str(""))`, which raises
`decimal.InvalidOperation`. That exception is not a `ContaPlusReadError`, so in
the CLI it is caught only by the broad `except Exception` in `cli.py:101` and
shown as an opaque "XLSX Render Error" — and in library use it escapes entirely.
**Fix:** Coerce defensively and skip uncoercible cells:
```python
def _to_decimal(v: object) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
sdo_sum = sum((d for r in balan.rows
               if (d := _to_decimal(r[sdo_idx])) is not None), Decimal("0"))
```

### WR-02: lenient mode silently swallows file-level secondary-table errors with no severity distinction

**File:** `src/contaplus_reader/__init__.py:87-99`
**Issue:** In lenient mode `_read_secondary_table` catches every
`ContaPlusReadError` and turns it into a single `ProblemEntry` with
`row_index=-1`. A genuinely corrupt operational table (e.g. truncated `amoinv.dbf`)
and a merely-uncatalogued file both end up as `row_index=-1` entries with no way
for a consumer to tell "table dropped due to corruption" from "table not
recognised". Given the project's core value is *correct, visible* extraction,
collapsing a corruption event into the same shape as an informational notice
risks a user shipping an incomplete workbook believing nothing was lost.
**Fix:** Add a `severity` (or `kind`) field to `ProblemEntry` —
`"error"` for read failures, `"info"` for uncatalogued files — and surface it in
the Problemas sheet so the distinction reaches the user.

### WR-03: `sheet_count` in the CLI success summary is stale and undercounts

**File:** `src/contaplus_reader/cli.py:126-129`
**Issue:** The D-16 summary computes `sheet_count` from only
`[journal, subcta, empresa, grupos, usuarios]` — the five Phase 1/2 tables. Phase 3
added `balan`, `venci`, `prede`, `amoinv`, `nivel`, `balance_cuenta`,
`balance_subcuenta`, and the `Problemas` sheet, all of which `render()` emits as
real sheets (`xlsx.py:94-122`). A full 10-table ZIP reports "5 sheet(s)" while
the workbook actually contains 13+. The user-facing summary is wrong.
**Fix:** Count from the same list `render()` iterates, or have `render()` return
the sheet count alongside the bytes:
```python
sheet_count = sum(t is not None for t in [
    data.journal, data.subcta, data.balan, data.balance_cuenta,
    data.balance_subcuenta, data.venci, data.prede, data.amoinv,
    data.nivel, data.empresa, data.grupos, data.usuarios,
]) + (1 if data.problems and data.problems.entries else 0)
```

### WR-04: uncatalogued-DBF scan can double-report a table that also failed to read

**File:** `src/contaplus_reader/__init__.py:240-255`
**Issue:** The D-13 uncatalogued scan iterates *every* `.dbf` in the company
directory and reports any whose lowercase name is not in `_CATALOGUE`. It runs
unconditionally after the secondary-table reads. A catalogued table that failed
to read already produced a `ProblemEntry` via `_read_secondary_table`; that is
fine because it is in `_CATALOGUE`. But the scan has no exclusion for the DIARIO
itself if DIARIO is the only file, and — more importantly — there is no guard
against the scan running while `diario_path.parent` contains files that were
just extracted but are *directories* named `*.dbf`; `candidate.is_file()` covers
that. The real defect: the scan uses `candidate.name.upper()` as the table name,
diverging from the lowercase convention used three lines earlier for catalogued
tables (see CR-02). Consistency aside, an archive with both `extra.dbf` and a
corrupt catalogued table yields two entries with two different casing
conventions in the same report.
**Fix:** Resolve alongside CR-02 by normalising all `ProblemEntry.table` values
through one helper.

### WR-05: `_read_dbf_path` reads the full DBF inside a single broad `except (struct.error, ValueError, OSError)`

**File:** `src/contaplus_reader/_reader.py:269-358`
**Issue:** The entire per-row iteration loop (`for idx, record in enumerate(table)`)
runs inside the outer `try` whose handler catches `ValueError`. dbfread can raise
`ValueError` mid-iteration on a malformed record. In lenient mode the intent is
that per-row problems become `ProblemEntry` records and iteration continues — but
a `ValueError` raised by dbfread itself (not a `ContaPlusReadError`) escapes the
inner per-row `except ContaPlusReadError` and is caught by the outer handler,
which converts it to a *file-level* `ContaPlusReadError`. Result: one malformed
record aborts the whole journal even in lenient mode, contradicting D-02. The
lenient path's robustness depends on dbfread never raising a bare `ValueError`
during iteration, which is not guaranteed.
**Fix:** Wrap the per-record body in a `try/except (ValueError, struct.error)`
that, in lenient mode, emits a `ProblemEntry` and `continue`s; keep the outer
handler for open-time / header-parse failures only.

### WR-06: `render()` uses `wb.active` without confirming the active sheet exists

**File:** `src/contaplus_reader/xlsx.py:84-87`
**Issue:** `_render_journal_sheet(wb.active, data.journal)` is annotated
`# type: ignore[arg-type]` because `wb.active` is `Worksheet | None`. The
`type: ignore` suppresses the warning but does not make the call safe — and
`data.journal` is typed `ContaPlusJournal | None`. In lenient mode `data.journal`
can legitimately be `None` (D-03: wholly-unreadable DIARIO). `_render_journal_sheet`
then iterates `journal.rows` on `None` and raises `AttributeError`. The lenient
path is specifically designed to continue after a dead journal, so a lenient
conversion of a corrupt-DIARIO ZIP will crash in the renderer instead of
producing a workbook with an empty Diario sheet plus the other tables.
**Fix:** Guard the journal sheet:
```python
ws = wb.active
if data.journal is not None:
    _render_journal_sheet(ws, data.journal)
else:
    ws.title = "Diario"
    # write headers only
```
Add a test: `render()` on a `ContaPlusData(journal=None, subcta=...)`.

### WR-07: `JournalRow.subcuenta_nombre` enrichment miss-rate is logged but never surfaced in lenient `problems`

**File:** `src/contaplus_reader/_reader.py:327-335`
**Issue:** WR-04's enrichment-miss counter is computed and logged at `INFO`, but
in lenient mode — where the explicit goal is to surface every data-quality issue
to the user via the Problemas sheet — a near-total enrichment miss (the comment
itself says this "likely signals a key-normalisation bug") produces no
`ProblemEntry`. A user converting in the PWA never sees the log. The diagnostic
exists but is invisible to the audience that needs it.
**Fix:** When `lenient=True` and the miss rate exceeds a threshold, append one
informational `ProblemEntry` (`table="SUBCTA"`, `row_index=-1`) summarising the
miss count.

## Info

### IN-01: `tempfile` import in `__init__.py` is fine, but `Path` import used only in a type position

**File:** `src/contaplus_reader/__init__.py:16-18`
**Issue:** `tempfile`, `Path`, `BinaryIO` are all used; no dead import. However
`from __future__ import annotations` is present so `Path` in `_read_secondary_table`'s
signature is a string at runtime — the import is only needed for the
`Path(tmpdir_str)` call at line 155, which is correct. No action needed; noted to
confirm it was checked.

### IN-02: magic-number decompression caps are module constants — good, but undocumented unit rationale

**File:** `src/contaplus_reader/_zip.py:29-31`
**Issue:** `_MAX_TOTAL_UNCOMPRESSED = 500 MB`, `_MAX_ENTRY_COUNT = 10_000`,
`_MAX_COMPRESSION_RATIO = 200` are sensible and named, but there is no comment on
why 500 MB / 200:1 specifically (a real ContaPlus multi-year archive size would
justify the number).
**Fix:** Add a one-line comment citing the largest observed real archive so a
future maintainer does not lower the cap below a legitimate file.

### IN-03: `_raw_value` defensively handles non-`get` records but `_build_journal_row` does not

**File:** `src/contaplus_reader/_reader.py:108-117` vs `:157`
**Issue:** `_raw_value` checks `hasattr(record, "get")` before calling `.get`,
but `_build_journal_row` calls `record.get("fecha")` directly with a
`# type: ignore[union-attr]`. The two helpers disagree on whether `record` is
trusted to have `.get`. dbfread records are dict-like so this is fine in
practice; the inconsistency is cosmetic.
**Fix:** Pick one assumption. Since dbfread guarantees a mapping, drop the
`hasattr` check in `_raw_value` for consistency.

### IN-04: test helpers construct `JournalRow` without `subcuenta_nombre` — relies on default

**File:** `tests/test_balance.py:32-41`, `tests/test_xlsx.py:32-40`
**Issue:** `_make_row` / `_sample_row` omit `subcuenta_nombre`, relying on the
`= None` default. Correct today, but if the field's default is ever removed the
failure is a collection-time `TypeError` across many tests. Low risk.
**Fix:** None required; acceptable for test code.

### IN-05: `_autosize_columns` and `_autosize_columns_from_offset` are near-duplicates

**File:** `src/contaplus_reader/xlsx.py:341-377`
**Issue:** The two functions differ only in the `if c.row >= start_row` filter
and the column-letter source (`col_cells[0].column_letter` vs
`get_column_letter(col_idx)`). The duplication is a maintenance hazard — a future
fix to the width cap must be applied twice.
**Fix:** Collapse into one function with a `start_row: int = 1` parameter and use
`get_column_letter(col_idx)` uniformly.

---

_Reviewed: 2026-05-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
