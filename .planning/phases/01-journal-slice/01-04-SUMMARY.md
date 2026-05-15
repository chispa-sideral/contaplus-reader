---
phase: 01-journal-slice
plan: "04"
subsystem: library-core
tags: [gap-closure, error-handling, immutability, tdd]
dependency_graph:
  requires: [01-03]
  provides: [INPUT-03, JRNL-03, API-02, CLI-01]
  affects: [models.py, _reader.py, _sniffer.py, cli.py, xlsx.py]
tech_stack:
  added: []
  patterns:
    - "tuple[JournalRow, ...] immutable result model"
    - "seekable() check before stream seek"
    - "OSError split-try guard in CLI"
    - "None-safe column width: `'' if c.value is None else c.value`"
key_files:
  created: []
  modified:
    - src/contaplus_reader/_reader.py
    - src/contaplus_reader/_sniffer.py
    - src/contaplus_reader/models.py
    - src/contaplus_reader/cli.py
    - src/contaplus_reader/xlsx.py
    - tests/test_reader.py
    - tests/test_cli.py
    - tests/test_xlsx.py
decisions:
  - "CR-04: != 0 guard replaces > 0; mixed-sign both-non-zero rows (e.g. debe=-10, haber=50) now correctly rejected"
  - "CR-01: data.seekable() replaces hasattr(data, 'seek'); non-seekable streams raise ContaPlusReadError not raw OSError"
  - "CR-03: rows: tuple[JournalRow, ...] on ContaPlusJournal; list accumulator kept internally, tuple() at construction"
  - "CR-02: split try-block approach — OSError guard around read_bytes(), existing ContaPlusReadError guard unchanged"
  - "WR-02: None-explicit check in autofit avoids 0.0 being coerced to empty string by 'or' operator"
  - "test assertion for typer.Exit: result.exception is SystemExit(1), not None — plan's assertion corrected to isinstance check"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-15"
  tasks_completed: 5
  files_modified: 8
---

# Phase 01 Plan 04: Gap Closure — Four Blocker Fixes Summary

Closes all four blockers from VERIFICATION.md that left requirements INPUT-03, JRNL-03, API-02, and CLI-01 PARTIAL after Plan 03. Adds 5 new tests (50 → 55); `uv run pytest` exits 0.

## What Was Built

Five targeted fixes to close four VERIFICATION.md blockers and one WARNING-level xlsx bug:

1. **CR-04** (`_reader.py`): Mixed-sign both-non-zero guard changed from `> 0` to `!= 0`. A row with `debe=-10.0, haber=50.0` previously slipped through; it now correctly raises `ContaPlusReadError`.

2. **CR-01** (`_sniffer.py`): Non-seekable `BinaryIO` previously propagated raw `OSError` from `seek(0)`. Now uses `data.seekable()` to detect and raise `ContaPlusReadError("Input stream is not seekable...")` before attempting the seek. Safety fallback wraps `OSError` for streams lacking `seekable()`.

3. **CR-03** (`models.py`, `_reader.py`): `ContaPlusJournal.rows` type changed from `list[JournalRow]` to `tuple[JournalRow, ...]`. List accumulator in `_read_dbf_path` unchanged; `tuple(rows)` wraps at construction. `_make_journal` helper in `test_xlsx.py` updated.

4. **CR-02** (`cli.py`): Introduced two sequential try blocks — first guards `raw_bytes = input_file.read_bytes()` with `except OSError`, showing a Rich "File Read Error" panel and raising `typer.Exit(1)`; second block (unchanged) handles `ContaPlusReadError`. No raw `FileNotFoundError` now propagates to the user.

5. **WR-02** (`xlsx.py`): One-line fix in the autofit loop — `c.value or ""` replaced by `"" if c.value is None else c.value`. Zero values (`0.0`) now contribute their string length to column width calculation instead of being silently treated as empty.

## Tests Added

| Test | File | Covers |
|------|------|--------|
| `test_negative_debe_positive_haber_raises` | test_reader.py | CR-04: (-10, 50) raises |
| `test_non_seekable_binary_io_raises_structured_error` | test_reader.py | CR-01: non-seekable BinaryIO → ContaPlusReadError |
| `test_journal_rows_is_immutable_tuple` | test_reader.py | CR-03: isinstance(rows, tuple), append raises |
| `test_cli_nonexistent_input_exits_nonzero` | test_cli.py | CR-02: exit 1, no Traceback, no raw OSError |
| `test_column_width_not_truncated_by_zero_values` | test_xlsx.py | WR-02: Haber column width > 0 with haber=0.0 data |

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: CR-04 | `744bbef` | Fix mixed-sign both-non-zero guard to use != 0 |
| Task 2: CR-01 | `f0ded91` | Fix non-seekable BinaryIO crash in sniffer |
| Task 3: CR-03 | `96e57c7` | Make ContaPlusJournal.rows immutable tuple |
| Task 4: CR-02 | `30d36d1` | Guard CLI read_bytes() against OSError |
| Task 5: WR-02 | `f106121` | Fix column width undercount for zero numeric values |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TDD RED test for CR-02 required an extra iteration**

- **Found during:** Task 4 RED phase
- **Issue:** The initial test only checked `exit_code == 1` and no Traceback, which passed trivially because CliRunner catches all exceptions. The plan's acceptance criteria required `result.exception is None`, but Typer's `raise typer.Exit(1)` always produces `SystemExit(1)` in CliRunner — not `None`.
- **Fix:** Added stronger assertion `isinstance(result.exception, SystemExit)` when exception is present, ensuring the raw `FileNotFoundError` is no longer leaking. Refined the test to properly fail RED before the implementation.
- **Files modified:** `tests/test_cli.py`
- **Commit:** `30d36d1`

## Known Stubs

None — all five fixes are complete implementations with test coverage.

## Threat Flags

None — all four threat mitigations from the plan's STRIDE register were applied:
- T-04-01 (rows tamper): CR-03 tuple makes rows immutable post-construction
- T-04-02 (non-seekable DoS): CR-01 wraps OSError as ContaPlusReadError
- T-04-03 (mixed-sign bypass): CR-04 != 0 closes the mixed-sign loophole
- T-04-04 (traceback disclosure): CR-02 wraps OSError in Rich panel, no stack frames

## Self-Check: PASSED

Files exist:
- `src/contaplus_reader/_reader.py` — FOUND, contains `if debe != 0 and haber != 0`
- `src/contaplus_reader/_sniffer.py` — FOUND, contains `data.seekable()`
- `src/contaplus_reader/models.py` — FOUND, contains `rows: tuple[JournalRow, ...]`
- `src/contaplus_reader/cli.py` — FOUND, contains `except OSError as exc`
- `src/contaplus_reader/xlsx.py` — FOUND, contains `"" if c.value is None else c.value`

Commits verified:
- `744bbef`, `f0ded91`, `96e57c7`, `30d36d1`, `f106121` — all in git log

Test count: 55 tests, 0 failures (`uv run pytest -v` exits 0)
