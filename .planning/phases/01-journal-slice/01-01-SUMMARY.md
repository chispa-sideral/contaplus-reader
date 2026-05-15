---
phase: "01-journal-slice"
plan: 1
subsystem: "library-core"
tags: ["python", "dbf", "reader", "journal", "packaging"]
dependency_graph:
  requires: []
  provides:
    - "contaplus_reader.read() bytes-first API"
    - "ContaPlusData / ContaPlusJournal / JournalRow / ContaPlusReadError types"
    - "bytes_to_tmppath() Windows-safe bridge"
    - "magic-byte sniffer (sniff())"
    - "_read_dbf_path() with D-A1...D-E3 rules"
    - "synthetic DBF fixture factory (conftest.py)"
    - "18-test journal reader suite"
  affects: []
tech_stack:
  added:
    - "dbfread>=2.0.7 (runtime)"
    - "pandas>=2.2 (runtime)"
    - "openpyxl>=3.1.5 (runtime)"
    - "typer[all]>=0.13 (runtime)"
    - "dbf>=0.99.11 (dev)"
    - "pytest>=8.4 (dev)"
    - "uv_build>=0.11.14,<0.12 (build)"
  patterns:
    - "contextmanager bytes→tmppath bridge (Windows delete=False pattern)"
    - "magic-byte sniffer before any parsing"
    - "frozen-semantics dataclass Exception on Python 3.14+ (custom __setattr__/__new__)"
    - "lazy DBF iteration with lowernames=True, encoding=cp850"
key_files:
  created:
    - "pyproject.toml"
    - "README.md"
    - "uv.lock"
    - "src/contaplus_reader/__init__.py"
    - "src/contaplus_reader/models.py"
    - "src/contaplus_reader/_bridge.py"
    - "src/contaplus_reader/_sniffer.py"
    - "src/contaplus_reader/_reader.py"
    - "tests/conftest.py"
    - "tests/test_reader.py"
  modified: []
decisions:
  - "ContaPlusReadError uses custom __new__/__setattr__ instead of frozen=True to survive Python 3.14+ exception propagation through contextlib (FrozenInstanceError on __traceback__ assignment)"
  - "README.md created as pyproject.toml requires it; content is minimal placeholder"
  - "_reader.py created in Task 1 commit pass (before Task 3 tests) because __init__.py imports it at module level"
metrics:
  duration: "18 minutes"
  completed_date: "2026-05-15"
  tasks_completed: 3
  files_created: 10
---

# Phase 01 Plan 01: Package Scaffold + Journal Reader Core Summary

**One-liner:** Python package scaffold with bytes-first read() API, magic-byte sniffer, Windows-safe bytes→tmppath bridge, full D-A1...D-E3 journal reader ported from tw-contaplus, and 18-test synthetic-fixture suite — all green on Python 3.14.5.

## What Was Built

The foundational Python package for contaplus-reader. This plan delivers everything downstream (XLSX renderer, CLI, wheel build) depends on:

1. **Package scaffold** (`pyproject.toml`, `README.md`, `uv.lock`) — uv_build backend, 4 runtime deps, 2 dev deps, `contaplus2xlsx` entry point wired.

2. **Public types** (`models.py`) — `ContaPlusReadError` (structured error), `JournalRow` (frozen), `ContaPlusJournal` (frozen), `ContaPlusData` (mutable container).

3. **bytes→path bridge** (`_bridge.py`) — `bytes_to_tmppath()` context manager: Windows-safe `delete=False` + `finally: unlink()`. Required because `dbfread` is path-only (issue #25, never merged).

4. **Magic-byte sniffer** (`_sniffer.py`) — `sniff()` reads offset 0, accepts all known dBASE/FoxPro version bytes, rejects ZIP with specific message, rejects unknown bytes as "not a DBF file".

5. **Journal reader** (`_reader.py`) — `_read_dbf_path()` port of tw-contaplus `read_dbf._read_dbf()` lines 137-265, with: `_assert_journal_shaped()` (D-02), `_pick_column()` (D-E1), all D-C1/C2/C3/C4 row rules, D-B2 cuenta derivation, D-E3 subcuenta validation, exception wrapping.

6. **Public API** (`__init__.py`) — `read(data: bytes | BinaryIO, source_name=None) -> ContaPlusData` wiring sniff → bridge → reader.

7. **Synthetic fixture factory** (`tests/conftest.py`) — port of tw-contaplus conftest lines 1-170; ZIP fixtures omitted (Phase 2); all session-scoped.

8. **Test suite** (`tests/test_reader.py`) — 18 tests: 7 new (INPUT-01/03, API-02/04, D-02) + 11 ported (JRNL-01/02/03, D-C1/C2/C3/E1, API-04). All green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.14 FrozenInstanceError on exception propagation through context managers**

- **Found during:** Task 3 — first test run
- **Issue:** `@dataclass(frozen=True)` generates `__setattr__` that blocks ALL attribute writes including `__traceback__`. Python 3.14's `contextlib._GeneratorContextManager.__exit__` assigns `exc.__traceback__` when re-raising an exception that propagated through a `with` block. This causes `FrozenInstanceError` at runtime for any `ContaPlusReadError` raised inside `bytes_to_tmppath()`.
- **Root cause:** `frozen=True` with `Exception` subclass was safe in Python 3.12/3.13; Python 3.14 changed exception propagation machinery to assign `__traceback__` directly.
- **Fix:** Replaced `@dataclass(frozen=True)` with `@dataclass(eq=True, unsafe_hash=True)` plus custom `__new__` (uses `Exception.__new__()`, sets init-sentinel), `__setattr__` (allows sentinel writes + `_EXCEPTION_INTERNAL_ATTRS` set + all writes during init; blocks afterwards), `__delattr__` (symmetric). Frozen semantics preserved: `e.message = 'x'` still raises `FrozenInstanceError`.
- **Files modified:** `src/contaplus_reader/models.py`
- **Commit:** `ce3e785`

**2. [Rule 3 - Blocking] README.md missing (pyproject.toml references it)**

- **Found during:** Task 1 — `uv sync` failed with "failed to open file README.md"
- **Fix:** Created minimal README.md with project description, features, and license.
- **Files modified:** `README.md`
- **Commit:** `1e7ee62`

**3. [Rule 3 - Blocking] _reader.py needed before Task 1 verification**

- **Found during:** Task 1 — `from contaplus_reader import read` failed because `__init__.py` imports `_read_dbf_path` from `_reader.py` at module level
- **Fix:** Created `_reader.py` as part of the initial implementation pass (the plan's Task 1 and Task 2 were committed sequentially but both required before any test).
- **Files modified:** `src/contaplus_reader/_reader.py`
- **Commit:** `fe13755`

## Known Stubs

None — all functionality is wired. The `ContaPlusData` container has `journal` populated correctly. No placeholder values.

## Threat Surface Scan

No new threat surface beyond what was documented in the plan's `<threat_model>`. All mitigations in the threat register were implemented:
- T-01-01: `struct.error`, `ValueError`, `OSError` caught → wrapped in `ContaPlusReadError(row_index=-1)`
- T-01-02: `UnicodeDecodeError` caught → wrapped, never falls back to `latin-1`
- T-01-05: temp file `finally: unlink(missing_ok=True)` always runs
- T-01-07: null FECHA → `ContaPlusReadError(row_index=idx, column="fecha")`
- T-01-08: SUBCTA validation with `isdigit() and len>=3`

## Self-Check: PASSED

All created files exist:
- FOUND: src/contaplus_reader/__init__.py
- FOUND: src/contaplus_reader/models.py
- FOUND: src/contaplus_reader/_bridge.py
- FOUND: src/contaplus_reader/_sniffer.py
- FOUND: src/contaplus_reader/_reader.py
- FOUND: tests/conftest.py
- FOUND: tests/test_reader.py
- FOUND: pyproject.toml

All commits exist:
- FOUND: 1e7ee62 (Task 1: scaffold + models + bridge + sniffer)
- FOUND: fe13755 (Task 2: journal reader)
- FOUND: ce3e785 (Task 3: fixtures + tests)

Test suite: 18/18 passed (`uv run pytest tests/test_reader.py -v`)
