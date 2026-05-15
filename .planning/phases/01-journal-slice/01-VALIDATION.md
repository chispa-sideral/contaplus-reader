---
phase: 1
slug: journal-slice
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-15
updated: 2026-05-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (>=8.x) — invoked via `uv run pytest` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Plan 01 establishes) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds (synthetic in-memory DBF fixtures) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | INPUT-01, INPUT-03, API-01, API-04 | T-01-01, T-01-05 | sniff rejects ZIP/unknown; bridge cleans up temp file | unit | `uv run python -c "from contaplus_reader import read, ContaPlusData; print('OK')"` | ❌ Wave 1 | ⬜ pending |
| 01-01-T2 | 01 | 1 | JRNL-01, JRNL-02, JRNL-03, API-02 | T-01-02, T-01-07, T-01-08 | D-C1..D-C5 validated; UnicodeDecodeError caught; struct.error caught | unit | `uv run pytest tests/test_reader.py -v` | ❌ Wave 1 | ⬜ pending |
| 01-01-T3 | 01 | 1 | TEST-01, TEST-02 | T-01-08 | no binary blobs; all ported tests pass | unit | `uv run pytest tests/test_reader.py -v` | ❌ Wave 1 | ⬜ pending |
| 01-02-T1 | 02 | 2 | XLSX-01, XLSX-04 | T-02-04 | render_journal returns bytes; no filesystem path; Spanish headers immutable | unit | `uv run pytest tests/test_xlsx.py -v` | ❌ Wave 2 | ⬜ pending |
| 01-02-T2 | 02 | 2 | CLI-01, CLI-04 | T-02-01, T-02-02, T-02-03 | overwrite guard; no traceback; error panel | smoke | `uv run pytest tests/test_cli.py -v` | ❌ Wave 2 | ⬜ pending |
| 01-03-T1 | 03 | 3 | DIST-02 | T-03-01, T-03-02 | wheel contains only src/ contents; pii-test-data/ gitignored | smoke | `uv build && python -c "import pathlib; wheels=list(pathlib.Path('dist').glob('*.whl')); assert wheels"` | ❌ Wave 3 | ⬜ pending |
| 01-03-T2 | 03 | 3 | CLI-04, DIST-02 | — | uvx installs from wheel; help text visible | human | `uvx --from dist/*.whl contaplus2xlsx --help` | ❌ Wave 3 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 1 Requirements (Plan 01 creates all test infrastructure)

- [ ] `pyproject.toml` with `[tool.pytest.ini_options]` testpaths + addopts
- [ ] `tests/conftest.py` — synthetic blob-free DBF fixture factory (TEST-01)
- [ ] `tests/test_reader.py` — ~27 cases: INPUT-01/03, JRNL-01/02/03, API-01/02/04, TEST-02
- [ ] `src/contaplus_reader/models.py`, `_bridge.py`, `_sniffer.py`, `_reader.py`, `__init__.py`

## Wave 2 Requirements (Plan 02)

- [ ] `tests/test_xlsx.py` — XLSX-01, XLSX-04 coverage
- [ ] `tests/test_cli.py` — CLI-01, CLI-04 coverage
- [ ] `src/contaplus_reader/xlsx.py`, `cli.py`

## Wave 3 Requirements (Plan 03)

- [ ] `README.md` (required by pyproject.toml for build)
- [ ] `.gitignore` with pii-test-data/ entry
- [ ] Wheel build verified; uvx smoke confirmed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uvx --from dist/*.whl contaplus2xlsx --help` shows help | CLI-04 | Requires out-of-process wheel install round-trip | Plan 03 checkpoint task covers this |
| Visual: XLSX opens in Excel/LibreOffice with styled headers and accounting format | XLSX-01 | Cell rendering is viewer-dependent | Plan 03 checkpoint: open output .xlsx and inspect |

*All other phase behaviors have automated verification via pytest.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or human checkpoint
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 (Wave 1 here — greenfield) covers all test file creation
- [x] No watch-mode flags in any verify command
- [x] Feedback latency < 15s (synthetic fixtures are fast)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned — pending execution
