---
phase: 2
slug: zip-subaccounts
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds (55 baseline + ~19 new tests) |

**Baseline:** 55 tests pass in ~0.80s. [VERIFIED: live test run before Phase 2]

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** < 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INPUT-02, INPUT-04, INPUT-05, INPUT-06, TABL-01, TABL-02, API-05 | — | No real ContaPlus data committed; all fixtures synthetic | fixture | `cd C:/dev/contaplus-reader && uv run pytest --collect-only -q 2>&1 \| tail -5` | ❌ Wave 0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INPUT-02, INPUT-04, INPUT-05, INPUT-06, TABL-01, TABL-02, API-05, CLI-02 | T-02-SC | Tests confirm zip-slip rejected before extraction | unit (RED) | `cd C:/dev/contaplus-reader && uv run pytest -q 2>&1 \| tail -20` | ❌ Wave 0 | ⬜ pending |
| 02-02-01 | 02 | 2 | INPUT-02, INPUT-04, INPUT-05, INPUT-06, TABL-01, TABL-02, API-05 | T-02-01, T-02-02 | ZIP-slip guard runs per-entry before extraction; malformed DBF wrapped in ContaPlusReadError | unit | `cd C:/dev/contaplus-reader && uv run pytest tests/test_reader.py -k "not zip" -q 2>&1 \| tail -10` | ❌ Wave 0 | ⬜ pending |
| 02-02-02 | 02 | 2 | INPUT-02, INPUT-04, INPUT-05, INPUT-06, TABL-01, TABL-02, API-05 | T-02-01, T-02-02 | All reader/SUBCTA/group-table tests GREEN | unit | `cd C:/dev/contaplus-reader && uv run pytest tests/test_reader.py -q 2>&1 \| tail -20` | ❌ Wave 0 | ⬜ pending |
| 02-03-01 | 03 | 3 | INPUT-02, INPUT-06, TABL-01, TABL-02, API-05 | T-02-04, T-02-05 | openpyxl writes literal values only; no formula injection | unit | `cd C:/dev/contaplus-reader && uv run pytest tests/test_xlsx.py -q 2>&1 \| tail -15` | ❌ Wave 0 | ⬜ pending |
| 02-03-02 | 03 | 3 | INPUT-02, INPUT-06, CLI-02 | — | --company flag passed to read(); multi-company error surfaces via Rich panel | unit | `cd C:/dev/contaplus-reader && uv run pytest tests/test_cli.py -q 2>&1 \| tail -15` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — add `single_company_zip_with_subcta`, `single_company_zip`, `multi_company_zip`, `zip_with_group_tables`, `zip_slip_zip`, `_build_subcta_dbf`, `_build_generic_dbf`
- [ ] `tests/test_reader.py` — 13 failing tests for ZIP reading, zip-slip, company resolution, SUBCTA enrichment, group table handling
- [ ] `tests/test_cli.py` — 2 failing tests for `--company` flag and multi-company error panel
- [ ] `tests/test_xlsx.py` — 2 failing tests for multi-sheet workbook and Descripción column

---

## Success Criteria Tests (End-to-End)

| Criterion | Test Filter | Automated Command |
|-----------|-------------|-------------------|
| #1: zip -> xlsx with SUBCTA names | `zip_to_xlsx_enriched` | `uv run pytest tests/test_cli.py -k zip_to_xlsx_enriched -x` |
| #2: Multi-company without --company lists dirs | `multi_company_error` | `uv run pytest tests/test_cli.py -k multi_company_error -x` |
| #3: Zip-slip entry rejected | `zipslip` | `uv run pytest tests/test_reader.py -k zipslip -x` |
| #4: Sheets for present tables only | `multi_sheet` | `uv run pytest tests/test_xlsx.py -k multi_sheet -x` |

---

## Requirement -> Test Coverage

| Req ID | Behavior | Test Function | Plan |
|--------|----------|---------------|------|
| INPUT-02 | `read()` accepts ZIP bytes | `test_read_zip_bytes` | 02-01 |
| INPUT-02 | `read()` accepts ZIP file-like | `test_read_zip_filelike` | 02-01 |
| INPUT-04 | Zip-slip entry raises `ContaPlusReadError` | `test_read_zipslip_rejected` | 02-01 |
| INPUT-05 | Recursive DIARIO.DBF discovery | (covered by all single/multi ZIP tests) | 02-01 |
| INPUT-06 | Multi-company without `--company` raises listing dirs | `test_read_multi_company_no_selector` | 02-01 |
| INPUT-06 | Multi-company with valid `--company` reads correct company | `test_read_multi_company_selected` | 02-01 |
| INPUT-06 | Selector against single-company validates | `test_read_single_company_wrong_selector` | 02-01 |
| INPUT-06 | Selector against raw DBF raises | `test_read_selector_on_dbf_raises` | 02-01 |
| TABL-01 | `subcta` reader builds correct lookup | `test_subcta_lookup_correct` | 02-01 |
| TABL-01 | Defensive field resolution (cod/codigo, titulo/descrip) | `test_subcta_candidate_fallback` | 02-01 |
| TABL-02 | `grupos/usuarios/empresa` absent -> no error | `test_group_tables_absent_no_error` | 02-01 |
| TABL-02 | `usuarios` present -> accessible in result | `test_usuarios_present_in_result` | 02-01 |
| API-05 | Journal rows enriched with `subcuenta_nombre` from SUBCTA | `test_subcta_lookup_correct` | 02-01 |
| API-05 | Missing SUBCTA key -> `subcuenta_nombre=None` | `test_subcta_lookup_missing_key` | 02-01 |
| API-05 | SUBCTA absent -> all `subcuenta_nombre=None` | `test_subcta_absent_all_none` | 02-01 |
| CLI-02 | `--company` passed to `read()` | `test_cli_company_flag_accepted` | 02-01 |
| CLI-02 | Multi-company ZIP without `--company` exits 1 with Rich panel | `test_cli_multi_company_no_flag_exits_1` | 02-01 |
| XLSX (D-12) | Multi-sheet workbook has correct sheet names | `test_render_multi_sheet_names` | 02-01 |
| XLSX (D-15) | Diario sheet has Descripción column after Subcuenta | `test_render_descripcion_column_present` | 02-01 |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual inspection of multi-sheet .xlsx output | D-12, D-14, D-15 | openpyxl cell styling (column widths, freeze panes, header fill) not easily asserted programmatically | Run `uv run contaplus2xlsx <zip> /tmp/out.xlsx` and open in Excel/LibreOffice; verify Diario/Subcuentas tabs, Descripción column header, frozen row 1 |
| pii-test-data smoke test (real ContaPlus backup) | INPUT-02, INPUT-04 | Synthetic fixtures cannot cover all real-world edge cases | Run `uv run contaplus2xlsx pii-test-data/<archive>.zip /tmp/real-out.xlsx`; verify success message and output file opens correctly — do NOT quote file contents |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands listed above
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (all tests start as ❌ Wave 0)
- [x] No watch-mode flags (`-q` only, no `--watch`)
- [x] Feedback latency < 10s (baseline 0.80s; estimated ~5s with new tests)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
