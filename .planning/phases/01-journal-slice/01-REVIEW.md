---
phase: 01-journal-slice
reviewed: 2026-05-15T16:30:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/contaplus_reader/__init__.py
  - src/contaplus_reader/_bridge.py
  - src/contaplus_reader/_reader.py
  - src/contaplus_reader/_sniffer.py
  - src/contaplus_reader/cli.py
  - src/contaplus_reader/models.py
  - src/contaplus_reader/xlsx.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_reader.py
  - tests/test_xlsx.py
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-05-15T16:30:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is a re-review of the Phase 1 journal slice after a prior round of fixes.
The earlier blockers (non-seekable `BinaryIO` crash, CLI leaking `FileNotFoundError`,
mutable-list `rows`, sign-blind D-C2) have been correctly addressed: the sniffer
now uses `seekable()`, the CLI wraps `read_bytes()` in `try/except OSError`,
`ContaPlusJournal.rows` is a `tuple`, and D-C2 uses `debe != 0 and haber != 0`.
The journal-correctness path — the core value of this project per CLAUDE.md — is
faithfully implemented and well-tested.

This review found new and remaining defects in the current code. One BLOCKER: a
write failure inside `bytes_to_tmppath` leaks the temp-file handle and, on
Windows, the cleanup `unlink` raises `PermissionError`, masking the real
exception — the exact Windows file-locking pitfall the module docstring claims
to defend against, but only on the happy path. WARNINGs cover an unhandled
`OSError` on the CLI output write (D-17 violation), a duplicated candidate-column
list that can silently drift between `_assert_journal_shaped` and `_pick_column`,
amount columns whose DBF type is never validated (asymmetric with the FECHA
type check), a truthiness-based null check on amounts, an over-narrow exception
catch in the reader, and an unguarded `Optional` dereference in the XLSX
renderer.

## Critical Issues

### CR-01: Temp-file handle leak and masked exception on write failure in `bytes_to_tmppath`

**File:** `src/contaplus_reader/_bridge.py:32-38`
**Issue:** `tempfile.NamedTemporaryFile(delete=False)` is created, then
`tmp.write(raw)` runs inside the `try`. If `tmp.write()` raises (disk full,
quota exceeded, I/O error), control jumps straight to the `finally` block and
`tmp.close()` on line 35 **never executes** — the file handle stays open. On
Windows the `finally` then runs `Path(tmp.name).unlink(missing_ok=True)`, which
raises `PermissionError` (WinError 32, "file in use by another process")
because the handle is still open. That cleanup exception **replaces the original
write exception**: the caller sees a misleading cleanup error, the real cause is
lost, and the temp file is leaked on disk. The module docstring explicitly
claims to handle the Windows file-locking pitfall, but the `close()` guard only
covers the path where `write()` succeeds.

**Fix:**
```python
@contextmanager
def bytes_to_tmppath(data: bytes | io.IOBase) -> Generator[Path, None, None]:
    raw: bytes = data if isinstance(data, bytes) else data.read()
    tmp = tempfile.NamedTemporaryFile(suffix=".dbf", delete=False)
    tmp_name = tmp.name
    try:
        try:
            tmp.write(raw)
        finally:
            tmp.close()  # always close, even if write() raised
        yield Path(tmp_name)
    finally:
        Path(tmp_name).unlink(missing_ok=True)
```
This guarantees the handle is closed before any `unlink`, so cleanup never masks
the original write error and no handle leaks.

## Warnings

### WR-01: CLI output write has no error handling — a write failure leaks a raw traceback

**File:** `src/contaplus_reader/cli.py:82`
**Issue:** The CLI carefully wraps `input_file.read_bytes()` in `try/except OSError`
that prints a clean Rich panel and exits 1 (lines 52-62). But the symmetric
`output_file.write_bytes(xlsx_bytes)` on line 82 has **no error handling**. If
the output directory is not writable, the disk is full, or the path is invalid,
this raises a raw `OSError` that escapes `main()` and the user sees a full Python
traceback — directly contradicting D-17's "no traceback" contract for user-facing
errors. The overwrite guard at line 45 only checks `exists()`, not writability.
**Fix:** Wrap the write in the same pattern used for the read:
```python
try:
    output_file.write_bytes(xlsx_bytes)
except OSError as exc:
    console.print(Panel(str(exc), title="File Write Error", border_style="red"))
    raise typer.Exit(1) from None
```

### WR-02: Candidate column lists are duplicated and can silently drift

**File:** `src/contaplus_reader/_reader.py:31-32` and `84-85`
**Issue:** The debe/haber candidate sets are declared **twice**: as module-level
tuples `_DEBE_COL_CANDIDATES` / `_HABER_COL_CANDIDATES` (lines 31-32), and again
as local literal sets `_DEBE` / `_HABER` inside `_assert_journal_shaped`
(lines 84-85). They currently match, but nothing enforces it. If a maintainer
adds a candidate (e.g. a third euro-era variant) to the module tuples, the shape
check at line 86 still runs against the stale local sets — so
`_assert_journal_shaped` and `_pick_column` can disagree: a DBF could pass the
shape check yet fail in `_pick_column` with the exact confusing "no debe column"
error the shape check exists to prevent (per the function's own docstring,
lines 60-64).
**Fix:** Derive from the single source of truth and delete the local literals:
```python
if not (field_set & set(_DEBE_COL_CANDIDATES)) or not (
    field_set & set(_HABER_COL_CANDIDATES)
):
```

### WR-03: `_assert_journal_shaped` does not verify the debe/haber columns are numeric

**File:** `src/contaplus_reader/_reader.py:59-95`
**Issue:** The shape check verifies FECHA exists *and has DBF type `D`* (line 72),
but for the debit/credit columns it only checks the **field name** is present
(line 86) — never the field type. A DBF with a character-typed field literally
named `DEBE` (`C(20)`) passes `_assert_journal_shaped`, `_pick_column` selects
it, then `float(record.get(debe_col) or 0)` raises `ValueError` on a non-numeric
string. That `ValueError` is caught at line 226 and surfaced as a generic
`"DBF read error: ..."` — exactly the confusing late failure the shape check
exists to prevent. The asymmetry (FECHA type-checked, amounts not) is a real
correctness gap for malformed inputs.
**Fix:** In `_assert_journal_shaped`, also assert the resolved debe/haber field
has a numeric type:
```python
numeric_types = {"N", "F"}
for kind, cands in (("debit", _DEBE_COL_CANDIDATES), ("credit", _HABER_COL_CANDIDATES)):
    matched = [c for c in cands if c in field_set]
    if not matched:
        raise ContaPlusReadError(row_index=-1, column=None,
            message=f"... no {kind} columns ...")
    if field_type_map.get(matched[0]) not in numeric_types:
        raise ContaPlusReadError(row_index=-1, column=None,
            message=f"{kind} column {matched[0]!r} is not numeric")
```

### WR-04: Amount null check relies on truthiness, treating any falsy value as missing

**File:** `src/contaplus_reader/_reader.py:152-153`
**Issue:** FECHA is checked explicitly with `is None` (lines 143-149), but amounts
use `float(record.get(debe_col) or 0)`. The `or` idiom treats **every falsy
value** as missing, not just `None`. For a journal debit/credit a `None` value
means the DBF field is absent or null — arguably as broken as a null FECHA — yet
here it is silently coerced to `0`, which then makes the row look like a both-zero
memo line (D-C3) and gets skipped instead of raising. The inconsistency (FECHA
explicit, amounts implicit) also obscures intent. It happens not to corrupt data
today only because a real `0` amount and the fallback `0` coincide.
**Fix:** Make the null handling explicit and deliberate per field:
```python
debe_raw = record.get(debe_col)
haber_raw = record.get(haber_col)
# Decide: is a null amount a broken row, or a legitimate zero?
debe = float(debe_raw) if debe_raw is not None else 0.0
haber = float(haber_raw) if haber_raw is not None else 0.0
```
If a null amount should be rejected, raise `ContaPlusReadError(column=debe_col)`
as is done for FECHA.

### WR-05: Reader catches only `(struct.error, ValueError, OSError)` — other dbfread errors escape as raw tracebacks

**File:** `src/contaplus_reader/_reader.py:226`
**Issue:** The outer fallback `except` catches `(struct.error, ValueError, OSError)`.
`dbfread`'s record iteration and field parsing can raise other exception types on
corrupted input — `KeyError`, `IndexError`, `AttributeError`, or `TypeError` from
internal field-parser code paths on a malformed header or unexpected field
descriptor. None of these are caught, so they propagate as a raw Python traceback,
violating the project contract that all reader failures surface as
`ContaPlusReadError` (D-04: "read() always raises ContaPlusReadError on invalid
data").
**Fix:** Add a final `Exception` fallback that re-wraps, while keeping the
specific handlers for clearer messages:
```python
except ContaPlusReadError:
    raise
except UnicodeDecodeError as exc:
    raise ContaPlusReadError(..., original=exc) from exc
except Exception as exc:  # struct.error, ValueError, OSError, and anything else
    raise ContaPlusReadError(
        row_index=-1, column=None,
        message=f"DBF read error: {type(exc).__name__}: {exc}",
        original=exc,
    ) from exc
```

### WR-06: XLSX renderer dereferences `wb.active` (`Worksheet | None`) without a guard

**File:** `src/contaplus_reader/xlsx.py:50-51`
**Issue:** `ws = wb.active` is typed `Worksheet | None` by openpyxl; the next line
does `ws.title = "Diario"` and all subsequent code dereferences `ws` with no
guard. For a fresh `Workbook()` `wb.active` is never `None` in practice so this
does not crash today, but it silently dereferences an `Optional`, which a strict
type checker (the project mandates strict typing — CLAUDE.md "Type safety") will
flag, and it leaves the invariant undocumented.
**Fix:** Add an explicit assertion that documents the invariant and satisfies the
type checker:
```python
ws = wb.active
assert ws is not None  # a fresh Workbook always has an active sheet
ws.title = "Diario"
```

## Info

### IN-01: Unused import and dead `TYPE_CHECKING` block in `__init__.py`

**File:** `src/contaplus_reader/__init__.py:14`, `27-28`
**Issue:** `import io` (line 14) is unused — nothing in `__init__.py` references
`io`. The `if TYPE_CHECKING: pass` block (lines 27-28) imports nothing and is
dead code; `TYPE_CHECKING` is imported only to gate an empty `pass`.
**Fix:** Delete `import io`, delete the `if TYPE_CHECKING: pass` block, and drop
`TYPE_CHECKING` from the `typing` import on line 15.

### IN-02: `ContaPlusReadError.__init_subclass__` override is a pure no-op

**File:** `src/contaplus_reader/models.py:57-58`
**Issue:** The `__init_subclass__` override only calls
`super().__init_subclass__(**kwargs)` and does nothing else — it is
indistinguishable from not defining it at all, and forces future readers to
inspect it to confirm it is inert.
**Fix:** Delete the `__init_subclass__` override unless a concrete reason to
intercept subclassing is documented.

### IN-03: `_pick_column` sets `column=kind` where `kind` is a category label, not a field name

**File:** `src/contaplus_reader/_reader.py:49-56`
**Issue:** On failure `_pick_column` raises `ContaPlusReadError(column=kind, ...)`
with `kind` being `"debe"` / `"haber"`. `models.py:48` documents `column` as
"field name or None when not row-specific". `"debe"` is a candidate *category*,
not necessarily a real DBF field name, and this is a file-level error
(`row_index=-1`). `_assert_journal_shaped` uses `column=None` for the same class
of file-shape error — the two are inconsistent.
**Fix:** Use `column=None` in the `_pick_column` error to match
`_assert_journal_shaped`, or document `column` as also accepting a category label.

### IN-04: Local `_DEBE` / `_HABER` use module-constant naming inside a function

**File:** `src/contaplus_reader/_reader.py:84-85`
**Issue:** The local variables `_DEBE` and `_HABER` use leading-underscore
"module-private constant" naming inside a function body, reading as if they were
module-level constants. Combined with WR-02 (duplication) this is a readability
trap.
**Fix:** Resolved naturally if WR-02 is applied (the locals are deleted).
Otherwise rename to plain locals such as `debit_names` / `credit_names`.

### IN-05: `Generator` imported from `typing` instead of `collections.abc`

**File:** `src/contaplus_reader/_bridge.py:13`
**Issue:** `from typing import Generator` is deprecated since Python 3.9. On
Python 3.13 (this project's minimum) the canonical import is
`from collections.abc import Generator`. `typing.Generator` still works but
triggers deprecation signals in strict tooling.
**Fix:** `from collections.abc import Generator`.

---

_Reviewed: 2026-05-15T16:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
