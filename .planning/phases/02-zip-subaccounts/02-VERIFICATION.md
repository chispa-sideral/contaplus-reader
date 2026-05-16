---
phase: 02-zip-subaccounts
verified: 2026-05-16T12:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run contaplus2xlsx against a real ContaPlus backup .zip from pii-test-data"
    expected: "XLSX produced with Diario sheet where Descripción column is populated for recognized subaccount codes; Subcuentas sheet present with all SUBCTA fields"
    why_human: "Synthetic SUBCTA fixture uses C(12) character fields. pii-test-data confirms this schema, but end-to-end rendering with real data volume and real field ordering cannot be verified programmatically without reading pii-test-data (which is confidential and gitignored)."
  - test: "Open the generated XLSX and verify Descripción values are non-empty for known subaccounts"
    expected: "Descripción column in Diario sheet shows subaccount names (not blank) for subcuenta codes present in SUBCTA.DBF"
    why_human: "Visual spot-check of rendered cell values in real XLSX output; cannot open Excel programmatically in this environment."
  - test: "Run contaplus2xlsx on a pii-test-data ZIP without --company (if multi-company archive exists)"
    expected: "Exit code 1; Rich error panel lists the actual company directory names from the archive"
    why_human: "Real multi-company archive behavior; pii-test-data content is confidential."
---

# Phase 2: ZIP & Subaccounts Verification Report

**Phase Goal:** A user can convert a full ContaPlus backup `.zip` — including SUBCTA enrichment of the journal — to a multi-sheet `.xlsx`
**Verified:** 2026-05-16T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `contaplus2xlsx backup.zip out.xlsx` produces a `.xlsx` with journal sheet where account names are populated from `SUBCTA.DBF` | VERIFIED | `render(data)` in `cli.py:89` consumes `ContaPlusData` with `subcuenta_nombre` populated; `xlsx.py` writes col 4 as `jr.subcuenta_nombre`; confirmed via manual end-to-end test with synthetic fixtures (see Behavioral Spot-Checks) |
| 2 | Multi-company ZIP without `--company` flag exits with error listing available company names | VERIFIED | `_resolve_company_diario` raises `ContaPlusReadError("Multi-company ZIP: pass --company to select one of ['Emp01', 'Emp02']")`; CLI surfaces via Rich panel; `test_cli_multi_company_no_flag_exits_1` passes; confirmed live: `"Emp01" in msg and "Emp02" in msg` |
| 3 | ZIP extraction rejects a path-traversal entry (zip-slip attack) with a structured error | VERIFIED with WARNING | `_safe_extract_zip` raises `ContaPlusReadError("Unsafe ZIP entry: '../evil.dbf'")` for the tested `../evil.dbf` forward-slash entry; confirmed live. The guard validates `clean` (backslash-normalised) path then extracts original `member` — a structural design flaw identified in CR-01. However, Python `zipfile` normalises member filenames to forward slashes before exposing them, so `clean == member.filename` in all cases Python's own API can produce — no practical bypass exists on Python 3.14. Untested attack vectors: backslash-only entries (POSIX-created ZIPs), symlink entries (WR-01). Test assertion uses an OR condition (`"Unsafe ZIP entry" OR "ZIP"`) so it would also pass for BadZipFile errors — the specific zip-slip behavior is confirmed correct by direct message inspection. |
| 4 | `.xlsx` includes sheets for `SUBCTA`, `grupos`, `usuarios`, and `empresa` when present | VERIFIED | `render()` in `xlsx.py:63-70` creates sheets conditionally; confirmed via live test: `['Diario', 'Subcuentas', 'Empresa', 'Grupos', 'Usuarios']` all present when all DBF siblings exist |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/contaplus_reader/_zip.py` | `_safe_extract_zip`, `_resolve_company_diario`, `_find_sibling_dbf` | VERIFIED | All three functions exist, are substantive, and are imported by `__init__.py` |
| `src/contaplus_reader/_subcta.py` | `build_subcta_lookup`, `read_subcta_table`, `read_table_raw` | VERIFIED | All three functions exist, substantive; wired via `from contaplus_reader._subcta import ...` in `__init__.py` |
| `src/contaplus_reader/models.py` | `JournalRow.subcuenta_nombre`, `ContaPlusData` with subcta/empresa/grupos/usuarios, `SubctaTable`, `GenericTable`, `SubctaRow` | VERIFIED | All present and populated correctly |
| `src/contaplus_reader/_sniffer.py` | `sniff()` returns `"dbf"` or `"zip"` | VERIFIED | Returns `"zip"` for `0x50` magic, `"dbf"` for known DBF version bytes |
| `src/contaplus_reader/__init__.py` | `read()` dispatches on fmt; ZIP path with TemporaryDirectory; `company` param | VERIFIED | Full ZIP dispatch path present; `company` param wired through to `_resolve_company_diario` |
| `src/contaplus_reader/xlsx.py` | `render(data: ContaPlusData) -> bytes`; `HEADERS` with `Descripción` | VERIFIED | `render()` present; `HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]` |
| `src/contaplus_reader/cli.py` | `--company` option; calls `render(data)` | VERIFIED | `company: Annotated[str | None, typer.Option("--company", ...)] = None`; `render(data)` called at line 89 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__init__.py` | `_zip.py` | `from contaplus_reader._zip import _safe_extract_zip, _resolve_company_diario, _find_sibling_dbf` | WIRED | Import confirmed at `__init__.py:24`; all three functions called in ZIP dispatch path |
| `__init__.py` | `_subcta.py` | `from contaplus_reader._subcta import build_subcta_lookup, read_subcta_table, read_table_raw` | WIRED | Import confirmed at `__init__.py:23`; all three called in ZIP dispatch path (lines 85-87, 101-107) |
| `_reader.py` | `models.py` | `subcuenta_nombre` field on `JournalRow` | WIRED | `_read_dbf_path` accepts `subcta_lookup` param; populates `subcuenta_nombre = subcta_lookup.get(subcuenta)` at line 202; passed to `JournalRow(...)` at line 213 |
| `cli.py` | `xlsx.py` | `from contaplus_reader.xlsx import render` | WIRED | Import inside `main()` at `cli.py:48`; `render(data)` called at `cli.py:89` |
| `cli.py` | `__init__.py` | `read(raw_bytes, source_name=..., company=company)` | WIRED | `company=company` passed at `cli.py:75`; wires CLI flag to library dispatch |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cli.py` | `data` (ContaPlusData) | `read(raw_bytes, ...)` → `_safe_extract_zip` → `_read_dbf_path` | Yes — dbfread iterates real DBF records | FLOWING |
| `xlsx.py` `render()` | `journal.rows` | `ContaPlusData.journal.rows` tuple of `JournalRow` | Yes — populated by `_read_dbf_path` from actual DBF | FLOWING |
| `xlsx.py` `_render_journal_sheet` | `jr.subcuenta_nombre` | `subcta_lookup.get(subcuenta)` from `build_subcta_lookup(subcta_path)` | Yes — reads real SUBCTA.DBF; returns `None` when key absent | FLOWING |
| `xlsx.py` `_render_subcta_sheet` | `subcta.rows[0].fields.keys()` | `read_subcta_table()` → `dbfread.DBF` iteration | Yes — reads real SUBCTA records | FLOWING; WARNING: headers derived from row 0 only (WR-05) |
| `xlsx.py` `_render_generic_sheet` | `table.headers`, `table.rows` | `read_table_raw()` → `dbfread.DBF` | Yes — reads real grupo/usuario/empresa records | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ZIP with SUBCTA → subcuenta_nombre populated | `read(zip_bytes)` → check `rows[0].subcuenta_nombre` | `"Cliente XYZ"` | PASS |
| Multi-company ZIP without selector → error listing names | `read(multi_zip_bytes)` → check error | `"Emp01" in msg and "Emp02" in msg` | PASS |
| Path-traversal entry `../evil.dbf` → structured error | `read(zip_slip_bytes)` → check error | `"Unsafe ZIP entry: '../evil.dbf'"` | PASS |
| All 5 table sheets in XLSX when all DBFs present | `render(data)` → check sheetnames | `['Diario', 'Subcuentas', 'Empresa', 'Grupos', 'Usuarios']` | PASS |
| `--company` flag accepted and passes company to read | CLI invocation with `--company Emp01` | `exit_code == 0` | PASS |
| `sniff()` returns `"zip"` for `PK` magic | `sniff(b"PK\x03\x04")` | `"zip"` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| INPUT-02 | 02-01, 02-02, 02-03 | Reader accepts `.zip` as bytes or file-like | SATISFIED | `read()` dispatches on `sniff()` returning `"zip"`; `test_read_zip_bytes` and `test_read_zip_filelike` pass |
| INPUT-04 | 02-01, 02-02 | ZIP extraction is zip-slip-safe | SATISFIED (with caveat) | `_safe_extract_zip` rejects `../evil.dbf`; CR-01 design flaw acknowledged but no practical bypass on Python 3.14 |
| INPUT-05 | 02-01, 02-02 | Recursively locates tables regardless of nesting depth | SATISFIED | `_resolve_company_diario` uses `extract_dir.rglob("*")` to find `diario.dbf` at any depth |
| INPUT-06 | 02-01, 02-02 | Multi-company ZIP disambiguated by company selector | SATISFIED | `_resolve_company_diario` handles single/multi-company cases; error lists available names; `test_read_multi_company_selected` and `test_read_multi_company_no_selector` pass |
| TABL-01 | 02-01, 02-02, 02-03 | Typed SUBCTA.DBF reader with defensive field-name resolution | SATISFIED | `build_subcta_lookup` uses `_pick_column` with candidates `("cod", "codigo")` and `("titulo", "descrip")`; `test_subcta_candidate_fallback` passes with alternate field names |
| TABL-02 | 02-01, 02-02, 02-03 | Typed readers for grupos/usuarios/empresa | SATISFIED | `read_table_raw()` handles all three; `test_usuarios_present_in_result` passes; all appear in XLSX |
| API-05 | 02-01, 02-02, 02-03 | Journal enriched with account names when SUBCTA present | SATISFIED | `JournalRow.subcuenta_nombre` populated via `subcta_lookup.get(subcuenta)`; `test_subcta_lookup_correct` and `test_subcta_lookup_missing_key` pass |
| CLI-02 | 02-01, 02-03 | CLI selects company in multi-company backup via flag | SATISFIED | `--company` option in `cli.py:30-36`; passed to `read()` at `cli.py:75`; `test_cli_company_flag_accepted` passes |

**Traceability note:** REQUIREMENTS.md traceability table maps `CLI-02 | Phase 4 | Complete`. The ROADMAP.md Phase 2 requirements section includes CLI-02, and both 02-01-PLAN.md and 02-03-PLAN.md claim it. The implementation is in Phase 2. The traceability table has an incorrect phase number (4 instead of 2) — this is a documentation inconsistency, not an implementation gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/contaplus_reader/_subcta.py` | 67 | `rec[cod_col].rstrip()` — no `isinstance(str)` guard | WARNING (CR-02) | `AttributeError` crash when SUBCTA `cod` field is numeric (`N` type) instead of character (`C` type); `AttributeError` escapes `except (struct.error, ValueError, OSError, UnicodeDecodeError)` clause; violates D-06 (present-but-unreadable SUBCTA must produce structured `ContaPlusReadError`). Real pii-test-data uses `C(12)` for `cod` so no practical impact on known archives, but defensiveness is missing. |
| `src/contaplus_reader/xlsx.py` | 139 | `headers = list(subcta.rows[0].fields.keys())` — row-0 schema derivation | WARNING (WR-05) | Headers derived from first row only; rows with different field sets silently drop columns. Schema should come from DBF metadata, not row 0. |
| `src/contaplus_reader/xlsx.py` | 174 | `def _autosize_columns(ws: Any)` | INFO (IN-02) | `Any` annotation; project rule requires strict typing; should be `ws: Worksheet`. |
| `src/contaplus_reader/cli.py` | 89-90 | `render(data)` and `output_file.write_bytes(...)` outside `try/except` | WARNING (WR-06) | `OSError` on write (read-only dir, disk full) or openpyxl exception from `render()` leaks raw Python traceback; violates D-17 "no traceback" contract. |
| `src/contaplus_reader/_zip.py` | 57 | `zf.extract(member, extract_dir)` — original member extracted after validating `clean` | WARNING (CR-01) | Guard validates `clean` (backslash-normalised) path but extracts original `member`; the two paths are semantically decoupled. Python `zipfile` normalises member filenames to forward slashes on read, so `clean == member.filename` in all Python-API cases — no practical bypass on Python 3.14. Untested: symlink entries (WR-01), backslash entries from POSIX-created ZIPs read by non-Python extractors. |
| `tests/test_reader.py` | 485 | `assert "Unsafe ZIP entry" in msg or "ZIP" in msg` | WARNING | OR condition means the test passes for any ZIP-related error, not specifically zip-slip. Should be `assert "Unsafe ZIP entry" in msg` only. Currently passes for the correct reason but does not enforce the specific guard behavior. |

No `TBD`, `FIXME`, or `XXX` debt markers found in any source file modified by this phase.

### Human Verification Required

The automated checks verified all 4 Success Criteria against synthetic fixtures. The following items require human testing against real data:

### 1. End-to-End Conversion with Real ContaPlus Archive

**Test:** `cd C:/dev/contaplus-reader && uv run contaplus2xlsx pii-test-data/<single-company>.zip /tmp/out.xlsx`
**Expected:** Success message `out.xlsx — N journal rows, 2 sheet(s)` (or more sheets if group tables present); no traceback
**Why human:** pii-test-data is confidential (gitignored, never read into context); real archive volume and field ordering cannot be verified programmatically.

### 2. Visual XLSX Inspection for Descripción Column

**Test:** Open `/tmp/out.xlsx` in Excel/LibreOffice after running the conversion above.
**Expected:** "Diario" tab has headers `Fecha, Cuenta, Subcuenta, Descripción, Debe, Haber, Concepto`; the Descripción column contains Spanish subaccount names (not blank) for the majority of rows that have recognized subcuenta codes.
**Why human:** Visual cell-value inspection; cannot run Excel or LibreOffice programmatically here.

### 3. Multi-Company Error with Real Archive (if applicable)

**Test:** If pii-test-data contains a multi-company backup: `uv run contaplus2xlsx pii-test-data/<multi-company>.zip /tmp/out.xlsx`
**Expected:** Exit code 1; Rich error panel with red border; panel body lists the actual company directory names from the archive.
**Why human:** Multi-company real archive content is confidential; exact company directory names must be confirmed visually.

---

## Gaps Summary

No functional gaps blocking the phase goal. All 4 Success Criteria are verified by automated tests and behavioral spot-checks.

Two code-quality issues from the code review are outstanding and should be tracked for the next phase:

1. **CR-02 (WARNING):** `build_subcta_lookup` crashes with `AttributeError` when SUBCTA `cod` field is numeric type (`N`). The `except` clause does not include `AttributeError`, so the crash is unstructured. Real pii-test-data archives use `C(12)` character type, so no practical impact on known archives. Fix: add `isinstance(v, str)` guard mirroring `_reader.py:175-179`.

2. **CR-01 (WARNING):** Zip-slip guard validates the normalised `clean` path but extracts the original `member` object. Python's `zipfile` normalises member filenames on read, so the two are always equal in Python-API usage. The structural decoupling remains a security design smell. Fix: extract to the validated path explicitly using `zf.open(member)` + `open(target, 'wb')` as described in the review. Add backslash-entry and absolute-path fixtures to complement the forward-slash `../evil.dbf` fixture.

3. **CLI-02 traceability (INFO):** REQUIREMENTS.md traceability table incorrectly maps `CLI-02 | Phase 4`. The implementation is in Phase 2. The Phase 4 roadmap only lists CLI-03 and DIST-01. The traceability table should be updated to `CLI-02 | Phase 2 | Complete`.

---

_Verified: 2026-05-16T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
