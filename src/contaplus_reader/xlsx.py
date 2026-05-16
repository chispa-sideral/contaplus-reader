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
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from contaplus_reader.models import (
    ContaPlusData,
    ContaPlusJournal,
    GenericTable,
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


def render(data: ContaPlusData) -> bytes:
    """Convert all populated tables in ContaPlusData to a multi-sheet xlsx workbook.

    Sheet order (D-14): Diario, Subcuentas, Empresa, Grupos, Usuarios.
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
    if data.empresa is not None:
        _render_generic_sheet(wb.create_sheet("Empresa"), data.empresa)
    if data.grupos is not None:
        _render_generic_sheet(wb.create_sheet("Grupos"), data.grupos)
    if data.usuarios is not None:
        _render_generic_sheet(wb.create_sheet("Usuarios"), data.usuarios)

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
