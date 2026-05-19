---
phase: 4
slug: full-cli-pypi-publication
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 04-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Task IDs are assigned by the planner. Each plan task addressing CLI-03 / DIST-01
> must carry an `<automated>` verify command or a Wave 0 dependency. The
> gsd-nyquist-auditor fills the concrete task rows after PLAN.md files exist.

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| CLI-03 | CLI prints per-table row counts to stdout after conversion | unit (CLI) | `uv run pytest tests/test_cli.py -x -k "test_report"` | ❌ W0 |
| CLI-03 | CLI prints skipped-memo count to stdout | unit (CLI) | `uv run pytest tests/test_cli.py -x -k "test_memo"` | ❌ W0 |
| CLI-03 | CLI lists problem entries inline (lenient mode) | unit (CLI) | `uv run pytest tests/test_cli.py -x -k "test_problems"` | ❌ W0 |
| DIST-01 | `uv build` produces a valid wheel with PEP 639 license metadata | smoke | `uv build && uv run --with dist/*.whl python -c "import contaplus_reader"` | ❌ W0 |
| DIST-01 | micropip installs wheel in Pyodide Node.js environment | CI smoke (Node.js) | `node ci/smoke.mjs` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` — add report-output tests for CLI-03 (extend the existing file from Phases 1–3; do not recreate)
- [ ] `ci/smoke.mjs` + `ci/package.json` — Node.js micropip smoke test for DIST-01
- [ ] `ci/` directory — create with `package.json` pinning `pyodide@0.29.4`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PyPI / TestPyPI trusted-publisher entries created on the websites | DIST-01 | Cannot be automated — a human must register the pending publisher on pypi.org and test.pypi.org | Marc registers publisher: repo `marcfargas/contaplus-reader`, workflow `release.yml` |
| GitHub Release published / deployment environment approved | DIST-01 | Publish authorization is a deliberate human action; Claude never holds a token | Marc creates the GitHub Release that triggers the publish workflow |
| TestPyPI project page renders correctly | DIST-01 | Visual confirmation of README rendering as the PyPI long description | Marc opens the TestPyPI project page after the dry-run upload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
