---
phase: 01-journal-slice
verified: 2026-05-15T16:30:00Z
status: gaps_found
score: 11/15 must-haves verified
overrides_applied: 0
gaps:
  - truth: "A row with both-non-zero debe/haber raises ContaPlusReadError with row_index>=0"
    status: failed
    reason: "D-C2 guard is `if debe > 0 and haber > 0` — a row where debe=-10.0 and haber=50.0 is silently accepted, producing a JournalRow with both sides non-zero. CR-04 confirmed live: read() returns a journal with debe=-10.0, haber=50.0 with no error raised."
    artifacts:
      - path: "src/contaplus_reader/_reader.py"
        issue: "Line 157: `if debe > 0 and haber > 0` — should be `if debe != 0 and haber != 0` to catch mixed-sign both-non-zero rows"
    missing:
      - "Change guard to `if debe != 0 and haber != 0` in _reader.py line 157"
      - "Add test `test_negative_debe_positive_haber_raises` to test_reader.py"
  - truth: "CLI exits with code 1 and shows a Rich error panel when given invalid input"
    status: failed
    reason: "CR-02 confirmed live: when input file does not exist, `input_file.read_bytes()` raises FileNotFoundError (OSError subclass) which is not caught by the `except ContaPlusReadError` block. The CliRunner captures an unhandled FileNotFoundError exception, exit code is 1 but the error is a raw Python exception, not a Rich panel — violating D-17."
    artifacts:
      - path: "src/contaplus_reader/cli.py"
        issue: "Lines 52-54: `read(input_file.read_bytes(), ...)` is not wrapped in an OSError guard. FileNotFoundError and PermissionError propagate as unhandled exceptions."
    missing:
      - "Wrap `input_file.read_bytes()` in a try/except OSError block that prints a Rich error panel and raises typer.Exit(1) — same pattern as the ContaPlusReadError handler"
      - "Add test `test_cli_nonexistent_input_exits_nonzero` to test_cli.py asserting exit_code==1 and 'Traceback' not in output"
  - truth: "D-07: ContaPlusJournal.rows is list[JournalRow] frozen dataclasses — no pandas type in the public API surface"
    status: failed
    reason: "CR-03 confirmed live: ContaPlusJournal is @dataclass(frozen=True) but its `rows` field is `list[JournalRow]`. frozen=True blocks reassignment of the `rows` attribute itself but does NOT prevent mutation of the list contents. `journal.rows.append(bad_row)` succeeds silently. The D-07 contract ('frozen, fully static-typed') is not enforced at the data structure level."
    artifacts:
      - path: "src/contaplus_reader/models.py"
        issue: "Line 119: `rows: list[JournalRow]` — should be `tuple[JournalRow, ...]` to make the sequence immutable"
    missing:
      - "Change `rows: list[JournalRow]` to `rows: tuple[JournalRow, ...]` in ContaPlusJournal"
      - "Change `return ContaPlusJournal(rows=rows, ...)` to `rows=tuple(rows)` in _reader.py"
      - "Update test_xlsx.py `_make_journal` helper and any other caller that passes `rows=[...]` to use tuples"
  - truth: "read(non_seekable_BinaryIO) raises ContaPlusReadError (not raw OSError)"
    status: failed
    reason: "CR-01 confirmed live: `sniff()` uses `hasattr(data, 'seek')` to decide whether to seek back after reading 1 byte. CPython's io.RawIOBase subclasses always have a `seek` method even when non-seekable; calling `data.seek(0)` on a non-seekable stream raises `OSError: [Errno 29] Illegal seek`, which is not caught and propagates as a raw Python traceback — violating D-17 and the contract that all errors surface as ContaPlusReadError."
    artifacts:
      - path: "src/contaplus_reader/_sniffer.py"
        issue: "Line 47: `if hasattr(data, 'seek')` — should be `if hasattr(data, 'seekable') and data.seekable()` with fallback OSError catch wrapped into ContaPlusReadError"
    missing:
      - "Replace `hasattr(data, 'seek')` with `hasattr(data, 'seekable') and data.seekable()` check; add except OSError fallback that raises ContaPlusReadError"
---

# Phase 1: Journal Slice Verification Report

**Phase Goal:** A user can convert a journal-only `DIARIO.DBF` to a styled `.xlsx` by running `contaplus2xlsx DIARIO.DBF out.xlsx`
**Verified:** 2026-05-15T16:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                  | Status     | Evidence                                                                  |
| --- | -------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------- |
| 1   | `read(bytes_of_valid_dbf)` returns ContaPlusData with a non-empty `.journal`          | VERIFIED   | test_read_accepts_bytes passes; 50/50 suite green                         |
| 2   | `.journal.rows` contains JournalRow objects with all 6 fields                         | VERIFIED   | test_output_df_has_correct_columns passes; field_names == expected set    |
| 3   | `cuenta` is always `subcuenta[:4]` for every row (D-B2)                              | VERIFIED   | test_reads_cp850_basic_dbf asserts ["4300","7000","6000"]; code at line 184 |
| 4   | Both-zero rows are skipped and counted in journal.skipped_memo                        | VERIFIED   | test_both_zero_skips_silently_with_log passes; skipped_memo==1 asserted   |
| 5   | `read(zip_bytes)` raises ContaPlusReadError with "ZIP" in message                    | VERIFIED   | test_rejects_zip_bytes passes; sniffer detects 0x50 and emits ZIP message |
| 6   | `read(non_journal_dbf_bytes)` raises ContaPlusReadError with "not a DIARIO.DBF"      | VERIFIED   | test_non_journal_dbf_rejected passes; _assert_journal_shaped raises       |
| 7   | A row with null FECHA raises ContaPlusReadError with row_index>=0 and column='fecha' | VERIFIED   | D-C4 guard at _reader.py line 144-149                                     |
| 8   | A row with both-non-zero debe/haber raises ContaPlusReadError with row_index>=0       | FAILED     | D-C2 guard uses `> 0` not `!= 0`; row(-10, 50) silently accepted (CR-04) |
| 9   | No import from tw_domain anywhere in contaplus_reader                                 | VERIFIED   | grep finds zero matches; test_no_tw_domain_import passes                  |
| 10  | D-06: read() signature is `read(data: bytes | BinaryIO, source_name=None)` only      | VERIFIED   | inspect.signature confirms exact signature; no path arg                   |
| 11  | D-07: ContaPlusJournal.rows is immutable (frozen semantics)                           | FAILED     | `journal.rows.append(row)` succeeds — list is mutable (CR-03 confirmed)  |
| 12  | CLI produces styled .xlsx with journal rows from `contaplus2xlsx DIARIO.DBF out.xlsx` | VERIFIED  | Human-verify checkpoint APPROVED in 01-03 SUMMARY; 50/50 tests green; E2E confirmed |
| 13  | CLI rejects invalid .dbf with Rich error panel naming offending row and column         | FAILED     | FileNotFoundError path leaks raw exception, not Rich panel (CR-02)        |
| 14  | `uv build` produces a wheel; `uvx contaplus2xlsx` installs and runs from that wheel  | VERIFIED   | dist/contaplus_reader-0.1.0-py3-none-any.whl exists; confirmed by human checkpoint |
| 15  | Test suite uses synthetic blob-free fixtures; all ported tw-contaplus coverage passes | VERIFIED   | 0 .dbf files in tests/; 50/50 green; conftest.py generates at runtime    |

**Score:** 11/15 truths verified

### Required Artifacts

| Artifact                                    | Expected                                      | Status      | Details                                                        |
| ------------------------------------------- | --------------------------------------------- | ----------- | -------------------------------------------------------------- |
| `pyproject.toml`                            | Package config, uv_build, entry points, deps  | VERIFIED    | uv_build backend, 4 runtime deps, contaplus2xlsx entry point  |
| `src/contaplus_reader/__init__.py`          | read() API, public type re-exports            | VERIFIED    | Exports all 5 public names; correct signature                 |
| `src/contaplus_reader/models.py`            | ContaPlusData/Journal/Row/ReadError types     | PARTIAL     | CR-03: rows field is mutable list, not tuple                  |
| `src/contaplus_reader/_bridge.py`           | bytes_to_tmppath() context manager            | VERIFIED    | delete=False + finally unlink; Windows-safe                   |
| `src/contaplus_reader/_sniffer.py`          | sniff() magic-byte validator                  | PARTIAL     | CR-01: uses hasattr(seek) not data.seekable() — OSError leaks |
| `src/contaplus_reader/_reader.py`           | _read_dbf_path() with D-A1..D-E3 rules       | PARTIAL     | CR-04: D-C2 guard `> 0` misses mixed-sign both-non-zero rows  |
| `src/contaplus_reader/xlsx.py`              | render_journal(ContaPlusJournal) -> bytes     | VERIFIED    | Returns bytes; Spanish headers; accounting format; freeze_panes |
| `src/contaplus_reader/cli.py`               | Typer app with contaplus2xlsx entry point     | PARTIAL     | CR-02: FileNotFoundError not caught; raw exception propagates |
| `tests/conftest.py`                         | Synthetic DBF fixture factory                 | VERIFIED    | _DIARIO_SPEC present; fixtures session-scoped; no blobs       |
| `tests/test_reader.py`                      | 18+ reader tests covering JRNL/INPUT/API      | VERIFIED    | 18 tests; all required categories covered                     |
| `tests/test_xlsx.py`                        | XLSX renderer tests (19 tests)                | VERIFIED    | 19 tests; bytes output, headers, styling, formats all covered |
| `tests/test_cli.py`                         | CLI argument + exit-code tests (13 tests)     | PARTIAL     | No test for missing-input-file FileNotFoundError (IN-03/CR-02) |
| `dist/contaplus_reader-0.1.0-py3-none-any.whl` | Installable wheel                         | VERIFIED    | File exists; uvx smoke test confirmed in human checkpoint     |
| `README.md`                                 | Minimal project description                   | VERIFIED    | Installation, Usage, License sections present                 |
| `.gitignore`                                | Ignores dist/, pii-test-data/, etc.           | VERIFIED    | pii-test-data/ and dist/ confirmed present                    |

### Key Link Verification

| From                              | To                           | Via                                 | Status      | Details                                               |
| --------------------------------- | ---------------------------- | ----------------------------------- | ----------- | ----------------------------------------------------- |
| `__init__.py`                     | `_sniffer.py`                | `sniff(data)` before bytes_to_tmppath | WIRED     | Line 56: `sniff(data)` call confirmed                 |
| `__init__.py`                     | `_bridge.py`                 | `bytes_to_tmppath` context manager  | WIRED       | Line 57: `with bytes_to_tmppath(data) as path:`       |
| `_reader.py`                      | `models.py`                  | ContaPlusReadError raised on invalid rows | WIRED  | Multiple raise sites confirmed in reader              |
| `tests/test_reader.py`            | `tests/conftest.py`          | cp850_basic_dbf and diario_dbf_builder fixtures | WIRED | Both fixtures imported and used in tests        |
| `cli.py`                          | `__init__.py`                | `read(input_file.read_bytes(), ...)` | WIRED      | Line 53: wired correctly                              |
| `cli.py`                          | `xlsx.py`                    | `render_journal(data.journal)`       | WIRED       | Line 68: wired correctly                              |

### Data-Flow Trace (Level 4)

| Artifact       | Data Variable    | Source                        | Produces Real Data | Status    |
| -------------- | ---------------- | ----------------------------- | ------------------ | --------- |
| `cli.py`       | `data.journal`   | `read(input_file.read_bytes())` → `_read_dbf_path()` → DBF iteration | Yes — real dbfread records | FLOWING |
| `xlsx.py`      | `journal.rows`   | ContaPlusJournal passed from reader | Yes — validated JournalRow objects | FLOWING |

### Behavioral Spot-Checks

| Behavior                                            | Command                                                    | Result                                    | Status  |
| --------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------- | ------- |
| 50-test suite passes                                | `uv run pytest tests/ -v`                                  | 50 passed in 0.82s                        | PASS    |
| CR-03: rows list is mutable                         | `journal.rows.append(row)` succeeds                        | len becomes 2 — no error raised           | FAIL    |
| CR-04: mixed-sign both-non-zero row accepted        | `read(dbf_with_debe=-10_haber=50)` returns journal         | debe=-10.0, haber=50.0 accepted silently  | FAIL    |
| CR-01: non-seekable BinaryIO raises raw OSError     | `read(NonSeekableStream(valid_bytes))`                     | OSError: Illegal seek (not ContaPlusReadError) | FAIL |
| CR-02: missing input file leaks raw exception       | `runner.invoke(app, ['/nonexistent/DIARIO.DBF', out])`     | exit_code=1, exception=FileNotFoundError  | FAIL    |
| Wheel exists                                        | `ls dist/*.whl`                                            | contaplus_reader-0.1.0-py3-none-any.whl  | PASS    |
| No binary .dbf blobs in tests/                      | `ls tests/*.dbf`                                           | 0 files                                   | PASS    |
| No tw_domain import in src/                         | grep -r tw_domain src/                                     | No matches                                | PASS    |
| read() API signature correct (D-06)                 | `inspect.signature(read)`                                  | `(data: bytes | BinaryIO, source_name=None)` | PASS |

### Probe Execution

No probe scripts declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description                                                         | Status   | Evidence                                                                |
| ----------- | ----------- | ------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------- |
| INPUT-01    | Plan 01     | Reader accepts bytes or BinaryIO (no filesystem path)               | SATISFIED | test_read_accepts_bytes, test_read_accepts_binary_io pass              |
| INPUT-03    | Plan 01     | Reader sniffs input type and rejects unsupported with structured error | PARTIAL | ZIP, unknown bytes rejected. Non-seekable BinaryIO raises raw OSError (CR-01) |
| JRNL-01     | Plan 01     | Extracts validated journal rows with all required fields            | SATISFIED | test_reads_cp850_basic_dbf, test_output_df_has_correct_columns pass    |
| JRNL-02     | Plan 01     | Handles cp850, trailing-whitespace, deleted records, both-zero memo, negatives | SATISFIED | All D-C1/C3/E1/deleted-record/encoding tests pass              |
| JRNL-03     | Plan 01     | Rejects invalid rows with structured per-row error                  | PARTIAL  | Null FECHA rejected. Both-non-zero check misses mixed-sign case (CR-04) |
| API-01      | Plan 01     | Single bytes-first read API used by all consumers                   | SATISFIED | read() is the sole entry point; wired to CLI and usable from PWA       |
| API-02      | Plan 01     | Strict read path fails loudly with row/column/context               | PARTIAL  | ContaPlusReadError carries row_index + column. CR-04 means one invalid shape accepted silently |
| API-04      | Plan 01     | Self-contained result types, no tw_domain dependency                | SATISFIED | No tw_domain import; test_no_tw_domain_import passes                   |
| XLSX-01     | Plan 02     | Styled workbook with one sheet per extracted table                  | SATISFIED | render_journal() produces Diario sheet with full styling               |
| XLSX-04     | Plan 02     | Renderer callable identically from CLI and PWA (returns bytes)      | SATISFIED | render_journal() returns bytes; no filesystem assumption                |
| CLI-01      | Plan 02     | contaplus2xlsx converts .dbf to styled .xlsx                        | SATISFIED | test_cli_happy_path passes; human E2E checkpoint approved              |
| CLI-04      | Plan 02/03  | CLI installable and runnable via uvx/pipx                           | SATISFIED | dist/*.whl exists; uvx smoke test confirmed in human checkpoint        |
| TEST-01     | Plan 01     | Synthetic blob-free fixtures generated at test-collection time      | SATISFIED | conftest.py generates DBFs via dbf library; zero .dbf blobs in tests/  |
| TEST-02     | Plan 01     | Ported tw-contaplus journal-reader coverage passing                 | SATISFIED | 18 reader tests pass, all porting targets covered per PATTERNS.md list  |
| DIST-02     | Plan 03     | uv build produces a wheel                                           | SATISFIED | dist/contaplus_reader-0.1.0-py3-none-any.whl confirmed                 |

### Anti-Patterns Found

| File                              | Line | Pattern                                               | Severity    | Impact                                                    |
| --------------------------------- | ---- | ----------------------------------------------------- | ----------- | --------------------------------------------------------- |
| `src/contaplus_reader/_reader.py` | 157  | `if debe > 0 and haber > 0:` — incomplete D-C2 guard | BLOCKER     | Mixed-sign both-non-zero rows silently accepted; CR-04    |
| `src/contaplus_reader/_sniffer.py`| 47   | `hasattr(data, "seek")` — wrong seekable check        | BLOCKER     | Non-seekable streams crash with raw OSError; CR-01        |
| `src/contaplus_reader/cli.py`     | 52   | `input_file.read_bytes()` unguarded from OSError      | BLOCKER     | FileNotFoundError leaks as raw exception; D-17 violated   |
| `src/contaplus_reader/models.py`  | 119  | `rows: list[JournalRow]` on frozen dataclass          | BLOCKER     | D-07 immutability contract not enforced; CR-03            |
| `src/contaplus_reader/__init__.py`| 27   | `if TYPE_CHECKING: pass` dead code block              | INFO        | Dead code; remove TYPE_CHECKING import and the pass block |
| `tests/conftest.py`               | 164  | `counter = {"n": 0}` Python 2 closure workaround      | INFO        | Project targets Python >=3.13; use `nonlocal`             |
| `src/contaplus_reader/xlsx.py`    | 74   | `len(str(c.value or ""))` — 0.0 treated as empty      | WARNING     | Numeric-zero cells contribute 0 to column width; may truncate Haber column in Excel |

### Human Verification Required

None — the phase gate's human-verify checkpoint (Plan 03, Task 2) was already completed and APPROVED. That checkpoint verified: E2E CLI conversion, overwrite guard, error panel, XLSX structure, and uvx wheel smoke test.

The gaps identified above are code-level bugs verifiable programmatically — they do not require further human testing to classify. They do require fixing.

---

## Gaps Summary

Four blockers were found, all documented in the code review (01-REVIEW.md) and confirmed against the live codebase:

**CR-04 (JRNL-03, API-02):** The D-C2 guard `if debe > 0 and haber > 0` does not reject rows where one amount is negative and the other is positive. A row with `debe=-10.0, haber=50.0` — both sides non-zero — is silently accepted and produces a `JournalRow` with both `debe` and `haber` non-zero. No downstream consumer (including tax-workbench) is designed to handle such rows. This directly undermines the "journal reader rejects invalid rows" success criterion.

**CR-02 (CLI-01, D-17):** The CLI does not catch `OSError` (including `FileNotFoundError`) from `input_file.read_bytes()`. When the user supplies a path to a non-existent file — one of the most common user errors — the CLI propagates a raw Python exception instead of the required Rich error panel. D-17 is violated.

**CR-03 (D-07):** `ContaPlusJournal.rows` is typed as `list[JournalRow]` on a `frozen=True` dataclass. `frozen=True` blocks reassignment of the `rows` attribute itself, but the list's contents remain fully mutable. `journal.rows.append(...)`, `journal.rows.clear()`, and `journal.rows[0] = bad_row` all succeed silently. For a library feeding tax filings, silent data mutation is the worst failure mode.

**CR-01 (INPUT-03, D-17):** The `sniff()` function uses `hasattr(data, "seek")` to decide whether to seek back after reading 1 byte. All CPython `io.RawIOBase` subclasses have a `seek` method regardless of whether the underlying stream is seekable. On a pipe or socket-backed stream, `data.seek(0)` raises `OSError: [Errno 29] Illegal seek`, which propagates unhandled as a raw traceback — violating the requirement that all errors surface as `ContaPlusReadError`.

The primary phase goal — `contaplus2xlsx DIARIO.DBF out.xlsx` produces a styled xlsx — is functional for the happy path (confirmed by human checkpoint). The blockers affect error-handling correctness and data-integrity contracts, not the happy-path conversion flow.

---

_Verified: 2026-05-15T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
