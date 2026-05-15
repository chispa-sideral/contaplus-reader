<!-- GSD:project-start source:PROJECT.md -->
## Project

**contaplus-reader**

A standalone tool that reads Sage **ContaPlus** accounting exports (raw `.dbf`
tables and ContaPlus backup `.zip` archives) and extracts *all* their data into
usable formats. It ships as three artifacts from one repo: a **library**
(`contaplus-reader`, published to PyPI), a **CLI** (`contaplus2xlsx`,
`.dbf`/`.zip` → styled `.xlsx`), and a fully client-side **PWA** where anyone can
convert their ContaPlus files in the browser with no install and no upload. It is
for anyone migrating off Sage ContaPlus — and for tax-workbench, which currently
owns this logic and will become a thin consumer.

**Core Value:** The library reads ContaPlus exports **correctly** — above all the journal, whose
strict, validated reading tax-workbench depends on for tax filings. Everything
else (CLI, PWA, styling) is delivery; correct extraction cannot fail.

### Constraints

- **Tech stack (library + CLI)**: Python `>=3.13` — matches existing `tw-contaplus` code
- **Runtime deps**: `dbfread >=2.0.7` (pure-Python, MIT, read-only) for DBF reading; `pandas` + `openpyxl` for XLSX — all pure-Python / Pyodide-available
- **Dev deps**: `dbf` (ethanfurman, BSD) — fixture generation only, never a runtime dependency
- **Tech stack (PWA)**: shadcn UI, Pyodide/PyScript runtime (TBD by research), deployed to Cloudflare Pages (static-only hosting)
- **License**: LGPL-3.0-or-later — consistent with current `tw-contaplus`
- **Dependencies**: must NOT depend on `tw-domain` — the library returns its own result types
- **Compatibility**: read API must be bytes-first — the browser has no filesystem path; ZIP extraction must work from an in-memory buffer
- **Privacy**: PWA conversion is fully client-side — the ContaPlus file never leaves the user's machine
- **i18n**: English everything — this is an external, public project
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.13 | Library + CLI runtime | Matches existing tw-contaplus; modern typing features (PEP 695 type aliases, tomllib, etc.); required by project constraint |
| uv | >=0.7 (current: 0.7.x) | Project manager, build, publish, editable installs, uvx runner | Single tool replacing pip/venv/pip-tools/twine; `uv build` + `uv publish` cover the full PyPI workflow; `uvx` is the modern pipx replacement for CLI tool consumption |
| uv_build | >=0.11.14,<0.12 | Build backend (wheel + sdist) | uv's own backend became stable in mid-2025; zero-config for pure-Python src-layout packages; 10-35x faster than hatchling/flit; tightly integrated with `uv build`; no separate install step |
| Pyodide | 0.29.4 (stable) | WASM Python runtime for PWA | Runs CPython 3.13.2 in-browser; pandas pre-compiled in distribution; pure-Python wheels (openpyxl, dbfread) installed via micropip; the only production-ready option for running the full stdlib + pandas in a browser — no equivalent in PyScript or MicroPython |
| React + TypeScript | 18.x / 5.x | PWA UI framework | shadcn/ui requires React; TypeScript required for type-safe worker bridge; consistent with Marc's standard TS+React+Vite stack |
| Vite | 6.x | PWA build tool | shadcn/ui official docs recommend Vite for setup; fastest dev server; `vite-plugin-static-copy` handles Pyodide WASM asset copying to dist |
| shadcn/ui | latest (CLI-driven) | PWA component library | Explicitly named in project constraints; copy-into-project model means no runtime library dependency; built on Radix UI + Tailwind CSS v4 |
| Tailwind CSS | v4 | PWA styling | shadcn/ui 2025 setup targets Tailwind v4 via `@tailwindcss/vite` plugin; single config entry in vite.config.ts |
| Cloudflare Pages | static-only | PWA hosting | Explicitly named in project constraints; free tier; global CDN; HTTPS by default; zero server config for static assets |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dbfread | >=2.0.7 | DBF file reading (runtime dep) | The chosen DBF reader; pure-Python, MIT, lazy iteration; 2.0.7 is the last release (2016) and remains the de-facto standard for read-only DBF access in Python; no C extensions = Pyodide compatible |
| pandas | >=2.2 | DataFrame manipulation + XLSX output (runtime dep) | XLSX writing via openpyxl engine; pre-compiled in Pyodide 0.29 distribution, loaded via `pyodide.loadPackage("pandas")` not micropip |
| openpyxl | >=3.1.5 | XLSX engine for pandas (runtime dep) | Pure Python (`py2.py3-none-any.whl`); NOT pre-compiled in Pyodide — must be installed via `micropip.install("openpyxl")`; current PyPI version 3.1.5 |
| dbf (ethanfurman) | >=0.99.11 | Dev-only: synthetic DBF fixture generation in tests | BSD, pure Python, actively maintained (last release Sep 2025); never a runtime dep — test conftest.py only |
| typer | >=0.13 | CLI framework for contaplus2xlsx | See CLI decision section below |
| rich | >=13 | Terminal output for CLI (pulled in by typer[all]) | Progress display; error formatting; included when typer installed with extras |
| vite-plugin-static-copy | >=2.0 | Copy Pyodide WASM assets to dist/assets at build time | Required because Pyodide's .wasm/.js runtime files cannot be bundled by Vite's normal import mechanism; must be excluded from optimizeDeps and copied manually |
| vite-plugin-pwa | >=0.21 | Service worker + offline caching for PWA | workbox-based; handles precaching of app shell; runtime caching strategy for Pyodide CDN/self-hosted assets |
| comlink | >=4.4 | Typed RPC bridge between React main thread and Pyodide web worker | Eliminates postMessage boilerplate; lets you call Python execution functions as normal async JS functions; use-pyodide library uses this pattern |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Dependency management, virtual env, build, publish, tool runner | `uv sync` installs all deps including dev; `uv build` produces wheel + sdist in dist/; `uv publish` uploads to PyPI |
| `uv run pytest` | Test runner invocation | No manual venv activation needed; `uv run` picks up pyproject.toml dev deps automatically |
| pytest | Test framework | Standard; session-scoped fixtures for synthetic DBF generation |
| pnpm | Frontend package manager | Marc's standard JS stack; faster than npm; workspace support if pwa/ becomes a separate subdir |
| TypeScript (tsc) | Type checking for PWA | Strict mode; no `any`; per Marc's global rules |
## Installation
# Python library + CLI — initialize project
# (then edit pyproject.toml — see pyproject.toml layout below)
# Add runtime dependencies
# Add dev dependencies
# Build wheel + sdist
# Publish to PyPI (set UV_PUBLISH_TOKEN env var)
# PWA — scaffold in pwa/ subdirectory
### pyproject.toml Layout
## Decision: CLI Framework — Typer
- `contaplus2xlsx` is a thin single-file-conversion CLI with 3-4 flags. Typer's type-hint-driven approach means the entire CLI fits in ~30 lines.
- Typer produces `--help` output automatically from function signatures and type annotations — no manual help string maintenance.
- `uvx contaplus-reader` or `uvx contaplus2xlsx` (once the script entry point is registered) gives isolated, reproducible invocation without polluting the user's Python environment. This is the modern `pipx` replacement.
- Typer is the 2025 consensus for new greenfield Python CLIs. Click is appropriate for legacy systems or complex multi-command hierarchies — this CLI has exactly one command.
- `argparse` is a non-starter: verbose, no type coercion, poor help formatting.
- Rich (pulled in by `typer[all]`) gives clean error panels for `ContaPlusReadError` surfacing, which matters for the UX of a migration tool.
- Click directly: more boilerplate than Typer for a simple CLI; Typer wraps Click, so nothing is lost.
- argparse: see above.
- Plain `sys.argv` parsing: no help generation, no type safety.
## Decision: PWA Runtime — Raw Pyodide (NOT PyScript)
### Pyodide vs PyScript
| Criterion | Raw Pyodide | PyScript |
|-----------|------------|---------|
| React integration | Purpose-built: npm package + hook pattern + web worker | HTML-centric framework; bolts onto React awkwardly via script tags or workarounds |
| Control | Full: you control initialization, micropip calls, worker lifecycle | Framework makes decisions for you; harder to customize load order |
| Web worker support | First-class: official docs and examples for loadPyodide in a worker | Supported but wrapped in PyScript's own worker abstraction |
| Overhead | Only what you use | PyScript adds its own layer over Pyodide with no benefit for this use case |
| shadcn integration | Zero friction: Pyodide runs in a worker, React/shadcn owns the DOM entirely | Friction: PyScript wants to own DOM elements; conflicts with React's virtual DOM |
| Community patterns | Multiple production React+Vite+Pyodide examples (use-pyodide hook library, verbitskiy.co guide) | Fewer React examples; most examples use vanilla HTML |
### Pyodide Package Landscape (0.29.4 / Python 3.13.2)
| Package | Status in Pyodide 0.29.4 | Load method | Notes |
|---------|--------------------------|-------------|-------|
| pandas | Pre-compiled built-in | `pyodide.loadPackage("pandas")` | Pre-compiled with -Oz in 0.29; significant load size (~10 MB gzipped with numpy) |
| openpyxl 3.1.5 | NOT pre-compiled | `micropip.install("openpyxl")` | Pure Python `py2.py3-none-any.whl`; micropip resolves from PyPI cleanly |
| dbfread 2.0.7 | NOT pre-compiled | `micropip.install("dbfread")` | Pure Python, no deps outside stdlib; micropip resolves cleanly from PyPI |
| contaplus-reader | NOT pre-compiled | `micropip.install("contaplus-reader")` | Pure Python wheel produced by `uv build`; micropip can install from PyPI or from a served local wheel URL |
| numpy | Pre-compiled built-in | auto-loaded as pandas dep | Pulled in by pandas |
### Cold Load Reality
- Pyodide core (`pyodide.js` + WASM): ~6.4 MB gzipped on first visit
- Adding pandas + numpy: ~10.5 MB additional gzipped
- Total first-visit download: ~17 MB gzipped, ~50 MB uncompressed
- Subsequent visits (service worker cached): near-instant
- Cold load time estimate: 4-8 seconds on broadband; unacceptable on mobile — **the service worker caching strategy is critical for UX**
### micropip and Local Development Wheels
## PWA UI + Hosting Architecture
### shadcn/ui with Vite
### Vite Config for Pyodide
### Web Worker Architecture
### Service Worker / PWA Offline Caching Strategy
- **App shell** (HTML, CSS, JS chunks < 2 MB): Workbox precache via `vite-plugin-pwa`
- **Pyodide runtime** (~6.4 MB gzipped): `runtimeCaching` with `CacheFirst` strategy, served from Cloudflare CDN or self-hosted in `dist/assets/`
- **Python packages** (pandas, openpyxl, etc.): `runtimeCaching` with `CacheFirst` — micropip fetches from PyPI/jsDelivr on first use, service worker intercepts and caches for offline
- **Workbox `maximumFileSizeToCacheInBytes`**: Set to `50 * 1024 * 1024` (50 MB) to allow WASM files through the precache manifest if self-hosting Pyodide
### Cloudflare Pages Deployment
- Static-only hosting fits perfectly: `pnpm run build` produces a `dist/` folder; push to Cloudflare Pages via Git integration or `wrangler pages deploy dist/`
- No server-side config needed — the entire app is JS + WASM + Python wheels
- One caveat: Cloudflare's default CDN cache TTL is 1 week; after deploying a new version, old service workers may serve stale assets until the SW update cycle runs. Use cache-busting hashes (Vite does this automatically) and configure Workbox's `clientsClaim: true` + `skipWaiting: true` for immediate SW activation
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Build backend | uv_build | hatchling | hatchling is the older uv default; uv_build is faster and zero-config for pure Python; only consider hatchling if you need build hooks or non-standard project layout |
| Build backend | uv_build | setuptools | Legacy; verbose configuration; no advantage for a new greenfield pure-Python project |
| CLI framework | typer | click | Click is Typer's foundation; Typer adds type-hint driven API on top; no reason to use Click directly for a new single-command CLI |
| CLI framework | typer | argparse | Standard library but verbose, poor UX, no automatic type coercion |
| PWA Python runtime | Pyodide (raw) | PyScript | PyScript wraps Pyodide; adds overhead; designed for HTML-centric use, not React component trees; raw Pyodide gives full control with less magic |
| PWA Python runtime | Pyodide | Brython | Brython does not support the scientific stack (pandas, numpy); transpiles Python to JS rather than running CPython; not suitable |
| PWA Python runtime | Pyodide | Skulpt | Same problem as Brython; subset of Python only; no pandas |
| PWA build tool | Vite | webpack/CRA | CRA is deprecated; webpack is slower and more complex; Vite is the 2025 standard for React projects |
| PWA deployment | Cloudflare Pages | Netlify / Vercel | All three are viable; Cloudflare Pages is explicitly named in project constraints; free tier covers this use case |
| Pyodide loading | Web worker | Main thread | Main thread Pyodide initialization blocks the UI for seconds; a drag-drop UI with a frozen tab is terrible UX; web worker is mandatory |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| setuptools as build backend | Unnecessary complexity for a pure-Python src-layout project; requires `setup.cfg` or verbose `[tool.setuptools]` config | uv_build |
| PyScript | Designed for HTML-centric Python-in-the-DOM use cases; React integration is awkward; adds a layer of abstraction over Pyodide with no benefit here | Raw Pyodide via npm package |
| `loadPyodide` on the main thread | Blocks the browser UI for 4-8 seconds during initialization | Web worker + Comlink |
| Precaching all Pyodide assets with Workbox default config | Default 2 MB limit causes WASM files to be silently dropped from the precache manifest | Override `maximumFileSizeToCacheInBytes` or use `runtimeCaching` with CacheFirst |
| `file://` URLs for micropip in browser | Browsers block `file://`; micropip explicitly documents this as Node.js only | Serve local wheel from Vite dev server or use emfs:// path |
| `latin-1` encoding for DBF files | Decodes CP850 bytes to wrong Unicode codepoints (e.g., `0x82` → U+0082 control char instead of `é`) | `encoding='cp850'` unconditionally (per SEED.md D-D1 rule) |
| `dbfread` with `load=True` on large journals | Loads entire file into memory; multi-year journals can be millions of rows | Lazy iteration (default `load=False`) |
| Committing binary `.dbf` blobs as test fixtures | Makes repo opaque; fixtures drift from code | Generate synthetic DBFs at test collection time via `dbf` package (ethanfurman) |
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Pyodide 0.29.4 | Python 3.13.2 | Match: project requires Python >=3.13; Pyodide 0.29 ships 3.13.2 |
| pandas >=2.2 | openpyxl >=3.1 | openpyxl is the pandas Excel engine; pandas 2.x requires openpyxl >=3.0.10 |
| uv_build 0.11.14 | pure Python only | uv_build only supports pure Python packages — valid here, no C extensions |
| Tailwind v4 | shadcn/ui 2025 | shadcn officially supports Tailwind v4; use `@tailwindcss/vite` not PostCSS config |
| vite-plugin-static-copy 2.x | Vite 6.x | Tested together per Pyodide Vite docs (0.26+ tested with these versions) |
| dbfread 2.0.7 | Python 3.13 | Pure Python, no C extensions; stdlib-only; works with any Python 3.x including 3.13 |
| dbf 0.99.11 (ethanfurman) | Python 3.13 | Explicitly supports 3.3–3.13 per PyPI metadata; dev-only fixture generator |
## Confidence Assessment
| Area | Confidence | Reason |
|------|------------|--------|
| Python tooling (uv, uv_build, pyproject.toml) | HIGH | Official docs confirm; uv_build 0.11.14 is the current stable version from PyPI |
| CLI framework (Typer) | HIGH | Clear community consensus; official Typer docs confirm uvx/pipx workflow |
| Runtime deps (dbfread, pandas, openpyxl) | HIGH | All pure-Python; versions verified on PyPI; pandas pre-compiled in Pyodide confirmed from multiple sources |
| Pyodide version (0.29.4 / Python 3.13.2) | HIGH | Verified from PyPI search results showing stable release docs |
| openpyxl NOT in Pyodide pre-compiled set | MEDIUM-HIGH | Absence of openpyxl meta.yaml in Pyodide's packages/ dir, plus GitHub issue #2959 requesting it — consistent with micropip-only install |
| micropip resolves dbfread + openpyxl from PyPI | MEDIUM-HIGH | Both are pure-Python `py3-none-any.whl`; micropip docs confirm pure-Python PyPI wheels work; not empirically tested in this Pyodide version |
| Cold load UX (4-8 sec) | MEDIUM | Derived from Pyodide docs stating 6.4 MB core + 10.5 MB pandas/numpy; actual times vary by network/device — must be validated in Phase 1 PWA work |
| Service worker / Workbox offline strategy | MEDIUM | Pattern is standard and documented; the specific Pyodide WASM file size exceeding Workbox defaults is a known gotcha with documented workaround |
| Vite + Pyodide integration | MEDIUM | Documented in Pyodide's bundler guide; tested examples exist; the `viteStaticCopyPyodide` helper pattern is community-confirmed but configuration details may need adjustment for Vite 6 |
## Sources
- [Pyodide 0.29.4 stable](https://pyodide.org/) — version, Python 3.13.2, package availability confirmed
- [Pyodide packages list 0.29.4](https://pyodide.org/en/stable/usage/packages-in-pyodide.html) — pandas in pre-compiled set; openpyxl absent
- [micropip 0.11.0 docs](https://micropip.pyodide.org/en/stable/project/usage.html) — pure-Python wheel install from PyPI
- [uv_build PyPI](https://pypi.org/project/uv-build/) — current version 0.11.14 (released 2026-05-12)
- [uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/) — pyproject.toml configuration, version pinning
- [uv project init docs](https://docs.astral.sh/uv/concepts/projects/init/) — project types, CLI entry points
- [Typer packaging guide](https://typer.tiangolo.com/tutorial/package/) — uvx consumption, `[project.scripts]` setup
- [shadcn/ui Vite installation](https://ui.shadcn.com/docs/installation/vite) — Tailwind v4 + Vite setup commands
- [openpyxl PyPI](https://pypi.org/project/openpyxl/) — current version 3.1.5; pure Python `py2.py3-none-any.whl` confirmed
- [dbfread PyPI](https://pypi.org/project/dbfread/) — version 2.0.7; pure Python; no external deps
- [dbf (ethanfurman) PyPI](https://pypi.org/project/dbf/) — version 0.99.11; Python 3.3–3.13; BSD
- [vite-plugin-pwa service worker precache](https://vite-pwa-org.netlify.app/guide/service-worker-precache) — maximumFileSizeToCacheInBytes, runtimeCaching strategies
- [Pyodide working with bundlers (stable)](https://pyodide.org/en/stable/usage/working-with-bundlers.html) — Vite optimizeDeps exclusion, static copy plugin
- [use-pyodide React hook](https://github.com/holdenmatt/use-pyodide) — web worker + Comlink pattern for React
- [No Backend Needed: Running Python in React with Pyodide](https://verbitskiy.co/blog/no-backend-needed-running-python-in-react-with-pyodide/) — usePyodide singleton hook architecture
- [Pyodide discussion: micropip npm package](https://github.com/pyodide/pyodide/discussions/5155) — local wheel via emfs:// / http URL
- [Python Build Backends 2025 comparison](https://medium.com/@dynamicy/python-build-backends-in-2025-what-to-use-and-why-uv-build-vs-hatchling-vs-poetry-core-94dd6b92248f) — uv_build vs hatchling tradeoffs
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
