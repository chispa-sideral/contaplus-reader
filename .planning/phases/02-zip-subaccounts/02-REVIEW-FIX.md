---
phase: 02-zip-subaccounts
fixed_at: 2026-05-16T00:00:00Z
review_path: .planning/phases/02-zip-subaccounts/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 5
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-05-16T00:00:00Z
**Source review:** .planning/phases/02-zip-subaccounts/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (CR-01, CR-02, WR-01..WR-06)
- Fixed: 8
- Skipped: 5 (all Info findings — explicitly out of scope)

**Test suite:** `uv run pytest` — 81 passed, 0 failed. Confirmed after all fixes
applied (the suite gained 9 new tests across the fixes).

## Fixed Issues

### CR-01: Zip-slip guard bypassed on POSIX — back-slash entry names escape the temp dir

**Files modified:** `src/contaplus_reader/_zip.py`, `tests/conftest.py`, `tests/test_reader.py`
**Commit:** 22a0708
**Applied fix:** Rewrote `_safe_extract_zip` so the path that is validated is
byte-for-byte the path that is written. Members are no longer handed to
`zf.extract()` (which applies its own, differing sanitisation); each member is
copied via `zf.open(member)` + `shutil.copyfileobj` to the exact resolved path
that `target.relative_to(base)` checked. Directory entries are skipped. Added
`zip_slip_backslash_zip` (entry `..\..\evil.dbf`) and `zip_slip_absolute_zip`
(entry `/etc/passwd`) fixtures to `conftest.py`, plus
`test_read_zipslip_backslash_rejected` and `test_read_zipslip_absolute_rejected`
in `test_reader.py`.

### CR-02: `build_subcta_lookup` crashes when SUBCTA `cod`/`titulo` field is numeric

**Files modified:** `src/contaplus_reader/_subcta.py`, `tests/test_reader.py`
**Commit:** 05f4c11
**Applied fix:** Added an `_as_str` helper that coerces a dbfread field value to
a right-stripped `str`, mirroring the `isinstance(..., str)` guards in
`_reader.py` — `int`/`Decimal` values from numeric DBF fields are stringified
instead of crashing on `.rstrip()`. The lookup comprehension now uses
`rec.get(...)` + `_as_str(...)`. Added `AttributeError` and `TypeError` to the
`except` tuple as a backstop so any residual coercion failure surfaces as a
structured `ContaPlusReadError` (D-06). Added
`test_subcta_numeric_cod_field_no_crash` which builds a SUBCTA with a numeric
(`N`) `cod` field.

### WR-01: ZIP extraction recreates symlink entries — secondary traversal vector

**Files modified:** `src/contaplus_reader/_zip.py`
**Commits:** 22a0708, 723cd96
**Applied fix:** `_safe_extract_zip` now rejects any entry whose Unix mode bits
(`external_attr >> 16`, masked by `_S_IFMT = 0o170000`) equal
`_S_IFLNK = 0o120000`, raising `ContaPlusReadError` "Unsafe ZIP entry
(symlink)". Follow-up commit 723cd96 corrected the mask: the initial commit
used `stat.S_IFMT`, which is a *function* not a constant — the bitwise `&`
raised `TypeError`. Replaced with the inlined octal literals.

### WR-02: No decompression-size limit — zip-bomb can exhaust disk/memory

**Files modified:** `src/contaplus_reader/_zip.py`
**Commit:** 22a0708
**Applied fix:** `_safe_extract_zip` now validates the archive up-front: rejects
more than 10 000 entries, rejects a total uncompressed size over 500 MB, and
rejects any individual entry whose uncompressed/compressed ratio exceeds 200:1.
All three raise a structured `ContaPlusReadError` before any byte is written.

### WR-03: `_pick_column` called with two different `field_set` shapes — fragile

**Files modified:** `src/contaplus_reader/_reader.py`, `tests/test_reader.py`
**Commit:** 6a2041b
**Applied fix:** `_pick_column` is now case-insensitive internally — it builds a
lower-cased `{lower: original}` map of `field_set` and matches candidates in
lower case, returning the original-cased member so callers can still index
records directly. The docstring documents the contract. Both call sites
(`_reader.py`, `_subcta.py`) no longer depend on an unstated "caller
pre-lowercased the set" invariant. Added `test_pick_column_case_insensitive`
and `test_pick_column_raises_when_absent`.

### WR-04: SUBCTA enrichment silently mismatches on whitespace-padded keys

**Files modified:** `src/contaplus_reader/_subcta.py`, `src/contaplus_reader/_reader.py`, `tests/test_reader.py`
**Commit:** 0f4954b
**Applied fix:** Added an `_as_key` helper that fully strips (both ends) a
field value, used for the SUBCTA `cod` lookup key so it normalises identically
to the digit-only journal `subcuenta` key — a leading-space `cod` no longer
survives as an unmatchable key. `titulo` keeps right-strip-only (`_as_str`)
since it is display text. `_read_dbf_path` now counts journal rows whose
`subcuenta` is absent from a *non-empty* lookup and logs the miss count at INFO
so a near-total miss (a likely key-normalisation bug) is visible. Added
`test_subcta_lookup_whitespace_padded_cod_matches`.

### WR-05: `read_subcta_table` builds headers from row 0 only — ragged rows truncate columns

**Files modified:** `src/contaplus_reader/models.py`, `src/contaplus_reader/_subcta.py`, `src/contaplus_reader/xlsx.py`, `tests/test_xlsx.py`
**Commit:** f036267
**Applied fix:** `SubctaTable` gained a `headers: tuple[str, ...]` field
carrying the DBF field-name tuple (mirroring `GenericTable.headers`).
`read_subcta_table` captures it from `table.fields`. `_render_subcta_sheet`
now renders against `subcta.headers` instead of `subcta.rows[0].fields.keys()`,
so ragged rows cannot drop columns and a zero-row table still produces a styled
header row (this also removes the early-return empty-table branch flagged in
IN-03). Updated the existing `test_render_multi_sheet_names` to construct
`SubctaTable` with the new required `headers` field, and added
`test_subcta_sheet_headers_from_schema_not_row0` and
`test_subcta_sheet_empty_table_has_header_row`.

### WR-06: `cli.py` writes XLSX with no error handling — `render`/`write_bytes` crash leaks traceback

**Files modified:** `src/contaplus_reader/cli.py`, `tests/test_cli.py`
**Commit:** 6ff493d
**Applied fix:** Wrapped `render(data)` in a broad `try/except Exception`
(openpyxl raises a wide set) and `output_file.write_bytes(...)` in
`try/except OSError`. Both print a Rich panel ("XLSX Render Error" /
"File Write Error") to the stderr console and `raise typer.Exit(1) from None`,
honouring D-17's no-traceback contract. Added
`test_cli_unwritable_output_exits_nonzero` which points the output at a path
inside a non-existent directory to force an `OSError` on write.

## Skipped Issues

All five Info-tier findings were skipped — the fix scope for this run is
`critical_warning` (Critical + Warning only). They are listed here for
completeness; none were modified.

### IN-01: `render_journal` is dead-ish public API with no test of its own contract

**File:** `src/contaplus_reader/xlsx.py:77-90`
**Reason:** skipped — Info finding, out of scope for the critical_warning fix pass.
**Original issue:** `render_journal` is described as a backward-compatible alias
but is not exported in `__init__.py`'s `__all__`; intent (public vs internal)
should be decided.

### IN-02: `Any` used for `_autosize_columns` parameter type

**File:** `src/contaplus_reader/xlsx.py:174`
**Reason:** skipped — Info finding, out of scope for the critical_warning fix pass.
**Original issue:** `_autosize_columns(ws: Any)` should be annotated
`ws: Worksheet` (already imported); the project rule forbids `Any`.

### IN-03: `_render_subcta_sheet` empty-table branch sets `freeze_panes` on a sheet with no header

**File:** `src/contaplus_reader/xlsx.py:132-136`
**Reason:** skipped — Info finding, out of scope. Note: the WR-05 fix removed
the empty-table early-return branch entirely, so a zero-row SUBCTA now gets a
proper styled header row. The symptom IN-03 describes is effectively resolved
as a side effect of WR-05, but IN-03 itself was not separately addressed.
**Original issue:** The empty-table branch froze panes below a non-existent
header row.

### IN-04: Sniffer `seekable` fallback branches are effectively unreachable / over-engineered

**File:** `src/contaplus_reader/_sniffer.py:52-71`
**Reason:** skipped — Info finding, out of scope for the critical_warning fix pass.
**Original issue:** `sniff()` has stream-handling fallback logic that is dead
code because `read()` always normalises input to `bytes` before calling it.

### IN-05: `models.py` `ContaPlusReadError.__init_subclass__` override is a no-op

**File:** `src/contaplus_reader/models.py:57-58`
**Reason:** skipped — Info finding, out of scope for the critical_warning fix pass.
**Original issue:** The overridden `__init_subclass__` only calls `super()` —
dead boilerplate that can be removed.

---

_Fixed: 2026-05-16T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
