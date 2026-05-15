"""Tests for contaplus_reader.xlsx -- render_journal() XLSX renderer.

Tests cover:
- Returns non-empty bytes that openpyxl can load
- Spanish headers in row 1
- Header row has bold white font and 4472C4 fill
- freeze_panes = "A2"
- debe/haber columns have accounting number format
- fecha column has DD/MM/YYYY format
- Empty journal (rows=[]) still produces a valid workbook with header row
- Column widths are set
- Negative debe values are stored correctly (not stripped)
"""

from __future__ import annotations

import datetime
import io

import pytest
from openpyxl import load_workbook

from contaplus_reader.models import ContaPlusJournal, JournalRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_row() -> JournalRow:
    return JournalRow(
        fecha=datetime.date(2025, 1, 1),
        cuenta="4300",
        subcuenta="4300000",
        debe=100.0,
        haber=0.0,
        concepto="Test entry",
    )


def _make_journal(*rows: JournalRow) -> ContaPlusJournal:
    """Build a ContaPlusJournal from JournalRow instances."""
    return ContaPlusJournal(rows=list(rows), skipped_memo=0)


# ---------------------------------------------------------------------------
# Import smoke test
# ---------------------------------------------------------------------------

def test_render_journal_importable() -> None:
    """render_journal and HEADERS must be importable from contaplus_reader.xlsx."""
    from contaplus_reader.xlsx import render_journal, HEADERS  # noqa: F401


def test_accounting_fmt_constant_importable() -> None:
    """ACCOUNTING_FMT constant must be importable."""
    from contaplus_reader.xlsx import ACCOUNTING_FMT  # noqa: F401
    assert ACCOUNTING_FMT == "#,##0.00_);[Red](#,##0.00)"


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

def test_render_produces_bytes() -> None:
    """render_journal() must return bytes, not BytesIO or a path."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    result = render_journal(journal)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_render_bytes_loadable_by_openpyxl() -> None:
    """The returned bytes must be parseable by openpyxl.load_workbook()."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    result = render_journal(journal)
    wb = load_workbook(io.BytesIO(result))
    assert wb is not None


# ---------------------------------------------------------------------------
# Sheet name
# ---------------------------------------------------------------------------

def test_active_sheet_title_is_diario() -> None:
    """The workbook's active sheet must be named 'Diario'."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    wb = load_workbook(io.BytesIO(render_journal(journal)))
    assert wb.active.title == "Diario"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Spanish headers (D-12 -- MANDATORY, do NOT change to English)
# ---------------------------------------------------------------------------

def test_headers_constant_is_spanish() -> None:
    """HEADERS constant must list the Spanish column names."""
    from contaplus_reader.xlsx import HEADERS

    assert HEADERS == ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]


def test_xlsx_row1_headers_are_spanish() -> None:
    """Row 1 cells must contain the Spanish header names."""
    from contaplus_reader.xlsx import render_journal, HEADERS

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    actual = [ws.cell(row=1, column=i + 1).value for i in range(len(HEADERS))]  # type: ignore[union-attr]
    assert actual == ["Fecha", "Cuenta", "Subcuenta", "Debe", "Haber", "Concepto"]


# ---------------------------------------------------------------------------
# Header styling (D-10)
# ---------------------------------------------------------------------------

def test_header_cells_are_bold() -> None:
    """All header cells must have font.bold == True."""
    from contaplus_reader.xlsx import render_journal, HEADERS

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)  # type: ignore[union-attr]
        assert cell.font.bold is True, f"Column {col_idx} header is not bold"


def test_header_cells_have_fill_color_4472c4() -> None:
    """All header cells must have PatternFill with fgColor containing '4472C4'."""
    from contaplus_reader.xlsx import render_journal, HEADERS

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)  # type: ignore[union-attr]
        rgb = cell.fill.fgColor.rgb
        assert "4472C4" in rgb, f"Column {col_idx} header fill is {rgb!r}, expected 4472C4"


# ---------------------------------------------------------------------------
# Freeze panes (D-10)
# ---------------------------------------------------------------------------

def test_freeze_panes_is_a2() -> None:
    """ws.freeze_panes must be 'A2' (freezes the header row)."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.freeze_panes == "A2"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Number formats (D-11)
# ---------------------------------------------------------------------------

def test_debe_column_has_accounting_format() -> None:
    """Data rows in column 4 (Debe) must have the accounting number format."""
    from contaplus_reader.xlsx import render_journal, ACCOUNTING_FMT

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=4).number_format == ACCOUNTING_FMT  # type: ignore[union-attr]


def test_haber_column_has_accounting_format() -> None:
    """Data rows in column 5 (Haber) must have the accounting number format."""
    from contaplus_reader.xlsx import render_journal, ACCOUNTING_FMT

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=5).number_format == ACCOUNTING_FMT  # type: ignore[union-attr]


def test_fecha_column_has_date_format() -> None:
    """Data rows in column 1 (Fecha) must have the DD/MM/YYYY date format."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=1).number_format == "DD/MM/YYYY"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Negative debe/haber values preserved (D-C1 + D-11 red rendering)
# ---------------------------------------------------------------------------

def test_negative_debe_value_stored_not_stripped() -> None:
    """Negative debe values must be stored as-is (visual red comes from format, not sign removal)."""
    from contaplus_reader.xlsx import render_journal

    row = JournalRow(
        fecha=datetime.date(2025, 3, 15),
        cuenta="6000",
        subcuenta="6000001",
        debe=-52.56,
        haber=0.0,
        concepto="Adjustment",
    )
    journal = _make_journal(row)
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=4).value == -52.56  # type: ignore[union-attr]


def test_negative_haber_value_stored_not_stripped() -> None:
    """Negative haber values must be stored as-is."""
    from contaplus_reader.xlsx import render_journal

    row = JournalRow(
        fecha=datetime.date(2025, 3, 15),
        cuenta="7000",
        subcuenta="7000001",
        debe=0.0,
        haber=-100.00,
        concepto=None,
    )
    journal = _make_journal(row)
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=5).value == -100.00  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Empty journal (D-13: no footer row)
# ---------------------------------------------------------------------------

def test_empty_journal_produces_valid_workbook() -> None:
    """An empty journal (rows=[]) must produce a valid workbook with only the header row."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal()
    result = render_journal(journal)
    wb = load_workbook(io.BytesIO(result))
    ws = wb.active
    assert ws is not None
    # Only one row: the header
    assert ws.max_row == 1  # type: ignore[union-attr]


def test_no_footer_row() -> None:
    """The sheet must contain exactly N+1 rows (header + data) with no totals row (D-13)."""
    from contaplus_reader.xlsx import render_journal

    row1 = _sample_row()
    row2 = JournalRow(
        fecha=datetime.date(2025, 2, 1),
        cuenta="7000",
        subcuenta="7000001",
        debe=0.0,
        haber=200.0,
        concepto="Revenue",
    )
    journal = _make_journal(row1, row2)
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    # 1 header + 2 data = 3 rows, no more
    assert ws.max_row == 3  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Column widths (D-10)
# ---------------------------------------------------------------------------

def test_column_widths_are_set() -> None:
    """At least column A must have a non-default width value."""
    from contaplus_reader.xlsx import render_journal

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    col_a_width = ws.column_dimensions["A"].width  # type: ignore[union-attr]
    assert col_a_width is not None
    assert col_a_width > 0


# ---------------------------------------------------------------------------
# Data round-trip
# ---------------------------------------------------------------------------

def test_data_values_round_trip() -> None:
    """Values written to the sheet must match the input JournalRow."""
    from contaplus_reader.xlsx import render_journal

    row = JournalRow(
        fecha=datetime.date(2025, 6, 15),
        cuenta="4300",
        subcuenta="4300001",
        debe=1500.75,
        haber=0.0,
        concepto="Invoice payment",
    )
    journal = _make_journal(row)
    ws = load_workbook(io.BytesIO(render_journal(journal))).active

    # openpyxl reads dates back as datetime objects; compare date() part
    fecha_val = ws.cell(row=2, column=1).value  # type: ignore[union-attr]
    if hasattr(fecha_val, "date"):
        fecha_val = fecha_val.date()
    assert fecha_val == datetime.date(2025, 6, 15)
    assert ws.cell(row=2, column=2).value == "4300"  # type: ignore[union-attr]
    assert ws.cell(row=2, column=3).value == "4300001"  # type: ignore[union-attr]
    assert ws.cell(row=2, column=4).value == 1500.75  # type: ignore[union-attr]
    assert ws.cell(row=2, column=5).value == 0.0  # type: ignore[union-attr]
    assert ws.cell(row=2, column=6).value == "Invoice payment"  # type: ignore[union-attr]
