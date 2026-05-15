# Project Research Summary

**Project:** contaplus-reader
**Domain:** Legacy accounting-data extraction tooling (Python library + CLI + client-side browser PWA)
**Researched:** 2026-05-15
**Confidence:** MEDIUM-HIGH

## Executive Summary

`contaplus-reader` is a three-artifact data-extraction tool — a PyPI library, a CLI, and a browser PWA — for reading Sage ContaPlus accounting exports. The product is well-defined: a legacy dBASE-family format with a fully specified journal schema (`DIARIO.DBF`), a partially specified chart-of-accounts table (`SUBCTA.DBF`), a known-unreliable cached trial balance (`BALAN.DBF`), and three under-documented operational tables (`venci`/`prede`/`amoinv`). The recommended approach is to build outward from the proven journal reader that already exists in tax-workbench — port it bytes-first into a standalone library, add secondary table readers, build the CLI and shared XLSX renderer on top, then cap with the PWA. The dependency chain is strict: everything blocks on the `bytes_to_tmppath` bridge, and the PWA blocks on a working published wheel.

The stack is settled with no meaningful alternatives: `uv` + `uv_build` for the Python side, raw Pyodide 0.29.4 (**not** PyScript) in a Web Worker for the browser runtime, Vite 6 + React + shadcn/ui for the PWA shell, Cloudflare Pages for hosting. The single highest-risk item is the Pyodide cold-load path (~17–25 MB on first visit): without a service worker and a Web Worker the PWA is unusable. This must be proven with a dedicated spike before committing to the full PWA build.

The highest-confidence table schema is `DIARIO.DBF` (fully pinned in `SEED.md`, rules D-A1…D-E3). `SUBCTA.DBF` is MEDIUM confidence with known field-name variants that must be resolved defensively at parse time. `venci.dbf`, `prede.dbf`, and `amoinv.dbf` are LOW confidence — their typed readers should not be built until the confidential `pii-test-data/` archives are inspected to pin the actual field layouts. That git-ignored directory is the local validation gate that resolves the remaining open schema questions; it is an execution step, not research debt.

## Key Findings

### Recommended Stack

Detail in [STACK.md](STACK.md). The Python side is uncontroversial; the PWA runtime is the one decision that carried real uncertainty, and research resolved it in favour of raw Pyodide over PyScript (PyScript's DOM-centric model conflicts with React's virtual DOM ownership).

**Core technologies:**
- **`uv` + `uv_build` (≥0.11.14)** — build backend & workflow; zero-config for pure-Python src-layout; one `uv build` wheel serves PyPI *and* local dev / `micropip`
- **`dbfread` ≥2.0.7** — DBF reading (pure-Python, MIT); note: path-only, needs a bytes bridge
- **`pandas` + `openpyxl` 3.1.5** — data frame + XLSX; pandas pre-built in Pyodide, openpyxl & dbfread install via `micropip`
- **Typer** — thin CLI; type-hint driven, first-class `uvx`/`pipx` consumption
- **Raw Pyodide 0.29.4** (Python 3.13.2) in a Web Worker — in-browser runtime; **not** PyScript
- **Vite 6 + React + shadcn/ui** — PWA shell; **Cloudflare Pages** static hosting

### Expected Features

Detail in [FEATURES.md](FEATURES.md). The user broadened scope to "extract *all* ContaPlus data" via a typed reader per table.

**Must have (table stakes):**
- Read `DIARIO.DBF` (journal) — port the existing validated reader and rules
- Read `SUBCTA.DBF` (chart of subaccounts) — defensive field-name resolution
- Styled multi-sheet `.xlsx` output — one sheet per extracted table
- `.dbf` and backup `.zip` input; multi-company ZIP disambiguation
- Journal enrichment with account names from `SUBCTA.DBF` when present
- Lenient conversion path — extract what's readable, report problems, never abort

**Should have (competitive):**
- `BALAN.DBF` raw extraction with a visible "derived/unreliable" disclaimer
- Recomputed trial balance from `DIARIO.DBF` (authoritative alternative to BALAN)
- Client-side PWA — conversion in-browser, file never uploaded (genuine differentiator; no open-source competitor exists)

**Defer (v2+):**
- Typed readers for `venci`/`prede`/`amoinv` — raw column dump in v1; typed readers need real-data schema validation first
- FacturaPlus article tables — out of scope (different product)
- Encoding autodetect, alpha-prefixed subaccounts, batch CLI (already in PROJECT.md Out of Scope)

### Architecture Approach

Detail in [ARCHITECTURE.md](ARCHITECTURE.md). Single `pyproject.toml` — library + CLI in one Python package (`src/contaplus_reader/`, CLI via `[project.scripts]`); the PWA is a separate Vite build in `web/` that consumes the library via `micropip`. Pyodide's MEMFS means stdlib filesystem APIs (`tempfile`, `Path`, `zipfile`) work unchanged in-browser — so the library has **zero** browser-specific code paths.

**Major components:**
1. **Input layer** — suffix sniffing (`.dbf`/`.zip`), `bytes_to_tmppath` bridge (works around `dbfread` being path-only), zip-slip-safe in-memory ZIP extraction
2. **Typed per-table readers** — `readers/journal.py` (port) plus `subcta`, `balan`, … each with its own result type and rules; strict + lenient postures share core code
3. **Result models + `ContaPlusReadError`** — self-contained types, no `tw-domain` dependency
4. **Shared XLSX renderer** — lives *inside* the library package so the bundled template is reachable via `importlib.resources` in both CPython and Pyodide
5. **CLI** (thin Typer wrapper) and **PWA** (Vite/shadcn + Pyodide Web Worker)

### Critical Pitfalls

Detail in [PITFALLS.md](PITFALLS.md).

1. **`dbfread` does not accept `BytesIO`** (issue #25, never merged; library inactive) — the bytes-first API is the foundational Phase 1 decision: solve via an Emscripten/MEMFS temp-file bridge (or evaluate a vendored minimal DBF parser).
2. **Pyodide cold-load is ~17–25 MB** — service worker + Web Worker (non-blocking init) + progress indicator are mandatory, not optional.
3. **Cloudflare Pages hard limits** — 25 MiB per file, 20,000 files per deploy: load Pyodide from a CDN (jsDelivr), don't bundle it; set COOP/COEP headers via `_headers` for SharedArrayBuffer.
4. **`zipfile.extractall` is unsafe by default in Python 3.13** (`filter="data"` is opt-in) — implement the manual zip-slip path-traversal check; it works from an in-memory buffer too.
5. **`BALAN.DBF` is a stale derived cache** — never treat as authoritative; emit a visible disclaimer in its sheet.

## Implications for Roadmap

Based on research, suggested phase structure (4 phases):

### Phase 1: Reader Core & Foundation
**Rationale:** Everything blocks on the bytes-first input layer; the journal reader is the proven, fully-specified starting point.
**Delivers:** Bytes-first `DIARIO.DBF` reader, `bytes_to_tmppath` bridge, zip-slip-safe in-memory ZIP extraction, result models, `ContaPlusReadError`, strict `read()` API, synthetic-fixture test harness.
**Addresses:** Journal table-stakes feature; ported rules D-A1…D-E3.
**Avoids:** `dbfread`/`BytesIO` pitfall, zip-slip pitfall.

### Phase 2: Full Table Readers, Lenient Path & XLSX Renderer
**Rationale:** Secondary readers and the lenient posture must exist before the renderer (which must handle `problems: list[ContaPlusReadError]`).
**Delivers:** `SUBCTA.DBF` reader + journal name-enrichment, `BALAN.DBF` raw extraction with disclaimer, `read_lenient()` posture, shared streaming openpyxl XLSX renderer with styled template.
**Uses:** `pandas`, `openpyxl`, `importlib.resources` for the bundled template.
**Implements:** Typed-reader and shared-renderer components.
**Note:** Inspect `pii-test-data/` archives to pin `SUBCTA` field-name variants before finalizing that reader.

### Phase 3: CLI & PyPI Publication
**Rationale:** The CLI is trivially thin once the renderer works — and its `uv build` is the step that produces the wheel Phase 4 needs.
**Delivers:** `contaplus2xlsx` Typer CLI (single-file convert, multi-company flag), LGPL-compliant wheel, PyPI publication, documented dev-wheel workflow (Makefile/justfile).
**Uses:** Typer, `uv build`, `uv publish`.

### Phase 4: PWA (Spike-First)
**Rationale:** Highest-risk artifact; the Pyodide + Web Worker + `micropip` + Cloudflare COOP/COEP combination must be empirically validated before the full shell is built.
**Delivers:** A Pyodide/`micropip` spike that gates the full build, then the Vite + React + shadcn PWA — drag-drop in, styled `.xlsx` out, service-worker caching, Cloudflare Pages deploy.

### Phase Ordering Rationale

- `bytes_to_tmppath` is the single foundational decision; Pyodide MEMFS means this one bridge makes all library code run identically in CPython and in-browser.
- The lenient path must be designed before the XLSX renderer, because the renderer consumes the collected problem list.
- The CLI phase produces the published wheel; the PWA cannot install `contaplus-reader` via `micropip` until that wheel exists.
- The PWA spike gates the full PWA build — do not start the shell until `micropip` + local wheel + Web Worker + COOP/COEP is proven.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (PWA):** The Pyodide + Web Worker + `micropip` + Cloudflare COOP/COEP combination is not empirically tested in this exact config — the spike itself is the validation.

Phases with standard patterns (skip research-phase):
- **Phase 1:** `DIARIO.DBF` fully pinned in `SEED.md`; `bytes_to_tmppath` pattern fully specified.
- **Phase 2:** `SUBCTA` field variants documented; `pii-test-data/` inspection replaces external research.
- **Phase 3:** Typer + `uv publish` fully documented; LGPL steps specified in PITFALLS.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python tooling from official sources; Pyodide package availability confirmed; openpyxl-via-micropip MEDIUM-HIGH |
| Features | MEDIUM | `DIARIO` HIGH (fully pinned); `SUBCTA` MEDIUM; `venci`/`prede`/`amoinv` LOW (no public schema) |
| Architecture | HIGH | All patterns specified with code; `dbfread` constraint confirmed by source inspection; Pyodide MEMFS from official docs |
| Pitfalls | HIGH (library) / MEDIUM (Pyodide) | Library pitfalls definitive; Pyodide runtime pitfalls well-documented but not empirically validated |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **`SUBCTA.DBF` field-name variant in real data** — resolve by inspecting `pii-test-data/` archives during Phase 2 (execution step, not research debt).
- **`venci`/`prede`/`amoinv` field layouts** — run `DBF(path).field_names` against the real archives during Phase 2; v1 emits a raw column dump until typed readers are justified.
- **Pyodide 0.29.4 + `openpyxl` via `micropip`** — validate in the Phase 4 spike (currently MEDIUM-HIGH from docs only).
- **Workbox + Pyodide CDN caching** — `maximumFileSizeToCacheInBytes` + `runtimeCaching` interaction needs live validation on Cloudflare Pages.

## Sources

### Primary (HIGH confidence)
- `SEED.md` — embedded `DIARIO.DBF` format reference, business rules D-A1…D-E3, error model, test inventory
- `uv` / `uv_build`, Typer, Pyodide, Cloudflare Pages official docs — versions, packaging, hosting limits
- `dbfread` source code — confirmed path-only constraint (issue #25)

### Secondary (MEDIUM confidence)
- Sage ContaPlus protocol PDFs, jggomez & Domatix importer source, accounting forums — `SUBCTA.DBF` / `BALAN.DBF` schemas and field variants
- Community sources — Pyodide bundle sizes, service-worker caching patterns

### Tertiary (LOW confidence)
- Forum mentions of `venci.dbf` / `prede.dbf` / `amoinv.dbf` existence — field layouts not publicly documented; require real-data inspection

---
*Research completed: 2026-05-15*
*Ready for roadmap: yes*
