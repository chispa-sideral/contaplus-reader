---
phase: 03-full-tables-balance-lenient-path
reviewed: 2026-05-17T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/contaplus_reader/xlsx.py
  - src/contaplus_reader/_reader.py
  - src/contaplus_reader/__init__.py
  - src/contaplus_reader/cli.py
  - tests/test_xlsx.py
  - tests/test_lenient.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 3: Code Review Report (gap-closure pass, plan 03-05)

**Reviewed:** 2026-05-17
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

> This review supersedes the earlier `03-REVIEW.md` (verification-cycle report).
> It assesses the **plan 03-05 gap-closure diff** since `9b3e91e` — the four
> fixes that closed WR-06 (blocker), WR-05, the `ProblemEntry.table` casing
> issue, and the CLI `sheet_count` issue from the prior verification report.

## Summary

The four gap fixes are functionally correct and each closes the behaviour the
verification report flagged. The WR-06 `journal=None` guard is the most important
and is covered by two new tests (`test_render_journal_none_produces_valid_workbook`,
`test_render_lenient_end_to_end`) including an end-to-end corrupt-ZIP path. WR-05's
`except (ContaPlusReadError, ValueError)` broadening is sound and tested in both
lenient and strict directions. The casing and `sheet_count` fixes are correct.

Adversarial assessment of *how* they were closed surfaces five Warnings and four
Info items — all quality/robustness defects in the fix code, none a regression of
the original gaps:

- WR-05's broadened catch wraps the entire `_build_journal_row` call, so a
  `ValueError` from amount parsing (`float()`) is now downgraded to an opaque
  `ProblemEntry` with blank `column`/`value` (WR-01).
- The casing fix canonicalised the `ProblemEntry.table` field but left the
  `_read_secondary_table` call sites passing inconsistently-cased `table_name`,
  which still feeds inconsistent casing into user-facing error messages (WR-02).
- The WR-06 helper `_write_diario_headers_only` duplicates the header/freeze/
  autosize block of `_render_journal_sheet` verbatim (WR-03) and is typed
  `ws: Any`, breaking the strict-typing contract the rest of the module keeps
  (WR-04).
- The CLI `sheet_count` fix passes `data_only=True` to `load_workbook`, which is a
  no-op for a sheet-name count and misleads the reader (WR-05).

No Critical issues in the gap-closure diff.

## Warnings

### WR-01: Broadened `ValueError` catch swallows amount-parsing failures as opaque problems

**File:** `src/contaplus_reader/_reader.py:296-317`
**Issue:** The WR-05 fix broadened the per-row handler to
`except (ContaPlusReadError, ValueError)`. The `ValueError` branch in lenient mode
appends a `ProblemEntry` with `column=""`, `value=""` and `reason=str(exc)`, then
`continue`s. The justifying comment scopes this to "dbfread field deserialization"
errors — but the `try` wraps the *entire* `_build_journal_row` call, which also
runs:

```python
debe = float(record.get(debe_col) or 0)    # line 166
haber = float(record.get(haber_col) or 0)  # line 167
```

If dbfread returns a `debe`/`haber` value that does not coerce (a malformed
numeric string, or a stray non-numeric character field), `float()` raises a bare
`ValueError`. That is a genuine, field-attributable data defect — but it now lands
in the generic `ValueError` branch and is reported with **blank `column` and blank
`value`**. The Problemas sheet then shows a row the user cannot act on: it does not
say which field (`debe` vs `haber`) failed or what the offending value was. The
prior `ContaPlusReadError` path (line 319-333) captures both `exc.column` and
`_raw_value(record, exc.column)` precisely — the new branch is strictly less
informative for the same class of error.

A secondary hazard: if a `ValueError` ever originates from a logic bug *inside*
`_build_journal_row` rather than from the data, lenient mode now silently skips the
row and masks the bug.

**Fix:** Convert the amount-parsing failures into typed `ContaPlusReadError` inside
`_build_journal_row` so they keep their column and raw value:

```python
raw_debe = record.get(debe_col)
try:
    debe = float(raw_debe or 0)
except (ValueError, TypeError) as exc:
    raise ContaPlusReadError(
        row_index=idx, column="debe",
        message=f"non-numeric debe: {raw_debe!r}",
    ) from exc
# ...same for haber...
```

This leaves the new `ValueError` branch catching only genuine dbfread-internal
deserialization failures (which are legitimately not field-attributable). At
minimum, prefix `reason` with the exception type so the Problemas row is not a
bare message with no context.

### WR-02: `_read_secondary_table` call sites still pass inconsistently-cased `table_name`

**File:** `src/contaplus_reader/__init__.py:214-237` (call sites);
consumed at `src/contaplus_reader/_subcta.py:198`
**Issue:** The casing fix changed `_read_secondary_table` to build
`ProblemEntry(table=Path(table_name).stem.upper(), ...)`, which canonicalises the
*ProblemEntry.table* field. But the eight call sites still pass `table_name` with
mixed casing:

```python
balan_path,  "BALAN.DBF",  ...   # uppercase
venci_path,  "venci.dbf",  ...   # lowercase
grupos_path, "grupos.dbf", ...   # lowercase
```

`table_name` is forwarded verbatim into `read_table_raw(path, table_name)`, where
it is interpolated into the user-facing error message
`f"{table_name} read error: {exc}"` (`_subcta.py:198`). So a corrupt BALAN reports
`BALAN.DBF read error: ...` while a corrupt VENCI reports `venci.dbf read error:
...` — inconsistent error text in the same conversion. The `.stem.upper()` only
normalises the `table` column of the `ProblemEntry`, not the `reason` text that is
built from the raw `table_name`. The fix masked half the inconsistency and left
the other half live.

**Fix:** Make all eight call sites use one casing. Lowercase matches `_CATALOGUE`
and the actual extracted filenames:

```python
balan = _read_secondary_table(
    balan_path, "balan.dbf", lenient=lenient, problems=collected_problems
)
```

`_read_secondary_table` already applies `.stem.upper()` for the ProblemEntry, so
the only consumer sensitive to the raw casing is the error message — normalising
the inputs fixes it.

### WR-03: `_write_diario_headers_only` duplicates `_render_journal_sheet`'s header block verbatim

**File:** `src/contaplus_reader/xlsx.py:183-201` vs `150-180`
**Issue:** The WR-06 fix added `_write_diario_headers_only`. Its entire body — the
`for col_idx, header in enumerate(HEADERS, 1)` styling loop, `ws.freeze_panes =
"A2"`, and `_autosize_columns(ws)` — is a verbatim copy of lines 159-165 + 180 of
`_render_journal_sheet`. The code comment admits it: "identical to
`_render_journal_sheet` row 1". Any future change to header styling, the freeze
cell, or the autosize policy must be applied to both functions in lockstep — a
drift hazard. `_render_journal_sheet` already handles the zero-row case correctly:
`enumerate(journal.rows, 2)` over an empty tuple writes no data rows.

**Fix:** Delete `_write_diario_headers_only` and reuse the existing renderer with
an empty journal:

```python
if data.journal is not None:
    _render_journal_sheet(wb.active, data.journal)
else:
    # D-03 lenient path: corrupt DIARIO -> headers-only Diario sheet.
    _render_journal_sheet(wb.active, ContaPlusJournal(rows=()))
```

`ContaPlusJournal` is already imported (`xlsx.py:27`) and `rows=()` is valid with
its other fields defaulted. This removes ~19 lines and guarantees the headers-only
sheet stays byte-identical to a real Diario header row.

### WR-04: `_write_diario_headers_only` typed `ws: Any` — breaks the module's strict-typing convention

**File:** `src/contaplus_reader/xlsx.py:183` (`ws: Any`); also `367`, `381`
**Issue:** CLAUDE.md mandates strict typing with no `any`. Every other render
helper in this file (`_render_journal_sheet`, `_render_subcta_sheet`,
`_render_generic_sheet`, `_render_balan_sheet`, `_render_balance_sheet`,
`_render_problems_sheet`) is annotated `ws: Worksheet`. The new WR-06 helper
`_write_diario_headers_only` was added at `ws: Any`, as were the two autosize
helpers it calls. `Any` disables the type checker exactly where the new gap-fix
code runs — `wb.active` is `Worksheet | None` in openpyxl's stubs, and passing it
into an `Any`-typed parameter silences a legitimate `None`-safety warning. The
`Worksheet` type is already imported (`xlsx.py:23`).

**Fix:** Annotate `_write_diario_headers_only`, `_autosize_columns`, and
`_autosize_columns_from_offset` as `ws: Worksheet` to match the rest of the module.
They are only ever called with a writable `Worksheet`.

### WR-05: CLI passes `data_only=True` to `load_workbook` for a sheet-name count — a no-op and misleading

**File:** `src/contaplus_reader/cli.py:127-129`
**Issue:** The `sheet_count` fix uses
`load_workbook(_io.BytesIO(xlsx_bytes), read_only=True, data_only=True).sheetnames`.
`data_only=True` tells openpyxl to return cached cell *values* instead of formulas
— it has zero effect on `.sheetnames` and zero effect when only sheet names are
read. Its presence signals an intent (inspecting cell values) that does not exist
and will mislead the next maintainer. Separately, re-parsing the freshly-written
xlsx purely to `len(...sheetnames)` is wasteful and couples the CLI summary to a
clean round-trip of the file it just produced.

**Fix:** Drop `data_only=True`. Better, avoid the re-parse entirely by having
`render()` return the sheet names (or count) alongside the bytes so the summary is
authoritative:

```python
sheet_count = len(_load_wb(_io.BytesIO(xlsx_bytes), read_only=True).sheetnames)
```

## Info

### IN-01: CLI imports placed mid-function, inconsistent with the file's deferred-import grouping

**File:** `src/contaplus_reader/cli.py:127-128`
**Issue:** `import io as _io` and `from openpyxl import load_workbook as _load_wb`
are placed two-thirds of the way down `main()`, after several statements. The file
already uses deferred imports (`from contaplus_reader import ...` at line 54) to
keep CLI startup fast — but those are grouped at the *start* of the function.
Burying two more imports mid-body with underscore-prefixed aliases reads as a
hurried patch.
**Fix:** Move both imports up with the other deferred imports at the top of
`main()`.

### IN-02: `ProblemEntry` docstring example is stale after the casing fix

**File:** `src/contaplus_reader/models.py:171`
**Issue:** `ProblemEntry.table`'s docstring says
`table: logical table name (e.g. "DIARIO", "venci.dbf")`. After the casing fix,
secondary tables are emitted as uppercase stems (`"VENCI"`, never `"venci.dbf"`).
The example now contradicts the canonical form the code produces.
**Fix:** Update the example to `"DIARIO"`, `"VENCI"`.

### IN-03: `_raw_value` `type: ignore[union-attr]` redundant with its own runtime guard

**File:** `src/contaplus_reader/_reader.py:108-117`
**Issue:** `_raw_value` does `if hasattr(record, "get"): return str(record.get(...))`
with a trailing `# type: ignore[union-attr]`. The `hasattr` already narrows at
runtime; the `type: ignore` exists only because `record` is statically typed
`object`. CLAUDE.md discourages loose `type: ignore`. Typing `record` as a
`Mapping[str, object]` protocol (or the dbfread record type) would let the ignore
be dropped. Pre-existing, but the WR-05 work touched the surrounding function.
**Fix:** Type `record` precisely and remove the ignore; low priority.

### IN-04: `_assert_journal_shaped` re-declares amount-column sets that duplicate module constants

**File:** `src/contaplus_reader/_reader.py:94-95`
**Issue:** `_assert_journal_shaped` declares local `_DEBE`/`_HABER` sets that
duplicate the module-level `_DEBE_COL_CANDIDATES`/`_HABER_COL_CANDIDATES` tuples
(lines 32-33). If a new amount-column variant is added to the canonical tuples but
not the local sets, the shape check and the column picker disagree. Pre-existing,
low severity.
**Fix:** Derive the assertion sets from the canonical tuples:
`set(_DEBE_COL_CANDIDATES)`.

---

## Gap-closure verdict

| Gap (from 03-VERIFICATION.md) | Closed? | Residual finding |
|-------------------------------|---------|------------------|
| WR-06 — `render()` crash on `journal=None` | Yes — guarded, tested end-to-end | WR-03 (duplication), WR-04 (typing) |
| WR-05 — `ValueError` escapes per-row handler | Yes — `except (ContaPlusReadError, ValueError)`, tested both modes | WR-01 (over-catch, opaque ProblemEntry) |
| `ProblemEntry.table` casing | Yes — for the `table` field | WR-02 (call-site casing still inconsistent in error text) |
| CLI `sheet_count` undercount | Yes — derived from rendered workbook | WR-05 (no-op `data_only`), IN-01 (import placement) |

All four gaps are genuinely closed for the behaviour the verification report
flagged; no regression detected. The residual findings are quality and robustness
defects in the fix code, not reopened gaps.

---

_Reviewed: 2026-05-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
