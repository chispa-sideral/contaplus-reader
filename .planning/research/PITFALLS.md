# Pitfalls Research

**Domain:** Python library + CLI + in-browser PWA for legacy accounting DBF extraction
**Researched:** 2026-05-15
**Confidence:** HIGH (library/format domain), MEDIUM (Pyodide runtime specifics)

---

## Critical Pitfalls

### Pitfall 1: dbfread requires a filesystem path — BytesIO is not natively supported

**What goes wrong:**
`dbfread.DBF()` accepts a file path string, not a file-like object. If you hand it an `io.BytesIO` (the bytes-first API shape the project needs), it raises a `TypeError` or silently tries to interpret the bytes object as a path string. In the browser there is no real path — the entire conversion pipeline must work from bytes handed in by a `<input type="file">` drag-drop. The existing `tw-contaplus` reader is `Path`-based; porting it naively without solving this first produces a library that cannot run in Pyodide.

**Why it happens:**
Issue olemb/dbfread#25 has been open since 2017 requesting file-like-object support. A patch was proposed but never formally merged into the 2.0.7 release. The library is now classified as inactive by Snyk (no new PyPI releases in 12+ months). Most users work around it by writing to a temp file first, which is impossible in the browser.

**How to avoid:**
The correct workaround for the browser path is: extract the ZIP entry to Pyodide's in-memory Emscripten filesystem (via `pyodide.FS.writeFile`), pass the virtual path to `dbfread.DBF()`, then delete the virtual file. For the CLI/library path, write to a `tempfile.TemporaryDirectory` then pass the real path. Both paths must be covered with tests before the XLSX renderer is built, because every downstream piece depends on this working.

Alternative: vendor a minimal DBF header+record parser (the format is fully specified in SEED.md §1) to eliminate the dependency entirely. The format is simple enough — fixed-width records with a typed header — that 150 lines of Python replaces dbfread entirely and removes the inactive-library risk.

**Warning signs:**
- Any test that constructs a `DBF()` from a `Path` and nothing else — the bytes-first contract is untested.
- A `conftest.py` that writes fixtures to disk and passes real paths — fine for the library, but will not port to WASM tests.

**Phase to address:**
Phase 1 (reader core / bytes-first API). Must be resolved before any other work starts.

---

### Pitfall 2: Pyodide cold-load is 20–30 MB on first visit — without a service worker this is a show-stopper UX

**What goes wrong:**
The Pyodide runtime itself is ~7 MB (CPython + stdlib compiled to WASM). `pandas` adds ~10 MB more. `openpyxl` adds another few MB. `dbfread` and `contaplus-reader` wheels are negligible. Total first-visit download: **~20–25 MB** over a typical connection. Without service-worker caching, every page load repeats this download. On a 10 Mbps connection that is 20+ seconds of blank-screen wait. Without visible progress the user assumes the page is broken.

**Why it happens:**
Developers prototype with `loadPyodide()` + `micropip.install()` in the main thread, confirm it works, then ship as-is. The service worker (which caches the runtime to IndexedDB or the Cache API for subsequent visits) is an afterthought. The Pyodide docs document this in the service-worker guide but it is easy to miss.

**How to avoid:**
1. Register a service worker on first install that pre-caches the Pyodide CDN assets (`pyodide.js`, `pyodide.asm.wasm`, `packages.json`) and the installed wheels.
2. Show a loading progress bar while Pyodide initialises — `loadPyodide` emits no built-in progress events, so the progress must be synthetic (e.g., fake steps: "Loading Python runtime…", "Loading data libraries…", "Ready").
3. Move Python execution off the main thread into a Web Worker so the UI does not freeze during 5-second cold initialisation.
4. Cache-bust only on new Pyodide version or app release, not on every deploy.

**Warning signs:**
- First Lighthouse audit shows TTI > 10 s.
- No service worker registered in DevTools → Application → Service Workers.
- `loadPyodide` called in the main thread (blocks UI responsiveness).

**Phase to address:**
Phase 3 (PWA shell). Must be solved before any user testing.

---

### Pitfall 3: SharedArrayBuffer / COOP+COEP headers required for Pyodide on Cloudflare Pages

**What goes wrong:**
Pyodide's threading and some internal WASM features require `SharedArrayBuffer`, which is only available in cross-origin-isolated contexts. Browsers gate `SharedArrayBuffer` behind two HTTP response headers: `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`. Without these headers `loadPyodide()` either raises a runtime error or falls back to a slower non-threaded mode. Cloudflare Pages does not set these headers by default.

**Why it happens:**
The headers must be configured in a `_headers` file at the project root of the Cloudflare Pages deployment. Developers either miss this file or discover the problem only after deploying to production because localhost development with `vite dev` may or may not enforce isolation.

**How to avoid:**
Add a `_headers` file to the Pages project root:
```
/*
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
```
Note: `require-corp` blocks any cross-origin resource that does not itself send a CORP header. If Pyodide is loaded from `cdn.jsdelivr.net`, that CDN must serve CORP headers — jsDelivr does. If loading wheels from PyPI directly, PyPI now sets CORS but not necessarily CORP. Prefer pre-bundling the wheels as static assets served from the same origin to avoid this issue.

**Warning signs:**
- Browser console shows: "SharedArrayBuffer is not defined" or "Cross-Origin-Opener-Policy" errors.
- Pyodide initialises but hangs or is extremely slow (non-threaded fallback).
- Works on localhost but breaks in the Cloudflare Pages preview URL.

**Phase to address:**
Phase 3 (PWA shell), before any Pyodide integration testing on the deployed URL.

---

### Pitfall 4: Cloudflare Pages 25 MB per-file limit and 20,000 file limit break naive Pyodide bundling

**What goes wrong:**
Cloudflare Pages enforces: (a) maximum 25 MiB per individual static asset file; (b) maximum 20,000 files per deployment. The Pyodide WASM binary (`pyodide.asm.wasm`) alone exceeds 25 MB in some versions. Bundling the entire Pyodide distribution — which includes hundreds of individual wheel files — easily exceeds the 20,000-file limit. Attempting to `vite bundle` the Pyodide CDN assets into the Pages deploy fails or is silently truncated.

**Why it happens:**
The naive approach is to copy the full Pyodide release directory into the `public/` folder and deploy. This works locally but fails at the Cloudflare Pages upload step.

**How to avoid:**
Do NOT bundle Pyodide assets in the Pages deploy. Instead:
1. Load Pyodide from the official jsDelivr CDN (`https://cdn.jsdelivr.net/pyodide/v0.x.y/full/`). This is the recommended approach in the Pyodide docs and avoids the file-count and file-size limits.
2. Only bundle the project's own wheel (`contaplus_reader-*.whl`) as a static asset — it is a few KB.
3. The service worker caches the CDN assets after first load, giving subsequent offline behaviour.
4. For the `contaplus-reader` wheel specifically, host it at `/assets/contaplus_reader-VERSION-py3-none-any.whl` and `micropip.install` from that path using `emfs:` scheme after uploading via `pyodide.FS`.

**Warning signs:**
- Cloudflare Pages deploy log shows: "Error: Pages only supports up to 20,000 files."
- Any `public/pyodide/` directory in the repo.
- Deploy succeeds but wheel assets are silently missing.

**Phase to address:**
Phase 3 (PWA shell / deployment config). Verify on first deploy to Cloudflare Pages, not just localhost.

---

### Pitfall 5: ZIP-slip from in-memory buffer — Python 3.12+ filter= is opt-in, not the default

**What goes wrong:**
`zipfile.ZipFile.extractall()` does NOT prevent zip-slip by default in any Python version. A crafted archive with entries like `../../etc/cron.d/pwned` will extract outside the target directory. Python 3.12 added a `filter=` parameter (`"data"`, `"tar"`, `"fully_trusted"`) but it is explicitly opt-in — the default is still `"fully_trusted"` (unsafe). Python 3.13 made no change to this default. The SEED.md acknowledges the lack of a `filter=` safety knob and describes the manual validation approach.

**Why it happens:**
Developers see that Python "handles" zip files and assume security is built in. The extraction is from an in-memory `BytesIO` (no real path context), which does not change the traversal risk — the extracted entries still land on the filesystem (or Emscripten VFS). In the browser, landing a file outside the VFS is contained, but in the CLI/library path on a real OS the risk is real.

**How to avoid:**
The SEED.md already specifies the correct approach: before extraction, validate every entry name with:
```python
import posixpath
from pathlib import Path

def _safe_extract(zf: zipfile.ZipFile, target: Path) -> None:
    for member in zf.infolist():
        # Resolve and assert stays inside target
        dest = (target / member.filename).resolve()
        if not str(dest).startswith(str(target.resolve())):
            raise ContaPlusReadError(
                row_index=-1, column=None,
                message=f"Zip-slip detected: {member.filename!r}"
            )
    zf.extractall(target)
```
On Python 3.12+, can additionally pass `filter="data"` as a second guard. Do not rely on `filter=` alone because it is unavailable on Python < 3.12 and the project targets `>=3.13`, so it can be used — but the explicit validation is still worth keeping as a belt-and-suspenders and documents intent.

**Warning signs:**
- Any call to `zf.extractall(path)` without a preceding member-name validation loop.
- Test suite has no fixture with a traversal-attempt entry.

**Phase to address:**
Phase 1 (reader core / ZIP handling). Must be in the initial implementation, not retrofitted.

---

### Pitfall 6: encoding=cp850 is correct but dbfread's default will silently use the wrong codepage

**What goes wrong:**
`dbfread` reads header byte-29 and uses it as the encoding if no explicit `encoding=` is passed. For ContaPlus files where byte-29 is `0x00` (unset — common in older Clipper installs), dbfread falls back to the system locale, which on a modern Linux CI box is `utf-8`. `utf-8` cannot decode many CP850 byte sequences; the result is either a `UnicodeDecodeError` (if strict) or silent mojibake (if the locale's codec happens to accept those bytes). The symptom is Spanish accented characters — `á`, `é`, `ñ` — appearing as garbage or triggering decode exceptions on CI but not on a developer's Spanish Windows machine.

**Why it happens:**
A developer tests on Windows where the system codepage is `cp1252` or `cp850`, so dbfread's default encoding happens to decode correctly. CI runs on Ubuntu with `utf-8`. The bug only surfaces on CI or on non-Spanish-locale machines.

**How to avoid:**
Always pass `encoding="cp850"` explicitly (SEED.md §5, rule D-D1). Never call `DBF(path)` or `DBF(path, lowernames=True)` without the encoding keyword. This is already specified in the SEED; the pitfall is forgetting it when copy-pasting dbfread examples from the internet that omit the parameter.

Add a CI lint rule or a unit test that: (a) inspects the single `DBF()` call site and asserts the `encoding` kwarg is present; or (b) runs the cp1252 fixture test (`cp1252_byte29_dbf`) which verifies that cp850-always decodes ASCII-clean cp1252 content correctly.

**Warning signs:**
- `UnicodeDecodeError` in CI that does not appear locally on a Windows machine.
- `DBF(path, lowernames=True)` without `encoding=` anywhere in the codebase.
- Test passes locally on Spanish Windows, fails on Ubuntu CI.

**Phase to address:**
Phase 1 (reader core). Baked into the single DBF invocation; the fixture suite from SEED.md pins it.

---

### Pitfall 7: LGPL-3.0 compliance for a library distributed as a PyPI wheel

**What goes wrong:**
LGPL-3.0-or-later requires that: (a) the license text is included with distributions; (b) users can replace the LGPL component (i.e., the library must be dynamically linked or its source available). Python wheels are zip archives of `.py` files — they are effectively statically linked from a distribution standpoint, which creates a grey area. The more acute risk is: wheels distributed on PyPI do not include instructions for obtaining the source code, which is technically required by LGPLv3 §4 when distributing object code without the source code itself.

**Why it happens:**
Most Python LGPL projects assume PyPI + a public GitHub repo satisfies the "source available" clause because the source is publicly accessible. This is generally accepted in practice, but the mechanism should be made explicit: the wheel metadata should include the `Source` URL pointing to the GitHub repo, and the `LICENSE` file must be included in the wheel's `dist-info`.

**How to avoid:**
1. Include `LICENSE` in `MANIFEST.in` / `pyproject.toml` `[tool.hatch.build.targets.wheel] include` so it is bundled in the wheel's `.dist-info`.
2. Set `project.urls.Source` in `pyproject.toml` to the GitHub repo URL.
3. In `pyproject.toml`, use PEP 639 license expression: `license = "LGPL-3.0-or-later"`.
4. Document the LGPL compliance posture in the README: "The source code is available at [URL]; consumers may replace this library with a compatible version."
5. For tax-workbench (the primary downstream consumer), note that LGPL allows linking from a proprietary/other-licensed project without requiring that project to adopt LGPL — the library's own modifications must remain LGPL.

**Warning signs:**
- `uv build` output wheel has no `LICENSE` file inside `contaplus_reader-*.dist-info/`.
- `pyproject.toml` `license` field is empty or uses the deprecated `license.file =` syntax without a SPDX expression.

**Phase to address:**
Phase 4 (distribution/packaging). Verify before the first PyPI publish.

---

### Pitfall 8: Lenient path silently masking real bugs in the strict path

**What goes wrong:**
When strict and lenient modes share the same row-iteration code, a common mistake is to introduce a `try/except` block in the shared loop that catches the errors the strict path is supposed to raise. Result: the strict path stops failing on bad data because the except branch now runs in both modes. The bug is invisible if tests for the strict path are written only for the "known bad inputs" and not as regression guards against a code refactor accidentally adding exception handling.

**Why it happens:**
The natural implementation pattern is: shared `_iter_rows()` generator that yields either row or error, with the strict consumer re-raising and the lenient consumer collecting. Developers under time pressure introduce a `try/except ContaPlusReadError` in `_iter_rows()` itself "to keep it clean" rather than in each consumer — this breaks the strict contract.

**How to avoid:**
The shared code must NEVER swallow errors internally. The correct architecture:
- `_iter_rows()` raises immediately on any invalid row (strict semantics by definition).
- The lenient consumer wraps each `next()` call from the iterator in its own `try/except`, collects the error, and continues manually (by calling `next()` again — a generator cannot be resumed after a raise without explicit handling).
- A simpler alternative: `_iter_rows()` yields `Union[ValidRow, RowError]` tagged unions; strict consumer calls `result.unwrap()` which re-raises; lenient consumer inspects the tag. This avoids exception-based flow for the lenient path while keeping the strict path fail-loud.

The test that catches this regression: a strict-mode call on a file with one bad row and several good rows must raise on the bad row, not return the good rows.

**Warning signs:**
- `try/except ContaPlusReadError` inside `_iter_rows()` or `_read_records()`.
- Strict-mode tests that only test files where ALL rows are bad (so the result is always raise); no test for "one bad row in the middle of a valid file."
- A refactor renames the shared function and none of the strict-mode tests break.

**Phase to address:**
Phase 2 (lenient path / full table readers). Design the shared/split boundary before writing the lenient consumer.

---

### Pitfall 9: Pyodide WASM memory limit — large multi-year journals hit the 2 GB WASM heap cap

**What goes wrong:**
Pyodide's WASM heap is capped at 2 GB by the browser's 32-bit WASM linear memory model (on 64-bit Wasm this is relaxed but browser support is not universal). A multi-year journal with millions of rows materialised as a full pandas DataFrame can exhaust this limit. Observed real-world case: a pandas DataFrame of ~1 M rows × ~7 columns raises a memory error during `sort_values` inside Pyodide. The user sees a cryptic JavaScript exception, not a Python traceback.

**Why it happens:**
The v1 library correctly uses `dbfread`'s lazy iteration (`load=False`, default). But the XLSX renderer almost certainly calls `pd.DataFrame(list(records))` — materialising all rows at once — before handing off to openpyxl. On large files this doubles memory: one copy as a Python list of dicts, one as the DataFrame.

**How to avoid:**
1. Stream rows directly into the DataFrame constructor from the generator (avoids the intermediate list): `pd.DataFrame(row for row in reader)`.
2. For the openpyxl writer, use `worksheet.append(row)` row-by-row rather than writing from a fully-built DataFrame, to avoid holding two full copies simultaneously.
3. In the PWA, display the file's row count before processing and warn the user for files > 500 K rows.
4. Expose a `max_rows` limit parameter in the lenient API so the browser can cap extraction to a safe size.

**Warning signs:**
- XLSX renderer builds `list(reader)` before constructing the DataFrame.
- No test for a fixture with > 10,000 rows (the lazy iteration guarantee is untested at scale).
- Browser console shows `RuntimeError: memory access out of bounds` during conversion.

**Phase to address:**
Phase 2 (XLSX renderer). The streaming write pattern must be the initial design, not a later optimisation.

---

### Pitfall 10: micropip cannot install from a local editable checkout — requires a built wheel

**What goes wrong:**
`micropip.install("contaplus-reader")` works when the package is on PyPI. During development, the wheel does not yet exist on PyPI. `micropip` cannot do `pip install -e .` — there is no editable-install concept in the browser. It also cannot install from a local filesystem path using `file:` URIs in the browser. The only way to test the PWA against the local dev build of the library is to:
1. `uv build` to produce `dist/contaplus_reader-*.whl`.
2. Serve the wheel over HTTP (e.g., `python -m http.server` in `dist/`).
3. `micropip.install("http://localhost:8000/contaplus_reader-VERSION-py3-none-any.whl")`.

This round-trip is slow and easy to forget, leading to the PWA being tested against a stale wheel.

**Why it happens:**
The divergence between CLI/library dev workflow (`uv sync`, editable install) and PWA dev workflow (must be a built wheel) is invisible until the first time someone tries to iterate on the library and test the PWA simultaneously.

**How to avoid:**
1. Add a `Makefile` or `justfile` target: `dev-wheel: uv build && cp dist/*.whl pwa/public/dev/` — copies the freshly built wheel to the PWA's static assets.
2. In the PWA dev mode, `micropip.install` from `/dev/contaplus_reader-...whl` (relative URL served by Vite's dev server).
3. In the PWA production build, `micropip.install` from PyPI or a pinned CDN URL.
4. Document this workflow in the project CONTRIBUTING guide.

**Warning signs:**
- PWA works in production (PyPI wheel) but breaks in dev (no dev wheel served).
- `micropip.install("contaplus-reader")` in PWA code without a dev/prod switch.
- No `uv build` step in the PWA dev server startup.

**Phase to address:**
Phase 3 (PWA shell). Set up the dev-wheel workflow before any PWA logic is written.

---

### Pitfall 11: Column-name variants not covered for non-DIARIO tables

**What goes wrong:**
SEED.md §3 documents the column-name variants for `DIARIO.DBF`'s debit/credit columns across ContaPlus versions. The same versioning instability applies to other tables. `SUBCTA.DBF` is explicitly noted in SEED.md as "more variable across versions" — the field for the subaccount code may be `CODIGO` or `COD`; the description field may be `DESCRIP` or `TITULO`. If the reader for `SUBCTA.DBF` hardcodes one column name and a user's ContaPlus version uses the other, it raises a `KeyError` with no useful message.

**Why it happens:**
The DIARIO reader already has defensive column resolution (the candidate-list pattern, rule D-E1). When writing readers for other tables, developers copy-paste the happy-path code from DIARIO without porting the defensive resolution logic, because the variant column names are not documented in the SEED for non-DIARIO tables.

**How to avoid:**
Apply the same candidate-list pattern to every multi-version field in every table reader. Before implementing a reader for a new table, document its field variants (even if only two known names). Provide a unit test with a fixture using the alternate column name. If the alternate name is unknown, the reader should fail with a structured error that lists the actual field names found — never a bare `KeyError`.

**Warning signs:**
- Any `record["CODIGO"]` (uppercase hardcode, not lowercased candidate list).
- A new table reader with no fixture for an alternate column-name variant.
- `dbfread lowernames=True` is used but the reader accesses fields with uppercase keys.

**Phase to address:**
Phase 2 (full table readers for SUBCTA, BALAN, etc.).

---

### Pitfall 12: BALAN.DBF is a derived/cached table — treating it as source of truth produces wrong balances

**What goes wrong:**
SEED.md §1 explicitly notes: "`BALAN.DBF` is a **derived/temporary** file rebuilt by ContaPlus's 'UTILIDADES > Refrescar datos'." Users who have not recently refreshed their data have a stale `BALAN.DBF` that diverges from `DIARIO.DBF`. Reading and exporting `BALAN.DBF` as though it were authoritative produces trial-balance figures that do not match the journal — exactly the kind of silent data corruption that causes problems for tax filings.

**Why it happens:**
`BALAN.DBF` is physically present in every ContaPlus export and looks like any other authoritative table. The derived/stale nature is only documented in internal Sage tooling and community forums, not visible in the file itself.

**How to avoid:**
1. In the `BALAN.DBF` reader output, include a visible disclaimer field: `source: "BALAN.DBF (derived — may be stale; recompute from DIARIO for authoritative figures)"`.
2. The XLSX renderer should add a prominent sheet-level warning note in the `BALAN` sheet.
3. Never use `BALAN.DBF` figures in any computation — only expose them as-read for reference.
4. Document this prominently in the README and CLI help text.

**Warning signs:**
- Any code that sums `BALAN.DBF` figures and presents them as final.
- A user comparing the tool's trial balance output to ContaPlus's own screen and finding discrepancies.
- No visible disclaimer in the BALAN sheet of the output XLSX.

**Phase to address:**
Phase 2 (BALAN reader). Must be part of the initial design, not a later UX note.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `DBF(path)` without `encoding="cp850"` | Simpler call site | Silent mojibake on non-Spanish CI, UnicodeDecodeError on edge cases | Never — one kwarg |
| `load=True` on dbfread | Simpler iteration | OOM on large journals; blocks in WASM | Never — lazy is always correct |
| `list(records)` before DataFrame | Simpler code | Doubles memory; fatal for large files in WASM | Never for WASM path; acceptable in CLI if file is known small |
| Load Pyodide in main thread | Simpler implementation | Freezes UI during 5 s cold start | Never in production; acceptable in a proof-of-concept prototype |
| Load Pyodide from CDN without service worker | Avoids service worker complexity | 20 s cold start on every visit | Prototyping only, must be fixed before any user testing |
| Bundle Pyodide assets in Pages deploy | Simpler local-dev experience | Exceeds Cloudflare Pages 20K file / 25 MB file limits | Never |
| Shared `_iter_rows()` with `try/except` inside | Less code | Strict mode silently stops failing | Never |
| Hardcode column names in non-DIARIO readers | Faster to write | KeyError on alternate-version ContaPlus installs | Never — candidate lists are cheap |
| Treat BALAN.DBF as authoritative | One fewer disclaimer to write | User gets wrong tax-filing numbers | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `dbfread` + bytes-first API | Pass `BytesIO` directly to `DBF()` | Write to temp path (CLI) or Emscripten VFS (WASM), pass the path |
| `openpyxl` + in-browser download | Call `wb.save("file.xlsx")` (no filesystem) | `buf = BytesIO(); wb.save(buf); buf.seek(0)` → pass `buf.getvalue()` as `Uint8Array` to JS `Blob` → `URL.createObjectURL` |
| `micropip` + local wheel | `micropip.install(".")` or `micropip.install("file:///...")` | Build wheel: `uv build`; serve from Vite dev server; `micropip.install("/dev/wheel.whl")` |
| `micropip` + PyPI | Assumes all deps have pure-Python wheels | Verify `dbfread` is pure-Python (it is, MIT); verify `openpyxl` and `pandas` are Pyodide-bundled (they are) |
| Cloudflare Pages + COOP/COEP | No `_headers` file | Add `_headers` with `Cross-Origin-Embedder-Policy: require-corp` and `Cross-Origin-Opener-Policy: same-origin` |
| Cloudflare Pages + Pyodide assets | Copy `pyodide/` into `public/` | Load from jsDelivr CDN; cache via service worker |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `load=True` on dbfread | High memory, slow first load | Always use lazy iteration (default) | ~10K rows in WASM, ~1M rows in CLI |
| `list(records)` before DataFrame | Memory doubles vs streaming | Stream directly into DataFrame constructor | ~500K rows in WASM (2 GB heap) |
| Re-initialising Pyodide per conversion | 5 s overhead on every file drop | Initialise once on page load; keep the runtime alive | Every conversion |
| `URL.createObjectURL` leak | Memory grows with each conversion | Always call `URL.revokeObjectURL` after the download link is clicked | After ~20 conversions |
| Loading all multi-year journals into one DataFrame | Peak memory = sum of all years | Expose per-year selection in the multi-exercise walk | ~3 years of journal data in WASM |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `zipfile.extractall(target)` without entry validation | Zip-slip: write outside temp dir on CLI/library path | Validate each member's resolved path stays inside target before extracting |
| Trusting Python 3.12 `filter="data"` alone | Misses Python <3.12 (irrelevant here — project is >=3.13) and relies on opt-in default | Belt-and-suspenders: explicit path validation loop + `filter="data"` |
| Loading WASM/wheels from a non-CORS-enabled self-hosted server | `micropip.install` fails silently or with CORS error | Use jsDelivr CDN (sets CORS) for Pyodide runtime; serve project wheel from same origin |
| Serving the PWA without COOP/COEP headers | `SharedArrayBuffer` unavailable; Pyodide may fail or degrade | `_headers` file on Cloudflare Pages |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Blank page for 20 s on first cold load | User thinks app is broken, leaves | Progress indicator with synthetic steps; Web Worker for non-blocking init |
| Generic "Conversion failed" on a structured `ContaPlusReadError` | User cannot diagnose their file | Render `row_index`, `column`, and `message` from the structured error in the UI |
| No warning that BALAN.DBF may be stale | User files taxes with wrong figures | Sheet-level warning note in the BALAN XLSX sheet + README callout |
| Multi-company ZIP with no company picker | Fails with "multi-company ZIP" error and no UI to pick | Show a company-selector dropdown when multi-company ZIP is detected before running conversion |
| XLSX download silently overwrites previous file | Users lose previous output if converting multiple files | Auto-include source filename and timestamp in the default download filename |

---

## "Looks Done But Isn't" Checklist

- [ ] **bytes-first API:** Reader accepts `bytes` / `BytesIO` — verify it runs *without* a real filesystem path, including in a WASM environment.
- [ ] **ZIP extraction safety:** Every `extractall` call is preceded by a path-traversal validation loop — verify with a fixture that contains a `../` entry.
- [ ] **encoding kwarg:** Every `DBF()` call site has `encoding="cp850"` — verify with a grep; the cp1252-byte29 fixture pins the behaviour.
- [ ] **lazy iteration:** No `load=True` anywhere — verify with a grep; streaming is tested with a large (10K+ row) fixture.
- [ ] **strict/lenient split:** A file with one bad row in the middle raises in strict mode and collects in lenient — verify with a specific test.
- [ ] **BALAN disclaimer:** The BALAN XLSX sheet has a visible stale-data warning — verify by opening the output.
- [ ] **LGPL in wheel:** The built wheel contains a `LICENSE` file — verify with `unzip -l dist/*.whl | grep LICENSE`.
- [ ] **COOP/COEP headers:** Deployed Cloudflare Pages URL returns both headers — verify with `curl -I`.
- [ ] **Service worker caching:** Second page load does not re-download pyodide assets — verify with DevTools network tab (all cached).
- [ ] **dev-wheel workflow:** PWA dev server tests against locally built wheel, not PyPI — verify the Makefile/justfile target exists and is documented.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| dbfread not accepting BytesIO | HIGH — requires either VFS workaround or custom parser | Option A: write to Emscripten VFS temp file (2–3 days). Option B: vendor minimal DBF parser (2–3 days, more robust long-term). |
| Cold-load UX is unacceptable | MEDIUM — service worker is addable post-launch | Add service worker + Web Worker move; requires re-testing on all browsers. |
| COOP/COEP missing on Pages | LOW — `_headers` file addition + redeploy | Add `_headers`, verify with `curl -I`, redeploy. |
| Strict path silently stopped raising | HIGH — requires auditing all test coverage | Identify where `except` was added; remove it; audit test suite for strict-mode regression tests. |
| BALAN stale data in user's XLSX | HIGH if user filed taxes with wrong figures | Add disclaimer retroactively; publish hotfix release; update README. |
| LGPL compliance gap in wheel | MEDIUM — rebuild and re-publish wheel | Add LICENSE to `pyproject.toml` build includes; `uv build`; re-publish to PyPI. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| dbfread BytesIO limitation | Phase 1 — Reader Core | Test: reader runs from `BytesIO` with no real path |
| cp850 encoding kwarg missing | Phase 1 — Reader Core | Test: cp1252-byte29 fixture; grep for `DBF(` without `encoding=` |
| ZIP-slip safety | Phase 1 — ZIP handling | Test: fixture with `../` entry raises `ContaPlusReadError` |
| Strict/lenient split architecture | Phase 2 — Lenient path | Test: one-bad-row-in-middle raises strict, collects lenient |
| Column-name variants in non-DIARIO tables | Phase 2 — Table readers | Test: alternate-column-name fixture per table |
| BALAN staleness disclaimer | Phase 2 — BALAN reader | Visual: inspect XLSX output sheet for warning note |
| Streaming write to openpyxl | Phase 2 — XLSX renderer | Test: large fixture (>10K rows) converts without OOM |
| LGPL wheel compliance | Phase 4 — Packaging | Verify: `unzip -l dist/*.whl | grep LICENSE` |
| dev-wheel micropip workflow | Phase 3 — PWA shell | Verify: `make dev-wheel` exists and is documented |
| COOP/COEP headers | Phase 3 — Cloudflare deploy | Verify: `curl -I` on deployed URL shows both headers |
| Service worker caching | Phase 3 — PWA shell | Verify: DevTools network shows cached assets on second load |
| Cloudflare Pages file/size limits | Phase 3 — Cloudflare deploy | Verify: deploy succeeds; Pyodide loaded from CDN not Pages |
| WASM memory for large journals | Phase 2 — XLSX renderer | Test: 500K-row fixture (or count-based guard) does not OOM |
| SharedArrayBuffer / WASM degradation | Phase 3 — PWA shell | Verify: browser console shows no SharedArrayBuffer errors |

---

## Sources

- SEED.md §1 (DBF format), §2 (encoding), §3 (column variants), §4 (ZIP layout), §5 (dbfread invocation), §6 (format gotchas) — primary reference
- PROJECT.md — requirements and constraints
- olemb/dbfread GitHub Issue #25 — file-like object / BytesIO not natively supported
- Snyk dbfread health analysis — inactive, last release 2.0.7, no maintenance since 2022
- Pyodide docs — service worker guide, WASM constraints, package sizes
- Pyodide GitHub Issues #1879, #1473 — memory errors on large DataFrames in WASM
- Python bug tracker Issue #35909 — zip-slip vulnerability
- Python 3.12 zipfile docs — `filter=` parameter added, opt-in, default still unsafe
- Cloudflare Pages limits docs — 25 MiB per file, 20,000 files per deployment
- Cloudflare Community — COEP/COOP headers via `_headers` file
- micropip docs — `emfs:` URI scheme for Emscripten VFS wheels
- pyodide/pyodide Discussion #4047 — SharedArrayBuffer / COOP+COEP requirements

---
*Pitfalls research for: ContaPlus DBF extraction library + CLI + in-browser PWA*
*Researched: 2026-05-15*
