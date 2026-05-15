# Architecture Research

**Domain:** Multi-artifact Python data extraction tool (library + CLI + browser PWA)
**Researched:** 2026-05-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CONSUMERS                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  tax-workbench   │  │  CLI             │  │  PWA             │   │
│  │  (thin adapter)  │  │  contaplus2xlsx  │  │  (Pyodide/React) │   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │
│           │                     │                     │             │
│           │          bytes/file-like in               │             │
│           └─────────────────────┴─────────────────────┘             │
├───────────────────────────────────────────────────────┬─────────────┤
│              contaplus-reader (PyPI library)          │ xlsx_render │
│  ┌────────────────────────────────────────────┐       │  (shared)   │
│  │              read_api.py                   │       │             │
│  │  read(source, table=None, company_dir=None)│       │  WorkbookRe-│
│  │  read_lenient(source, ...)                 │       │  nderer     │
│  └──────────────────┬─────────────────────────┘       │  .render(   │
│                     │                                  │   results) │
│  ┌──────────────────▼─────────────────────────┐       │  -> bytes  │
│  │              io_sniff.py                   │       └─────────────┤
│  │  sniff(source) -> (.dbf | .zip) + bytes    │                     │
│  └──────┬──────────────────┬──────────────────┘                     │
│         │ .dbf             │ .zip                                    │
│  ┌──────▼──────┐   ┌───────▼────────────────┐                       │
│  │ bytes_to_   │   │ zip_extract.py          │                       │
│  │ tmppath.py  │   │ safe_extract_to_tmpdir()│                       │
│  │ (context    │   │ find_dbf_files()        │                       │
│  │  manager)   │   │ resolve_company()       │                       │
│  └──────┬──────┘   └───────┬────────────────┘                       │
│         │                  │ Path(s) to .dbf                         │
│  ┌──────▼──────────────────▼────────────────────────────────────┐   │
│  │                  per-table readers/                           │   │
│  │  journal.py    subcta.py    balan.py    groups.py  …          │   │
│  │  read_journal(path) -> ContaPlusJournal                       │   │
│  │  read_subcta(path) -> ContaPlusSubcta                         │   │
│  │  read_balan(path) -> ContaPlusBalan                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  errors.py: ContaPlusReadError                                       │
│  models.py: ContaPlusJournal, ContaPlusSubcta, ContaPlusBalan, …     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|---------------|-------|
| `read_api.py` | Single public entry point. Dispatches to io_sniff, then per-table readers. Returns typed result models. Offers strict (`read`) and lenient (`read_lenient`) postures. | The only public surface consumers import. |
| `io_sniff.py` | Determines input type from suffix (`.dbf` vs `.zip`). Returns a normalized `(kind, data: bytes)` pair. Rejects unknown suffixes with plain `ValueError`. | No filesystem I/O. Pure bytes inspection. |
| `bytes_to_tmppath.py` | Context manager: writes raw `.dbf` bytes to a POSIX-safe temp file, yields the `Path`, cleans up on exit. Abstracts the `dbfread` path-only constraint from the rest of the library. | Works identically in CPython (disk) and Pyodide (MEMFS). |
| `zip_extract.py` | Zip-slip-safe extraction of a ZIP from bytes into a `TemporaryDirectory`. Recursive `DIARIO.DBF` discovery. Multi-company disambiguation. | Pure stdlib: `io.BytesIO` + `zipfile.ZipFile`. |
| `per-table readers` (`readers/journal.py`, `readers/subcta.py`, etc.) | Each accepts a `Path` to a `.dbf` file. Reads via `dbfread`, applies table-specific business rules, returns a typed result model. | `journal.py` implements D-A1…D-E3 verbatim from SEED. |
| `models.py` | Dataclass result types: `ContaPlusJournal`, `ContaPlusSubcta`, `ContaPlusBalan`, etc. Self-contained — no `tw-domain` dependency. | Pure Python dataclasses. |
| `errors.py` | `ContaPlusReadError` — structured error carrying `row_index`, `column`, `expression`, `original`. | Used by all readers. |
| `xlsx_render/` | `WorkbookRenderer`: accepts a dict of `{sheet_name: DataFrame}` + an optional template path, returns `bytes` (the rendered `.xlsx`). Used by CLI and PWA. Lives in the library package. | `openpyxl`-based. Template is a bundled resource under `contaplus_reader/templates/`. |

---

## Recommended Project Structure

```
contaplus-reader/                 # repo root
├── pyproject.toml                # single pyproject; library + CLI entry point
├── uv.lock
├── SEED.md
├── README.md
│
├── src/
│   └── contaplus_reader/         # the PyPI library package
│       ├── __init__.py           # re-exports: read, read_lenient, ContaPlusReadError, result types
│       ├── read_api.py           # public API: read() / read_lenient()
│       ├── io_sniff.py           # suffix sniffing, bytes normalization
│       ├── bytes_to_tmppath.py   # context manager: bytes -> temp Path -> cleanup
│       ├── zip_extract.py        # zip-slip-safe in-memory extraction + DBF discovery
│       ├── errors.py             # ContaPlusReadError
│       ├── models.py             # ContaPlusJournal, ContaPlusSubcta, ContaPlusBalan, …
│       ├── readers/
│       │   ├── __init__.py
│       │   ├── journal.py        # DIARIO.DBF reader (D-A1…D-E3)
│       │   ├── subcta.py         # SUBCTA.DBF reader
│       │   ├── balan.py          # BALAN.DBF reader (derived; read with caveat)
│       │   └── groups.py         # grupo-level tables (grupos.dbf, usuarios.dbf, …)
│       └── xlsx_render/
│           ├── __init__.py
│           ├── renderer.py       # WorkbookRenderer: results -> bytes
│           └── templates/
│               └── default.xlsx  # styled template workbook (openpyxl-managed)
│
├── cli/
│   └── main.py                   # contaplus2xlsx entry point (thin wrapper)
│
├── web/                          # PWA frontend
│   ├── package.json              # Vite + React + shadcn/ui
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/           # shadcn UI components
│   │   └── worker.ts             # Web Worker: Pyodide bootstrap + Python bridge
│   └── public/
│       └── manifest.json
│
└── tests/
    ├── conftest.py               # synthetic fixture factory (dbf dev dep)
    ├── test_io_sniff.py
    ├── test_zip_extract.py
    ├── test_bytes_to_tmppath.py
    ├── test_journal.py           # ports tw-contaplus test_read_dbf.py coverage
    ├── test_subcta.py
    ├── test_xlsx_render.py
    └── test_cli.py
```

### Structure Rationale

- **`src/contaplus_reader/`** — standard `src` layout. Forces import resolution against the installed package, preventing silent "import from cwd" bugs. Required for correct `uv build` wheel generation.
- **`readers/` sub-package** — isolates per-table logic. Each reader is independently testable. New tables (v2, v3) are added here without touching the public API.
- **`xlsx_render/` inside the library** — the renderer must be available to both CLI and PWA without duplication. The CLI and PWA import the same `WorkbookRenderer`. The template `.xlsx` is a package resource (`importlib.resources`) — it's bundled in the wheel and accessible in Pyodide after `micropip.install`.
- **`cli/` at repo root, not in `src/`** — the CLI is a thin 30-line wrapper. It lives in `cli/main.py` and is wired via `[project.scripts]` in `pyproject.toml`: `contaplus2xlsx = "cli.main:main"`. No separate package needed.
- **`web/` at repo root** — the PWA is a separate build artifact (Vite). It is NOT a Python package; it has its own `package.json` and build pipeline. It consumes the library via `micropip` from PyPI (or a locally built wheel during development).
- **Single `pyproject.toml`** — one package (`contaplus-reader`) with one `[project.scripts]` entry for the CLI. The PWA is a separate build step (`cd web && npm run build`), not a Python distribution artifact.

---

## Architectural Patterns

### Pattern 1: Bytes-First Public API with Tempfile Bridge

**What:** The public `read()` function accepts `bytes | BinaryIO | Path`. Internally, raw bytes are written to a temp file via `bytes_to_tmppath` context manager before being handed to `dbfread` (which is path-only).

**When to use:** Whenever a third-party library is path-only but callers may have in-memory data or no filesystem (browser).

**Trade-offs:** A small temp-file write is added to the hot path for `.dbf`-from-bytes input. Acceptable cost: `.dbf` files are typically small (< 50 MB); the temp write is dominated by parse time. In Pyodide, the "temp file" goes to MEMFS (RAM) — there is no actual I/O.

**Critical:** Pyodide uses MEMFS as its default virtual filesystem. Python's `tempfile` module, `Path`, and all stdlib filesystem APIs work unchanged in Pyodide — they just operate against an in-memory VFS. This means `bytes_to_tmppath` and `zip_extract` (which use `tempfile.TemporaryDirectory`) require zero browser-specific code paths.

```python
# bytes_to_tmppath.py — the bridge
from contextlib import contextmanager
import tempfile
from pathlib import Path

@contextmanager
def bytes_to_tmppath(data: bytes, suffix: str = ".dbf"):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmp = Path(f.name)
    try:
        yield tmp
    finally:
        tmp.unlink(missing_ok=True)
```

### Pattern 2: Strict vs Lenient via Shared Row-Level Logic

**What:** Both postures (`read` and `read_lenient`) call the same per-row parsing and field-extraction logic. The posture difference is at the error-handling boundary only: strict postures re-raise `ContaPlusReadError` immediately; lenient posture catches it, appends to a `problems: list[ContaPlusReadError]`, and continues to the next row.

**When to use:** Any reader that must serve both a fail-loud API consumer (tax-workbench) and an extract-what-you-can consumer (migration users).

**Trade-offs:** Shared row logic means one implementation to maintain. The cost is a slightly more complex `read_lenient` accumulator, but this is contained in `read_api.py`, not scattered in individual readers.

```python
# read_api.py — posture split at the outermost boundary
def read(source, *, table=None, company_dir=None):
    return _read_internal(source, table=table, company_dir=company_dir, lenient=False)

def read_lenient(source, *, table=None, company_dir=None):
    return _read_internal(source, table=table, company_dir=company_dir, lenient=True)
```

The per-table reader (`journal.py`) raises `ContaPlusReadError` on every bad row. `read_api.py` wraps the iteration loop when `lenient=True`, catching per-row errors and collecting them. File-level errors (no DBF found, zip-slip) always propagate regardless of posture — they represent corrupt or dangerous inputs, not recoverable data issues.

### Pattern 3: XLSX Renderer as a Library Sub-Module (not a separate package)

**What:** `xlsx_render/renderer.py` lives inside `contaplus_reader`. The template `.xlsx` is bundled as a package data resource in the wheel.

**When to use:** Shared output formatting logic accessed by multiple consumers from the same install.

**Trade-offs:** Bundling the template in the wheel means it is accessible via `importlib.resources` in both CPython and Pyodide post-`micropip.install`. The alternative — shipping the template as a separate file the CLI/PWA must locate — breaks in Pyodide where there is no writable install directory accessible to user code.

```python
# renderer.py — template access via importlib.resources
from importlib.resources import files

def _load_template() -> openpyxl.Workbook:
    template_bytes = files("contaplus_reader.xlsx_render.templates").joinpath("default.xlsx").read_bytes()
    return openpyxl.load_workbook(io.BytesIO(template_bytes))
```

---

## Data Flow

### Flow 1: CLI — `.dbf` file on disk → `.xlsx` on disk

```
User: contaplus2xlsx input.dbf -o output.xlsx
    │
    ▼
cli/main.py
    │  open(input.dbf, "rb").read() → bytes
    ▼
contaplus_reader.read(source=bytes, ...)
    │
    ▼
io_sniff.py: suffix = ".dbf", data = bytes
    │
    ▼
bytes_to_tmppath(data, suffix=".dbf")  → temp Path (disk)
    │
    ▼
readers/journal.py: DBF(str(tmp_path), ...) → iterate records
    │  applies D-A1…D-E3 rules
    ▼
ContaPlusJournal (pandas DataFrame + metadata)
    │
    ▼
xlsx_render/renderer.py: WorkbookRenderer.render(results) → bytes
    │  openpyxl load_workbook(template) + fill sheets + wb.save(BytesIO)
    ▼
open(output.xlsx, "wb").write(xlsx_bytes)
```

### Flow 2: CLI — `.zip` backup on disk → `.xlsx` on disk

```
User: contaplus2xlsx backup.zip --company Emp01 -o output.xlsx
    │
    ▼
cli/main.py
    │  open(backup.zip, "rb").read() → bytes
    ▼
contaplus_reader.read(source=bytes, company_dir="Emp01")
    │
    ▼
io_sniff.py: suffix = ".zip", data = bytes
    │
    ▼
zip_extract.py:
    io.BytesIO(data) → zipfile.ZipFile(buf)
    safe_extractall() → TemporaryDirectory (disk)
    find_dbf_files() → [Path("…/Emp01/DIARIO.DBF"), Path("…/Emp01/SUBCTA.DBF"), …]
    resolve_company("Emp01") → selected set of Paths
    │
    ▼
readers/journal.py(diario_path) → ContaPlusJournal
readers/subcta.py(subcta_path) → ContaPlusSubcta  [if present; enriches journal]
readers/balan.py(balan_path) → ContaPlusBalan     [if present]
    │
    ▼
xlsx_render/renderer.py.render({journal, subcta, balan}) → bytes
    │
    ▼
open(output.xlsx, "wb").write(xlsx_bytes)
    (TemporaryDirectory cleaned up on context exit)
```

### Flow 3: PWA (browser, no filesystem) — drag-drop `.dbf` or `.zip` → download `.xlsx`

```
User: drops file onto PWA
    │
    ▼
Web Worker (worker.ts)
    │  FileReader.readAsArrayBuffer(file) → ArrayBuffer → Uint8Array → Python bytes
    │  postMessage({type: "convert", bytes, filename, companyDir})
    ▼
Pyodide (WASM, in Web Worker)
    │  micropip.install("contaplus-reader")  [cached after first load]
    │  from contaplus_reader import read
    │  results = read(source=bytes, ...)
    │       ↓
    │  io_sniff.py: exactly as CPython
    │       ↓
    │  bytes_to_tmppath: NamedTemporaryFile → MEMFS path (RAM, not disk)
    │       ↓
    │  readers/journal.py: DBF(str(memfs_path), ...) — identical code path
    │       ↓
    │  ContaPlusJournal
    │       ↓
    │  xlsx_render/renderer.py.render(results) → xlsx_bytes (BytesIO)
    ▼
Pyodide → JavaScript: xlsx_bytes transferred as Uint8Array
    │
    ▼
worker.ts: postMessage({type: "result", blob: new Blob([uint8array], {type: "application/vnd.openxmlformats..."})})
    │
    ▼
App.tsx: URL.createObjectURL(blob) → <a download="output.xlsx"> → browser saves file
```

**Key insight:** The bytes-first public API + `bytes_to_tmppath` + Pyodide's MEMFS means the Python library code is **identical** in CPython and Pyodide. There are no browser-specific code paths inside `contaplus_reader`. The only browser-specific code is in `worker.ts` (the JS/TS bridge between the DOM File API and Pyodide).

---

## Component Boundaries: What Talks to What

| From | To | Interface | Notes |
|------|----|-----------|-------|
| CLI (`cli/main.py`) | `contaplus_reader.read_api` | `read(bytes, ...)` | CLI reads file to bytes; calls library |
| CLI | `contaplus_reader.xlsx_render` | `WorkbookRenderer.render(results)` | Gets `bytes` back, writes to disk |
| PWA Web Worker (`worker.ts`) | Pyodide Python runtime | `pyodide.runPythonAsync(...)` | Bytes in via `to_py()`, bytes out |
| Pyodide Python | `contaplus_reader.read_api` | `read(bytes, ...)` | Identical to CLI call |
| Pyodide Python | `contaplus_reader.xlsx_render` | `WorkbookRenderer.render(results)` | Returns `bytes` directly to JS |
| `read_api.py` | `io_sniff.py` | `sniff(source) -> (kind, bytes)` | Internal |
| `read_api.py` | `bytes_to_tmppath.py` (`.dbf` path) | context manager | Internal |
| `read_api.py` | `zip_extract.py` (`.zip` path) | `safe_extract(data, company_dir)` | Internal |
| `read_api.py` | `readers/*.py` | `read_journal(path)`, etc. | Internal; per-table |
| `readers/*.py` | `errors.py` | `raise ContaPlusReadError(...)` | Internal |
| `readers/*.py` | `models.py` | Construct result types | Internal |
| `xlsx_render/renderer.py` | `importlib.resources` | Load bundled template `.xlsx` | Must work in Pyodide |
| tax-workbench (future) | `contaplus_reader` | `read(bytes, ...)` + wrap result | Out of scope here |

---

## Build Order (Dependency Graph)

The roadmap should follow this strict dependency order:

```
1. errors.py + models.py
        │  (no dependencies within the project)
        ▼
2. io_sniff.py + bytes_to_tmppath.py + zip_extract.py
        │  (depends on: errors.py)
        ▼
3. readers/journal.py  [BLOCKING: all other work waits on this]
        │  (depends on: errors.py, models.py, bytes_to_tmppath.py, zip_extract.py)
        │  Ports all tw-contaplus business rules D-A1…D-E3.
        │  Ports existing test coverage verbatim.
        ▼
4. read_api.py (strict posture: read())
        │  (depends on: all readers, io_sniff, zip_extract)
        ▼
5. read_api.py (lenient posture: read_lenient())
        │  (depends on: read_api strict; shared row logic already in readers)
        ▼
6. readers/subcta.py, readers/balan.py, readers/groups.py
        │  (depends on: errors.py, models.py, bytes_to_tmppath.py)
        │  (journal enrichment with subcta names depends on subcta.py)
        ▼
7. xlsx_render/renderer.py + template resource
        │  (depends on: models.py; consumes DataFrames from result types)
        │  (depends on: openpyxl; template bundled as package resource)
        ▼
8. CLI (cli/main.py + pyproject.toml [project.scripts])
        │  (depends on: read_api, xlsx_render)
        │  Thin wrapper: parse args, read bytes, call read(), call render(), write file.
        ▼
9. PWA (web/ Vite+React+shadcn+Pyodide)
        │  (depends on: published wheel OR local wheel via micropip)
        │  (depends on: CLI being validated first — confirms the Python pipeline end-to-end)
        │  Blocked until: micropip install of contaplus-reader works from a local wheel.
```

**Why this order:**
- `errors.py` and `models.py` are pure definitions with no internal deps — start here to unblock everything.
- The journal reader is the most complex, highest-value, and most tested component. It should be fully working (strict + lenient + ZIP) before any rendering or CLI work begins. Shipping the journal first proves the bytes-first interface and the `bytes_to_tmppath` bridge.
- `xlsx_render` comes after all readers because the renderer consumes the result models. Once the renderer works, CLI follows immediately (it's two functions: call library, call renderer, write file).
- The PWA is last because it depends on a working local wheel (`uv build` → `micropip.install` from local URL). The local wheel must exist before Pyodide integration can be tested. The PWA also has its own non-trivial JS/TS build (Vite, shadcn, Web Worker bootstrap), which should be the final phase.

---

## Anti-Patterns

### Anti-Pattern 1: Exposing Per-Table Readers as the Public API

**What people do:** Export `read_journal`, `read_subcta`, etc. directly from `contaplus_reader.__init__`.

**Why it's wrong:** Forces every consumer to know which tables exist and to call multiple functions. Couples consumers to the internal table enumeration. Breaks the "one read API for all consumers" contract from SEED architecture decision §3.

**Do this instead:** Export only `read()` and `read_lenient()` from `__init__`. Per-table readers are internal; they are called by `read_api.py` based on what files are present in the input.

### Anti-Pattern 2: Passing `Path` to the Public API as the Primary Interface

**What people do:** Design `read(path: Path, ...)` as the primary API, treating bytes support as a secondary option.

**Why it's wrong:** The PWA has no filesystem path. A path-first API forces the PWA to use a workaround at the call site. The `Path`-based interface is what tax-workbench's `ReadDBFParams` was, and this is exactly the coupling being shed.

**Do this instead:** `read(source: bytes | BinaryIO, ...)` is primary. `Path` acceptance in the public API is a convenience shim that reads the file to bytes before passing to the core: `if isinstance(source, Path): source = source.read_bytes()`. This shim lives in `read_api.py`, not in the readers.

### Anti-Pattern 3: Returning `tw-domain` Types (or pandas DataFrames Directly)

**What people do:** Return `pd.DataFrame` directly as the result, or reference `tw-domain.Diario`.

**Why it's wrong:** Raw DataFrames have no semantic type — the XLSX renderer cannot know which columns to style, callers cannot type-check. `tw-domain` types couple this library to tax-workbench.

**Do this instead:** Return `ContaPlusJournal(df: pd.DataFrame, skipped_memo: int, source_meta: dict)` — a thin dataclass wrapper. The `df` is still inside, accessible as `.df`, but the wrapping type carries semantic meaning for the renderer and for callers.

### Anti-Pattern 4: Monkeypatching dbfread or Forking It for BytesIO Support

**What people do:** Attempt to patch `dbfread.DBF` to accept `BytesIO` directly (the open issue #25 in the dbfread repo was never merged).

**Why it's wrong:** Forks require maintenance. The `bytes_to_tmppath` context manager is 10 lines and solves the problem portably — in CPython it writes to disk, in Pyodide it writes to MEMFS. No fork needed.

**Do this instead:** Use `bytes_to_tmppath` as the internal bridge. The public API stays bytes-first; the path-only limitation of `dbfread` is fully encapsulated inside the bridge.

### Anti-Pattern 5: Shipping the XLSX Template as a Separate Download

**What people do:** Ship `default.xlsx` as a file the user/admin must place at a known path.

**Why it's wrong:** In Pyodide there is no writable user-accessible directory at a predictable path. `micropip.install` places package data under Pyodide's MEMFS package tree; `importlib.resources` is the correct cross-environment accessor.

**Do this instead:** Declare the template in `pyproject.toml` as `[tool.setuptools.package-data]` (or equivalent), access via `importlib.resources.files("contaplus_reader.xlsx_render.templates")`.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `read_api` ↔ `readers/*` | Direct Python function calls | `read_api` calls reader functions with `Path` arguments; no async, no queue |
| `read_api` ↔ `xlsx_render` | Not direct — callers get results, pass to renderer separately | Renderer is a separate call; decoupled from reading |
| `cli` ↔ `contaplus_reader` | `import contaplus_reader; read(...)` | One import, two calls (read + render) |
| `web/worker.ts` ↔ Pyodide | `pyodide.runPythonAsync(code)` + `to_py()` / `fromJs()` for bytes transfer | Web Worker thread; bytes as `Uint8Array` ↔ Python `bytes` |
| Pyodide Python ↔ `contaplus_reader` | `micropip.install(wheel_url)` then normal import | Wheel must be a pure Python `py3-none-any.whl` (confirmed: dbfread, openpyxl, pandas are all pure Python / pre-built in Pyodide) |

### External Dependencies at Runtime

| Dependency | Version | Why | Pyodide-available? |
|------------|---------|-----|-------------------|
| `dbfread` | >=2.0.7 | DBF parsing (pure Python, read-only, lazy) | Yes — pure Python wheel on PyPI |
| `pandas` | >=2.0 | DataFrame output type, dtype coercion | Yes — pre-built in Pyodide package set |
| `openpyxl` | >=3.1 | XLSX write (template load + styled render) | Yes — pre-built in Pyodide package set |

`dbfread` is path-only (confirmed via source inspection — `DBF.__init__` calls `os.path.basename` and `open(filename, 'rb')` directly). The `bytes_to_tmppath` bridge is therefore required for in-memory DBF data. This constraint is fully handled inside the library; consumers never see it.

---

## Scaling Considerations

This tool is a local data transformation pipeline, not a web service. "Scaling" means large files, not concurrent users.

| Scale | Architecture Adjustment |
|-------|------------------------|
| Small journals (< 50k rows) | Default path; DataFrame fits in RAM trivially |
| Large multi-year journals (1M+ rows) | `dbfread` lazy iteration already handles this (never `load=True`); chunked DataFrame append if needed |
| Multi-company ZIPs (10+ companies) | `zip_extract.py` discovers all companies; caller picks one via `company_dir`; no parallel reads needed in v1 |
| PWA cold load (Pyodide + pandas + openpyxl) | Service worker caches the Pyodide runtime + wheels after first visit; subsequent visits / offline use are fast. Cold load is a UX concern, not an architecture concern — documented as an open research question. |

---

## Sources

- SEED.md — architecture decisions §1–§5, ContaPlus format reference §1–§6, journal business rules D-A1…D-E3
- PROJECT.md — requirements, constraints, key decisions
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — existing implementation confirming `tempfile.TemporaryDirectory` + `zipfile.ZipFile` pattern already in use
- dbfread source: `github.com/olemb/dbfread/blob/master/dbfread/dbf.py` — confirmed `DBF.__init__` accepts only file paths (calls `os.path.basename`, `open(filename, 'rb')` directly); issue #25 (BytesIO support request, never merged) — MEDIUM confidence
- Pyodide MEMFS: `pyodide.org/en/stable/usage/file-system.html` — Python `tempfile` and path operations work against MEMFS in Pyodide; no browser-specific code paths needed for path-based libraries — MEDIUM confidence (official docs, HTTP 403 on direct fetch; confirmed via WebSearch)
- openpyxl `wb.save(BytesIO())` pattern — MEDIUM confidence (multiple sources, standard usage)
- `micropip` pure Python wheel installation — HIGH confidence (official Pyodide docs); dbfread, openpyxl, pandas are pure Python or pre-built in Pyodide — MEDIUM confidence (needs validation in a live Pyodide environment)

---
*Architecture research for: contaplus-reader (Python library + CLI + browser PWA)*
*Researched: 2026-05-15*
