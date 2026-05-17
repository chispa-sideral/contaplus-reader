"""XLSX renderer for ContaPlus data (journal + secondary tables).

D-08: DataFrame is renderer-internal only -- no pandas type appears in the
      signature or result model.
D-10: Polished-but-restrained styling: bold filled header, freeze_panes, auto-sized columns.
D-11: debe/haber use accounting number format with red negatives.
D-12: Data-driven renderer -- one sheet per populated table in ContaPlusData.
D-13: Non-journal sheets reproduce every field in DBF field order; headers are raw DBF field names.
D-14: Sheet tabs use Spanish names: Diario, Subcuentas, Empresa, Grupos, Usuarios.
D-15: Diario sheet gains Descripción column after Subcuenta; blank when subcuenta_nombre is None.
XLSX-04: render() returns bytes (buf.getvalue()), not a file path.
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from contaplus_reader.models import (
    BalanceTable,
    ContaPlusData,
    ContaPlusJournal,
    GenericTable,
    ProblemsReport,
    SubctaTable,
)

# D-14/D-15 MANDATORY: Headers are Spanish -- do NOT change to English.
# D-15: Descripción inserted after Subcuenta at index 3 (1-based column 4).
HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]

# D-11: Accounting format with thousands separator and red negatives.
# openpyxl built-in format 40; OOXML standard format; locale-independent in the file.
ACCOUNTING_FMT = "#,##0.00_);[Red](#,##0.00)"

# Standard Spanish accounting date display.
DATE_FMT = "DD/MM/YYYY"

# D-10: Office Blue header fill -- professional and understated.
HEADER_FILL = PatternFill(fill_type="solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")

# XLSX-03: Red banner fill for descuadre warning (D-09).
BANNER_FILL = PatternFill(fill_type="solid", fgColor="FF0000")
BANNER_FONT = Font(bold=True, color="FFFFFF")

# D-08: Trial-balance column headers (Spanish, per plan 03-04).
_BALANCE_HEADERS_CUENTA = [
    "Cuenta", "Suma Debe", "Suma Haber",
    "Saldo Deudor", "Saldo Acreedor", "Saldo",
]
_BALANCE_HEADERS_SUBCUENTA = [
    "Subcuenta", "Descripción", "Suma Debe", "Suma Haber",
    "Saldo Deudor", "Saldo Acreedor", "Saldo",
]

# D-06: Problems sheet column headers (Spanish).
_PROBLEMS_HEADERS = ["Tabla", "Fila", "Columna", "Motivo", "Valor"]


def render(data: ContaPlusData) -> bytes:
    """Convert all populated tables in ContaPlusData to a multi-sheet xlsx workbook.

    Sheet order (D-11/D-14/D-15):
    Diario → Subcuentas → Balance → Sumas y Saldos (Cuentas) →
    Sumas y Saldos (Subcuentas) → Vencimientos → Predefinidos →
    Amortizaciones → Niveles → Empresa → Grupos → Usuarios →
    Problemas (only when problems.entries is non-empty, D-05).

    Only tables that are not None produce a sheet (D-06 / D-12).

    Args:
        data: ContaPlusData with populated table attributes.

    Returns:
        Bytes of a valid .xlsx workbook.
    """
    wb = Workbook()

    # Sheet 1: Diario (always present -- wb.active is sheet 1).
    _render_journal_sheet(wb.active, data.journal)  # type: ignore[arg-type]

    if data.subcta is not None:
        _render_subcta_sheet(wb.create_sheet("Subcuentas"), data.subcta)

    # Phase 3: raw BALAN sheet with conditional descuadre banner (XLSX-03 / D-09).
    if data.balan is not None:
        _render_balan_sheet(wb.create_sheet("Balance"), data.balan)

    # Phase 3: recomputed trial-balance sheets at cuenta and subcuenta levels (BAL-02 / D-07).
    if data.balance_cuenta is not None:
        _render_balance_sheet(wb.create_sheet("Sumas y Saldos (Cuentas)"), data.balance_cuenta)
    if data.balance_subcuenta is not None:
        _render_balance_sheet(wb.create_sheet("Sumas y Saldos (Subcuentas)"), data.balance_subcuenta)

    # Phase 3: operational tables (TABL-03 / D-15 Spanish tab names).
    if data.venci is not None:
        _render_generic_sheet(wb.create_sheet("Vencimientos"), data.venci)
    if data.prede is not None:
        _render_generic_sheet(wb.create_sheet("Predefinidos"), data.prede)
    if data.amoinv is not None:
        _render_generic_sheet(wb.create_sheet("Amortizaciones"), data.amoinv)
    if data.nivel is not None:
        _render_generic_sheet(wb.create_sheet("Niveles"), data.nivel)

    # Existing Phase 2 secondary tables (moved after operational tables per D-11 order).
    if data.empresa is not None:
        _render_generic_sheet(wb.create_sheet("Empresa"), data.empresa)
    if data.grupos is not None:
        _render_generic_sheet(wb.create_sheet("Grupos"), data.grupos)
    if data.usuarios is not None:
        _render_generic_sheet(wb.create_sheet("Usuarios"), data.usuarios)

    # Phase 3: problems sheet — only when entries exist (D-05).
    if data.problems is not None and data.problems.entries:
        _render_problems_sheet(wb.create_sheet("Problemas"), data.problems)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def render_journal(journal: ContaPlusJournal) -> bytes:
    """Convert a ContaPlusJournal to an xlsx workbook, returned as bytes.

    Backward-compatible alias for render(ContaPlusData(journal=journal)).
    D-08: Any DataFrame use stays internal to this function.
    XLSX-04: Returns bytes (buf.getvalue()), not a file path or BytesIO.

    Args:
        journal: Validated journal data from the reader.

    Returns:
        Bytes of a valid .xlsx workbook.
    """
    return render(ContaPlusData(journal=journal))


def _render_journal_sheet(ws: Worksheet, journal: ContaPlusJournal) -> None:
    """Render the Diario journal sheet onto ws.

    Private helper. Sets sheet title to 'Diario', writes HEADERS with D-10 styling,
    freezes pane at A2, writes all data rows with D-11/D-15 formatting.
    """
    ws.title = "Diario"

    # Header row (row 1) with D-10 styling.
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    # D-10: Freeze header row.
    ws.freeze_panes = "A2"

    # Data rows -- D-13: no footer/totals row.
    # D-15: col 4 = Descripción (subcuenta_nombre); blank when None.
    for row_idx, jr in enumerate(journal.rows, 2):
        ws.cell(row=row_idx, column=1, value=jr.fecha).number_format = DATE_FMT
        ws.cell(row=row_idx, column=2, value=jr.cuenta)
        ws.cell(row=row_idx, column=3, value=jr.subcuenta)
        ws.cell(row=row_idx, column=4, value=jr.subcuenta_nombre)  # D-15: None = blank cell
        ws.cell(row=row_idx, column=5, value=jr.debe).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=6, value=jr.haber).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=7, value=jr.concepto)

    # D-10: Auto-size columns (openpyxl has no built-in autofit).
    # Pitfall 4: use col_cells[0].column_letter, NOT col_cells.column_letter.
    _autosize_columns(ws)


def _render_subcta_sheet(ws: Worksheet, subcta: SubctaTable) -> None:
    """Render the Subcuentas sheet onto ws.

    Private helper. WR-05: headers come from the table schema
    (``subcta.headers``), captured from the DBF itself -- not from row 0 --
    so ragged rows cannot drop columns and a zero-row table still gets a
    proper styled header row. Applies D-10 styling.
    """
    # WR-05: schema-driven headers (DBF field names in original order, D-13).
    headers = list(subcta.headers)

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    ws.freeze_panes = "A2"

    for row_idx, row in enumerate(subcta.rows, 2):
        for col_idx, key in enumerate(headers, 1):
            ws.cell(row=row_idx, column=col_idx, value=row.fields.get(key))

    _autosize_columns(ws)


def _render_generic_sheet(ws: Worksheet, table: GenericTable) -> None:
    """Render a GenericTable onto ws with D-10 styling.

    Private helper. table.headers are raw DBF field names (D-13).
    """
    for col_idx, header in enumerate(table.headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    ws.freeze_panes = "A2"

    for row_idx, row in enumerate(table.rows, 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    _autosize_columns(ws)


def _render_balan_sheet(ws: Worksheet, balan: GenericTable) -> None:
    """Render the raw BALAN sheet onto ws with conditional descuadre banner.

    XLSX-03 / D-09: When SDO_CIERRE sum != 0, injects a red AVISO banner at
    row 1 and shifts header/data down by one row. When balanced, no banner.
    Pitfall 5 (T-03-12): column widths are computed from data rows only (not
    the banner) to avoid DESCRIP/FORMULA columns setting enormous widths.
    """
    # Locate SDO_CIERRE column index (0-based in balan.headers).
    sdo_idx: int | None = next(
        (i for i, h in enumerate(balan.headers) if h.upper() == "SDO_CIERRE"),
        None,
    )

    header_row_offset = 1  # row where field-name headers are written (1 = no banner)
    if sdo_idx is not None:
        sdo_sum = sum(
            (
                Decimal(str(row[sdo_idx]))
                for row in balan.rows
                if row[sdo_idx] is not None  # T-03-13: None guard mandatory
            ),
            Decimal("0"),
        )
        if sdo_sum != Decimal("0"):
            # Inject AVISO banner at row 1 (D-09 descuadre detected).
            cell = ws.cell(
                row=1,
                column=1,
                value=(
                    f"AVISO: Balance desnivelado — SDO_CIERRE suma {sdo_sum}"
                    f" ≠ 0. Datos derivados, puede ser no fiable."
                ),
            )
            cell.fill = BANNER_FILL
            cell.font = BANNER_FONT
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
            header_row_offset = 2

    # Write field-name headers at header_row_offset.
    for col_idx, header in enumerate(balan.headers, 1):
        cell = ws.cell(row=header_row_offset, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    # Freeze panes below the header row.
    ws.freeze_panes = ws.cell(row=header_row_offset + 1, column=1).coordinate

    # Write data rows starting immediately after the header row.
    for row_idx, row in enumerate(balan.rows, header_row_offset + 1):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Pitfall 5 / T-03-12: compute widths from data rows (not the banner).
    _autosize_columns_from_offset(ws, start_row=header_row_offset)


def _render_balance_sheet(ws: Worksheet, table: BalanceTable) -> None:
    """Render a trial-balance (sumas y saldos) sheet onto ws.

    BAL-02 / D-07 / D-08: Supports both cuenta and subcuenta levels.
    Cuenta level: 6 columns (no Descripción).
    Subcuenta level: 7 columns with Descripción at position B.
    Decimal values are converted to float for openpyxl with ACCOUNTING_FMT.
    """
    headers = (
        _BALANCE_HEADERS_SUBCUENTA
        if table.level == "subcuenta"
        else _BALANCE_HEADERS_CUENTA
    )

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

        ws.cell(row=row_idx, column=offset + 1, value=float(br.suma_debe)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset + 2, value=float(br.suma_haber)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset + 3, value=float(br.saldo_deudor)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset + 4, value=float(br.saldo_acreedor)).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=offset + 5, value=float(br.saldo)).number_format = ACCOUNTING_FMT

    _autosize_columns(ws)


def _render_problems_sheet(ws: Worksheet, report: ProblemsReport) -> None:
    """Render the Problemas sheet onto ws.

    XLSX-02 / D-06: Five columns — Tabla, Fila, Columna, Motivo, Valor.
    Only genuine defects are listed (D-05: memo skips excluded).
    """
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


def _autosize_columns(ws: Any) -> None:
    """Auto-size all columns based on max cell content length.

    D-10 pattern: capped at 50 characters wide. Uses col_cells[0].column_letter
    to avoid openpyxl Pitfall 4.
    """
    for col_cells in ws.columns:
        max_len = max(
            (len(str("" if c.value is None else c.value)) for c in col_cells),
            default=0,
        )
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)


def _autosize_columns_from_offset(ws: Any, start_row: int) -> None:
    """Auto-size columns based on max cell content length, starting from start_row.

    Pitfall 5 / T-03-12: used for _render_balan_sheet to avoid the AVISO banner
    text (which can be very long) from inflating column widths. Capped at 50.
    Uses col_cells[0].column_letter to avoid openpyxl Pitfall 4.

    Args:
        ws: openpyxl Worksheet.
        start_row: first row to include in width computation (1-based).
    """
    for col_idx, col_cells in enumerate(ws.columns, 1):
        max_len = max(
            (
                len(str("" if c.value is None else c.value))
                for c in col_cells
                if c.row >= start_row
            ),
            default=0,
        )
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)
