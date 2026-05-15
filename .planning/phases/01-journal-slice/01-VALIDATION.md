---
phase: 1
slug: journal-slice
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (>=8.x) — invoked via `uv run pytest` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 establishes) |
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

> Populated by the planner — one row per task once PLAN.md files exist.
> Test type, automated command, and Wave 0 dependency are derived from each
> task's `<acceptance_criteria>` and `<automated>` blocks.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | `uv run pytest -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — pytest config + `dbf` (ethanfurman) as dev dependency
- [ ] `tests/conftest.py` — synthetic blob-free DBF fixture factory ported from `tw-contaplus` (TEST-01)
- [ ] `tests/test_journal_read.py` — stubs for INPUT-01, INPUT-03, JRNL-01/02/03, API-01/02/04
- [ ] `tests/test_xlsx_render.py` — stubs for XLSX-01, XLSX-04
- [ ] `tests/test_cli.py` — stubs for CLI-01, CLI-04
- [ ] `tests/test_dist.py` — wheel build / `uvx` smoke test for DIST-02

*Phase 1 is greenfield — no test infrastructure exists; Wave 0 installs it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `uv build` produces a wheel and `uvx contaplus2xlsx` installs + runs from it | DIST-02 | Requires building a wheel artifact and invoking `uvx` against it — an out-of-process install round-trip not covered by in-process pytest | Run `uv build`, then `uvx --from dist/*.whl contaplus2xlsx --help`; confirm exit 0 and help text. (May be partially automated as a subprocess test.) |

*Remaining phase behaviors have automated verification via pytest.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
