---
phase: 04-full-cli-pypi-publication
reviewed: 2026-05-19T10:30:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - .github/workflows/ci.yml
  - .github/workflows/release.yml
  - ci/package.json
  - ci/smoke.mjs
  - pyproject.toml
  - README.md
  - src/contaplus_reader/cli.py
  - tests/conftest.py
  - tests/test_cli.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-05-19T10:30:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 4 ships a Typer CLI (`contaplus2xlsx`), publication metadata in `pyproject.toml`, a GitHub Actions CI/release workflow using OIDC trusted publishing, and a Pyodide/micropip smoke test. The library and CLI logic are sound; all 128 tests pass. Findings are concentrated in the CI/CD workflows and one code-quality defect in `cli.py`. No data-loss or security blockers were found.

## Warnings

### WR-01: `micropip-smoke` job has no retry — will fail transiently due to PyPI propagation delay

**File:** `.github/workflows/release.yml:57-69`
**Issue:** The `micropip-smoke` job starts immediately after `pypi` finishes uploading. PyPI's CDN propagation (the `simple/` index becoming aware of the new release) takes 30–120 seconds on average. `micropip.install("contaplus-reader")` in `smoke.mjs` issues a single HTTP request to the PyPI simple index with no retry logic. If the index has not yet propagated, micropip raises a `404`-equivalent error and the job fails with exit code 1, blocking the release dashboard and requiring a manual re-run.
**Fix:** Add a retry loop in `smoke.mjs` before the install call, or add a `sleep 60` step in the workflow between the `pypi` job and `micropip-smoke`. The `smoke.mjs` option is more portable:
```js
// Replace the single micropip.install() call with:
async function installWithRetry(micropip, pkg, retries = 5, delayMs = 30000) {
  for (let i = 0; i < retries; i++) {
    try {
      await micropip.install(pkg);
      return;
    } catch (e) {
      if (i === retries - 1) throw e;
      console.log(`Install attempt ${i + 1} failed, retrying in ${delayMs / 1000}s...`);
      await new Promise(r => setTimeout(r, delayMs));
    }
  }
}
await installWithRetry(micropip, packageRef);
```

---

### WR-02: `micropip.install` does not pin the package version — installs latest, not just-published

**File:** `ci/smoke.mjs:14-15`
**Issue:** `micropip.install("contaplus-reader")` always resolves to the latest version on PyPI. After a release it installs the correct new version. But on re-runs (e.g., after a transient failure) triggered days or weeks later — after a subsequent release — it will install a different version than the one originally published, making the smoke test test the wrong release. Additionally, `micropip.install` is called without a version specifier, which violates reproducibility expectations for a release gate.
**Fix:** Inject the version at build time via an environment variable or embed it from `pyproject.toml`. The simplest approach is to pass it from the workflow:
```yaml
# release.yml micropip-smoke job
- run: node smoke.mjs
  working-directory: ci/
  env:
    PACKAGE_VERSION: ${{ github.ref_name }}   # e.g. "0.1.0" from the release tag
```
```js
// smoke.mjs
const version = process.env.PACKAGE_VERSION;
const packageRef = process.env.WHEEL_URL || (version ? `contaplus-reader==${version}` : "contaplus-reader");
```

---

### WR-03: `ContaPlusData` used as a type annotation in `_print_report` but not imported at module scope — `typing.get_type_hints()` raises `NameError`

**File:** `src/contaplus_reader/cli.py:26`
**Issue:** `_print_report(data: ContaPlusData, output_file: Path)` uses `ContaPlusData` as an annotation at module level, but the name is only imported inside `main()` at line 99. With `from __future__ import annotations` (line 14), the annotation is stored as the string `"ContaPlusData"` and never evaluated at definition time, so module import and all normal call paths work correctly. However, `typing.get_type_hints(_print_report)` raises `NameError: name 'ContaPlusData' is not defined`, which can be triggered by any framework or tool that introspects CLI annotations (e.g., future type-checking integration, documentation generators). Verified:
```
>>> typing.get_type_hints(cli._print_report)
NameError: name 'ContaPlusData' is not defined
```
**Fix:** Add a module-level import guarded by `TYPE_CHECKING`, keeping the lazy import inside `main()` to avoid circular-import risk at runtime:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contaplus_reader import ContaPlusData
```
Or simply hoist the `from contaplus_reader import ContaPlusData` to module level alongside the existing `from pathlib import Path` import — there is no circular dependency risk since `cli.py` is a leaf module.

---

### WR-04: `ci/` directory has no `package-lock.json` — violates lockfile discipline and causes non-reproducible CI installs

**File:** `ci/package.json` / `.github/workflows/release.yml:66`
**Issue:** The `micropip-smoke` job runs `npm install pyodide@0.29.4` against a `package.json` that has no accompanying `package-lock.json`. The `npm install` command (not `npm ci`) writes a lockfile locally but never persists it. While `pyodide: "0.29.4"` is an exact version pin, pyodide's own transitive dependencies (e.g., `ws`, `node-fetch`) are subject to semver ranges and will be resolved fresh on every CI run. This means a dependency of pyodide could change between runs, making the smoke test non-reproducible. Per project lockfile-discipline rules, `package-lock.json` must be committed alongside `package.json`.
**Fix:** Run `npm install` locally in `ci/`, commit the generated `package-lock.json`, and change the workflow step to `npm ci`:
```yaml
# release.yml
- run: npm ci
  working-directory: ci/
```

## Info

### IN-01: `checkout` and `setup-uv` steps in `testpypi`/`pypi` publish jobs are unnecessary

**File:** `.github/workflows/release.yml:31-35` and `:49-53`
**Issue:** Both `testpypi` and `pypi` jobs check out the repository source code and set up uv, then immediately download the pre-built artifact and run `uv publish`. `uv publish` operates only on the `dist/` artifact — it requires only the `uv` binary and the OIDC token, not the source tree. The `actions/checkout` step adds repository read permissions and increases attack surface unnecessarily.
**Fix:** Remove the `actions/checkout` and `astral-sh/setup-uv` steps from both publish jobs and replace with a direct `uv` install:
```yaml
steps:
  - uses: astral-sh/setup-uv@v6   # only uv binary needed, no checkout
  - uses: actions/download-artifact@v4
    with:
      name: dist
      path: dist/
  - run: uv publish --trusted-publishing always
```

---

### IN-02: CI workflow has no linting or type-checking step

**File:** `.github/workflows/ci.yml`
**Issue:** `ci.yml` runs only `uv run pytest`. There is no `ruff`, `mypy`, or `pyright` step. WR-03 (the `ContaPlusData` annotation defect) would have been caught automatically by a type checker. Adding at minimum a `ruff check` step catches a broad class of issues at low cost.
**Fix:** Add a lint step:
```yaml
- run: uv run ruff check src/ tests/
```
And add `ruff>=0.9` to `[dependency-groups] dev` in `pyproject.toml`.

---

### IN-03: Smoke test only verifies importability, not `read()` functionality

**File:** `ci/smoke.mjs:18-22`
**Issue:** The smoke test imports `contaplus_reader`, `read`, and `ContaPlusReadError` and prints a success message, but never calls `read()` with any data. A broken `read()` implementation (import-time crash aside) would not be caught. For a package where "correct extraction cannot fail" is the core value proposition, a smoke test that exercises the actual parser is more defensible.
**Fix:** Add a minimal functional call after the import test. A small synthetic DBF encoded as a base64 constant can serve as the smoke payload without requiring any file I/O:
```python
import base64, io
# Minimal valid DBF (empty DIARIO with correct header) encoded as base64
# OR: simply verify read() raises ContaPlusReadError on invalid bytes (smoke of error path)
try:
    read(b"not a dbf")
except ContaPlusReadError:
    pass  # expected
print("read() error path verified")
```

---

_Reviewed: 2026-05-19T10:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
