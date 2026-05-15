# Phase 1: Journal Slice - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 12 new files (greenfield repo)
**Analogs found:** 12 / 12 (all from external `tw-contaplus` package — no in-repo analogs exist)

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `pyproject.toml` | config | — | RESEARCH.md Pattern 8 (synthesized) | research-derived |
| `src/contaplus_reader/__init__.py` | public API surface | request-response | `read_dbf.py` `ReadDBF.run()` (entry point pattern) | role-match |
| `src/contaplus_reader/models.py` | model | — | RESEARCH.md Pattern 4 + 5 (synthesized from SEED.md error model) | research-derived |
| `src/contaplus_reader/_bridge.py` | utility | file-I/O | RESEARCH.md Pattern 1 (synthesized from Python tempfile docs) | research-derived |
| `src/contaplus_reader/_sniffer.py` | utility | transform | RESEARCH.md Pattern 2 (synthesized from DBF format spec) | research-derived |
| `src/contaplus_reader/_reader.py` | service | CRUD | `read_dbf.py` `ReadDBF._read_dbf()` | exact |
| `src/contaplus_reader/xlsx.py` | service | transform | RESEARCH.md Pattern 6 (synthesized from openpyxl docs) | research-derived |
| `src/contaplus_reader/cli.py` | controller | request-response | RESEARCH.md Pattern 7 (synthesized from Typer docs) | research-derived |
| `tests/conftest.py` | config/test | — | `tw-contaplus/tests/conftest.py` | exact |
| `tests/test_reader.py` | test | — | `tw-contaplus/tests/test_read_dbf.py` | exact |
| `tests/test_xlsx.py` | test | — | (no analog — XLSX tests are new) | no analog |
| `tests/test_cli.py` | test | — | (no analog — CLI tests are new) | no analog |

---

## Pattern Assignments

### `pyproject.toml` (config)

**Analog:** RESEARCH.md Pattern 8 (verified against uv build backend docs)

**Full layout** (copy verbatim, adjust only `version` and `authors`):
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

---

### `src/contaplus_reader/__init__.py` (public API, request-response)

**Analog:** `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — `ReadDBF.run()` method (lines 49–61) provides the dispatch pattern, but the new file wraps it in a function instead of a class.

**Public surface pattern** — re-export all public names from submodules:
```python
from contaplus_reader.models import (
    ContaPlusData,
    ContaPlusJournal,
    JournalRow,
    ContaPlusReadError,
)
from contaplus_reader._sniffer import sniff
from contaplus_reader._reader import _read_dbf_path
from contaplus_reader._bridge import bytes_to_tmppath

__all__ = [
    "read",
    "ContaPlusData",
    "ContaPlusJournal",
    "JournalRow",
    "ContaPlusReadError",
]

def read(data: bytes | BinaryIO, source_name: str | None = None) -> ContaPlusData:
    """Read a ContaPlus DIARIO.DBF from bytes or file-like object."""
    sniff(data)                           # raises ContaPlusReadError on bad input
    with bytes_to_tmppath(data) as path:
        journal = _read_dbf_path(path, source_name=source_name)
    return ContaPlusData(journal=journal)
```

**Import pattern** (from analog `read_dbf.py` lines 16–32, adapted):
```python
from __future__ import annotations

import io
from typing import BinaryIO
```

---

### `src/contaplus_reader/models.py` (model)

**Analog:** RESEARCH.md Pattern 4 + 5 (synthesized from SEED.md error model + CONTEXT.md D-03/07/08/09).
Also references `tw_domain.errors.BlockExecutionError` as the structural template for `ContaPlusReadError`.

**Error model** (copy from RESEARCH.md Pattern 4):
```python
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

**Result model** (copy from RESEARCH.md Pattern 5):
```python
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

**Critical constraint:** `ContaPlusData` is NOT frozen — it will gain new attributes in Phases 2–3. `ContaPlusJournal` and `JournalRow` ARE frozen (immutable read results).

---

### `src/contaplus_reader/_bridge.py` (utility, file-I/O)

**Analog:** RESEARCH.md Pattern 1. No in-codebase analog.

**Full implementation** (copy verbatim):
```python
from __future__ import annotations

import io
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

@contextmanager
def bytes_to_tmppath(data: bytes | io.IOBase) -> Generator[Path, None, None]:
    """Write bytes or file-like to a NamedTemporaryFile and yield its Path.

    On Windows, NamedTemporaryFile cannot be reopened while open.
    Strategy: delete=False + explicit unlink in finally.
    """
    raw: bytes = data if isinstance(data, bytes) else data.read()
    tmp = tempfile.NamedTemporaryFile(suffix=".dbf", delete=False)
    try:
        tmp.write(raw)
        tmp.close()           # close before yielding — required on Windows
        yield Path(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
```

**Windows pitfall to avoid:** Never yield before `tmp.close()`. The `PermissionError: [WinError 32]` is the symptom if you do (RESEARCH.md Pitfall 1).

---

### `src/contaplus_reader/_sniffer.py` (utility, transform)

**Analog:** RESEARCH.md Pattern 2. No in-codebase analog.

**Full implementation** (copy verbatim from RESEARCH.md Pattern 2):
```python
from __future__ import annotations

import io
from contaplus_reader.models import ContaPlusReadError

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
        if hasattr(data, "seek"):
            data.seek(0)
        first_byte = first_byte_bytes[0] if first_byte_bytes else None

    if first_byte is None or first_byte not in _KNOWN_DBF_VERSION_BYTES:
        hint = (
            "ZIP archive detected — ZIP input is supported in a future phase"
            if first_byte == 0x50
            else "not a DBF file"
        )
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Unsupported input format: {hint}",
        )
```

---

### `src/contaplus_reader/_reader.py` (service, CRUD)

**Analog:** `C:\dev\tax-workbench\packages\tw-contaplus\tw_contaplus\read_dbf.py` — `ReadDBF._read_dbf()` (lines 137–265) is the **exact** porting source.

**Imports pattern** (adapted from `read_dbf.py` lines 16–32):
```python
from __future__ import annotations

import logging
import struct
from pathlib import Path
from typing import Any

from dbfread import DBF

from contaplus_reader.models import (
    ContaPlusData,
    ContaPlusJournal,
    JournalRow,
    ContaPlusReadError,
)
```

**Column candidate constants** (from `read_dbf.py` lines 35–36, unchanged):
```python
_DEBE_COL_CANDIDATES: tuple[str, ...] = ("eurodebe", "eurdebe", "debe", "pesedebe")
_HABER_COL_CANDIDATES: tuple[str, ...] = ("eurohaber", "eurhaber", "haber", "pesehaber")
```

**Journal-shape check** (new — D-02, from RESEARCH.md Pattern 3, insert BEFORE `_pick_column` calls):
```python
def _assert_journal_shaped(table: DBF) -> None:
    field_set = {n.lower() for n in table.field_names}
    field_type_map = {f.name.lower(): f.type for f in table.fields}

    if "fecha" not in field_set or field_type_map.get("fecha") != "D":
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(multi-table support is planned in a future phase). "
                f"Available fields: {sorted(field_set)}"
            ),
        )
    _DEBE = {"eurodebe", "eurdebe", "debe", "pesedebe"}
    _HABER = {"eurohaber", "eurhaber", "haber", "pesehaber"}
    if not (field_set & _DEBE) or not (field_set & _HABER):
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(no debit/credit columns found). "
                f"Available fields: {sorted(field_set)}"
            ),
        )
```

**Core read function** (port from `read_dbf.py` `_read_dbf()` lines 137–247, adapt `BlockExecutionError` → `ContaPlusReadError`, drop `params`, return `ContaPlusJournal` not `Diario`):
```python
def _read_dbf_path(path: Path, *, source_name: str | None = None) -> ContaPlusJournal:
    try:
        table = DBF(
            str(path),
            lowernames=True,
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        _assert_journal_shaped(table)          # D-02 check (new vs analog)
        field_set = {n.lower() for n in table.field_names}
        debe_col = _pick_column(field_set, _DEBE_COL_CANDIDATES, kind="debe")
        haber_col = _pick_column(field_set, _HABER_COL_CANDIDATES, kind="haber")

        rows: list[JournalRow] = []
        skipped_memo = 0
        for idx, record in enumerate(table):
            fecha_raw = record.get("fecha")
            if fecha_raw is None:
                raise ContaPlusReadError(
                    row_index=idx, column="fecha",
                    message="null FECHA",
                )
            debe = float(record.get(debe_col) or 0)
            haber = float(record.get(haber_col) or 0)
            if debe > 0 and haber > 0:          # D-C2; note: NOT != 0 (Pitfall 2)
                raise ContaPlusReadError(
                    row_index=idx, column=None,
                    message=f"both-non-zero row: debe={debe}, haber={haber}",
                )
            if debe == 0 and haber == 0:        # D-C3: memo skip
                skipped_memo += 1
                continue

            subcta_raw = record.get("subcta") or ""
            subcuenta = subcta_raw.rstrip() if isinstance(subcta_raw, str) else str(subcta_raw).rstrip()
            if not subcuenta or not subcuenta.isdigit() or len(subcuenta) < 3:
                raise ContaPlusReadError(
                    row_index=idx, column="subcuenta",
                    message=f"empty/non-numeric SUBCTA: {subcta_raw!r}",
                )
            cuenta = subcuenta[:4]
            concepto_raw = record.get("concepto") or ""
            concepto_str = concepto_raw.rstrip() if isinstance(concepto_raw, str) else str(concepto_raw).rstrip()
            concepto: str | None = concepto_str if concepto_str else None

            rows.append(JournalRow(
                fecha=fecha_raw,
                cuenta=cuenta,
                subcuenta=subcuenta,
                debe=debe,
                haber=haber,
                concepto=concepto,
            ))

        if skipped_memo:
            logger.info("_read_dbf_path skipped %d memo lines (zero amounts)", skipped_memo)

        return ContaPlusJournal(rows=rows, skipped_memo=skipped_memo, source_name=source_name)

    except ContaPlusReadError:
        raise
    except UnicodeDecodeError as exc:
        raise ContaPlusReadError(row_index=-1, column=None,
            message="Unicode decode error — input must be cp850-encoded",
            original=exc) from exc
    except (struct.error, ValueError, OSError) as exc:
        raise ContaPlusReadError(row_index=-1, column=None,
            message=f"DBF read error: {exc}",
            original=exc) from exc
```

**Column picker** (port from `read_dbf.py` lines 249–265, swap error type):
```python
def _pick_column(field_set: set[str], candidates: tuple[str, ...], *, kind: str) -> str:
    for name in candidates:
        if name in field_set:
            return name
    raise ContaPlusReadError(
        row_index=-1, column=kind,
        message=f"DBF has no {kind} column; tried {candidates}; available: {sorted(field_set)}",
    )
```

**Key porting deltas from the analog** (changes required vs `read_dbf.py`):
- Remove: `BlockExecutionError` → use `ContaPlusReadError`
- Remove: `Diario` return type → use `ContaPlusJournal`
- Remove: `pd.DataFrame(rows)` at the end → collect `list[JournalRow]` directly
- Remove: `ReadDBFParams` dependency — signature becomes `_read_dbf_path(path, source_name)`
- Add: `_assert_journal_shaped()` call before `_pick_column` (D-02)
- Remove: ZIP handling, `_safe_extractall`, `_resolve_dbf_in_zip` (Phase 2)
- Keep unchanged: `lowernames=True`, `encoding="cp850"`, `ignore_missing_memofile=True`
- Keep unchanged: `debe > 0 and haber > 0` guard (NOT `!= 0`)
- Keep unchanged: `subcuenta.isdigit() and len >= 3` validation
- Keep unchanged: `.rstrip()` on CHAR fields

---

### `src/contaplus_reader/xlsx.py` (service, transform)

**Analog:** RESEARCH.md Pattern 6 (synthesized from openpyxl docs). No in-codebase analog.

**Full implementation** (copy from RESEARCH.md Pattern 6):
```python
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from contaplus_reader.models import ContaPlusJournal

# D-12: Spanish headers are intentional — these label Spanish statutory accounting data.
# Do NOT change to English.
HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]
ACCOUNTING_FMT = "#,##0.00_);[Red](#,##0.00)"  # openpyxl built-in format 40; red negatives per D-11
DATE_FMT = "DD/MM/YYYY"
HEADER_FILL = PatternFill(fill_type="solid", fgColor="4472C4")  # Office Blue
HEADER_FONT = Font(bold=True, color="FFFFFF")

def render_journal(journal: ContaPlusJournal) -> bytes:
    """Convert a ContaPlusJournal to an xlsx workbook, returned as bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario"

    # Header row (row 1)
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"  # freeze header row

    # Data rows
    for row_idx, jr in enumerate(journal.rows, 2):
        ws.cell(row=row_idx, column=1, value=jr.fecha).number_format = DATE_FMT
        ws.cell(row=row_idx, column=2, value=jr.cuenta)
        ws.cell(row=row_idx, column=3, value=jr.subcuenta)
        ws.cell(row=row_idx, column=4, value=jr.debe).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=5, value=jr.haber).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=6, value=jr.concepto)

    # Auto-size columns (openpyxl has no built-in autofit)
    for col_cells in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col_cells), default=0)
        # Pitfall 4: use col_cells[0].column_letter, NOT col_cells.column_letter
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

---

### `src/contaplus_reader/cli.py` (controller, request-response)

**Analog:** RESEARCH.md Pattern 7 (synthesized from Typer docs + D-14/15/16/17). No in-codebase analog.

**Full implementation** (copy from RESEARCH.md Pattern 7):
```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

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

**Entry point wiring** (in `pyproject.toml` `[project.scripts]`):
```toml
contaplus2xlsx = "contaplus_reader.cli:app"
```

---

### `tests/conftest.py` (test config)

**Analog:** `C:\dev\tax-workbench\packages\tw-contaplus\tests\conftest.py` (lines 1–211) — **port verbatim**.

**What to keep:**
- `_DIARIO_SPEC` constant (lines 32–35) — unchanged
- `_build_diario_dbf()` helper function (lines 38–56) — unchanged
- `cp850_basic_dbf` fixture (lines 59–93) — unchanged
- `cp1252_byte29_dbf` fixture (lines 96–117) — unchanged
- `with_deleted_record_dbf` fixture (lines 120–154) — unchanged
- `diario_dbf_builder` fixture (lines 157–170) — unchanged

**What to remove:**
- `single_company_zip` fixture (lines 173–183) — ZIP is Phase 2
- `multi_company_zip` fixture (lines 185–210) — ZIP is Phase 2

**Import change** (lines 1–26): drop `zipfile` import (no ZIP fixtures in Phase 1). Keep all other imports unchanged.

**Fixture scope:** all fixtures remain `scope="session"` (expensive DBF generation runs once per test session).

**_DIARIO_SPEC** (line 32–35, copy verbatim):
```python
_DIARIO_SPEC = (
    "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
    "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
)
```

---

### `tests/test_reader.py` (test)

**Analog:** `C:\dev\tax-workbench\packages\tw-contaplus\tests\test_read_dbf.py` (lines 1–256) — port the reader tests, adapting imports and class references.

**Import change** (lines 1–19 of analog):
```python
# Replace:
from tw_domain import Diario
from tw_domain.errors import BlockExecutionError
from tw_contaplus.params import ReadDBFParams
from tw_contaplus.read_dbf import ReadDBF

# With:
from contaplus_reader import read, ContaPlusReadError
from contaplus_reader.models import ContaPlusData, ContaPlusJournal, JournalRow
```

**Invocation pattern change** — analog calls `ReadDBF(ReadDBFParams(path=path)).run()`. New pattern:
```python
# Analog (read_dbf.py call):
diario = ReadDBF(ReadDBFParams(path=cp850_basic_dbf)).run()

# New pattern (bytes-first API):
data = read(cp850_basic_dbf.read_bytes(), source_name=str(cp850_basic_dbf))
journal = data.journal
```

**Assertion changes** — analog asserts on `diario.df["column"]`. New pattern asserts on `journal.rows`:
```python
# Analog:
assert len(diario.df) == 3
assert diario.df["cuenta"].tolist() == ["4300", "7000", "6000"]

# New:
assert len(journal.rows) == 3
assert [r.cuenta for r in journal.rows] == ["4300", "7000", "6000"]
```

**Error type change** — `BlockExecutionError` → `ContaPlusReadError`:
```python
# Analog:
with pytest.raises(BlockExecutionError) as exc_info:
    ReadDBF(ReadDBFParams(path=path)).run()
assert exc_info.value.row_index == 0

# New:
with pytest.raises(ContaPlusReadError) as exc_info:
    read(path.read_bytes())
assert exc_info.value.row_index == 0
```

**Tests to drop (out of Phase 1 scope):**
- `test_params_accepts_dbf_path` — no `ReadDBFParams` class
- `test_params_accepts_zip_path` — ZIP is Phase 2
- `test_params_rejects_other_suffix` — no `ReadDBFParams` class
- `test_params_is_frozen` — no `ReadDBFParams` class
- `test_block_name`, `test_block_input_shapes_is_empty_tuple`, `test_block_output_shape_is_diario` — block class gone
- `test_reader_module_does_not_import_pyside6`, `test_params_module_does_not_import_pyside6` — Qt concern gone
- `test_output_df_fecha_is_datetime` — no DataFrame in result; `fecha` is already `datetime.date`
- `test_output_df_debe_haber_are_float` — no DataFrame; check `jr.debe` type directly
- `test_reads_single_company_zip`, `test_multi_company_zip_*`, `test_zip_with_no_diario_dbf_raises` — ZIP is Phase 2

**Tests to add (Phase 1 new requirements):**
- `test_read_accepts_bytes` — INPUT-01
- `test_read_accepts_binary_io` — INPUT-01
- `test_rejects_zip_bytes` — INPUT-03 (check error message contains "ZIP")
- `test_rejects_unknown_magic` — INPUT-03
- `test_no_tw_domain_import` — API-04
- `test_error_carries_context` — API-02
- `test_non_journal_dbf_rejected` — D-02 (feed SUBCTA-shaped DBF, expect structured error)

**Tests to keep (port verbatim with invocation adaption):**
- `test_reads_cp850_basic_dbf` — JRNL-01
- `test_reads_cp850_basic_dbf_has_correct_amounts` — JRNL-01
- `test_reads_cp850_basic_dbf_concepto_not_empty` — JRNL-01
- `test_reads_cp1252_byte29_dbf_with_cp850_decode` — JRNL-02 / D-D1
- `test_reads_skips_deleted_records` — JRNL-02
- `test_negative_debe_passes_through` — JRNL-02 / D-C1
- `test_negative_haber_passes_through` — JRNL-02 / D-C1
- `test_both_non_zero_raises` — JRNL-03 / D-C2
- `test_both_zero_skips_silently_with_log` — JRNL-02 / D-C3 (adapt: check `journal.skipped_memo`)
- `test_column_resolution_falls_back_to_debe_haber` — JRNL-02 / D-E1
- `test_output_df_has_correct_columns` — API-04 (adapt: check `JournalRow` fields)

**`test_both_zero_skips_silently_with_log` adaptation note:**
The analog checks `caplog` for `"memo lines"` text. The new `_reader.py` also calls `logger.info(...)` with the same message — keep the `caplog` assertion, adjust logger name from `tw_contaplus.read_dbf` to `contaplus_reader._reader`.

---

### `tests/test_xlsx.py` (test)

**Analog:** None — XLSX tests are new. Follow pytest conventions from `test_read_dbf.py`.

**Pattern to follow** (from `test_read_dbf.py` test structure):
```python
from __future__ import annotations
import io
import pytest
from openpyxl import load_workbook
from contaplus_reader.xlsx import render_journal, HEADERS
from contaplus_reader.models import ContaPlusJournal, JournalRow
import datetime

def _make_journal(*rows) -> ContaPlusJournal:
    """Helper: build a ContaPlusJournal from simple row dicts."""
    return ContaPlusJournal(rows=list(rows), skipped_memo=0)

def _sample_row() -> JournalRow:
    return JournalRow(
        fecha=datetime.date(2025, 1, 1),
        cuenta="4300",
        subcuenta="4300000",
        debe=100.0,
        haber=0.0,
        concepto="Test",
    )
```

**Key assertions pattern** (open xlsx bytes with openpyxl to inspect):
```python
def test_render_produces_bytes():
    journal = _make_journal(_sample_row())
    result = render_journal(journal)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_xlsx_headers_are_spanish():
    journal = _make_journal(_sample_row())
    wb = load_workbook(io.BytesIO(render_journal(journal)))
    ws = wb.active
    headers = [ws.cell(row=1, column=i+1).value for i in range(len(HEADERS))]
    assert headers == ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]
```

---

### `tests/test_cli.py` (test)

**Analog:** None — CLI tests are new. Use `typer.testing.CliRunner`.

**Pattern to follow** (Typer testing docs):
```python
from __future__ import annotations
from pathlib import Path
from typer.testing import CliRunner
from contaplus_reader.cli import app

runner = CliRunner()

def test_cli_refuses_overwrite(tmp_path, cp850_basic_dbf):
    out = tmp_path / "out.xlsx"
    out.touch()  # pre-exist
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 1
    assert "already exists" in result.output or "already exists" in (result.stderr or "")
```

**Note:** `cp850_basic_dbf` fixture from `conftest.py` is available to CLI tests. CLI tests should use `session`-scoped fixtures for DBF inputs but `tmp_path` (function-scoped) for output paths to avoid state leakage.

---

## Shared Patterns

### Error Model (all modules)

**Source:** `src/contaplus_reader/models.py` — `ContaPlusReadError`

**Apply to:** `_sniffer.py`, `_reader.py`, `__init__.py`, `cli.py`

The structured error carries `(message, row_index, column, original)`. All library code raises `ContaPlusReadError`; the CLI catches it and presents via `rich.Panel`. No module leaks Python tracebacks — CLI uses `raise typer.Exit(1) from None`.

### DBF invocation (any future DBF reader)

**Source:** `_reader.py` (ported from `read_dbf.py` lines 139–143)

```python
table = DBF(
    str(path),           # path-only API; bridge handles bytes→path
    lowernames=True,     # D-E2: field names lowercased for candidate matching
    encoding="cp850",    # D-D1: unconditional; never latin-1, never auto-detect
    ignore_missing_memofile=True,  # D-E2: no .fpt sibling in temp dir
)
```

**Apply to:** any future `_reader_*.py` modules in Phases 2–3.

### Fixture factory pattern (all test files)

**Source:** `tests/conftest.py` — `_build_diario_dbf()` + `diario_dbf_builder` fixture

**Apply to:** `test_reader.py`, `test_xlsx.py`, `test_cli.py`

All synthetic fixtures are built at collection time via the `dbf` library. No committed `.dbf` binary blobs. The `diario_dbf_builder` fixture (function-call returns a new `Path`) is the parametric entry point for anomaly tests.

### Bytes-first invocation (callers of `read()`)

**Source:** `cli.py`

```python
data = read(input_file.read_bytes(), source_name=str(input_file))
```

**Apply to:** all test files that call `read()` — always pass `path.read_bytes()`, not the path itself.

---

## No Analog Found (in-repo)

The repository is greenfield — no source code exists yet. All 12 files being created are covered by either the external `tw-contaplus` analog or RESEARCH.md synthesized patterns. The following have no close external analog and depend entirely on RESEARCH.md:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/contaplus_reader/_bridge.py` | utility | file-I/O | No tempfile bridge pattern in tw-contaplus (it was path-based) |
| `src/contaplus_reader/_sniffer.py` | utility | transform | No magic-byte sniffer in tw-contaplus (used suffix, not bytes) |
| `src/contaplus_reader/xlsx.py` | service | transform | No XLSX renderer in tw-contaplus (returned Diario/DataFrame) |
| `src/contaplus_reader/cli.py` | controller | request-response | No Typer CLI in tw-contaplus (was Qt-based) |
| `tests/test_xlsx.py` | test | — | No XLSX tests in tw-contaplus |
| `tests/test_cli.py` | test | — | No CLI tests in tw-contaplus |

---

## Metadata

**Analog search scope:** `C:\dev\tax-workbench\packages\tw-contaplus\`
**Files scanned:** 4 external files (read_dbf.py, params.py, tests/conftest.py, tests/test_read_dbf.py)
**In-repo files scanned:** 0 (greenfield)
**Pattern extraction date:** 2026-05-15
