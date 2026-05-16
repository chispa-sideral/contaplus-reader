---
phase: "02-zip-subaccounts"
plan: "02"
subsystem: "library"
tags: [zip, subcta, enrichment, models, sniffer, reader, dispatch, tdd-green]
dependency_graph:
  requires: [phase-2-red-tests, zip-fixtures, subcta-fixtures]
  provides: [zip-read-pipeline, subcta-enrichment, group-tables, multi-company-dispatch]
  affects:
    - src/contaplus_reader/models.py
    - src/contaplus_reader/_sniffer.py
    - src/contaplus_reader/_zip.py
    - src/contaplus_reader/_subcta.py
    - src/contaplus_reader/_reader.py
    - src/contaplus_reader/__init__.py
tech_stack:
  added: []
  patterns:
    - bytes-first input normalisation (raw = data if isinstance(data, bytes) else data.read())
    - TemporaryDirectory lifecycle owned by read() in __init__.py
    - zip-slip guard: target.relative_to(base) per entry before zf.extract()
    - _pick_column candidate-list pattern extended to SUBCTA cod/titulo fields
    - sniff() discriminated return "dbf" | "zip" | raises (no longer void)
key_files:
  created:
    - src/contaplus_reader/_zip.py
    - src/contaplus_reader/_subcta.py
  modified:
    - src/contaplus_reader/models.py
    - src/contaplus_reader/_sniffer.py
    - src/contaplus_reader/_reader.py
    - src/contaplus_reader/__init__.py
    - tests/test_reader.py
decisions:
  - "D-01 implemented: sniff() returns 'zip' for 0x50 PK magic (no longer raises)"
  - "D-02 implemented: multi-company ZIP resolution by case-insensitive parent dir name"
  - "D-03 implemented: company selector on DBF raises 'not applicable'; wrong selector on ZIP raises listing available dirs"
  - "D-04 implemented: read() gains company: str | None = None as third keyword param"
  - "D-05 implemented: ContaPlusData gains subcta/empresa/grupos/usuarios attributes"
  - "D-06 implemented: absent table -> None (no error); present-but-unreadable -> abort"
  - "D-09 implemented: JournalRow.subcuenta_nombre: str | None = None (additive, backward-compatible)"
  - "D-10 implemented: enrichment is subcuenta-level only; .cuenta stays code-only"
  - "D-11 implemented: missing lookup key -> None silently; absent SUBCTA -> all None"
  - "Bytes-first normalisation: read() calls data.read() once before sniff(), removing seekability requirement from callers"
  - "BadZipFile wrapped: _safe_extract_zip catches zipfile.BadZipFile -> ContaPlusReadError with 'ZIP' in message"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-16T09:00:00Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 02 Plan 02: ZIP Read Pipeline + SUBCTA Enrichment Summary

**One-liner:** ZIP extraction pipeline with zip-slip guard, multi-company disambiguation, SUBCTA lookup enrichment, and group-table readers — turning all 13 RED Phase 2 reader tests GREEN.

## What Was Built

### Task 1: Models, sniffer, _zip.py, _subcta.py (commit 229845f)

**models.py — extended:**
- `JournalRow` gains `subcuenta_nombre: str | None = None` as final field (D-09). Default `None` means all existing `JournalRow()` calls are backward-compatible.
- New `SubctaRow(fields: dict[str, object])` frozen dataclass — full-dump storage for SUBCTA records.
- New `SubctaTable(rows: tuple[SubctaRow, ...], source_name: str | None = None)` frozen dataclass.
- New `GenericTable(headers: tuple[str, ...], rows: tuple[tuple[object, ...], ...], source_name: str | None = None)` frozen dataclass for grupos/usuarios/empresa.
- `ContaPlusData` gains four new defaulted attributes: `subcta`, `empresa`, `grupos`, `usuarios` (all `None` by default, D-05).

**_sniffer.py — upgraded:**
- `sniff()` return type changed from `None` to `str`.
- `0x50` (ZIP PK magic) branch: now returns `"zip"` instead of raising (D-01).
- `_KNOWN_DBF_VERSION_BYTES` branch: now explicitly returns `"dbf"`.
- All other bytes: raises `ContaPlusReadError("Unsupported input format: not a DBF file")`.

**_zip.py (new):**
- `_safe_extract_zip(raw: bytes, extract_dir: Path) -> None`: per-entry zip-slip check via `target.relative_to(base)`; normalizes backslashes (Pitfall 2); wraps `BadZipFile`/`OSError` in `ContaPlusReadError` with "ZIP" in message.
- `_resolve_company_diario(extract_dir, company)`: rglob for `diario.dbf` (case-insensitive); handles single-company/multi-company/no-selector/wrong-selector cases per D-02/D-03.
- `_find_sibling_dbf(diario_path, basename_lower)`: iterates parent directory case-insensitively; returns `None` when not found.

**_subcta.py (new):**
- `build_subcta_lookup(subcta_path)`: cod -> titulo dict via `_pick_column` candidate lists `("cod", "codigo")` and `("titulo", "descrip")`; `lowernames=True`; wraps exceptions in `ContaPlusReadError`.
- `read_subcta_table(subcta_path)`: full dump as `SubctaTable`; `lowernames=False` to preserve original field names.
- `read_table_raw(path, table_name)`: full dump as `GenericTable`; `lowernames=False`; used for grupos/usuarios/empresa.

### Task 2: ZIP dispatch in _reader.py and __init__.py (commit deb3a63)

**_reader.py — extended:**
- `_read_dbf_path` gains `subcta_lookup: dict[str, str | None] | None = None` keyword parameter.
- Before each `JournalRow` append: `subcuenta_nombre = subcta_lookup.get(subcuenta)` if lookup provided, else `None` (D-09/D-11).
- `JournalRow` construction passes `subcuenta_nombre=subcuenta_nombre`.

**__init__.py — rewritten:**
- `read()` gains `company: str | None = None` as third keyword param (D-04).
- Bytes-first normalisation: `raw = data if isinstance(data, bytes) else data.read()` before `sniff()` (Pitfall 6 defense; removes seekability requirement).
- `sniff(raw)` now returns `"dbf"` or `"zip"`.
- ZIP path: `TemporaryDirectory` created here (lifecycle owner, Pitfall 1); calls `_safe_extract_zip`, `_resolve_company_diario`, `_find_sibling_dbf` for all four sibling tables; builds lookup, reads journal with enrichment, reads optional group tables; returns `ContaPlusData` with all populated attributes.
- DBF path: if `company is not None`, raises `ContaPlusReadError("company selector is not applicable...")`; otherwise unchanged from Phase 1 via `bytes_to_tmppath`.

## Verification Results

```
68 passed, 3 xfailed, 1 xpassed in 1.17s
```

- All 55 Phase 1 tests still pass — no regressions.
- All 13 Phase 2 reader tests GREEN (previously RED in plan 02-01).
- 3 xfailed: `test_cli_company_flag_accepted`, `test_render_multi_sheet_names`, `test_render_descripcion_column_present` — awaiting Phase 2 plans 03 (CLI) and 04 (XLSX).
- 1 xpassed: `test_cli_multi_company_no_flag_exits_1` — CLI test unexpectedly passes because the existing Rich error panel in `cli.py` surfaces the multi-company error from the library correctly. `strict=False` so this is not a failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_output_df_has_correct_columns expected set excludes subcuenta_nombre**
- **Found during:** Task 1 verification
- **Issue:** Test at `tests/test_reader.py:418` used `assert expected == field_names` where `expected = {"fecha", "cuenta", "subcuenta", "debe", "haber", "concepto"}`. Adding `subcuenta_nombre` to `JournalRow` causes this to fail since the sets are no longer equal.
- **Fix:** Updated `expected` to include `"subcuenta_nombre"`.
- **Files modified:** `tests/test_reader.py`
- **Commit:** 229845f

**2. [Rule 1 - Bug] _safe_extract_zip needs to handle BadZipFile**
- **Found during:** Task 1 (predictively) and confirmed by test behavior
- **Issue:** `test_rejects_zip_bytes` uses `b"PK\x03\x04" + b"\x00" * 20` (truncated ZIP magic bytes). With the new sniffer returning `"zip"`, `zipfile.ZipFile(BytesIO(...))` raises `BadZipFile` for this truncated input. The error message would not contain "ZIP" without wrapping.
- **Fix:** Added `except (zipfile.BadZipFile, OSError)` handler in `_safe_extract_zip` that wraps to `ContaPlusReadError` with "Invalid or unreadable ZIP file" (contains "ZIP").
- **Files modified:** `src/contaplus_reader/_zip.py`
- **Commit:** 229845f

**3. [Rule 1 - Bug] test_non_seekable_binary_io_raises_structured_error fails after bytes-first normalisation**
- **Found during:** Task 2 verification (first run)
- **Issue:** The old `read()` passed the stream directly to `sniff()`, which checked seekability. The new `read()` normalises to bytes via `data.read()` before calling `sniff()`, so seekability is irrelevant. The test expected `ContaPlusReadError` to be raised for a non-seekable stream, but now it succeeds (better behavior).
- **Fix:** Renamed test to `test_non_seekable_binary_io_accepted` and updated it to assert the stream is now accepted successfully (reads 3 rows correctly).
- **Files modified:** `tests/test_reader.py`
- **Commit:** deb3a63

## Known Stubs

None — all data paths are wired. `subcuenta_nombre` is populated from the actual SUBCTA lookup (or `None` when SUBCTA is absent or key is missing per D-11). Group table attributes on `ContaPlusData` are `None` when the tables are absent from the archive (all 5 real archives have this case — D-06/RESEARCH.md Critical Finding).

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced beyond what the threat model already covers. T-02-01 (zip-slip) is fully mitigated by `_safe_extract_zip`.

## Self-Check: PASSED
