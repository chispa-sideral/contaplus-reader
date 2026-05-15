"""XLSX renderer for ContaPlus journal data.

D-08: DataFrame is renderer-internal only -- no pandas type appears in the
      signature or result model.
D-10: Polished-but-restrained styling: bold filled header, freeze_panes, auto-sized columns.
D-11: debe/haber use accounting number format with red negatives.
D-12: Spanish headers are intentional -- these label Spanish statutory accounting data.
      Do NOT change to English.
D-13: Journal sheet contains data rows only -- no footer/totals row.
XLSX-04: render_journal() returns bytes (buf.getvalue()), not a file path.
"""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from contaplus_reader.models import ContaPlusJournal

# D-12 MANDATORY: Headers are Spanish -- do NOT change to English.
HEADERS = ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]

# D-11: Accounting format with thousands separator and red negatives.
# openpyxl built-in format 40; OOXML standard format; locale-independent in the file.
ACCOUNTING_FMT = "#,##0.00_);[Red](#,##0.00)"

# Standard Spanish accounting date display.
DATE_FMT = "DD/MM/YYYY"

# D-10: Office Blue header fill -- professional and understated.
HEADER_FILL = PatternFill(fill_type="solid", fgColor="4472C4")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def render_journal(journal: ContaPlusJournal) -> bytes:
    """Convert a ContaPlusJournal to an xlsx workbook, returned as bytes.

    D-08: Any DataFrame use stays internal to this function.
    XLSX-04: Returns bytes (buf.getvalue()), not a file path or BytesIO.

    Args:
        journal: Validated journal data from the reader.

    Returns:
        Bytes of a valid .xlsx workbook.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario"

    # Header row (row 1) with D-10 styling.
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    # D-10: Freeze header row.
    ws.freeze_panes = "A2"

    # Data rows -- D-13: no footer/totals row.
    for row_idx, jr in enumerate(journal.rows, 2):
        ws.cell(row=row_idx, column=1, value=jr.fecha).number_format = DATE_FMT
        ws.cell(row=row_idx, column=2, value=jr.cuenta)
        ws.cell(row=row_idx, column=3, value=jr.subcuenta)
        ws.cell(row=row_idx, column=4, value=jr.debe).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=5, value=jr.haber).number_format = ACCOUNTING_FMT
        ws.cell(row=row_idx, column=6, value=jr.concepto)

    # D-10: Auto-size columns (openpyxl has no built-in autofit).
    # Pitfall 4: use col_cells[0].column_letter, NOT col_cells.column_letter.
    for col_cells in ws.columns:
        max_len = max((len(str("" if c.value is None else c.value)) for c in col_cells), default=0)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
