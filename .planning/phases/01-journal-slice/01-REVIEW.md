---
phase: 01-journal-slice
reviewed: 2026-05-15T15:46:35Z
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
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-05-15T15:46:35Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the complete Phase 1 journal-slice implementation: library core (`_bridge.py`,
`_reader.py`, `_sniffer.py`, `models.py`), public API (`__init__.py`), CLI (`cli.py`),
XLSX renderer (`xlsx.py`), and the full test suite.

The encoding policy (cp850 unconditionally), the journal business rules (D-C1 through
D-E3), and the bytes-first API are correctly implemented. The temp-file bridge uses
`delete=False` + `finally` unlink, which is the right Windows-safe pattern.

Four blockers require immediate attention: a crash on non-seekable BinaryIO input
(unhandled `OSError` from `seek(0)`), unhandled `FileNotFoundError` in the CLI leaking
a raw Python traceback, a mutable `list` on a frozen dataclass breaking the D-07
immutability contract for `ContaPlusJournal.rows`, and a D-C2 logic gap where a row
with `(debe < 0, haber > 0)` bypasses the both-non-zero rejection. Five warnings
cover: zero-value column width underestimation in XLSX, the missing `data.seekable()`
check before seek, an unconstrained `data.read()` for streaming BinaryIO, a dead-code
`if TYPE_CHECKING: pass` block, and the `ContaPlusReadError` freeze bypass via sentinel.

---

## Critical Issues

### CR-01: Non-seekable BinaryIO crashes with unhandled OSError instead of ContaPlusReadError

**File:** `src/contaplus_reader/_sniffer.py:47-48`

**Issue:** `sniff()` checks `hasattr(data, "seek")` to decide whether to seek back after
reading 1 byte. On CPython, all `io.RawIOBase` and `io.BufferedIOBase` subclasses define
a `seek` method even when the underlying stream is non-seekable (e.g., stdin pipe,
`socket.makefile()`). Calling `data.seek(0)` on a non-seekable stream raises
`OSError: [Errno 29] Illegal seek`, which is not caught anywhere in the call chain and
propagates as a raw Python traceback — violating D-17 and the contract that all errors
surface as `ContaPlusReadError`.

The correct check is `data.seekable()`, which returns `False` for pipes/sockets without
raising. Additionally, even if `seek(0)` succeeds, if it silently no-ops (some custom
IO implementations), `bytes_to_tmppath` then calls `data.read()` from offset 1, writing
a truncated file to the temp path and producing a corrupted DBF parse.

**Fix:**
```python
# _sniffer.py
if hasattr(data, "seekable") and data.seekable():
    data.seek(0)
elif hasattr(data, "seek"):
    try:
        data.seek(0)
    except OSError:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message="Input stream is not seekable; provide bytes or a seekable BinaryIO",
        )
```

---

### CR-02: CLI leaks raw FileNotFoundError traceback when input file does not exist

**File:** `src/contaplus_reader/cli.py:53`

**Issue:** `input_file.read_bytes()` raises `FileNotFoundError` (a subclass of `OSError`)
when the input path does not exist. This exception is not caught by the surrounding
`except ContaPlusReadError` block, so it propagates as a raw Python traceback to the
terminal — directly violating D-17 ("ContaPlusReadError is shown as a Rich error panel
with no traceback; exits 1").

The same problem applies to `PermissionError` (e.g., file exists but is not readable).
Both are common user errors that deserve a clean error message, not a traceback.

**Fix:**
```python
# cli.py
try:
    raw_bytes = input_file.read_bytes()
except OSError as exc:
    console.print(
        Panel(
            str(exc),
            title="File Read Error",
            border_style="red",
        )
    )
    raise typer.Exit(1) from None

try:
    data = read(raw_bytes, source_name=str(input_file))
except ContaPlusReadError as exc:
    ...
```

---

### CR-03: ContaPlusJournal.rows is a mutable list on a frozen dataclass — D-07 contract broken

**File:** `src/contaplus_reader/models.py:119`

**Issue:** `ContaPlusJournal` is declared `@dataclass(frozen=True)`, and D-07 states rows
are "frozen, fully static-typed dataclasses." `frozen=True` prevents reassignment of
`rows` itself (`journal.rows = []` raises `FrozenInstanceError`), but it does NOT prevent
mutation of the list contents:

```python
journal.rows.append(bad_row)   # silently succeeds
journal.rows.clear()           # silently succeeds
journal.rows[0] = bad_row      # silently succeeds
```

`tax-workbench` and other consumers that rely on `journal.rows` being immutable after
construction will be silently corrupted by any intermediate code that mutates the list.
Since this library feeds tax filings, silent data mutation is the worst failure mode.

**Fix:** Use a tuple for `rows`, or convert to tuple at construction time.

```python
# models.py
@dataclass(frozen=True)
class ContaPlusJournal:
    rows: tuple[JournalRow, ...]   # immutable sequence
    skipped_memo: int = 0
    source_name: str | None = None
```

Then in `_reader.py`, change:
```python
return ContaPlusJournal(
    rows=tuple(rows),   # was: rows=rows
    skipped_memo=skipped_memo,
    source_name=source_name,
)
```

And update any test code that constructs `ContaPlusJournal(rows=[...])` to use `rows=(...)`.

---

### CR-04: D-C2 check does not reject rows where one side is negative and the other is positive

**File:** `src/contaplus_reader/_reader.py:157`

**Issue:** The D-C2 rule is documented as "both-non-zero debe+haber -> ContaPlusReadError".
The code implements:

```python
if debe > 0 and haber > 0:
    raise ContaPlusReadError(...)
```

The comment says this is intentional ("uses > 0, NOT != 0 — Pitfall 2 — negatives must
pass through per D-C1"). However, a row where `debe = -10.0` and `haber = 50.0` has BOTH
values non-zero: both a debit and a credit are populated simultaneously. This is equally
non-standard double-entry bookkeeping as the `(50, 50)` case. The current logic accepts
`(-10, 50)` silently, producing a `JournalRow` where both `debe` and `haber` are
non-zero, which no downstream consumer (including tax-workbench) is designed to handle.

The correct reading of "negatives pass through per D-C1" is that a row like `(-10, 0)` or
`(0, -50)` is a valid correction/reversal; a row with BOTH sides non-zero (regardless of
sign) is always invalid. The D-C2 check should be sign-agnostic:

**Fix:**
```python
# Both non-zero regardless of sign is invalid (D-C2).
# D-C1 negatives: (-10, 0) or (0, -50) pass through; (-10, 50) is still both-non-zero.
if debe != 0 and haber != 0:
    raise ContaPlusReadError(
        row_index=idx,
        column=None,
        message=f"both-non-zero row: debe={debe}, haber={haber}",
    )
```

Note: this change requires the existing test `test_negative_debe_passes_through` to
remain passing (it uses `eurodebe=-1.0, eurohaber=0.0` — one side is zero, so it still
passes). A new test `test_negative_debe_positive_haber_raises` should be added.

---

## Warnings

### WR-01: sniff() does not handle non-seekable streams before bytes_to_tmppath reads them

**File:** `src/contaplus_reader/_sniffer.py:46-48` / `src/contaplus_reader/__init__.py:56-57`

**Issue:** Separate from the OSError crash (CR-01), there is a data integrity gap: even
when `seek(0)` succeeds for a seekable stream, `sniff()` uses `hasattr(data, "seek")`
rather than `data.seekable()`. Streams that are seekable will work. But the two-step
protocol (`sniff(data)` then `bytes_to_tmppath(data)`) requires that the stream position
is reset to 0 after `sniff` reads 1 byte. If the `seek(0)` call in `sniff` is skipped or
fails silently, `bytes_to_tmppath` reads from offset 1 onward, producing a DBF missing
its first byte (its version byte) — which will then be misread or fail to parse, and the
error message will be confusing.

**Fix:** Use `data.seekable()` as the canonical check (see CR-01 fix). Add an assertion
or test that verifies `bytes_to_tmppath` receives the full stream.

---

### WR-02: xlsx.py column autofit uses `c.value or ""` which treats 0.0 as empty

**File:** `src/contaplus_reader/xlsx.py:74`

**Issue:** The column-width calculation is:

```python
max_len = max((len(str(c.value or "")) for c in col_cells), default=0)
```

`0.0 or ""` evaluates to `""` (because `0.0` is falsy in Python), so any cell holding
the value `0.0` contributes `0` to the width calculation instead of `len("0.00") = 4`.
In a journal where many rows have `haber=0.0` (debit-only rows), the Haber column width
is calculated from the concepto header length only, and numeric cells may be truncated
in Excel's display (showing `######`).

**Fix:**
```python
max_len = max(
    (len(str("" if c.value is None else c.value)) for c in col_cells),
    default=0,
)
```

Or more explicitly:
```python
def _cell_display_len(v: object) -> int:
    return 0 if v is None else len(str(v))

max_len = max((_cell_display_len(c.value) for c in col_cells), default=0)
```

---

### WR-03: bytes_to_tmppath reads BinaryIO into memory without size limit

**File:** `src/contaplus_reader/_bridge.py:31`

**Issue:** `raw: bytes = data if isinstance(data, bytes) else data.read()` calls
`data.read()` with no size limit. For an untrusted or malformed BinaryIO that does not
terminate (e.g., a network socket in file mode, or a generator-backed IO), this hangs
indefinitely. For a very large stream it exhausts available memory. There is no
`ContaPlusReadError` raised — the process either hangs or is killed by the OS.

While the project description targets desktop/local use and the bytes path already
requires the caller to hold the full bytes in memory, a safeguard prevents the library
from becoming a denial-of-service vector when consumed via the future PWA worker bridge
(where `BinaryIO` might wrap a network stream).

**Fix:** Apply a size cap when reading from BinaryIO:

```python
_MAX_DBF_BYTES = 256 * 1024 * 1024  # 256 MB — well above any realistic journal

raw: bytes
if isinstance(data, bytes):
    raw = data
else:
    raw = data.read(_MAX_DBF_BYTES + 1)
    if len(raw) > _MAX_DBF_BYTES:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Input exceeds maximum supported size ({_MAX_DBF_BYTES // 1024 // 1024} MB)",
        )
```

---

### WR-04: ContaPlusReadError freeze can be bypassed by setting the init sentinel

**File:** `src/contaplus_reader/models.py:70-78`

**Issue:** The sentinel flag name `_contaplus_init_` is stored as a module-level constant
`_INIT_SENTINEL` and exposed via the instance `__dict__`. Any code can bypass the
freeze protection by setting this sentinel directly:

```python
exc = ContaPlusReadError(message="original")
object.__setattr__(exc, "_contaplus_init_", True)
exc.message = "tampered"   # succeeds, no FrozenInstanceError
object.__delattr__(exc, "_contaplus_init_")
```

For a library producing tax-filing data, silent mutation of error objects (which carry
`row_index` and `column` that determine which data is accepted or rejected) is a
correctness risk. A consuming module that receives a `ContaPlusReadError` and "corrects"
the `row_index` to hide a real data error would be undetectable.

**Fix:** Use a private name that is harder to guess, or use `object.__setattr__` guarded
by a check against the class's `__dataclass_fields__` keys — setting any declared field
outside of `__init__` raises unconditionally, without relying on a sentinel in
`__dict__`:

```python
def __setattr__(self, name: str, value: object) -> None:
    if name in _EXCEPTION_INTERNAL_ATTRS:
        object.__setattr__(self, name, value)
        return
    # Only allow writes to declared fields during dataclass __init__,
    # detected by whether the instance has any declared fields yet.
    if not any(
        k in self.__dict__
        for k in _dataclasses.fields(self.__class__)
        if k not in _EXCEPTION_INTERNAL_ATTRS
    ):
        object.__setattr__(self, name, value)
        return
    raise _dataclasses.FrozenInstanceError("cannot assign to field " + repr(name))
```

Alternatively, accept this as a known limitation of the custom approach and document it.

---

### WR-05: _reader.py does not catch all exceptions that dbfread can raise during iteration

**File:** `src/contaplus_reader/_reader.py:226-232`

**Issue:** The outer `except` block catches `(struct.error, ValueError, OSError)`. During
record iteration, `dbfread`'s `FieldParser` can raise `UnicodeDecodeError` (already
caught at line 219), but the `_decode_text` method in dbfread also uses the configured
encoding, and an unexpected field type or corrupted field data could raise
`AttributeError` or `TypeError` from the internal `field_parser`. These are not in the
caught set and would propagate as unhandled exceptions — producing a raw traceback
instead of a `ContaPlusReadError`.

**Fix:** Extend the catch clause to cover `Exception` as a final fallback, re-wrapping
as `ContaPlusReadError`:

```python
except (ContaPlusReadError, UnicodeDecodeError):
    raise
except Exception as exc:
    raise ContaPlusReadError(
        row_index=-1,
        column=None,
        message=f"Unexpected DBF read error: {type(exc).__name__}: {exc}",
        original=exc,
    ) from exc
```

---

## Info

### IN-01: Dead code — empty `if TYPE_CHECKING: pass` block in `__init__.py`

**File:** `src/contaplus_reader/__init__.py:27-28`

**Issue:** The `if TYPE_CHECKING: pass` block imports nothing and serves no purpose. It
was likely left over from a scaffolding step.

**Fix:** Remove lines 27-28 entirely, and remove the `TYPE_CHECKING` import from line 15.

---

### IN-02: `diario_dbf_builder` fixture uses mutable dict workaround instead of nonlocal

**File:** `tests/conftest.py:164-170`

**Issue:** The `counter = {"n": 0}` / `counter["n"] += 1` pattern is a Python 2
workaround for the absence of `nonlocal`. The project targets Python >=3.13 where
`nonlocal` is standard. This is misleading to future contributors.

**Fix:**
```python
def diario_dbf_builder(...):
    counter = 0

    def _build(rows):
        nonlocal counter
        counter += 1
        target_dir = tmp_path_factory.mktemp(f"custom_{counter}")
        ...

    return _build
```

---

### IN-03: test_cli.py does not test that a missing input file produces a clean error

**File:** `tests/test_cli.py` (missing test)

**Issue:** The CLI has no guard around `input_file.read_bytes()` (see CR-02). There is no
test that invokes the CLI with a path to a non-existent file and asserts that the exit
code is 1 and no traceback appears in output. Without this test, CR-02 will not be caught
by the test suite.

**Fix:** Add a test:
```python
def test_cli_nonexistent_input_exits_nonzero(tmp_path: Path) -> None:
    """CLI must exit non-zero cleanly when the input file does not exist."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(tmp_path / "no_such_file.dbf"), str(out)])
    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "Traceback" not in combined
```

---

_Reviewed: 2026-05-15T15:46:35Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
