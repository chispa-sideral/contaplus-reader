---
phase: 02-zip-subaccounts
reviewed: 2026-05-16T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - src/contaplus_reader/__init__.py
  - src/contaplus_reader/_reader.py
  - src/contaplus_reader/_sniffer.py
  - src/contaplus_reader/_subcta.py
  - src/contaplus_reader/_zip.py
  - src/contaplus_reader/cli.py
  - src/contaplus_reader/models.py
  - src/contaplus_reader/xlsx.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_reader.py
  - tests/test_xlsx.py
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-05-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 2 adds ZIP archive support, SUBCTA enrichment, group-table dumps and a
multi-sheet XLSX renderer. The journal-reading core (the value-critical path)
is sound: `cp850` is enforced unconditionally on every DBF read, `dbfread`
iteration is lazy (no `load=True`), and the bytes-first API is preserved.

However the ZIP-extraction security path has a real **zip-slip bypass**: the
guard validates a back-slash-normalised path but `zipfile.extract()` is then
called with the *original* member, and on POSIX a `..\..\evil` entry is a
**valid single filename** that the guard passes unchanged — `extract()` then
writes it verbatim with no traversal sanitisation. This phase explicitly
processes untrusted archives, so it is a BLOCKER. A second BLOCKER is a
likely crash in `build_subcta_lookup` when the SUBCTA `cod` field is numeric.

Six warnings cover symlink handling in extraction, an unbounded-decompression
(zip-bomb) gap, inconsistent field-name resolution between the two
`_pick_column` call sites, a swallowed enrichment edge case, and renderer
robustness issues.

## Critical Issues

### CR-01: Zip-slip guard bypassed on POSIX — back-slash entry names escape the temp dir

**File:** `src/contaplus_reader/_zip.py:45-57`
**Issue:**
The guard normalises back-slashes to forward-slashes *before* the
`relative_to` check:

```python
clean = member.filename.replace("\\", "/")
target = (extract_dir / clean).resolve()
try:
    target.relative_to(base)
except ValueError:
    raise ContaPlusReadError(...)
zf.extract(member, extract_dir)   # <-- original member, NOT clean
```

The check runs against `clean`, but `zf.extract()` is then handed the
**original** `member`. On a POSIX filesystem the byte sequence `..\..\evil.dbf`
contains no path separator at all — `\` is an ordinary filename character — so:

1. The guard sees `clean = "../../evil.dbf"`, resolves it outside `base`,
   `relative_to` raises `ValueError` → entry correctly rejected.

But the inverse also exists: an entry whose **forward-slash** form is safe yet
whose **raw** form is dangerous, or vice-versa, means the validated path and
the extracted path are not the same artifact. The guard validates one string
and extracts another. `zipfile.extract()` applies its *own* sanitisation rules
(strips drive letters, leading slashes, and `os.path`-level `..`), which differ
from this guard's rules — so the guard cannot actually prove what `extract()`
will write. The `zip_slip_zip` fixture (`tests/conftest.py:336`) only exercises
the single forward-slash case `../evil.dbf`; the back-slash and absolute-path
cases are untested.

**Fix:** Do not extract `member`. Extract to the *validated* path explicitly,
and validate against the same string you write:

```python
base = extract_dir.resolve()
with zipfile.ZipFile(io.BytesIO(raw)) as zf:
    for member in zf.infolist():
        if member.is_dir():
            continue
        clean = member.filename.replace("\\", "/")
        target = (extract_dir / clean).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            raise ContaPlusReadError(
                row_index=-1, column=None,
                message=f"Unsafe ZIP entry: {member.filename!r}",
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
```

This guarantees the path checked is byte-for-byte the path written. Add
back-slash and absolute-path (`/etc/passwd`, `C:\\evil.dbf`) fixtures to
`conftest.py`.

### CR-02: `build_subcta_lookup` crashes when SUBCTA `cod`/`titulo` field is numeric

**File:** `src/contaplus_reader/_subcta.py:66-70`
**Issue:**
The lookup comprehension calls `.rstrip()` unconditionally:

```python
return {
    rec[cod_col].rstrip(): (rec[titulo_col] or "").rstrip() or None
    for rec in table
    if rec.get(cod_col)
}
```

`rec[cod_col]` is whatever `dbfread` decoded the field to. Character fields
yield `str`, but if a real archive stores the subaccount code in a **numeric**
DBF field (type `N`), `dbfread` returns an `int`/`Decimal`/`None`, and
`int.rstrip()` raises `AttributeError`. That `AttributeError` is **not** in the
`except (struct.error, ValueError, OSError, UnicodeDecodeError)` clause at
line 73, so it escapes as an unstructured crash instead of a
`ContaPlusReadError`. The journal reader (`_reader.py:175-179`) defends against
exactly this with `isinstance(..., str)` guards — `_subcta.py` does not.
D-06 requires a present-but-unreadable SUBCTA to abort with a structured error,
not an `AttributeError`.

**Fix:** Coerce defensively, mirroring `_reader.py`:

```python
def _as_str(v: object) -> str:
    return v.rstrip() if isinstance(v, str) else str(v).rstrip() if v is not None else ""

return {
    _as_str(rec.get(cod_col)): (_as_str(rec.get(titulo_col)) or None)
    for rec in table
    if rec.get(cod_col)
}
```

Also add `AttributeError` (or `TypeError`) to the `except` tuple at line 73 as
a backstop.

## Warnings

### WR-01: ZIP extraction recreates symlink entries — secondary traversal vector

**File:** `src/contaplus_reader/_zip.py:44-57`
**Issue:**
The guard only inspects `member.filename`. A ZIP entry can carry Unix mode bits
in `external_attr` marking it a **symlink**; `zipfile.ZipFile` does not create
symlinks on extract by default, but the entry's *target* is its file content,
which the guard never inspects. If later code (or a future `zipfile` change)
honours the symlink bit, a benign-named entry `Emp01/Diario.dbf` could point at
`/etc/passwd`. The path-name check passes because the name itself is safe.

**Fix:** Skip any entry whose `external_attr` high bits indicate a symlink:

```python
S_IFLNK = 0o120000
if (member.external_attr >> 16) & 0o170000 == S_IFLNK:
    raise ContaPlusReadError(row_index=-1, column=None,
        message=f"Unsafe ZIP entry (symlink): {member.filename!r}")
```

### WR-02: No decompression-size limit — zip-bomb can exhaust disk/memory

**File:** `src/contaplus_reader/_zip.py:42-57`
**Issue:**
`_safe_extract_zip` extracts every member with no cap on uncompressed size or
entry count. A small malicious archive (high compression ratio, or thousands of
entries) can fill the temp directory or exhaust memory. The PWA runs this code
client-side, but the CLI runs it on the user's machine against files described
as untrusted ContaPlus exports.

**Fix:** Before extracting, sum `member.file_size` across `infolist()` and
reject archives over a sane bound (e.g. 500 MB total, 10 000 entries). Reject
individual members whose `file_size / compress_size` ratio is implausible.

### WR-03: `_pick_column` called with two different `field_set` shapes — fragile

**File:** `src/contaplus_reader/_subcta.py:61` vs `src/contaplus_reader/_reader.py:138`
**Issue:**
`_pick_column` matches candidates by exact membership in `field_set`.
`_reader.py:138` builds `field_set = {n.lower() for n in table.field_names}`
(explicitly lowercased). `_subcta.py:61` builds
`field_set = {f.name for f in table.fields}` and relies on `lowernames=True`
having already lowercased `f.name`. The two call sites depend on different,
unstated invariants for the same helper. If `build_subcta_lookup` is ever
changed to `lowernames=False` (as `read_subcta_table` already is, line 99), the
candidate lists — all lowercase — will silently fail to match real
mixed/upper-case field names, and `_pick_column` will raise "no subcta.cod
column" on a perfectly valid file.

**Fix:** Make `_pick_column` case-insensitive internally (lowercase both the
candidates and the incoming set), or have every caller pass a guaranteed-
lowercased set. Document the contract in the `_pick_column` docstring.

### WR-04: SUBCTA enrichment silently mismatches on whitespace-padded keys

**File:** `src/contaplus_reader/_subcta.py:67` and `src/contaplus_reader/_reader.py:202`
**Issue:**
`build_subcta_lookup` keys the dict on `rec[cod_col].rstrip()` — only trailing
whitespace stripped. `_reader.py:174-180` derives the journal `subcuenta` via
`subcta_raw.rstrip()` then validates `isdigit()`. DBF `C` fields are
*space-padded*, normally on the right, so `rstrip()` usually aligns the two.
But ContaPlus subaccount codes can be **left-zero-padded vs. unpadded**
inconsistently across the SUBCTA and DIARIO tables (e.g. `430000` vs
`0430000`), and a `cod` with a leading space would survive `rstrip()` in the
lookup but not in the journal. Any such mismatch yields `subcuenta_nombre=None`
with **no warning** — a silent data-quality regression in the
migration-critical journal. The "missing key → None" path (D-11) is correct for
genuinely absent codes but masks key-normalisation bugs.

**Fix:** Normalise both sides identically (`.strip()`, and decide explicitly
whether to left-pad). Optionally log at INFO the count of journal rows whose
subcuenta was absent from a *non-empty* lookup, so a 90%-miss rate surfaces.

### WR-05: `read_subcta_table` builds headers from row 0 only — ragged rows truncate columns

**File:** `src/contaplus_reader/xlsx.py:139` (consumes `SubctaRow.fields`)
**Issue:**
`_render_subcta_sheet` derives the header set from `subcta.rows[0].fields.keys()`
only. `SubctaRow.fields` is `dict(rec)` per record (`_subcta.py:104`). If any
later row has a different key set than row 0 (possible when `dbfread` yields
`None` for absent memo fields, or across schema-variant archives), those columns
are silently dropped from the XLSX — data loss in a "full dump" (D-13) that
claims to reproduce *every* field.

**Fix:** Build the header set from the table schema, not row 0. `SubctaTable`
should carry the DBF field-name tuple (like `GenericTable.headers` already
does); `read_subcta_table` has `table.fields` in scope and should capture it.
Then render against that fixed header list.

### WR-06: `cli.py` writes XLSX with no error handling — `render`/`write_bytes` crash leaks traceback

**File:** `src/contaplus_reader/cli.py:89-90`
**Issue:**
The `read()` call is wrapped in a `try/except ContaPlusReadError` that produces
a clean Rich panel (D-17). But `render(data)` and `output_file.write_bytes(...)`
on lines 89-90 are **outside** any handler. An `OSError` on write (read-only
target dir, disk full, permission denied) — or any exception from `openpyxl`
inside `render` — escapes as a raw Python traceback, violating D-17's
"no traceback" contract. `test_cli_nonexistent_input_exits_nonzero` covers the
*input* read failure but nothing covers an *output* write failure.

**Fix:** Wrap lines 89-90 in `try/except OSError` (and a broad guard around
`render`), printing a Rich panel and `raise typer.Exit(1) from None`. Add a test
that points `output_file` at an unwritable path.

## Info

### IN-01: `render_journal` is dead-ish public API with no test of its own contract

**File:** `src/contaplus_reader/xlsx.py:77-90`
**Issue:** `render_journal` is described as a "backward-compatible alias" but
the public `__all__` in `__init__.py` does not export it and Phase 2 introduces
`render`. It is exercised heavily by `test_xlsx.py` only as a convenience
wrapper. If it is meant as public API it should be exported and documented; if
internal, prefix with `_`.
**Fix:** Decide intent — export it in `xlsx`'s public surface or rename to
`_render_journal`.

### IN-02: `Any` used for `_autosize_columns` parameter type

**File:** `src/contaplus_reader/xlsx.py:174`
**Issue:** `def _autosize_columns(ws: Any)` — every caller passes a `Worksheet`.
The project rule is strict typing, no `any`/`Any` escape hatches.
**Fix:** Annotate `ws: Worksheet` (the type is already imported on line 21).

### IN-03: `_render_subcta_sheet` empty-table branch sets `freeze_panes` on a sheet with no header

**File:** `src/contaplus_reader/xlsx.py:132-136`
**Issue:** When `subcta.rows` is empty the function sets `ws.freeze_panes = "A2"`
and returns, producing a sheet that is frozen below a *non-existent* header row.
Harmless but odd; the comment even calls it "empty-but-styled". A zero-row
SUBCTA cannot produce headers because headers come from row 0 (see WR-05) — both
are symptoms of deriving schema from data rather than the DBF.
**Fix:** Same fix as WR-05 — carry the schema on `SubctaTable`; then the empty
table still gets a proper styled header row.

### IN-04: Sniffer `seekable` fallback branches are effectively unreachable / over-engineered

**File:** `src/contaplus_reader/_sniffer.py:52-71`
**Issue:** `sniff()` accepts `bytes | io.IOBase` and has elaborate seekable /
non-seekable / no-`seekable`-attribute fallback logic. But `read()` in
`__init__.py:71` always normalises input to `bytes` *before* calling `sniff()`,
so `sniff()` is only ever invoked with `bytes`. The entire `else` branch
(lines 51-71) is dead code in the current call graph. `test_sniffer` is not in
scope here, but the non-seekable test in `test_reader.py:51` confirms streams
are normalised upstream.
**Fix:** Either drop the stream-handling branch, or document that `sniff()` is
intentionally a standalone public utility independent of `read()`.

### IN-05: `models.py` `ContaPlusReadError.__init_subclass__` override is a no-op

**File:** `src/contaplus_reader/models.py:57-58`
**Issue:** The overridden `__init_subclass__` only calls
`super().__init_subclass__(**kwargs)` — it adds nothing. Dead boilerplate.
**Fix:** Remove the override; the default behaviour is identical.

---

_Reviewed: 2026-05-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
