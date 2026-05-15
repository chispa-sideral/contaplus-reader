# Stack Research

**Domain:** Python library + CLI + client-side browser PWA (three artifacts, one repo)
**Researched:** 2026-05-15
**Confidence:** HIGH for Python tooling and CLI; MEDIUM-HIGH for PWA/Pyodide runtime; LOW-MEDIUM for cold-load UX specifics

---

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

---

## Installation

```bash
# Python library + CLI — initialize project
uv init --lib contaplus-reader
# (then edit pyproject.toml — see pyproject.toml layout below)

# Add runtime dependencies
uv add "dbfread>=2.0.7" "pandas>=2.2" "openpyxl>=3.1.5" "typer[all]>=0.13"

# Add dev dependencies
uv add --dev "dbf>=0.99.11" pytest

# Build wheel + sdist
uv build

# Publish to PyPI (set UV_PUBLISH_TOKEN env var)
uv publish

# PWA — scaffold in pwa/ subdirectory
pnpm create vite@latest pwa -- --template react-ts
cd pwa
pnpm add tailwindcss @tailwindcss/vite
pnpm dlx shadcn@latest init -t vite
pnpm add pyodide comlink
pnpm add -D vite-plugin-static-copy vite-plugin-pwa
```

### pyproject.toml Layout

```toml
[project]
name = "contaplus-reader"
version = "0.1.0"
description = "Read Sage ContaPlus accounting exports and convert to XLSX"
readme = "README.md"
license = "LGPL-3.0-or-later"
requires-python = ">=3.13"
dependencies = [
    "dbfread>=2.0.7",
    "pandas>=2.2",
    "openpyxl>=3.1.5",
    "typer[all]>=0.13",
]

[project.scripts]
contaplus2xlsx = "contaplus_reader.cli:app"

[build-system]
requires = ["uv_build>=0.11.14,<0.12"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "dbf>=0.99.11",
    "pytest>=8",
]
```

**Notes on `uv_build` version pinning:** The upper bound `<0.12` follows the official uv docs recommendation — it ensures the package builds correctly as new minor versions are released. Check PyPI for the latest 0.11.x before publishing.

---

## Decision: CLI Framework — Typer

**Recommendation: Typer with `[all]` extras** (pulls in Rich for terminal output).

**Rationale:**
- `contaplus2xlsx` is a thin single-file-conversion CLI with 3-4 flags. Typer's type-hint-driven approach means the entire CLI fits in ~30 lines.
- Typer produces `--help` output automatically from function signatures and type annotations — no manual help string maintenance.
- `uvx contaplus-reader` or `uvx contaplus2xlsx` (once the script entry point is registered) gives isolated, reproducible invocation without polluting the user's Python environment. This is the modern `pipx` replacement.
- Typer is the 2025 consensus for new greenfield Python CLIs. Click is appropriate for legacy systems or complex multi-command hierarchies — this CLI has exactly one command.
- `argparse` is a non-starter: verbose, no type coercion, poor help formatting.
- Rich (pulled in by `typer[all]`) gives clean error panels for `ContaPlusReadError` surfacing, which matters for the UX of a migration tool.

**What NOT to use:**
- Click directly: more boilerplate than Typer for a simple CLI; Typer wraps Click, so nothing is lost.
- argparse: see above.
- Plain `sys.argv` parsing: no help generation, no type safety.

---

## Decision: PWA Runtime — Raw Pyodide (NOT PyScript)

**Recommendation: Raw Pyodide 0.29.4 via npm package, loaded in a Web Worker, NOT PyScript.**

**Confidence: MEDIUM-HIGH** — this is the highest-uncertainty item in the stack, but the evidence is clear enough to be prescriptive.

### Pyodide vs PyScript

| Criterion | Raw Pyodide | PyScript |
|-----------|------------|---------|
| React integration | Purpose-built: npm package + hook pattern + web worker | HTML-centric framework; bolts onto React awkwardly via script tags or workarounds |
| Control | Full: you control initialization, micropip calls, worker lifecycle | Framework makes decisions for you; harder to customize load order |
| Web worker support | First-class: official docs and examples for loadPyodide in a worker | Supported but wrapped in PyScript's own worker abstraction |
| Overhead | Only what you use | PyScript adds its own layer over Pyodide with no benefit for this use case |
| shadcn integration | Zero friction: Pyodide runs in a worker, React/shadcn owns the DOM entirely | Friction: PyScript wants to own DOM elements; conflicts with React's virtual DOM |
| Community patterns | Multiple production React+Vite+Pyodide examples (use-pyodide hook library, verbitskiy.co guide) | Fewer React examples; most examples use vanilla HTML |

**PyScript is appropriate when:** you want Python to write to the DOM directly, or you are not using a JS framework. For a React + shadcn app where Python is a computation engine accessed from TypeScript, raw Pyodide is unambiguously correct.

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

In the browser, `file://` URLs are blocked by browsers. The local dev workflow for testing a locally-built `contaplus-reader` wheel is:

1. `uv build` produces `dist/contaplus_reader-0.1.0-py3-none-any.whl`
2. Vite's dev server serves `dist/` — load via `micropip.install("http://localhost:5173/wheels/contaplus_reader-0.1.0-py3-none-any.whl")`
3. Production: `micropip.install("contaplus-reader")` from PyPI directly

In Node.js test environments, `file://` URLs work with micropip.

---

## PWA UI + Hosting Architecture

### shadcn/ui with Vite

The 2025 shadcn/ui Vite setup is:
1. `pnpm create vite@latest pwa -- --template react-ts`
2. Install Tailwind v4 via Vite plugin: `@tailwindcss/vite` (NOT the old PostCSS config path)
3. `pnpm dlx shadcn@latest init -t vite` (handles tsconfig path aliases, adds components.json)
4. Add components individually: `pnpm dlx shadcn@latest add card button progress`

**Tailwind v4 note:** shadcn/ui now officially supports Tailwind CSS v4. The setup uses `@tailwindcss/vite` in `vite.config.ts` instead of a `tailwind.config.ts` file. This is simpler and the current recommended path as of 2025.

### Vite Config for Pyodide

Pyodide cannot be bundled by Vite's standard dependency pre-bundling. Required configuration:

```typescript
// vite.config.ts
import { viteStaticCopyPyodide } from "vite-plugin-static-copy"; // community helper
export default {
  optimizeDeps: { exclude: ["pyodide"] },
  plugins: [
    react(),
    tailwindcss(),
    viteStaticCopyPyodide(), // copies pyodide WASM/JS to dist/assets
    VitePWA({ /* see below */ }),
  ]
}
```

The `viteStaticCopyPyodide()` helper from `@pyodide/vite-plugin` (or manual `vite-plugin-static-copy` config) copies the Pyodide runtime files into `dist/assets/` so they are served alongside the app.

### Web Worker Architecture

Python execution MUST run in a Web Worker to avoid blocking the React UI thread. Pattern:

```
React UI (main thread)
  └─ Comlink proxy → PyodideWorker (web worker)
                       ├─ loadPyodide()
                       ├─ micropip.install([openpyxl, dbfread, contaplus-reader])
                       └─ runConversion(fileBytes) → Uint8Array (xlsx bytes)
```

The worker receives the file as `ArrayBuffer` (from drag-drop FileReader API), runs the full Python pipeline, and returns the XLSX output bytes. The main thread creates a Blob URL and triggers `<a>.click()` for the download.

### Service Worker / PWA Offline Caching Strategy

The large Pyodide runtime cannot be precached by Workbox (default 2 MB precache limit). Recommended strategy:

- **App shell** (HTML, CSS, JS chunks < 2 MB): Workbox precache via `vite-plugin-pwa`
- **Pyodide runtime** (~6.4 MB gzipped): `runtimeCaching` with `CacheFirst` strategy, served from Cloudflare CDN or self-hosted in `dist/assets/`
- **Python packages** (pandas, openpyxl, etc.): `runtimeCaching` with `CacheFirst` — micropip fetches from PyPI/jsDelivr on first use, service worker intercepts and caches for offline
- **Workbox `maximumFileSizeToCacheInBytes`**: Set to `50 * 1024 * 1024` (50 MB) to allow WASM files through the precache manifest if self-hosting Pyodide

**Self-hosting Pyodide vs CDN:** For a privacy-first PWA where the file never leaves the user's machine, self-hosting Pyodide assets in `dist/` is preferable — avoids third-party requests, ensures offline works after the first visit, and gives control over caching headers. Cloudflare Pages serves static assets with aggressive CDN caching automatically.

### Cloudflare Pages Deployment

- Static-only hosting fits perfectly: `pnpm run build` produces a `dist/` folder; push to Cloudflare Pages via Git integration or `wrangler pages deploy dist/`
- No server-side config needed — the entire app is JS + WASM + Python wheels
- One caveat: Cloudflare's default CDN cache TTL is 1 week; after deploying a new version, old service workers may serve stale assets until the SW update cycle runs. Use cache-busting hashes (Vite does this automatically) and configure Workbox's `clientsClaim: true` + `skipWaiting: true` for immediate SW activation

---

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

---

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

---

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

---

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

---

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

---

*Stack research for: contaplus-reader (Python library + CLI + client-side PWA)*
*Researched: 2026-05-15*
