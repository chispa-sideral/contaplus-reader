# Phase 2: ZIP & Subaccounts - Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/contaplus_reader/_zip.py` | utility | file-I/O | `C:/dev/tax-workbench/packages/tw-contaplus/tw_contaplus/read_dbf.py` lines 54–135 | exact (same algorithm, adapt error type) |
| `src/contaplus_reader/_subcta.py` | utility | transform | `src/contaplus_reader/_reader.py` (`_pick_column` + `_read_dbf_path` error boundary) | role-match |
| `src/contaplus_reader/_sniffer.py` | utility | request-response | itself — flip one branch | self-modification |
| `src/contaplus_reader/models.py` | model | CRUD | itself — additive extension | self-modification |
| `src/contaplus_reader/__init__.py` | utility | request-response | itself — extend `read()` + dispatch | self-modification |
| `src/contaplus_reader/xlsx.py` | utility | transform | itself — generalise `render_journal()` | self-modification |
| `src/contaplus_reader/cli.py` | utility | request-response | itself — add `--company` option | self-modification |
| `tests/conftest.py` | test | batch | itself — add ZIP/SUBCTA fixture builders | self-modification |

---

## Pattern Assignments

### `src/contaplus_reader/_zip.py` (new utility, file-I/O)

**Analog:** `C:/dev/tax-workbench/packages/tw-contaplus/tw_contaplus/read_dbf.py` lines 54–135

This is a straight port of the two static methods `_safe_extractall` and
`_resolve_dbf_in_zip`, adapted to use `ContaPlusReadError` instead of
`BlockExecutionError`, and with the three Phase 2 differences: bytes-first
input (not a filesystem path), case-insensitive company matching (D-02),
single-company selector validation (D-03), and backslash normalisation in
entry names (RESEARCH.md Pitfall 2).

**Imports pattern** (model after `_reader.py` lines 1–27):
```python
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from contaplus_reader.models import ContaPlusReadError
```

**Zip-slip-safe extraction pattern** (analog: tw-contaplus lines 64–87, adapted):
```python
def _safe_extract_zip(raw: bytes, extract_dir: Path) -> None:
    """Extract ZIP bytes to extract_dir, rejecting any zip-slip entries."""
    base = extract_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for member in zf.infolist():
            # Normalise Windows backslash before resolve (Pitfall 2 in RESEARCH.md)
            clean = member.filename.replace("\\", "/")
            target = (extract_dir / clean).resolve()
            try:
                target.relative_to(base)
            except ValueError:
                raise ContaPlusReadError(
                    row_index=-1,
                    column=None,
                    message=f"Unsafe ZIP entry escapes temp dir: {member.filename!r}",
                )
            zf.extract(member, extract_dir)
```

**Company resolution pattern** (analog: tw-contaplus lines 91–135, adapted with D-02/D-03):
```python
def _resolve_company_diario(
    extract_dir: Path,
    company: str | None,
) -> Path:
    diarios = [
        p for p in extract_dir.rglob("*")
        if p.is_file() and p.name.lower() == "diario.dbf"   # case-insensitive (Pitfall 4)
    ]
    if not diarios:
        raise ContaPlusReadError(row_index=-1, column=None,
                                  message="No DIARIO.DBF found in ZIP")

    if len(diarios) == 1:
        if company is not None:
            # D-03: validate selector even for single-company ZIP
            if diarios[0].parent.name.lower() != company.lower():
                available = [diarios[0].parent.name]
                raise ContaPlusReadError(
                    row_index=-1, column=None,
                    message=f"Company {company!r} not found; available: {available}",
                )
        return diarios[0]

    # Multi-company: company selector is required (D-02)
    company_dirs = sorted({p.parent.name for p in diarios})
    if company is None:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"Multi-company ZIP: pass --company to select one of {company_dirs}",
        )
    matches = [p for p in diarios if p.parent.name.lower() == company.lower()]
    if len(matches) != 1:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"Company {company!r} not found; available: {company_dirs}",
        )
    return matches[0]
```

**Sibling-file discovery pattern** (RESEARCH.md Code Examples):
```python
def _find_sibling_dbf(diario_path: Path, basename_lower: str) -> Path | None:
    """Find a sibling DBF in the same directory as DIARIO.DBF (case-insensitive)."""
    for candidate in diario_path.parent.iterdir():
        if candidate.is_file() and candidate.name.lower() == basename_lower:
            return candidate
    return None
```

**TemporaryDirectory lifecycle note:** The `TemporaryDirectory` object must
be kept alive for the entire extraction-read-render pipeline. The recommended
owner is `read()` in `__init__.py` via `with tempfile.TemporaryDirectory() as tmpdir:`.
If `_zip.py` returns paths, it must also return the `TemporaryDirectory` object (or
accept it as a parameter) to prevent premature cleanup on Windows (RESEARCH.md Pitfall 1).

---

### `src/contaplus_reader/_subcta.py` (new utility, transform)

**Analog:** `src/contaplus_reader/_reader.py` — specifically `_pick_column` (lines 35–56)
and the `_read_dbf_path` error boundary (lines 217–233).

This module has no existing peer in the repo. The `_pick_column` function and
the `except ContaPlusReadError: raise` / `except (struct.error, ValueError,
OSError)` error-wrapping pattern from `_reader.py` are the exact model to copy.

**Imports pattern** (model after `_reader.py` lines 1–27):
```python
from __future__ import annotations

import struct
from pathlib import Path

from dbfread import DBF

from contaplus_reader._reader import _pick_column
from contaplus_reader.models import ContaPlusReadError
```

**Candidate-list constants** (extend `_reader.py` lines 31–32 pattern):
```python
# SUBCTA field-name variants (RESEARCH.md §SUBCTA Schema, D-16)
# Real archives use cod/titulo; codigo/descrip are defensive fallbacks.
_SUBCTA_COD_CANDIDATES: tuple[str, ...] = ("cod", "codigo")
_SUBCTA_TITULO_CANDIDATES: tuple[str, ...] = ("titulo", "descrip")
```

**SUBCTA lookup dict builder** (model after `_read_dbf_path` lines 125–233):
```python
def build_subcta_lookup(subcta_path: Path) -> dict[str, str | None]:
    """Build cod -> titulo lookup dict from SUBCTA.DBF.

    D-11: Returns empty dict if path is None (missing table is not an error).
    D-06: Present-but-unreadable SUBCTA raises ContaPlusReadError (aborts conversion).
    """
    try:
        table = DBF(
            str(subcta_path),
            lowernames=True,
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        field_set = {f.name for f in table.fields}
        cod_col = _pick_column(field_set, _SUBCTA_COD_CANDIDATES, kind="subcta.cod")
        titulo_col = _pick_column(field_set, _SUBCTA_TITULO_CANDIDATES, kind="subcta.titulo")
        return {
            rec[cod_col].rstrip(): (rec[titulo_col] or "").rstrip() or None
            for rec in table
            if rec.get(cod_col)
        }
    except ContaPlusReadError:
        raise  # present-but-unreadable -> abort (D-06); already structured
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"SUBCTA.DBF read error: {exc}",
            original=exc,
        ) from exc
```

**Generic raw-table reader** (for `grupos`/`usuarios`/`empresa`, model after
`_read_dbf_path` error boundary):
```python
def read_table_raw(path: Path, table_name: str) -> list[dict[str, object]]:
    """Read all records from a DBF as a list of dicts. Full dump (D-13).

    D-06: Raises ContaPlusReadError if present but unreadable.
    """
    try:
        table = DBF(
            str(path),
            lowernames=False,    # keep original field names for raw header (D-13)
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        return [dict(rec) for rec in table]
    except ContaPlusReadError:
        raise
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"{table_name} read error: {exc}",
            original=exc,
        ) from exc
```

---

### `src/contaplus_reader/_sniffer.py` (self-modification)

**Analog:** itself — flip one branch.

The only change is lines 68–71: replace the "future phase" rejection with a
`ZipFormat` sentinel or a pass-through that allows `__init__.py` to dispatch
to the ZIP path.

**Branch to flip** (current `_sniffer.py` lines 67–77):
```python
# CURRENT (Phase 1) — rejects ZIP:
if first_byte is None or first_byte not in _KNOWN_DBF_VERSION_BYTES:
    hint = (
        "ZIP archive detected — ZIP input is supported in a future phase"
        if first_byte == 0x50  # 'P' -- PK magic byte
        else "not a DBF file"
    )
    raise ContaPlusReadError(row_index=-1, column=None,
                              message=f"Unsupported input format: {hint}")

# PHASE 2 — sniff() returns a format enum or the caller checks separately.
# Simplest approach: sniff() returns a literal "zip" | "dbf" | raises.
```

The planner should decide whether `sniff()` returns a discriminated type or
`__init__.py` peeks at the first byte itself before calling `sniff()`. Either
way the validation set `_KNOWN_DBF_VERSION_BYTES` is unchanged.

---

### `src/contaplus_reader/models.py` (self-modification, additive)

**Analog:** itself — additive extension of `ContaPlusData` and `JournalRow`.

**`JournalRow` extension** (current `models.py` lines 92–108, D-09):
```python
# CURRENT (Phase 1):
@dataclass(frozen=True)
class JournalRow:
    fecha: datetime.date
    cuenta: str
    subcuenta: str
    debe: float
    haber: float
    concepto: str | None

# PHASE 2 — add defaulted field AFTER existing fields (Pitfall 5 in RESEARCH.md):
@dataclass(frozen=True)
class JournalRow:
    fecha: datetime.date
    cuenta: str
    subcuenta: str
    debe: float
    haber: float
    concepto: str | None
    subcuenta_nombre: str | None = None   # D-09: additive, default None
```

**`ContaPlusData` extension** (current `models.py` lines 124–133, D-05):
```python
# CURRENT (Phase 1):
@dataclass
class ContaPlusData:
    journal: ContaPlusJournal | None = None

# PHASE 2 — add sibling table attributes (each its own typed result type):
@dataclass
class ContaPlusData:
    journal: ContaPlusJournal | None = None
    subcta: SubctaTable | None = None       # D-05: present when SUBCTA.DBF found
    empresa: GenericTable | None = None     # D-05: present when empresa.dbf found
    grupos: GenericTable | None = None      # D-05: present when grupos.dbf found
    usuarios: GenericTable | None = None    # D-05: present when usuarios.dbf found
```

**New typed result types** (model after `ContaPlusJournal` at lines 110–122):
```python
# New frozen dataclasses for SUBCTA and generic tables.
# Exact type names are planner discretion per D-05.

@dataclass(frozen=True)
class SubctaRow:
    """One subaccount record — all fields from SUBCTA.DBF (D-13 full dump)."""
    # Fields: all DBF columns, with cod/titulo guaranteed by _pick_column.
    # Store as dict to support full-dump without enumerating 130+ field names.
    fields: dict[str, object]

@dataclass(frozen=True)
class SubctaTable:
    rows: tuple[SubctaRow, ...]
    source_name: str | None = None

# For grupos/usuarios/empresa: a generic table holding raw dicts (D-13).
@dataclass(frozen=True)
class GenericTable:
    """Full dump of an undocumented table. headers = DBF field names in order."""
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    source_name: str | None = None
```

---

### `src/contaplus_reader/__init__.py` (self-modification)

**Analog:** itself — extend `read()` with `company` param and ZIP dispatch.

**Current `read()` signature** (lines 39–59):
```python
def read(
    data: bytes | BinaryIO,
    source_name: str | None = None,
) -> ContaPlusData:
    sniff(data)  # raises ContaPlusReadError on unsupported format
    with bytes_to_tmppath(data) as path:
        journal = _read_dbf_path(path, source_name=source_name)
    return ContaPlusData(journal=journal)
```

**Phase 2 extended `read()`** (D-04, bytes-first, company param):
```python
def read(
    data: bytes | BinaryIO,
    source_name: str | None = None,
    company: str | None = None,          # D-04: additive; None = auto-detect
) -> ContaPlusData:
    raw: bytes = data if isinstance(data, bytes) else data.read()
    fmt = sniff(raw)   # now returns "dbf" | "zip"; raises on unrecognised
    if fmt == "zip":
        # ZIP path -- lifecycle of tmpdir owned here (RESEARCH.md Pitfall 1)
        with tempfile.TemporaryDirectory(prefix="contaplus_") as tmpdir:
            extract_dir = Path(tmpdir)
            _safe_extract_zip(raw, extract_dir)
            return _read_from_zip(extract_dir, company=company,
                                   source_name=source_name)
    else:
        # DBF path (unchanged from Phase 1)
        if company is not None:
            raise ContaPlusReadError(
                row_index=-1, column=None,
                message="company selector is not applicable to a raw DBF input",
            )
        with bytes_to_tmppath(raw) as path:
            journal = _read_dbf_path(path, source_name=source_name)
        return ContaPlusData(journal=journal)
```

**Imports addition** (lines 1–36 current block):
```python
# Add to existing imports:
import tempfile
from pathlib import Path
from contaplus_reader._zip import _safe_extract_zip, _resolve_company_diario, _find_sibling_dbf
from contaplus_reader._subcta import build_subcta_lookup, read_table_raw
```

---

### `src/contaplus_reader/_reader.py` (self-modification)

**Analog:** itself — `_read_dbf_path` gains `subcta_lookup` parameter; `JournalRow`
construction gains `subcuenta_nombre`.

**`_read_dbf_path` signature extension** (current lines 98–102):
```python
# CURRENT:
def _read_dbf_path(
    path: Path,
    *,
    source_name: str | None = None,
) -> ContaPlusJournal:

# PHASE 2:
def _read_dbf_path(
    path: Path,
    *,
    source_name: str | None = None,
    subcta_lookup: dict[str, str | None] | None = None,   # D-09/D-11
) -> ContaPlusJournal:
```

**`JournalRow` construction extension** (current lines 194–204, D-09):
```python
# CURRENT:
rows.append(
    JournalRow(
        fecha=fecha_raw,
        cuenta=cuenta,
        subcuenta=subcuenta,
        debe=debe,
        haber=haber,
        concepto=concepto,
    )
)

# PHASE 2 -- subcuenta_nombre added (D-09/D-10/D-11):
subcuenta_nombre: str | None = None
if subcta_lookup is not None:
    subcuenta_nombre = subcta_lookup.get(subcuenta)   # None if key absent (D-11)

rows.append(
    JournalRow(
        fecha=fecha_raw,
        cuenta=cuenta,
        subcuenta=subcuenta,
        debe=debe,
        haber=haber,
        concepto=concepto,
        subcuenta_nombre=subcuenta_nombre,   # D-09
    )
)
```

---

### `src/contaplus_reader/xlsx.py` (self-modification)

**Analog:** itself — `render_journal()` generalises to multi-sheet `render()`.

**Current single-sheet function** (lines 37–79):
```python
def render_journal(journal: ContaPlusJournal) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario"
    # ... header row, freeze_panes, data rows, auto-size ...
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

**Phase 2 data-driven renderer** (D-12, D-13, D-14, D-15):
```python
# New entry point -- consumes ContaPlusData (not just journal).
def render(data: ContaPlusData) -> bytes:
    """Convert all populated tables in ContaPlusData to a multi-sheet xlsx workbook.

    Sheet order (D-14): Diario, Subcuentas, Empresa, Grupos, Usuarios.
    Only tables that are not None produce a sheet (D-06 / Success Criterion #4).
    """
    wb = Workbook()

    # Sheet 1: Diario (always present -- wb.active is sheet 1)
    _render_journal_sheet(wb.active, data.journal)

    if data.subcta is not None:
        _render_subcta_sheet(wb.create_sheet("Subcuentas"), data.subcta)
    if data.empresa is not None:
        _render_generic_sheet(wb.create_sheet("Empresa"), data.empresa)
    if data.grupos is not None:
        _render_generic_sheet(wb.create_sheet("Grupos"), data.grupos)
    if data.usuarios is not None:
        _render_generic_sheet(wb.create_sheet("Usuarios"), data.usuarios)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

# Backward-compatible alias for Phase 1 tests (RESEARCH.md Open Question 3):
def render_journal(journal: ContaPlusJournal) -> bytes:
    from contaplus_reader.models import ContaPlusData
    return render(ContaPlusData(journal=journal))
```

**Diario sheet with Descripción column** (D-15 — insert after Subcuenta):
```python
# PHASE 2 HEADERS (D-14/D-15 -- DO NOT change to English):
HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]

# In _render_journal_sheet, data row construction:
for row_idx, jr in enumerate(journal.rows, 2):
    ws.cell(row=row_idx, column=1, value=jr.fecha).number_format = DATE_FMT
    ws.cell(row=row_idx, column=2, value=jr.cuenta)
    ws.cell(row=row_idx, column=3, value=jr.subcuenta)
    ws.cell(row=row_idx, column=4, value=jr.subcuenta_nombre)   # D-15: blank when None
    ws.cell(row=row_idx, column=5, value=jr.debe).number_format = ACCOUNTING_FMT
    ws.cell(row=row_idx, column=6, value=jr.haber).number_format = ACCOUNTING_FMT
    ws.cell(row=row_idx, column=7, value=jr.concepto)
```

**Generic sheet renderer** (D-13 full dump, raw DBF field names as headers):
```python
def _render_generic_sheet(ws: Any, table: GenericTable) -> None:
    """Render a GenericTable onto ws with Phase-1 styling (D-10 pattern)."""
    # Header row -- raw DBF field names (D-13)
    for col_idx, header in enumerate(table.headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL    # reuse Phase-1 constants
        cell.font = HEADER_FONT

    ws.freeze_panes = "A2"

    for row_idx, row in enumerate(table.rows, 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-size (same pattern as Phase-1 lines 72–75)
    for col_cells in ws.columns:
        max_len = max(
            (len(str("" if c.value is None else c.value)) for c in col_cells),
            default=0,
        )
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)
```

---

### `src/contaplus_reader/cli.py` (self-modification)

**Analog:** itself — add `--company` `typer.Option` and update the call to `read()`.

**Current `main()` signature** (lines 25–36):
```python
@app.command()
def main(
    input_file: Annotated[Path, typer.Argument(help="Path to DIARIO.DBF file")],
    output_file: Annotated[Path, typer.Argument(help="Path to write .xlsx output")],
    force: Annotated[
        bool,
        typer.Option("--force", "--overwrite",
                     help="Overwrite output file if it already exists"),
    ] = False,
) -> None:
```

**Phase 2 extended `main()`** (D-07 / D-08):
```python
@app.command()
def main(
    input_file: Annotated[Path, typer.Argument(help="Path to DIARIO.DBF or backup .zip")],
    output_file: Annotated[Path, typer.Argument(help="Path to write .xlsx output")],
    company: Annotated[
        str | None,
        typer.Option(
            "--company",
            help="Company directory name (e.g. Emp01) for multi-company ZIP backups",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "--overwrite",
                     help="Overwrite output file if it already exists"),
    ] = False,
) -> None:
```

**Updated `read()` call** (current line 66):
```python
# CURRENT:
data = read(raw_bytes, source_name=str(input_file))

# PHASE 2:
data = read(raw_bytes, source_name=str(input_file), company=company)
```

**Rich error panel pattern** (current lines 67–78 — copy verbatim for
multi-company ContaPlusReadError surfacing, D-08):
```python
except ContaPlusReadError as exc:
    # D-17 / D-08: Structured Rich panel -- no Python traceback.
    console.print(
        Panel(
            f"{exc.message}\n"
            f"Row: {exc.row_index if exc.row_index >= 0 else 'n/a'}\n"
            f"Column: {exc.column or 'n/a'}",
            title="ContaPlus Read Error",
            border_style="red",
        )
    )
    raise typer.Exit(1) from None
```

**Updated XLSX call** (current line 81–82):
```python
# CURRENT:
xlsx_bytes = render_journal(journal)

# PHASE 2:
from contaplus_reader.xlsx import render
xlsx_bytes = render(data)
```

**Updated success summary** (current line 84–88 — extend for multi-sheet, D-16):
```python
# Multi-sheet summary (sheet count replaces single "journal rows" line):
sheet_count = sum(1 for t in [data.journal, data.subcta, data.empresa,
                               data.grupos, data.usuarios] if t is not None)
row_count = len(data.journal.rows) if data.journal else 0
skip_msg = (
    f" ({data.journal.skipped_memo} memo lines skipped)"
    if data.journal and data.journal.skipped_memo else ""
)
typer.echo(
    f"{output_file} — {row_count} journal rows, {sheet_count} sheet(s){skip_msg}"
)
```

---

### `tests/conftest.py` (self-modification)

**Analog:** itself — extend with ZIP and SUBCTA fixture builders. The tw-contaplus
`conftest.py` lines 173–210 are the model for `single_company_zip` /
`multi_company_zip`.

**Additional imports needed** (current conftest line 28 block):
```python
import zipfile    # new for Phase 2 ZIP fixtures
```

**SUBCTA DBF builder** (model after `_build_diario_dbf` lines 40–58):
```python
_SUBCTA_SPEC = "cod C(12,0); titulo C(40,0); nif C(15,0)"   # minimal verified schema

def _build_subcta_dbf(
    target: Path,
    rows: list[dict[str, Any]],
    *,
    codepage: str = "cp850",
) -> Path:
    """Build a SubCta.dbf at `target` with the given rows. Returns the path."""
    table = dbf.Table(
        filename=str(target),
        field_specs=_SUBCTA_SPEC,
        codepage=codepage,
    )
    table.open(mode=dbf.READ_WRITE)
    try:
        for row in rows:
            table.append(row)
    finally:
        table.close()
    return target
```

**Single-company ZIP fixture** (model after tw-contaplus conftest lines 173–195):
```python
@pytest.fixture(scope="session")
def single_company_zip(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP backup with one company (Emp01), DIARIO + SubCta."""
    zip_dir = tmp_path_factory.mktemp("single_company_zip")
    zip_path = zip_dir / "backup.zip"
    subcta_path = zip_dir / "SubCta.dbf"
    _build_subcta_dbf(subcta_path, [
        {"cod": "4300000", "titulo": "Cliente XYZ", "nif": ""},
        {"cod": "7000000", "titulo": "Ventas mercaderias", "nif": ""},
    ])
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")
    return zip_path
```

**Multi-company ZIP fixture** (model after tw-contaplus conftest lines 196–210):
```python
@pytest.fixture(scope="session")
def multi_company_zip(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP backup with two companies (Emp01, Emp02), DIARIO only."""
    zip_dir = tmp_path_factory.mktemp("multi_company_zip")
    zip_path = zip_dir / "multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(cp850_basic_dbf, arcname="Emp02/Diario.dbf")
    return zip_path
```

**Generic table DBF builders for `grupos`/`usuarios`/`empresa`** — use the
same `_build_diario_dbf` pattern with assumed specs from RESEARCH.md
§Critical Finding (all `[ASSUMED]` — no real data):
```python
_GRUPOS_SPEC = "COD C(10,0); DESCRIP C(40,0)"
_USUARIOS_SPEC = "CODIGO C(10,0); NOMBRE C(40,0); CLAVE C(20,0)"
_EMPRESA_SPEC = "CODIGO C(10,0); NOMBRE C(60,0); NIF C(15,0)"
```

---

## Shared Patterns

### Structured Error Construction
**Source:** `src/contaplus_reader/models.py` lines 39–90 (`ContaPlusReadError`)
**Apply to:** `_zip.py`, `_subcta.py`, modified `__init__.py`, modified `_reader.py`

Every Phase 2 failure (zip-slip, company not found, table unreadable) raises:
```python
raise ContaPlusReadError(
    row_index=-1,       # file-level error
    column=None,
    message="<descriptive English message>",
    original=exc,       # wrapped cause, or omit if None
)
```
File-level errors always use `row_index=-1` (established in Phase 1). The
`original` field is present only when wrapping a lower-level exception.

### DBF Invocation
**Source:** `src/contaplus_reader/_reader.py` lines 126–131
**Apply to:** `_subcta.py` and any new DBF reader
```python
table = DBF(
    str(path),
    lowernames=True,
    encoding="cp850",
    ignore_missing_memofile=True,
)
```
For the generic raw-table reader (`grupos`/`usuarios`/`empresa`) use
`lowernames=False` to preserve original DBF field names for raw headers (D-13).

### `_pick_column` Candidate Resolution
**Source:** `src/contaplus_reader/_reader.py` lines 35–56
**Apply to:** `_subcta.py` (for `cod`/`titulo` resolution)

The function is already importable from `_reader.py`. Import it; do not copy.
```python
from contaplus_reader._reader import _pick_column
```

### Rich Error Panel
**Source:** `src/contaplus_reader/cli.py` lines 67–78
**Apply to:** `cli.py` (unchanged pattern, handles multi-company error too)

The existing `except ContaPlusReadError` block already matches the D-08
requirement. The multi-company "pass --company" message surfaces through
`exc.message` automatically.

### Styling Constants
**Source:** `src/contaplus_reader/xlsx.py` lines 27–34
**Apply to:** All new sheet renderers in `xlsx.py`

`ACCOUNTING_FMT`, `DATE_FMT`, `HEADER_FILL`, `HEADER_FONT` are module-level
constants. Import them by name in any helper that applies header styling — do
not redefine.

### Bytes-First Input Normalisation
**Source:** `src/contaplus_reader/_bridge.py` line 31 and `__init__.py` Phase 2 pattern
**Apply to:** `_zip.py` (receives already-normalised `bytes`)

The convention established in `_bridge.py` is:
```python
raw: bytes = data if isinstance(data, bytes) else data.read()
```
`read()` in `__init__.py` performs this normalisation once and passes `raw:
bytes` into `_safe_extract_zip`. Do not re-normalise inside `_zip.py`.

---

## No Analog Found

All 8 files have analogs (exact or role-match). No file requires fallback to
RESEARCH.md patterns exclusively.

| File | Analog Quality | Note |
|------|---------------|-------|
| `_zip.py` | exact | Direct port from tw-contaplus with error-type substitution |
| `_subcta.py` | role-match | No existing lookup-builder; `_reader.py` error pattern is the model |

---

## Metadata

**Analog search scope:** `src/contaplus_reader/`, `tests/`, `C:/dev/tax-workbench/packages/tw-contaplus/`
**Files scanned:** 11 (7 Phase 1 source, 4 Phase 1 test, tw-contaplus `read_dbf.py`)
**Pattern extraction date:** 2026-05-16
