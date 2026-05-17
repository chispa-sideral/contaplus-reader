---
phase: 03
slug: full-tables-balance-lenient-path
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no version change) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (synthetic blob-free DBF fixtures, fast) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Populated by the planner/executor once PLAN.md tasks are finalized. Source
> mapping (Requirement → behavior → command) is in `03-RESEARCH.md` §"Validation
> Architecture" → "Phase Requirements → Test Map".

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TABL-03 | — | N/A | unit | `uv run pytest tests/test_tables.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tables.py` — stubs for TABL-03 / BAL-01 (venci/prede/amoinv/nivel/balan readers)
- [ ] `tests/test_balance.py` — stubs for BAL-02 (compute_balance Decimal precision, saldo formula)
- [ ] `tests/test_lenient.py` — stubs for API-03 (lenient path mechanics — D-02/D-03/D-04)
- [ ] `tests/test_xlsx.py` (extend) — stubs for XLSX-02 (Problemas sheet), XLSX-03 (BALAN banner)
- [ ] `tests/conftest.py` (extend) — synthetic venci/prede/amoinv/nivel/balan DBF fixtures + defect-bearing DBFs for lenient tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operational-table field schemas match the 5 real `pii-test-data/` archives | TABL-03 | `pii-test-data/` is confidential and git-ignored — cannot be a committed automated fixture | Run the schema-probe described in `03-RESEARCH.md` against `pii-test-data/` archives; confirm venci/prede/amoinv/nivel field names+types match the synthetic fixtures before committing typed readers |
| `BALAN.DBF` field schema (esp. `SDO_CIERRE`) matches real archives | BAL-01 | Same — confidential local-only validation gate | Run the schema-probe against `pii-test-data/` BALAN tables; confirm the synthetic `balan` fixture mirrors real field layout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
