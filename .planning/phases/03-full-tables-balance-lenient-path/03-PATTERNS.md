# Phase 3: Full Tables, Balance & Lenient Path — Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 9 (7 modified, 1 new, 1 new test file + 3 extended test files)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/contaplus_reader/models.py` | model | — | itself (Phase 1/2 base) | exact — additive extension |
| `src/contaplus_reader/__init__.py` | service | request-response | itself (Phase 2 base) | exact — additive extension |
| `src/contaplus_reader/_reader.py` | service | request-response | itself (Phase 2 base) | exact — parametric extension of D-C5 loop |
| `src/contaplus_reader/_balance.py` | utility | transform | `src/contaplus_reader/_subcta.py` `read_table_raw()` | role-match (pure computation, no I/O) |
| `src/contaplus_reader/_subcta.py` | service | file-I/O | itself (unchanged) | exact — `read_table_raw()` reused verbatim for all 4 new tables + BALAN |
| `src/contaplus_reader/_zip.py` | service | file-I/O | itself (unchanged) | exact — `_find_sibling_dbf()` reused for 4 new siblings |
| `src/contaplus_reader/xlsx.py` | utility | transform | itself (Phase 2 base) | exact — new sheet renderers follow `_render_generic_sheet()` |
| `src/contaplus_reader/cli.py` | controller | request-response | itself (Phase 2 base) | exact — additive `--lenient` flag |
| `tests/conftest.py` | test | — | itself (Phase 2 base) | exact — `_build_generic_dbf()` reused for new DBF specs |
| `tests/test_tables.py` | test | — | `tests/test_reader.py` | role-match |
| `tests/test_balance.py` | test | — | `tests/test_reader.py` | role-match |
| `tests/test_lenient.py` | test | — | `tests/test_reader.py` | role-match |
| `tests/test_xlsx.py` (extended) | test | — | itself | exact |

---

## Pattern Assignments

### `src/contaplus_reader/models.py` — additive extension

**Analog:** itself (lines 1–180 — read in full above)

**Imports pattern** (lines 1–14):
```python
from __future__ import annotations

import datetime
from dataclasses import dataclass
import dataclasses as _dataclasses
```

**Existing frozen dataclass pattern** (lines 92–110) — copy for all new frozen types:
```python
@dataclass(frozen=True)
class JournalRow:
    fecha: datetime.date
    cuenta: str
    subcuenta: str
    debe: float
    haber: float
    concepto: str | None
    subcuenta_nombre: str | None = None  # additive field with default
```

**ContaPlusData extension seam** (lines 167–179) — add new attributes here with `None` defaults:
```python
@dataclass
class ContaPlusData:
    """NOT frozen -- grows new attributes in Phases 2-3."""
    journal: ContaPlusJournal | None = None
    subcta: SubctaTable | None = None
    empresa: GenericTable | None = None
    grupos: GenericTable | None = None
    usuarios: GenericTable | None = None
    # Phase 3 additions follow the same pattern:
    # balan: GenericTable | None = None
    # venci: GenericTable | None = None
    # ...
    # balance_cuenta: BalanceTable | None = None
    # balance_subcuenta: BalanceTable | None = None
    # problems: ProblemsReport | None = None
```

**New types to add** (from RESEARCH.md §models.py — New Types):
- `ProblemEntry` — `@dataclass(frozen=True)` with fields: `table: str`, `row_index: int`, `column: str`, `reason: str`, `value: str`
- `ProblemsReport` — `@dataclass(frozen=True)` with field: `entries: tuple[ProblemEntry, ...]`
- `BalanceRow` — `@dataclass(frozen=True)` with fields: `code: str`, `suma_debe: Decimal`, `suma_haber: Decimal`, `saldo_deudor: Decimal`, `saldo_acreedor: Decimal`, `saldo: Decimal`, `descripcion: str | None = None`
- `BalanceTable` — `@dataclass(frozen=True)` with fields: `rows: tuple[BalanceRow, ...]`, `level: str`

**Import addition required** — add `from decimal import Decimal` to the imports block.

---

### `src/contaplus_reader/__init__.py` — additive extension

**Analog:** itself (lines 1–127 — read in full above)

**Imports pattern** (lines 1–38): copy as-is, add new model imports for Phase 3 types.

**Optional-table read pattern** (lines 97–115) — this is the exact pattern to replicate for each new sibling table:
```python
# Strict (existing — replicate for venci/prede/amoinv/nivel/balan):
grupos_path = _find_sibling_dbf(diario_path, "grupos.dbf")
grupos = read_table_raw(grupos_path, "grupos.dbf") if grupos_path else None
```

**Lenient wrapper pattern** (from RESEARCH.md §Pattern 2) — wrap each table read in lenient mode:
```python
# Lenient (new — wrap each optional-table read):
if venci_path:
    try:
        venci = read_table_raw(venci_path, "venci.dbf")
    except ContaPlusReadError as exc:
        venci = None
        problems.append(ProblemEntry(
            table="venci.dbf",
            row_index=-1,
            column="",
            reason=exc.message,
            value="",
        ))
```

**Whole-journal lenient catch pattern** (from RESEARCH.md §Q5):
```python
try:
    journal = _read_dbf_path(diario_path, ..., lenient=lenient, problems=problems)
except ContaPlusReadError as exc:
    if lenient:
        journal = None
        problems.append(ProblemEntry(
            table="DIARIO", row_index=-1, column="",
            reason=exc.message, value="",
        ))
    else:
        raise
```

**ContaPlusData return** (lines 109–115) — extend with all new attributes:
```python
return ContaPlusData(
    journal=journal,
    subcta=subcta_table,
    empresa=empresa,
    grupos=grupos,
    usuarios=usuarios,
    # Phase 3 additions:
    # balan=balan, venci=venci, prede=prede, amoinv=amoinv, nivel=nivel,
    # balance_cuenta=balance_cuenta, balance_subcuenta=balance_subcuenta,
    # problems=ProblemsReport(entries=tuple(problems)) if problems else None,
)
```

**`read()` signature extension** (lines 41–45) — add `lenient: bool = False` parameter:
```python
def read(
    data: bytes | BinaryIO,
    source_name: str | None = None,
    company: str | None = None,
    lenient: bool = False,   # D-01: strict default; API-03 opt-in
) -> ContaPlusData:
```

---

### `src/contaplus_reader/_reader.py` — parametric extension of D-C5 loop

**Analog:** itself (lines 1–268 — read in full above)

**`_read_dbf_path()` signature extension** (lines 107–112) — add `lenient` and `problems` params:
```python
def _read_dbf_path(
    path: Path,
    *,
    source_name: str | None = None,
    subcta_lookup: dict[str, str | None] | None = None,
    lenient: bool = False,          # Phase 3 D-01
    problems: list[...] | None = None,  # Phase 3 accumulator
) -> ContaPlusJournal:
```

**D-C5 loop** (lines 158–230) — extract per-row validation into `_build_journal_row()` helper, then add lenient catch around its call. Critical rule from RESEARCH.md §Pitfall 3: re-raise when `exc.row_index == -1` even in lenient mode:
```python
for idx, record in enumerate(table):
    try:
        row = _build_journal_row(record, idx, debe_col, haber_col, subcta_lookup)
    except ContaPlusReadError as exc:
        if not lenient or exc.row_index == -1:  # file-level always raises
            raise
        if problems is not None:
            problems.append(ProblemEntry(
                table="DIARIO",
                row_index=idx,
                column=exc.column or "",
                reason=exc.message,
                value=str(record.get(exc.column or "subcta", "")),
            ))
        continue
    if row is None:  # memo skip (D-C3) -- NOT added to problems (D-05)
        skipped_memo += 1
        continue
    rows.append(row)
```

**Error handling pattern** (lines 252–267) — unchanged; re-raise chain preserved:
```python
except ContaPlusReadError:
    raise  # re-raise unchanged -- already structured
except UnicodeDecodeError as exc:
    raise ContaPlusReadError(row_index=-1, column=None,
        message="Unicode decode error — input must be cp850-encoded",
        original=exc) from exc
except (struct.error, ValueError, OSError) as exc:
    raise ContaPlusReadError(row_index=-1, column=None,
        message=f"DBF read error: {exc}", original=exc) from exc
```

---

### `src/contaplus_reader/_balance.py` — new module

**Analog:** `src/contaplus_reader/_subcta.py` (pure computation without I/O; same import style)

**Module header pattern** (from `_subcta.py` lines 1–14):
```python
"""Trial balance (sumas y saldos) computation from ContaPlusJournal rows.

BAL-02: Groups journal rows by cuenta (4-digit) and subcuenta; sums debe/haber
using Decimal; derives saldo_deudor / saldo_acreedor per account.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal

from contaplus_reader.models import BalanceRow, BalanceTable, ContaPlusJournal

logger = logging.getLogger("contaplus_reader._balance")
```

**Core computation pattern** (from RESEARCH.md §Pattern 3):
```python
def compute_balance(
    journal: ContaPlusJournal,
    *,
    by_subcuenta: bool = False,
    subcta_lookup: dict[str, str | None] | None = None,
) -> BalanceTable:
    key_fn = (lambda r: r.subcuenta) if by_subcuenta else (lambda r: r.cuenta)
    debe: dict[str, Decimal] = defaultdict(Decimal)
    haber: dict[str, Decimal] = defaultdict(Decimal)
    for row in journal.rows:
        k = key_fn(row)
        # Mandatory str() conversion: Decimal(float) gives wrong binary repr
        debe[k] += Decimal(str(row.debe))
        haber[k] += Decimal(str(row.haber))
    result = []
    for key in sorted(debe.keys()):
        sd = debe[key]; sh = haber[key]
        saldo_deudor = max(sd - sh, Decimal("0"))
        saldo_acreedor = max(sh - sd, Decimal("0"))
        signed_saldo = sd - sh
        descripcion: str | None = None
        if by_subcuenta and subcta_lookup:
            descripcion = subcta_lookup.get(key)
        result.append(BalanceRow(
            code=key, suma_debe=sd, suma_haber=sh,
            saldo_deudor=saldo_deudor, saldo_acreedor=saldo_acreedor,
            saldo=signed_saldo, descripcion=descripcion,
        ))
    level = "subcuenta" if by_subcuenta else "cuenta"
    return BalanceTable(rows=tuple(result), level=level)
```

**No error wrapping needed** — this function operates on already-validated `ContaPlusJournal.rows` (no I/O), so no `ContaPlusReadError` wrapping is required.

---

### `src/contaplus_reader/_subcta.py` — unchanged

**Analog:** itself (lines 1–201 — read in full above)

`read_table_raw()` (lines 160–201) is reused verbatim for all Phase 3 operational tables and BALAN. The caller (`__init__.py`) passes the appropriate path and `table_name`. No changes to `_subcta.py` are required.

**`read_table_raw()` call pattern** (lines 160–200) — copy for venci/prede/amoinv/nivel/balan:
```python
def read_table_raw(path: Path, table_name: str) -> GenericTable:
    try:
        table = DBF(
            str(path),
            lowernames=False,      # keep original field names (D-13)
            encoding="cp850",      # never latin-1
            ignore_missing_memofile=True,
        )
        headers = tuple(f.name for f in table.fields)  # WR-05: schema from DBF
        rows = tuple(tuple(rec[h] for h in headers) for rec in table)
        return GenericTable(headers=headers, rows=rows, source_name=str(path))
    except ContaPlusReadError:
        raise
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"{table_name} read error: {exc}", original=exc,
        ) from exc
```

---

### `src/contaplus_reader/_zip.py` — unchanged

**Analog:** itself (lines 210–227 — `_find_sibling_dbf` read in full above)

`_find_sibling_dbf()` is reused verbatim for the 4 new sibling lookups. No changes to `_zip.py` are required.

**`_find_sibling_dbf()` call pattern** (lines 210–227):
```python
def _find_sibling_dbf(diario_path: Path, basename_lower: str) -> Path | None:
    for candidate in diario_path.parent.iterdir():
        if candidate.is_file() and candidate.name.lower() == basename_lower:
            return candidate
    return None
```

**Uncatalogued-DBF scan pattern** (new in `__init__.py`, lenient mode only, per D-13):
```python
# After extracting all catalogued tables, scan for uncatalogued .dbf files:
CATALOGUE = {"diario.dbf", "subcta.dbf", "balan.dbf", "grupos.dbf",
             "usuarios.dbf", "empresa.dbf", "venci.dbf", "prede.dbf",
             "amoinv.dbf", "nivel.dbf"}
for candidate in diario_path.parent.iterdir():
    if (candidate.is_file()
            and candidate.suffix.lower() == ".dbf"
            and candidate.name.lower() not in CATALOGUE):
        problems.append(ProblemEntry(
            table=candidate.name.upper(),
            row_index=-1,
            column="",
            reason="unrecognized table — not extracted",
            value="",
        ))
```

---

### `src/contaplus_reader/xlsx.py` — additive extension

**Analog:** itself (lines 1–182 — read in full above)

**Existing imports pattern** (lines 1–28) — add `GenericTable` already imported; add new model imports:
```python
from contaplus_reader.models import (
    BalanceTable,      # new Phase 3
    ContaPlusData,
    ContaPlusJournal,
    GenericTable,
    ProblemsReport,    # new Phase 3
    SubctaTable,
)
```

**`render()` data-driven pattern** (lines 46–74) — extend with Phase 3 sheets in the documented order:
```python
def render(data: ContaPlusData) -> bytes:
    wb = Workbook()
    _render_journal_sheet(wb.active, data.journal)
    if data.subcta is not None:
        _render_subcta_sheet(wb.create_sheet("Subcuentas"), data.subcta)
    # Phase 3 additions follow this pattern:
    # if data.balan is not None:
    #     _render_balan_sheet(wb.create_sheet("Balance"), data.balan)
    # if data.balance_cuenta is not None:
    #     _render_balance_sheet(wb.create_sheet("Sumas y Saldos (Cuentas)"), data.balance_cuenta)
    # if data.balance_subcuenta is not None:
    #     _render_balance_sheet(wb.create_sheet("Sumas y Saldos (Subcuentas)"), data.balance_subcuenta)
    # if data.venci is not None:
    #     _render_generic_sheet(wb.create_sheet("Vencimientos"), data.venci)
    # ... prede -> "Predefinidos", amoinv -> "Amortizaciones", nivel -> "Niveles"
    # ... empresa, grupos, usuarios (existing)
    # if data.problems is not None and data.problems.entries:
    #     _render_problems_sheet(wb.create_sheet("Problemas"), data.problems)
```

**`_render_generic_sheet()` pattern** (lines 151–167) — copy verbatim for each new operational table sheet; the sheet title is set by the caller via `wb.create_sheet("Vencimientos")` etc.:
```python
def _render_generic_sheet(ws: Worksheet, table: GenericTable) -> None:
    for col_idx, header in enumerate(table.headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"
    for row_idx, row in enumerate(table.rows, 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    _autosize_columns(ws)
```

**New `_render_balan_sheet()` pattern** (from RESEARCH.md §Pattern 4):
```python
from decimal import Decimal
from openpyxl.styles import Font, PatternFill

BANNER_FILL = PatternFill(fill_type="solid", fgColor="FF0000")
BANNER_FONT = Font(bold=True, color="FFFFFF")

def _render_balan_sheet(ws: Worksheet, balan: GenericTable) -> None:
    # ws.title already set by caller via create_sheet("Balance")
    try:
        sdo_idx = next(i for i, h in enumerate(balan.headers) if h.upper() == "SDO_CIERRE")
    except StopIteration:
        sdo_idx = None  # unknown schema -- skip descuadre check, no banner

    header_row_offset = 1
    if sdo_idx is not None:
        sdo_sum = sum(
            (Decimal(str(row[sdo_idx])) for row in balan.rows if row[sdo_idx] is not None),
            Decimal("0"),
        )
        if sdo_sum != Decimal("0"):
            cell = ws.cell(row=1, column=1,
                value=f"AVISO: Balance desnivelado — SDO_CIERRE suma {sdo_sum} ≠ 0. Datos derivados, puede ser no fiable.")
            cell.fill = BANNER_FILL
            cell.font = BANNER_FONT
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
            header_row_offset = 2

    # Write headers at header_row_offset, data starting at header_row_offset+1
    for col_idx, header in enumerate(balan.headers, 1):
        cell = ws.cell(row=header_row_offset, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = ws.cell(row=header_row_offset + 1, column=1).coordinate
    for row_idx, row in enumerate(balan.rows, header_row_offset + 1):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    # Pitfall 5: compute widths from data rows only (not the banner)
    _autosize_columns_from_offset(ws, start_row=header_row_offset)
```

**New `_render_balance_sheet()` pattern** — for BalanceTable (both cuenta and subcuenta levels):
```python
# Spanish column headers per D-08
_BALANCE_HEADERS_CUENTA = ["Cuenta", "Suma Debe", "Suma Haber", "Saldo Deudor", "Saldo Acreedor", "Saldo"]
_BALANCE_HEADERS_SUBCUENTA = ["Subcuenta", "Descripción", "Suma Debe", "Suma Haber", "Saldo Deudor", "Saldo Acreedor", "Saldo"]

def _render_balance_sheet(ws: Worksheet, table: BalanceTable) -> None:
    headers = _BALANCE_HEADERS_SUBCUENTA if table.level == "subcuenta" else _BALANCE_HEADERS_CUENTA
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"
    for row_idx, br in enumerate(table.rows, 2):
        if table.level == "subcuenta":
            ws.cell(row=row_idx, column=1, value=br.code)
            ws.cell(row=row_idx, column=2, value=br.descripcion)
            offset = 2
        else:
            ws.cell(row=row_idx, column=1, value=br.code)
            offset = 1
        ws.cell(row=row_idx, column=offset+1, value=float(br.suma_debe)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset+2, value=float(br.suma_haber)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset+3, value=float(br.saldo_deudor)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset+4, value=float(br.saldo_acreedor)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset+5, value=float(br.saldo)).number_format = ACCOUNTING_FMT
    _autosize_columns(ws)
```

**New `_render_problems_sheet()` pattern**:
```python
_PROBLEMS_HEADERS = ["Tabla", "Fila", "Columna", "Motivo", "Valor"]

def _render_problems_sheet(ws: Worksheet, report: ProblemsReport) -> None:
    for col_idx, header in enumerate(_PROBLEMS_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    ws.freeze_panes = "A2"
    for row_idx, entry in enumerate(report.entries, 2):
        ws.cell(row=row_idx, column=1, value=entry.table)
        ws.cell(row=row_idx, column=2, value=entry.row_index)
        ws.cell(row=row_idx, column=3, value=entry.column)
        ws.cell(row=row_idx, column=4, value=entry.reason)
        ws.cell(row=row_idx, column=5, value=entry.value)
    _autosize_columns(ws)
```

**`_autosize_columns()` pattern** (lines 170–181) — for the banner-offset variant, the planner should add `_autosize_columns_from_offset(ws, start_row)` that starts iteration at `start_row` instead of row 1 to avoid the Pitfall 5 banner-width problem.

---

### `src/contaplus_reader/cli.py` — additive extension

**Analog:** itself (lines 1–129 — read in full above)

**Existing `--force` flag pattern** (lines 37–45) — copy exactly for `--lenient`:
```python
lenient: Annotated[
    bool,
    typer.Option(
        "--lenient",
        help="Extract all readable data; skip unreadable rows/tables into a problems sheet",
    ),
] = False,
```

**`read()` call** (line 75) — add `lenient=lenient`:
```python
data = read(raw_bytes, source_name=str(input_file), company=company, lenient=lenient)
```

**One-line summary** (lines 117–128) — extend to include problems count when present:
```python
# Phase 3: add problems count to summary when lenient mode produced problems
problems_msg = ""
if data.problems and data.problems.entries:
    problems_msg = f", {len(data.problems.entries)} problem(s)"
typer.echo(f"{output_file} — {row_count} journal rows, {sheet_count} sheet(s){skip_msg}{problems_msg}")
```

**Rich error panel pattern** (lines 76–87) — unchanged; `ContaPlusReadError` already surfaced here; lenient mode never raises `ContaPlusReadError` from the read path, so no changes to the error handler are needed.

---

### `tests/conftest.py` — additive extension

**Analog:** itself (lines 1–376 — read in full above)

**DBF spec constants pattern** (lines 42–53) — add Phase 3 specs immediately after the existing Phase 2 specs:
```python
# Phase 3 operational table specs (RESEARCH.md §Q1 — VERIFIED from pii-test-data/)
_VENCI_SPEC = (
    "FECHA D; COD C(12); ACPA C(1); CONTRA C(12); CONCEPTO C(25); "
    "PTA N(16,2); TIPO C(2); PREPROCESO L; ESTADO L; DOCUMENTO C(10); "
    "IMPMONEX N(16,2); CODDIVISA C(5); MONEDAUSO C(1); LFACTPLUS L; "
    "FECHAPAG D; REMESA C(12); NCOBRO N(2,0); NPAGARE N(2,0); "
    "EURO N(16,2); NUMRECFAC C(12); METALIMP N(16,2)"
)
_PREDE_SPEC = (
    "ASIEN N(4,0); TSUBCTA C(1); SUBCTA C(12); NSUBCTA N(3,0); "
    "TCONTRA C(1); CONTRA C(12); NCONTRA N(3,0); CIMPORTE C(1); "
    "TIMPORTE C(1); IMPORTE C(50); NIMPORTE N(3,0); TCONCEPTO C(1); "
    "CONCEPTO C(25); FACTURA L; IVA N(5,2); MOD347 L"
    # (minimal subset — full 41-field spec used for schema tests)
)
_AMOINV_SPEC = (
    "NUMEROINV C(10); DOCUMENTO C(10); FECHACOMP D; FECPRIAM D; "
    "CODNAT C(10); IMPORTCOM N(16,2); CONCEPTO C(25); GRUPO C(2); "
    "SUBCTAAM C(12); SUBCTADO C(12); IMPORTAM N(16,2); TPCA N(6,2)"
    # (minimal subset for testing)
)
_NIVEL_SPEC = (
    "N1 L; N2 L; N3 L; N4 L; N5 L; N6 L; "
    "N7 L; N8 L; N9 L; N10 L; N11 L; N12 L; LASTCASADO N(6,0)"
)
_BALAN_SPEC = (
    "NATURALEZA C(2); CODBAL C(10); DESCRIP C(100); CTA C(11); "
    "TIPO N(1,0); BITMAP C(10); DOBLE C(1); FORMULA C(255); "
    "NIVEL N(2,0); DESGLOSE N(2,0); ACPA C(1); NUMERO C(6); "
    "CTAPGC C(12); SDO_CIERRE N(19,2); NIV_CIERRE N(2,0); "
    "LINTERRUMP L; NOTMEMORIA C(50)"
)
```

**`_build_generic_dbf()` usage pattern** (lines 99–118) — reused for all new tables:
```python
# nivel always has exactly 1 row (RESEARCH.md §Pitfall 6)
_build_generic_dbf(nivel_path, _NIVEL_SPEC, [
    {"n1": True, "n2": True, ..., "lastcasado": 0}
])
```

**ZIP fixture pattern** (lines 298–332) — copy `zip_with_group_tables` structure for a new `zip_with_all_tables` fixture that includes venci/prede/amoinv/nivel/balan:
```python
@pytest.fixture(scope="session")
def zip_with_all_tables(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP with all 10 catalogued tables present (TABL-04 integration fixture)."""
    zip_dir = tmp_path_factory.mktemp("zip_with_all_tables")
    zip_path = zip_dir / "backup_full.zip"
    # Build each sibling DBF using _build_generic_dbf()...
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        # ... add all 9 siblings
    return zip_path
```

**Defect-bearing fixture pattern** (new for lenient tests) — build a DIARIO.DBF with one bad row:
```python
@pytest.fixture(scope="session")
def diario_with_bad_row(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """DIARIO.DBF with one row whose SUBCTA is non-numeric (triggers D-E3 in strict mode)."""
    target_dir = tmp_path_factory.mktemp("bad_row")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {"asien": 1, "fecha": _dt.date(2025, 1, 1), "subcta": "4300000",
         "contra": "", "concepto": "good", "eurodebe": 100.0, "eurohaber": 0.0},
        {"asien": 2, "fecha": _dt.date(2025, 1, 2), "subcta": "BAD_CODE",
         "contra": "", "concepto": "bad subcta", "eurodebe": 50.0, "eurohaber": 0.0},
        {"asien": 3, "fecha": _dt.date(2025, 1, 3), "subcta": "7000000",
         "contra": "", "concepto": "good again", "eurodebe": 0.0, "eurohaber": 50.0},
    ]
    return _build_diario_dbf(target, rows, codepage="cp850")
```

---

### `tests/test_tables.py` — new test file

**Analog:** `tests/test_reader.py` (lines 1–80 — pattern for test structure)

**Test module header pattern** (from `test_reader.py` lines 1–28):
```python
"""Table reader tests for contaplus-reader (TABL-03, BAL-01).

Covers:
- read_table_raw() works for venci/prede/amoinv/nivel/balan synthetic DBFs
- GenericTable.headers matches DBF field order (WR-05)
- nivel fixture has exactly 1 row
- BALAN SDO_CIERRE column readable
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contaplus_reader._subcta import read_table_raw
from contaplus_reader.models import GenericTable
```

**Individual test pattern** (from `test_reader.py` lines 34–39):
```python
def test_venci_headers(venci_dbf: Path) -> None:
    """TABL-03: GenericTable.headers matches venci DBF field order."""
    table = read_table_raw(venci_dbf, "venci.dbf")
    assert isinstance(table, GenericTable)
    assert table.headers[0] == "FECHA"   # first field per RESEARCH.md schema
    assert table.headers[1] == "COD"
```

---

### `tests/test_balance.py` — new test file

**Analog:** `tests/test_reader.py`

**Core pattern** — test with hand-crafted `ContaPlusJournal` rows (no fixture needed):
```python
from decimal import Decimal
from contaplus_reader._balance import compute_balance
from contaplus_reader.models import ContaPlusJournal, JournalRow

def _make_row(subcuenta: str, debe: float, haber: float) -> JournalRow:
    import datetime
    return JournalRow(fecha=datetime.date(2025, 1, 1),
                      cuenta=subcuenta[:4], subcuenta=subcuenta,
                      debe=debe, haber=haber, concepto=None)

def test_decimal_precision() -> None:
    """BAL-02: Decimal accumulation avoids float binary representation errors."""
    rows = [_make_row("4300000", 0.1, 0.0), _make_row("4300000", 0.2, 0.0)]
    journal = ContaPlusJournal(rows=tuple(rows))
    table = compute_balance(journal, by_subcuenta=True)
    assert table.rows[0].suma_debe == Decimal("0.3")  # not 0.30000000000000004
```

---

### `tests/test_lenient.py` — new test file

**Analog:** `tests/test_reader.py` (uses `read()` entry point + conftest fixtures)

**Import pattern** (from `test_reader.py` lines 25–28):
```python
from contaplus_reader import ContaPlusReadError, read
from contaplus_reader.models import ContaPlusData
```

**Lenient test pattern**:
```python
def test_lenient_bad_journal_row_skipped(diario_with_bad_row: Path) -> None:
    """API-03 D-02: lenient=True skips bad journal rows and adds to problems."""
    data = read(diario_with_bad_row.read_bytes(), lenient=True)
    assert data.journal is not None
    assert len(data.journal.rows) == 2      # bad row skipped
    assert data.problems is not None
    assert len(data.problems.entries) == 1
    entry = data.problems.entries[0]
    assert entry.table == "DIARIO"
    assert entry.row_index == 1             # 0-based index of bad row
    assert entry.column == "subcuenta"

def test_strict_still_raises_on_bad_row(diario_with_bad_row: Path) -> None:
    """API-03: strict mode (default) still raises ContaPlusReadError."""
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(diario_with_bad_row.read_bytes())  # strict=default
    assert exc_info.value.row_index == 1
```

---

### `tests/test_xlsx.py` — extended

**Analog:** itself (lines 1–80 — read in full above)

**Existing openpyxl load pattern** (lines 77–80) — reuse for all new sheet tests:
```python
from openpyxl import load_workbook

wb = load_workbook(io.BytesIO(render(data)))
ws_names = [ws.title for ws in wb.worksheets]
assert "Balance" in ws_names
assert "Sumas y Saldos (Cuentas)" in ws_names
```

**Header-style verification pattern** (already in `test_xlsx.py`) — copy for new sheets:
```python
ws = wb["Balance"]
assert ws["A1"].font.bold
assert ws["A1"].fill.fgColor.rgb == "FF4472C4"
```

---

## Shared Patterns

### ContaPlusReadError wrapping
**Source:** `src/contaplus_reader/_subcta.py` lines 109–117 and `_reader.py` lines 252–267
**Apply to:** All reader boundaries (new DBF readers in `_subcta.py` call sites, `_balance.py` has no I/O so does NOT need this)
```python
except ContaPlusReadError:
    raise  # re-raise unchanged -- already structured
except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
    raise ContaPlusReadError(
        row_index=-1,
        column=None,
        message=f"{table_name} read error: {exc}",
        original=exc,
    ) from exc
```

### DBF open pattern
**Source:** `src/contaplus_reader/_subcta.py` lines 179–185
**Apply to:** Every new DBF read (balan, venci, prede, amoinv, nivel)
```python
table = DBF(
    str(path),
    lowernames=False,               # preserve original field names (D-13)
    encoding="cp850",               # never latin-1 (SEED.md D-D1)
    ignore_missing_memofile=True,
)
headers = tuple(f.name for f in table.fields)  # WR-05: schema from DBF, not row 0
```

### HEADER_FILL / HEADER_FONT styling
**Source:** `src/contaplus_reader/xlsx.py` lines 36–43 and `_render_generic_sheet()` lines 155–159
**Apply to:** All new sheet renderers (`_render_balan_sheet`, `_render_balance_sheet`, `_render_problems_sheet`)
```python
HEADER_FILL = PatternFill(fill_type="solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")
# Usage:
cell = ws.cell(row=1, column=col_idx, value=header)
cell.fill = HEADER_FILL
cell.font = HEADER_FONT
ws.freeze_panes = "A2"
```

### ACCOUNTING_FMT for monetary columns
**Source:** `src/contaplus_reader/xlsx.py` line 36
**Apply to:** `_render_balance_sheet()` for all six Decimal columns
```python
ACCOUNTING_FMT = "#,##0.00_);[Red](#,##0.00)"
ws.cell(...).number_format = ACCOUNTING_FMT
```

### `from __future__ import annotations`
**Source:** Every existing module (e.g. `_reader.py` line 1, `_subcta.py` line 1)
**Apply to:** `_balance.py` (new module) and any new test files

### `scope="session"` fixture pattern
**Source:** `tests/conftest.py` lines 121, 158, 182, 219, etc.
**Apply to:** All new conftest fixtures (DBF fixture builds are expensive — session scope amortises cost)

### Conventional commit messages (git-workflow rule)
**Apply to:** All commits in Phase 3 — `feat:`, `test:`, `refactor:` as appropriate per module.

---

## No Analog Found

All Phase 3 files have strong analogs in the codebase. No file requires falling back to RESEARCH.md patterns exclusively.

| File | Role | Note |
|------|------|-------|
| `src/contaplus_reader/_balance.py` | utility/transform | Closest analog is `_subcta.py` structure; the computation logic itself is novel (Decimal groupby) but the module layout is a direct copy of `_subcta.py`'s header/imports/logger pattern |

---

## Metadata

**Analog search scope:** `src/contaplus_reader/` (all 7 modules), `tests/` (all 4 files)
**Files scanned:** 11 source/test files read in full
**Pattern extraction date:** 2026-05-17
