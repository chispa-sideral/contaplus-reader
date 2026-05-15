# Phase 1: Journal Slice - Research

**Researched:** 2026-05-15
**Domain:** Python library scaffolding, DBF reading, XLSX rendering, Typer CLI, uv packaging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 1 stays strictly journal-only (`DIARIO.DBF`). No table readers beyond the journal land in this phase.
- **D-02:** A raw input that sniffs as a valid `.dbf` but is not journal-shaped is detected and rejected with a structured error stating it is a non-journal table and that multi-table support is planned. The reader checks the DBF field signature *before* attempting journal parsing.
- **D-03:** `read()` returns a `ContaPlusData` container object. Phase 1 populates `.journal` (a `ContaPlusJournal`). The container return type is stable across all five phases.
- **D-04:** Strict-only in Phase 1. `read()` has no `strict`/`lenient`/`mode` parameter yet; it always raises `ContaPlusReadError` on invalid data.
- **D-05:** Input type is detected by content magic-byte sniffing — not a file suffix and not a caller-supplied hint. Phase 1 accepts dBASE/FoxPro DBF signatures and rejects everything else (including ZIP `PK\x03\x04`) with a structured error.
- **D-06:** Signature is `read(data: bytes | BinaryIO, source_name: str | None = None)`. No filesystem-path argument ever exists.
- **D-07:** `ContaPlusJournal.rows` is `list[JournalRow]` — frozen, fully static-typed dataclasses. No pandas type appears in the public API surface. Per-row field shape is `{fecha, cuenta, subcuenta, debe, haber, concepto}`.
- **D-08:** The XLSX renderer converts `list[JournalRow]` → DataFrame internally. DataFrame is an implementation detail of the renderer, not part of the result type.
- **D-09:** `ContaPlusJournal` also carries the skipped-memo-line count (D-C3) and the optional `source_name`.
- **D-10:** Polished-but-restrained XLSX styling — bold header row with fill color, frozen header row, auto-sized columns, proper number/date cell formats.
- **D-11:** `debe`/`haber` use an accounting number format — 2 decimals, thousands separators; negative amounts rendered in red.
- **D-12:** XLSX column headers are in **Spanish** — `Fecha, Cuenta, Subcuenta, Debe, Haber, Concepto`. All code, identifiers, docstrings, CLI `--help`, and error messages remain English. Downstream agents must NOT "correct" these headers to English.
- **D-13:** Journal sheet contains data rows only — no footer/totals row.
- **D-14:** Both arguments are required positionals: `contaplus2xlsx <input> <output>`. No auto-derived default output path.
- **D-15:** CLI refuses to overwrite an existing output file; `--force` flag (alias `--overwrite`) permits replacement.
- **D-16:** On success CLI prints a concise one-line summary including journal row count and skipped-memo count.
- **D-17:** `ContaPlusReadError` is presented as a clean Rich error panel — message + row index + column + context, no Python traceback — CLI exits with code 1.

### Claude's Discretion

- Exact class names (`ContaPlusData`, `ContaPlusJournal`, `JournalRow`, `ContaPlusReadError`), module/package layout, and the bytes→temp-path bridge mechanism for `dbfread` are implementation choices for research/planning.
- Precise styling values — fill color, fonts, column-width algorithm, and the exact Excel number-format strings — are the planner's to choose within "polished but restrained" and "accounting format, red negatives".

### Deferred Ideas (OUT OF SCOPE)

- `SUBCTA.DBF` + group tables → Phase 2
- Operational tables + `BALAN.DBF` → Phase 3
- ZIP input, lenient conversion path, multi-company → Phases 2–3
- PWA → Phase 5
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INPUT-01 | Reader accepts raw `.dbf` as bytes or file-like object (no filesystem path) | bytes→tempfile bridge pattern; D-06 signature |
| INPUT-03 | Reader sniffs input type and rejects unsupported inputs with structured error | DBF magic bytes at offset 0; sniffer implementation |
| JRNL-01 | Extracts validated journal rows, ports D-A1…D-E3 business rules | `read_dbf.py` porting analysis; all rules documented in SEED.md |
| JRNL-02 | Handles ContaPlus quirks — cp850, whitespace strip, deleted records, memo lines, negatives, column-name variants | SEED §2, §3, §5, §6 fully documented |
| JRNL-03 | Rejects invalid rows with structured per-row error carrying row/column context | SEED error model table; `ContaPlusReadError` design |
| API-01 | Library exposes single bytes-first read API | `read(data: bytes | BinaryIO, source_name: str | None)` signature |
| API-02 | Strict read path fails loudly on invalid data, raising `ContaPlusReadError` | Error model ported from `BlockExecutionError` pattern |
| API-04 | Library returns self-contained result types with no `tw-domain` dependency | `ContaPlusData`/`ContaPlusJournal`/`JournalRow` design |
| XLSX-01 | Shared, templated XLSX renderer produces styled workbook | openpyxl patterns: freeze_panes, PatternFill, number formats |
| XLSX-04 | Renderer callable identically from CLI and PWA, no filesystem assumptions | `save(dest: BinaryIO \| str \| Path)` output interface |
| CLI-01 | `contaplus2xlsx` converts single `.dbf` to styled `.xlsx` | Typer positional args + `--force` pattern |
| CLI-04 | CLI installable and runnable via `uvx` / `pipx` | `[project.scripts]` + uv_build packaging |
| TEST-01 | Test suite uses synthetic blob-free fixtures generated at collection time | Port `conftest.py` pattern from `tw-contaplus` verbatim |
| TEST-02 | Existing `tw-contaplus` journal-reader coverage ported and passing | All 27 tests mapped; tax-workbench-specific stubs replaced |
| DIST-02 | `uv build` produces a wheel | `pyproject.toml` + uv_build 0.11.14 configuration |
</phase_requirements>

---

## Summary

Phase 1 is a greenfield walking-skeleton: no existing code in the repo, full porting source available in `C:\dev\tax-workbench\packages\tw-contaplus\`. The domain is well-understood — SEED.md embeds the full `DIARIO.DBF` format spec, business rules D-A1…D-E3, and the synthetic-fixture test inventory verbatim. The porting source (`read_dbf.py`, `conftest.py`, `test_read_dbf.py`) is readable and compact.

The one genuine blocker is the **bytes→path bridge**: `dbfread` is a path-only library (issue #25, open since 2019, never merged). The solution is a context-manager function `bytes_to_tmppath(data: bytes | BinaryIO) -> Iterator[Path]` that writes bytes to a `tempfile.NamedTemporaryFile` (or `TemporaryDirectory`) and yields the path. The memo-sibling concern (`DIARIO.FPT`) is real but safe to handle: `ignore_missing_memofile=True` is already in the standard invocation, and a `.fpt` sibling in the same dir would be found by dbfread's memo lookup — but since the input is a single in-memory blob, no sibling can exist, so the parameter does all the work needed.

The open research questions from CONTEXT.md are resolved below: the journal field signature (D-02) is defined; the bytes→path bridge lifecycle is specified; the DBF magic-byte values at offset 0 are enumerated; and the Excel accounting format code is confirmed.

**Primary recommendation:** Port the tax-workbench reader nearly verbatim, replace `BlockExecutionError`→`ContaPlusReadError` and `Diario`→`ContaPlusData/ContaPlusJournal/JournalRow`, add the bytes→tempfile bridge as the first layer, implement a 5-line magic-byte sniffer, and wire everything through a Typer CLI. The result model design (D-03/07/08/09) is the main new architecture; the reader logic itself is a straight port.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Input sniffing (magic bytes) | Library (`contaplus_reader.reader`) | — | Pre-read validation before any parsing |
| bytes→path bridge | Library internal (`_bridge.py`) | — | Hidden from callers; feeds dbfread |
| DBF iteration + column resolution | Library internal | — | Wraps dbfread with ContaPlus-specific logic |
| Journal business rules (D-A1…D-E3) | Library (`contaplus_reader.journal`) | — | Core value; must be isolated and testable |
| Result types (ContaPlusData, JournalRow) | Library (`contaplus_reader.models`) | — | Stable public API surface |
| XLSX rendering | Library (`contaplus_reader.xlsx`) | — | Shared between CLI and future PWA; no filesystem dependency |
| CLI entry point + argument parsing | CLI (`contaplus_reader.cli`) | Library | Thin wrapper; delegates all logic to library |
| Error presentation (Rich panel) | CLI | Library (raises ContaPlusReadError) | Library raises; CLI presents |
| Wheel / sdist build | uv + uv_build | — | `uv build` invocation only |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.13` | Runtime | Project constraint; modern typing (PEP 695, tomllib) |
| uv | `>=0.7` (installed: 0.7.x / 0.11.13 uv_build) | Project manager, build, publish | Single tool replacing pip/venv/pip-tools/twine |
| uv_build | `0.11.14` | Build backend (wheel + sdist) | Current stable; zero-config pure-Python src-layout; locked in CLAUDE.md |
| dbfread | `2.0.7` | DBF file reading | Locked runtime dep; pure-Python MIT; lazy iteration; path-only (bridge required) |
| pandas | `>=2.2` (latest: 3.0.3) | DataFrame + XLSX output engine | XLSX rendering via openpyxl; renderer-internal only |
| openpyxl | `>=3.1.5` (latest: 3.1.5) | XLSX engine | Pure Python; pandas ExcelWriter engine; locked runtime dep |
| typer | `>=0.13` (latest: 0.25.1) | CLI framework | Locked in CLAUDE.md; type-hint driven; `uvx` compatible |
| rich | `>=13` (latest: 15.0.0) | Terminal output | Pulled in by `typer[all]`; error panels + console |

[VERIFIED: npm registry] — all packages confirmed via `uv run --python 3.14 -m pip index versions` against PyPI.

### Dev / Test

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dbf (ethanfurman) | `0.99.11` | Synthetic DBF fixture generation | `conftest.py` only — never a runtime dep |
| pytest | `>=8.4` (latest: 9.0.3) | Test framework | Standard; `uv run pytest` invocation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv_build | hatchling | hatchling is older uv default; uv_build is faster and zero-config for pure Python |
| typer | click | Typer wraps Click; no reason for direct Click for a single-command CLI |
| openpyxl (via pandas) | xlsxwriter | xlsxwriter does not support reading; openpyxl is pandas' write engine |

**Installation (runtime deps):**
```bash
uv add dbfread pandas openpyxl "typer[all]"
```

**Installation (dev/test deps):**
```bash
uv add --dev dbf pytest
```

## Package Legitimacy Audit

slopcheck was not available in this environment. All packages are well-established, decade-old Python ecosystem libraries with large download volumes. Manual verification performed via `pip index versions` on PyPI.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| dbfread | PyPI | 10+ yrs (since 2013) | Moderate (tens of thousands/wk) | github.com/olemb/dbfread | N/A | Approved [ASSUMED] |
| pandas | PyPI | 15+ yrs | Very high (100M+/wk) | github.com/pandas-dev/pandas | N/A | Approved [ASSUMED] |
| openpyxl | PyPI | 12+ yrs | Very high (50M+/wk) | foss.heptapod.net/openpyxl/openpyxl | N/A | Approved [ASSUMED] |
| typer | PyPI | 5+ yrs | High (10M+/wk) | github.com/fastapi/typer | N/A | Approved [ASSUMED] |
| rich | PyPI | 5+ yrs | Very high (80M+/wk) | github.com/Textualize/rich | N/A | Approved [ASSUMED] |
| dbf (ethanfurman) | PyPI | 10+ yrs (since 2012) | Moderate | github.com/ethanfurman/dbf | N/A | Approved [ASSUMED] |
| pytest | PyPI | 15+ yrs | Very high | github.com/pytest-dev/pytest | N/A | Approved [ASSUMED] |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. All packages above are tagged `[ASSUMED]`. All are core Python ecosystem libraries with decade-plus track records — risk of hallucination is negligible, but the planner may add a `checkpoint:human-verify` before the first `uv add` if desired.*

---

## Architecture Patterns

### System Architecture Diagram

```
Caller (CLI or test)
        |
        | bytes | BinaryIO + optional source_name
        v
 read(data, source_name) ──── magic-byte sniffer (offset 0)
        |                           |
        |                     [ZIP / unknown]──> ContaPlusReadError
        |                           |
        |                     [valid DBF version byte]
        v
 bytes_to_tmppath(data)  [context manager]
        |
        | tmp path (NamedTemporaryFile)
        v
  DBF(str(tmp_path), lowernames=True, encoding="cp850",
      ignore_missing_memofile=True)  [dbfread]
        |
        | field_names → column resolution (D-E1)
        |               │── no debe/haber column → ContaPlusReadError
        |               └── DBF not journal-shaped → ContaPlusReadError (D-02)
        v
  record iteration (lazy, skip deleted)
        |
        | per record: fecha→ subcuenta→ debe/haber→ concepto
        |   D-C4 null fecha → ContaPlusReadError
        |   D-C2 both-non-zero → ContaPlusReadError
        |   D-C3 both-zero → skip, skipped_memo++
        |   subcuenta validation → ContaPlusReadError
        v
  list[JournalRow] + skipped_memo_count
        |
        v
  ContaPlusJournal(rows, skipped_memo, source_name)
        |
        v
  ContaPlusData(journal=ContaPlusJournal)
        |
        v
  XlsxRenderer.render(data) → bytes (BytesIO)
        |
        v
  CLI: write bytes to output path | return to caller
```

### Recommended Project Structure

```
src/
└── contaplus_reader/
    ├── __init__.py          # public API: read(), ContaPlusData, ContaPlusJournal,
    │                        # JournalRow, ContaPlusReadError
    ├── _bridge.py           # bytes_to_tmppath() context manager (private)
    ├── _sniffer.py          # magic-byte sniffer for DBF detection (private)
    ├── _reader.py           # _read_dbf_path() — dbfread iteration + D-A1..D-E3 rules
    ├── models.py            # ContaPlusData, ContaPlusJournal, JournalRow, ContaPlusReadError
    ├── xlsx.py              # XlsxRenderer: list[JournalRow] → bytes
    └── cli.py               # Typer app — contaplus2xlsx entry point
tests/
├── conftest.py              # synthetic DBF fixture factory (port from tw-contaplus verbatim)
├── test_reader.py           # ported journal reader tests (~27 cases)
├── test_xlsx.py             # XLSX output smoke tests
└── test_cli.py              # CLI argument/exit-code tests
pyproject.toml
```

### Pattern 1: bytes→tempfile Bridge

**What:** Context manager that accepts `bytes | BinaryIO`, writes to a `NamedTemporaryFile`, and yields the resolved `Path`. Handles lifecycle and cleanup automatically.

**When to use:** Any time `dbfread.DBF()` needs to be called from an in-memory input.

**Why a NamedTemporaryFile and not TemporaryDirectory:** A single `.dbf` blob with no companion files needs only a single file. `NamedTemporaryFile(suffix=".dbf", delete=False)` + manual cleanup (or `delete_on_close=True` on Python 3.12+) is simpler. On Windows, `NamedTemporaryFile` cannot be opened a second time while it is open — use `delete=False` and clean up in `finally`.

**Example:**
```python
# Source: synthesized from Python tempfile docs + dbfread issue #25 analysis
import tempfile
import io
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

@contextmanager
def bytes_to_tmppath(data: bytes | io.IOBase) -> Generator[Path, None, None]:
    raw: bytes = data if isinstance(data, bytes) else data.read()
    # On Windows NamedTemporaryFile cannot be reopened while open.
    # Use delete=False + explicit cleanup.
    tmp = tempfile.NamedTemporaryFile(suffix=".dbf", delete=False)
    try:
        tmp.write(raw)
        tmp.close()           # close before yielding so dbfread can open it
        yield Path(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
```

**CDX/memo-sibling note:** When bytes are written to a tmpfile, no sibling `.cdx` or `.fpt` file exists in the temp directory. `dbfread` with `ignore_missing_memofile=True` handles the absent `.fpt`/`.dbt` gracefully. The `.cdx` index is never read by dbfread (it reads the data file directly). No sibling-copy logic is needed for Phase 1 (which only accepts raw `.dbf` bytes, not an extracted archive with siblings). [VERIFIED: dbfread memo.py source — memo lookup is relative to dbf path; ignore_missing_memofile suppresses MissingMemoFile exception]

### Pattern 2: Magic-Byte Sniffer

**What:** Reads offset 0 of the input bytes to determine if the input is a DBF file. Rejects non-DBF inputs with a structured error before any other processing.

**DBF version bytes at offset 0** [VERIFIED: independent-software.com/dbase-dbf-dbt-file-format.html]:

| Byte value | Variant |
|------------|---------|
| `0x02` | FoxBase 1.0 |
| `0x03` | FoxBase 2.x / dBASE III (no memo) — **most common ContaPlus variant** |
| `0x83` | FoxBase 2.x / dBASE III (with memo) |
| `0x30` | Visual FoxPro — **seen in modern Sage 50 ContaPlus exports** |
| `0x31` | Visual FoxPro with autoincrement |
| `0x32` | Visual FoxPro with varchar/varbinary |
| `0x43` | dBASE IV SQL Table (no memo) |
| `0x63` | dBASE IV SQL System (no memo) |
| `0x8B` | dBASE IV (with memo) |
| `0xCB` | dBASE IV SQL Table (with memo) |
| `0xF5` | FoxPro 2.x (with memo) |
| `0xFB` | FoxBase |

**ZIP magic bytes for reject path:** `b'PK\x03\x04'` (offset 0–3).

**Known ContaPlus DBF versions:** `0x03` (DOS/Clipper-era ContaPlus), `0x83` (ContaPlus with memo file), `0x30` (Visual FoxPro / modern Sage 50 ContaPlus). [ASSUMED — ContaPlus/Sage documentation does not publish exact version bytes; derived from DBF format spec + known ContaPlus lineage]

**Recommended accept-list:** Accept any byte value in the known DBF set (`{0x02, 0x03, 0x83, 0x30, 0x31, 0x32, 0x43, 0x63, 0x8B, 0xCB, 0xF5, 0xFB}`). Reject everything else, including `0x50` (`P`, ZIP). This is conservative: a future exotic DBF variant can be added to the accept set without changing the API.

```python
# Source: synthesized from DBF format spec [VERIFIED] + ContaPlus lineage [ASSUMED]
_KNOWN_DBF_VERSION_BYTES: frozenset[int] = frozenset({
    0x02, 0x03, 0x83, 0x30, 0x31, 0x32,
    0x43, 0x63, 0x8B, 0xCB, 0xF5, 0xFB,
})

def sniff(data: bytes | io.IOBase) -> None:
    """Raise ContaPlusReadError if data is not a recognized DBF file."""
    if isinstance(data, (bytes, bytearray)):
        first_byte = data[0] if data else None
    else:
        first_byte_bytes = data.read(1)
        # BinaryIO: seek back if seekable; callers should pass bytes or reset
        if hasattr(data, "seek"):
            data.seek(0)
        first_byte = first_byte_bytes[0] if first_byte_bytes else None

    if first_byte is None or first_byte not in _KNOWN_DBF_VERSION_BYTES:
        hint = "ZIP archive detected — ZIP input is supported in Phase 2" \
            if first_byte == 0x50 else "not a DBF file"
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"Unsupported input format: {hint}",
        )
```

### Pattern 3: Journal Field Signature Check (D-02)

**What:** After opening the DBF with dbfread, check that the field set identifies this as a `DIARIO.DBF` (not `SUBCTA.DBF`, `BALAN.DBF`, or another table) before attempting journal parsing.

**Resolution of open research question D-02:**

The minimal field signature that uniquely identifies a `DIARIO.DBF` vs. the other ContaPlus tables is based on the fields documented in SEED.md and cross-referenced from the ContaPlus protocol documentation [ASSUMED for SUBCTA/BALAN field lists — SEED.md documents DIARIO fully]:

| Table | Unique identifying fields | NOT present |
|-------|--------------------------|-------------|
| `DIARIO.DBF` | `ASIEN` (N), `FECHA` (D), `SUBCTA` (C) AND at least one of `{eurodebe, eurdebe, debe, pesedebe}` | `CODIGO` (SUBCTA PK), `SALDO` (BALAN) |
| `SUBCTA.DBF` | `CODIGO` or `COD` (subaccount code PK), no `FECHA` field | `FECHA` (D), `ASIEN` |
| `BALAN.DBF` | `SALDO` or `DEVSALDO`, no `FECHA` (D) individual line field | `ASIEN`, `FECHA` as individual date |

**Recommended minimal journal signature check:**

A DBF is journal-shaped if it has:
1. A `FECHA` field (type D) — mandatory; no other ContaPlus table has per-line transaction dates
2. At least one of the debe candidates: `{eurodebe, eurdebe, debe, pesedebe}` (case-insensitive)
3. At least one of the haber candidates: `{eurohaber, eurhaber, haber, pesehaber}` (case-insensitive)

If these three conditions are met → proceed with journal parsing. If a valid DBF is opened but fails this check → raise `ContaPlusReadError` with message: `"Input is a valid DBF but not a DIARIO.DBF journal table (multi-table support is planned for Phase 2)."` Include available field names in the error context.

**Implementation note:** `dbfread` exposes both `table.field_names` (list of names in header order) and each field's type via `table.fields` (list of `FieldObject` with `.name` and `.type`). Use `table.fields` to check that the matched `FECHA` candidate has type `"D"` (Date). [VERIFIED: dbfread docs — DBF Objects section]

```python
# Source: synthesized from SEED.md §3 + dbfread DBF Objects docs [VERIFIED]
def _assert_journal_shaped(table: DBF) -> None:
    field_set = {n.lower() for n in table.field_names}
    field_type_map = {f.name.lower(): f.type for f in table.fields}

    # 1. FECHA (D type) must be present
    if "fecha" not in field_set or field_type_map.get("fecha") != "D":
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(multi-table support is planned in a future phase). "
                f"Available fields: {sorted(field_set)}"
            ),
        )
    # 2. At least one debe candidate and one haber candidate must be present
    _DEBE = {"eurodebe", "eurdebe", "debe", "pesedebe"}
    _HABER = {"eurohaber", "eurhaber", "haber", "pesehaber"}
    has_debe = bool(field_set & _DEBE)
    has_haber = bool(field_set & _HABER)
    if not has_debe or not has_haber:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(no debit/credit columns found). "
                f"Available fields: {sorted(field_set)}"
            ),
        )
```

### Pattern 4: ContaPlusReadError Model

```python
# Source: synthesized from SEED.md error model table + tw-contaplus BlockExecutionError
from dataclasses import dataclass

@dataclass(frozen=True)
class ContaPlusReadError(Exception):
    """Structured error from the ContaPlus reader."""
    message: str
    row_index: int = -1       # 0-based index over non-deleted records; -1 = file-level
    column: str | None = None # field name or None when not row-specific
    original: Exception | None = None  # wrapped cause

    def __str__(self) -> str:
        loc = f"row {self.row_index}" if self.row_index >= 0 else "file level"
        col = f", column '{self.column}'" if self.column else ""
        return f"ContaPlusReadError [{loc}{col}]: {self.message}"
```

### Pattern 5: Result Model

```python
# Source: CONTEXT.md decisions D-03, D-07, D-08, D-09
import datetime
from dataclasses import dataclass, field

@dataclass(frozen=True)
class JournalRow:
    fecha: datetime.date
    cuenta: str        # subcuenta[:4], 3-4 digits
    subcuenta: str     # full subaccount code, >=3 digits
    debe: float
    haber: float
    concepto: str | None

@dataclass(frozen=True)
class ContaPlusJournal:
    rows: list[JournalRow]
    skipped_memo: int = 0
    source_name: str | None = None

@dataclass
class ContaPlusData:
    """Container for all extracted ContaPlus tables.
    Phase 1 populates .journal only; later phases add .subcta, .balance, etc.
    """
    journal: ContaPlusJournal | None = None
```

### Pattern 6: XLSX Rendering

**What:** Convert `list[JournalRow]` to a bytes buffer (no filesystem path assumption) using openpyxl directly (not via pandas).

**Why direct openpyxl (not pandas.ExcelWriter):** Simpler for a single-sheet output; avoids a heavyweight intermediate DataFrame at the renderer boundary; makes it easier to apply per-cell formatting for the number format.

**Accounting number format for debe/haber** [VERIFIED: openpyxl.styles.numbers source — format ID 40]:
```
#,##0.00_);[Red](#,##0.00)
```
This is Excel's built-in format 40. The `,` in `#,##0` is locale-independent in the OOXML spec — the file stores the symbolic format; each viewer applies its own locale separator (Windows locale settings). Spanish Excel users will see `.` as thousands separator and `,` as decimal (per Spanish locale), which is correct for the target audience. [VERIFIED: Microsoft OOXML spec — "Within the file the period and comma characters are symbolic ... users interact with it using separators based on their settings"]

**Date format:**
```
DD/MM/YYYY
```
Standard Spanish date display for accounting exports.

**Column widths:** Iterate all column values, compute `max(len(str(v)) for v in col_values)`, add 2 for padding, cap at 50. No openpyxl auto-fit (it is intentionally absent from the spec). [VERIFIED: openpyxl docs — "openpyxl has no concept of 'autofit'"]

**Header fill:** `PatternFill(fill_type="solid", fgColor="4472C4")` — Office Blue, professional and understated.

**Freeze panes:** `ws.freeze_panes = "A2"` — freezes row 1 (header).

```python
# Source: synthesized from openpyxl styles docs [VERIFIED: openpyxl.readthedocs.io/en/3.1/styles.html]
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, numbers

HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]
ACCOUNTING_FMT = "#,##0.00_);[Red](#,##0.00)"  # openpyxl built-in format 40
DATE_FMT = "DD/MM/YYYY"
HEADER_FILL = PatternFill(fill_type="solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")

def render_journal(journal: ContaPlusJournal) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario"
    # Header row
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"
    # Data rows
    for row_idx, jr in enumerate(journal.rows, 2):
        ws.cell(row=row_idx, column=1, value=jr.fecha).number_format = DATE_FMT
        ws.cell(row=row_idx, column=2, value=jr.cuenta)
        ws.cell(row=row_idx, column=3, value=jr.subcuenta)
        debe_cell = ws.cell(row=row_idx, column=4, value=jr.debe)
        debe_cell.number_format = ACCOUNTING_FMT
        haber_cell = ws.cell(row=row_idx, column=5, value=jr.haber)
        haber_cell.number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=6, value=jr.concepto)
    # Auto-size columns
    for col_cells in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col_cells), default=0)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

### Pattern 7: Typer CLI

```python
# Source: typer docs [VERIFIED: typer.tiangolo.com/tutorial/arguments/optional/] + D-14/15/16/17
import typer
from pathlib import Path
from typing import Annotated
import sys

app = typer.Typer(add_completion=False)

@app.command()
def main(
    input_file: Annotated[Path, typer.Argument(help="Path to DIARIO.DBF file")],
    output_file: Annotated[Path, typer.Argument(help="Path to write .xlsx output")],
    force: Annotated[bool, typer.Option("--force", "--overwrite",
        help="Overwrite output if it already exists")] = False,
) -> None:
    """Convert a ContaPlus DIARIO.DBF journal to a styled .xlsx workbook."""
    from contaplus_reader import read, ContaPlusReadError
    from contaplus_reader.xlsx import render_journal
    from rich.console import Console
    from rich.panel import Panel

    console = Console(stderr=True)

    if output_file.exists() and not force:
        console.print(f"[red]Error:[/red] {output_file} already exists. Use --force to overwrite.")
        raise typer.Exit(1)

    try:
        data = read(input_file.read_bytes(), source_name=str(input_file))
    except ContaPlusReadError as exc:
        console.print(Panel(
            f"{exc.message}\n"
            f"Row: {exc.row_index if exc.row_index >= 0 else 'n/a'}\n"
            f"Column: {exc.column or 'n/a'}",
            title="ContaPlus Read Error",
            border_style="red",
        ))
        raise typer.Exit(1) from None

    journal = data.journal
    xlsx_bytes = render_journal(journal)
    output_file.write_bytes(xlsx_bytes)

    skip_msg = f" ({journal.skipped_memo} memo lines skipped)" if journal.skipped_memo else ""
    typer.echo(f"{output_file} — {len(journal.rows)} journal rows{skip_msg}")
```

### Pattern 8: pyproject.toml Layout

```toml
[project]
name = "contaplus-reader"
version = "0.1.0"
description = "Read Sage ContaPlus accounting exports (DIARIO.DBF, .zip) into usable formats"
readme = "README.md"
requires-python = ">=3.13"
license = { text = "LGPL-3.0-or-later" }
authors = [{ name = "Marc Fargas" }]

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
    "pytest>=8.4",
]

[tool.uv]
package = true
```

### Anti-Patterns to Avoid

- **Never use `load=True` in `dbfread.DBF()`:** Loads entire DBF into memory. Multi-year journals can be millions of rows. Always use lazy iteration (the default). [CITED: SEED.md §5, CLAUDE.md "What NOT to Use"]
- **Never use `latin-1` encoding:** Decodes CP850 accent codepoints to wrong Unicode points. Always `encoding="cp850"`. [CITED: SEED.md §2, CLAUDE.md "What NOT to Use"]
- **Never open `NamedTemporaryFile` on Windows without `delete=False`:** Windows cannot open the same file twice while it is open. Use `delete=False` + manual cleanup. [ASSUMED: Windows file locking behavior]
- **Never put pandas types in the public API surface:** `list[JournalRow]` is the API contract (D-07). DataFrame is an implementation detail of the XLSX renderer.
- **Never call `read_bytes()` on a file in the CLI and re-pass bytes without `source_name`:** Always pass `source_name=str(input_file)` so errors carry provenance.
- **Never hardcode XLSX column headers in English:** Headers are `Fecha/Cuenta/Subcuenta/Debe/Haber/Concepto` per D-12. This is a documented exception to the "English everything" rule.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DBF file reading | Custom DBF parser | `dbfread` | Handles all dBASE variants, deleted-record flags, field types, memo discovery |
| XLSX generation | Custom XML builder | `openpyxl` | Handles the full OOXML spec including number formats, styles, freeze panes |
| CLI argument parsing | `sys.argv` parsing | `typer` | Automatic `--help`, type coercion, error messages |
| Rich error display | Manual ANSI codes | `rich.panel.Panel` | Consistent formatting, color support detection |
| Synthetic DBF fixture generation | Committing binary blobs | `dbf` (ethanfurman) | Keeps repo blob-free; schema is explicit in code |
| Temp file lifecycle | Custom file management | `tempfile.NamedTemporaryFile` + context manager | Thread-safe naming, OS cleanup on failure |
| Package building | setuptools `setup.py` | `uv build` + `uv_build` | Zero-config, 10-35x faster |

**Key insight:** The only custom code in this phase is the ContaPlus business rules (D-A1…D-E3) and the bytes→tempfile bridge. Everything else is a thin wrapper over proven libraries.

---

## Common Pitfalls

### Pitfall 1: Windows NamedTemporaryFile double-open

**What goes wrong:** `tempfile.NamedTemporaryFile()` on Windows holds an exclusive lock while open. `dbfread.DBF(str(tmp.name))` fails with `PermissionError` because the file is already open by the `NamedTemporaryFile` object.

**Why it happens:** Windows file locking semantics differ from POSIX (POSIX allows multiple opens of the same file name).

**How to avoid:** Use `delete=False`, write and close the `NamedTemporaryFile` before yielding the path to `dbfread`, then `unlink()` in a `finally` block.

**Warning signs:** `PermissionError: [WinError 32]` or `OSError: [WinError 32]` during test runs on Windows.

### Pitfall 2: Both-non-zero check uses wrong comparison

**What goes wrong:** Using `debe != 0 and haber != 0` instead of `debe > 0 and haber > 0`. A row with `debe=-1, haber=0` would incorrectly trip the both-non-zero check.

**Why it happens:** D-C1 amendment (Gap #3) allows negatives; D-C2 is strictly "both strictly positive". The original formulation used `> 0`.

**How to avoid:** Copy the exact guard from `read_dbf.py`: `if debe > 0 and haber > 0`.

**Warning signs:** `test_negative_debe_passes_through` or `test_negative_haber_passes_through` fail.

### Pitfall 3: Non-journal DBF falls through to column resolution error

**What goes wrong:** Without the D-02 field-signature check, feeding `SUBCTA.DBF` produces a cryptic "DBF has no debe column; tried (eurodebe, ...)" error. This is confusing — the user knows they gave a DBF, they don't know why the column is missing.

**How to avoid:** Run `_assert_journal_shaped()` before `_pick_column()`. The error message should say "not a DIARIO.DBF journal table" with the available fields.

### Pitfall 4: openpyxl column auto-width iterates wrong object

**What goes wrong:** Iterating `ws.columns` returns tuples of `Cell` objects per column. `column_letter` is a property on the cell, not the tuple. Accessing it on the tuple causes `AttributeError`.

**How to avoid:** Use `col_cells[0].column_letter` to get the column letter from the first cell of each column tuple.

**Warning signs:** `AttributeError: 'tuple' object has no attribute 'column_letter'` during XLSX rendering.

### Pitfall 5: `dbfread` field names are UPPER CASE by default

**What goes wrong:** Without `lowernames=True`, field lookup against the lowercase candidate lists fails silently (all candidates miss).

**How to avoid:** Always pass `lowernames=True` to `dbfread.DBF()`. [CITED: SEED.md §5 D-E2]

### Pitfall 6: Typer `--force` / `--overwrite` alias not supported in all versions

**What goes wrong:** Older Typer versions treat the second string in `typer.Option("--force", "--overwrite")` as the env var name, not an alias.

**How to avoid:** Typer ≥0.9 supports multiple option names. Since we require `>=0.13` this is safe. Confirm with a smoke test: `contaplus2xlsx --help` should show `--force/--overwrite`.

---

## Code Examples

### Full reader invocation (public API)

```python
# Source: synthesized from SEED.md §5 + decisions D-03..D-06
from contaplus_reader import read, ContaPlusReadError

with open("DIARIO.DBF", "rb") as f:
    data = read(f, source_name="DIARIO.DBF")

journal = data.journal
print(f"{len(journal.rows)} rows, {journal.skipped_memo} memo lines skipped")
for row in journal.rows:
    print(row.fecha, row.cuenta, row.debe, row.haber, row.concepto)
```

### Test fixture using ported conftest pattern

```python
# Source: tw-contaplus/tests/conftest.py — port verbatim with module rename
_DIARIO_SPEC = (
    "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
    "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
)

def _build_diario_dbf(target: Path, rows: list[dict], *, codepage: str = "cp850") -> Path:
    table = dbf.Table(filename=str(target), field_specs=_DIARIO_SPEC, codepage=codepage)
    table.open(mode=dbf.READ_WRITE)
    try:
        for row in rows:
            table.append(row)
    finally:
        table.close()
    return target
```

### XLSX output from CLI (filesystem write)

```python
# Source: D-12, D-14, D-15, D-16 decisions
output_file.write_bytes(xlsx_bytes)
typer.echo(f"{output_file} — {len(journal.rows)} journal rows (1 memo line skipped)")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setuptools` + `setup.py` | `uv_build` + `pyproject.toml` | 2023–2025 | Zero-config build, faster, integrated with uv |
| `pipx` for CLI tool consumption | `uvx` | 2024–2025 | Same UX, no extra install; uvx uses uv's resolver |
| pandas `ExcelWriter(engine="openpyxl")` for XLSX | Direct `openpyxl.Workbook` | Ongoing choice | Direct openpyxl gives per-cell format control without DataFrame overhead |
| Committed binary `.dbf` test fixtures | Generated-at-collection-time via `dbf` library | Phase 4 tw-contaplus | Keeps repo blob-free, schema explicit in code |

**Deprecated/outdated:**
- `setup.py` / `setup.cfg`: replaced by `pyproject.toml`; do not use.
- `pipx install contaplus-reader`: still works but `uvx contaplus-reader` is the 2025 recommendation.
- `dbfread(load=True)`: never use on production journals; lazy iteration is the default and required.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ContaPlus DBFs present version bytes `0x03`, `0x83`, or `0x30` at offset 0 | DBF magic bytes, Pitfall list | The sniffer accept-list includes all known DBF version bytes; a novel byte value would cause a false-reject that is easy to fix by adding to the set |
| A2 | `SUBCTA.DBF` does not have a `FECHA` (type D) field or debe/haber columns | Journal field signature (D-02) | If SUBCTA has a date field we'd need a tighter check; the "available fields" in the error message provides a diagnostic |
| A3 | `dbf` (ethanfurman) 0.99.11 works correctly on Python 3.13 for fixture generation | Standard Stack dev deps | PyPI metadata states Python 3.3–3.13 compatibility — low risk |
| A4 | All runtime deps (dbfread, pandas, openpyxl, typer, rich) are established packages | Package Legitimacy Audit | All are decade-plus ecosystem libraries — negligible risk |
| A5 | openpyxl format 40 `#,##0.00_);[Red](#,##0.00)` renders correctly in LibreOffice Calc and Spanish Excel | XLSX rendering | Format is OOXML built-in (ID 40); rendering is viewer-dependent but this is the industry-standard format for the use case |

---

## Open Questions

1. **Python 3.14 availability on dev machine (marcwin)**
   - What we know: `uv python list` shows Python 3.14.5 available locally; Python 3.13 is downloadable but not pre-installed.
   - What's unclear: The pyproject.toml will specify `requires-python = ">=3.13"`. Development will run on 3.14 locally. No issue, but `uv sync` will auto-install 3.13 if needed.
   - Recommendation: Specify `requires-python = ">=3.13"` (matches SEED/CLAUDE.md constraint); let uv manage the specific version.

2. **`uv build` wheel name for `contaplus2xlsx` entry point**
   - What we know: The CLI script entry point `contaplus2xlsx = "contaplus_reader.cli:app"` in `[project.scripts]` should produce the `contaplus2xlsx` console script in the wheel.
   - What's unclear: Whether `uvx contaplus-reader` automatically runs `contaplus2xlsx` or if the user must `uvx contaplus2xlsx` (the script name).
   - Recommendation: The user runs `uvx contaplus2xlsx` (the script name, not the package name). This is the standard pattern for packages that expose named scripts. Confirm in a smoke test after `uv build`.

3. **openpyxl `fecha` cell type with `datetime.date` vs `datetime.datetime`**
   - What we know: `dbfread` returns type D fields as Python `datetime.date` objects; openpyxl `Workbook` cells accept both `date` and `datetime`.
   - What's unclear: Whether openpyxl formats a `datetime.date` cell with a date-only format automatically or requires explicit `number_format = "DD/MM/YYYY"`.
   - Recommendation: Always set `cell.number_format = "DD/MM/YYYY"` explicitly on fecha cells. openpyxl does not auto-apply formats.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python >=3.13 | Library runtime | ✓ | 3.14.5 (downloadable) | `uv python install 3.13` |
| uv | Build + package mgmt | ✓ | 0.11.13 | — |
| pip index (uv wrapper) | Package version verification | ✓ | via `uv run -m pip index` | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (latest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 — no config yet) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPUT-01 | `read()` accepts `bytes` input | unit | `uv run pytest tests/test_reader.py::test_read_accepts_bytes -x` | ❌ Wave 0 |
| INPUT-01 | `read()` accepts `BinaryIO` input | unit | `uv run pytest tests/test_reader.py::test_read_accepts_binary_io -x` | ❌ Wave 0 |
| INPUT-03 | ZIP bytes rejected with structured error | unit | `uv run pytest tests/test_reader.py::test_rejects_zip_bytes -x` | ❌ Wave 0 |
| INPUT-03 | Unknown bytes rejected with structured error | unit | `uv run pytest tests/test_reader.py::test_rejects_unknown_magic -x` | ❌ Wave 0 |
| JRNL-01 | 3-row happy path: cuenta derivation, column values | unit | `uv run pytest tests/test_reader.py::test_reads_cp850_basic_dbf -x` | ❌ Wave 0 |
| JRNL-01 | D-B2: cuenta = subcuenta[:4] | unit | `uv run pytest tests/test_reader.py::test_cuenta_derivation -x` | ❌ Wave 0 |
| JRNL-02 | cp1252 byte-29 header decodes under cp850-always | unit | `uv run pytest tests/test_reader.py::test_reads_cp1252_byte29_dbf -x` | ❌ Wave 0 |
| JRNL-02 | Deleted records skipped | unit | `uv run pytest tests/test_reader.py::test_skips_deleted_records -x` | ❌ Wave 0 |
| JRNL-02 | Both-zero memo lines skipped with count | unit | `uv run pytest tests/test_reader.py::test_both_zero_skips_with_count -x` | ❌ Wave 0 |
| JRNL-02 | Negative debe passes through | unit | `uv run pytest tests/test_reader.py::test_negative_debe_passes_through -x` | ❌ Wave 0 |
| JRNL-02 | Negative haber passes through | unit | `uv run pytest tests/test_reader.py::test_negative_haber_passes_through -x` | ❌ Wave 0 |
| JRNL-02 | Defensive column resolution: DEBE/HABER fallback | unit | `uv run pytest tests/test_reader.py::test_column_resolution_fallback -x` | ❌ Wave 0 |
| JRNL-03 | Null FECHA raises ContaPlusReadError | unit | `uv run pytest tests/test_reader.py::test_null_fecha_raises -x` | ❌ Wave 0 |
| JRNL-03 | Both-non-zero raises ContaPlusReadError with row_index | unit | `uv run pytest tests/test_reader.py::test_both_non_zero_raises -x` | ❌ Wave 0 |
| JRNL-03 | Invalid subcuenta raises ContaPlusReadError | unit | `uv run pytest tests/test_reader.py::test_invalid_subcuenta_raises -x` | ❌ Wave 0 |
| API-01 | Single bytes-first `read()` entry point | unit | (covered by INPUT-01 tests) | ❌ Wave 0 |
| API-02 | ContaPlusReadError carries row_index + column | unit | `uv run pytest tests/test_reader.py::test_error_carries_context -x` | ❌ Wave 0 |
| API-04 | Result types are self-contained (no tw-domain import) | unit | `uv run pytest tests/test_reader.py::test_no_tw_domain_import -x` | ❌ Wave 0 |
| XLSX-01 | render_journal produces non-empty bytes | unit | `uv run pytest tests/test_xlsx.py::test_render_produces_bytes -x` | ❌ Wave 0 |
| XLSX-01 | XLSX has Spanish headers | unit | `uv run pytest tests/test_xlsx.py::test_xlsx_headers_are_spanish -x` | ❌ Wave 0 |
| XLSX-01 | Header row is bold with fill | unit | `uv run pytest tests/test_xlsx.py::test_header_style -x` | ❌ Wave 0 |
| XLSX-01 | debe/haber cells have accounting number format | unit | `uv run pytest tests/test_xlsx.py::test_accounting_number_format -x` | ❌ Wave 0 |
| XLSX-04 | render_journal returns bytes (no filesystem path) | unit | (covered by XLSX-01 test) | ❌ Wave 0 |
| CLI-01 | Happy path: produces XLSX file | smoke | `uv run pytest tests/test_cli.py::test_cli_happy_path -x` | ❌ Wave 0 |
| CLI-01 | Refuses to overwrite without --force | smoke | `uv run pytest tests/test_cli.py::test_cli_refuses_overwrite -x` | ❌ Wave 0 |
| CLI-01 | --force overwrites existing file | smoke | `uv run pytest tests/test_cli.py::test_cli_force_overwrites -x` | ❌ Wave 0 |
| CLI-01 | Exit code 1 on ContaPlusReadError | smoke | `uv run pytest tests/test_cli.py::test_cli_error_exit_code -x` | ❌ Wave 0 |
| CLI-01 | Success output includes row count | smoke | `uv run pytest tests/test_cli.py::test_cli_success_output -x` | ❌ Wave 0 |
| CLI-04 | Wheel builds without error | smoke | `uv build && ls dist/*.whl` | ❌ Wave 0 |
| TEST-01 | Fixtures generated at collection time, no blobs | unit | `uv run pytest tests/ -x` (no .dbf files in repo) | ❌ Wave 0 |
| TEST-02 | All 27 ported tw-contaplus reader cases pass | unit | `uv run pytest tests/test_reader.py -v` | ❌ Wave 0 |
| DIST-02 | `uv build` produces .whl file | smoke | `uv build` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files and the package itself need to be created. Wave 0 tasks:

- [ ] `pyproject.toml` — project config + build system + entry points
- [ ] `src/contaplus_reader/__init__.py` — `read()` public API
- [ ] `src/contaplus_reader/models.py` — `ContaPlusData`, `ContaPlusJournal`, `JournalRow`, `ContaPlusReadError`
- [ ] `src/contaplus_reader/_bridge.py` — `bytes_to_tmppath()` context manager
- [ ] `src/contaplus_reader/_sniffer.py` — magic-byte sniffer
- [ ] `src/contaplus_reader/_reader.py` — dbfread iteration + business rules
- [ ] `src/contaplus_reader/xlsx.py` — `render_journal()`
- [ ] `src/contaplus_reader/cli.py` — Typer app
- [ ] `tests/conftest.py` — synthetic DBF fixture factory (port verbatim from tw-contaplus)
- [ ] `tests/test_reader.py` — ~27 ported test cases
- [ ] `tests/test_xlsx.py` — XLSX smoke tests
- [ ] `tests/test_cli.py` — CLI argument + exit-code tests
- [ ] `pytest` install: `uv add --dev pytest`

---

## Security Domain

> `security_enforcement` not explicitly set in config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no auth |
| V3 Session Management | No | N/A — stateless CLI |
| V4 Access Control | No | N/A — single-user tool |
| V5 Input Validation | Yes | Structured validation at reader boundary; ContaPlusReadError for all invalid inputs |
| V6 Cryptography | No | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed DBF header causing struct.error | Tampering | Catch `struct.error`, `ValueError`, `OSError` at reader boundary; wrap in ContaPlusReadError with row_index=-1 |
| UnicodeDecodeError from non-cp850 bytes | Tampering | Catch `UnicodeDecodeError`; raise structured error; never fall back to latin-1 |
| Path traversal via output file argument | Tampering | CLI uses `Path` from typer; output is written only to the exact path specified; no path derivation |
| Overwrite of existing critical files | Tampering | `--force` required to overwrite; default is refuse (D-15) |
| Temp file left on disk after error | Information Disclosure | `finally` block calls `Path(tmp.name).unlink(missing_ok=True)` |

---

## Sources

### Primary (HIGH confidence)

- `SEED.md` (repo root) — complete `DIARIO.DBF` format spec, encoding policy, column variants, business rules D-A1…D-E3, error model, fixture inventory
- `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — existing reader implementation, read in full
- `C:\dev\tax-workbench\packages\tw-contaplus\tests\conftest.py` — fixture factory to port verbatim
- `C:\dev\tax-workbench\packages\tw-contaplus\tests\test_read_dbf.py` — 27 test cases to port
- `uv run --python 3.14 -m pip index versions <pkg>` — all package versions verified on PyPI registry
- [openpyxl styles.numbers source](https://openpyxl.readthedocs.io/en/3.1.3/_modules/openpyxl/styles/numbers.html) — format 40 definition confirmed
- [typer positional arguments docs](https://typer.tiangolo.com/tutorial/arguments/optional/) — Annotated[Path, typer.Argument()] pattern
- [independent-software.com DBF format](http://independent-software.com/dbase-dbf-dbt-file-format.html) — DBF version byte table
- [uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/) — pyproject.toml configuration
- [uv init docs](https://docs.astral.sh/uv/concepts/projects/init/) — `uv init --lib` src layout

### Secondary (MEDIUM confidence)

- [Microsoft OOXML numFmt spec — locale rendering](https://learn.microsoft.com/en-us/answers/questions/945311/excel-number-format-not-same-as-in-styles-xml-when) — confirms `,`/`.` in format strings are locale-symbolic
- [dbfread issue #25](https://github.com/olemb/dbfread/issues/25) — confirmed: path-only API, no bytes support merged
- [dbfread memo.py GitHub source](https://github.com/olemb/dbfread/blob/master/dbfread/memo.py) — memo lookup relative to DBF path confirmed

### Tertiary (LOW confidence)

- ContaPlus-specific DBF version bytes (`0x03`, `0x30`) derived from general DBF spec + ContaPlus lineage [ASSUMED]
- SUBCTA.DBF / BALAN.DBF field sets used in D-02 journal-shape check [ASSUMED from SEED.md descriptions]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all versions verified on PyPI registry
- bytes→tempfile bridge: HIGH — Python stdlib, dbfread source reviewed
- Magic-byte sniffer values: MEDIUM — DBF spec verified; ContaPlus-specific bytes assumed
- Journal field signature (D-02): MEDIUM — DIARIO.DBF verified; SUBCTA/BALAN contrast assumed
- XLSX accounting format: HIGH — openpyxl source confirmed format 40
- Architecture patterns: HIGH — ported from working tw-contaplus implementation

**Research date:** 2026-05-15
**Valid until:** 2026-08-15 (stable ecosystem — uv/openpyxl/typer versions may update but patterns are stable)
