"""Tests for contaplus_reader.xlsx -- render_journal() XLSX renderer + render() multi-sheet.

Tests cover:
- Returns non-empty bytes that openpyxl can load
- Spanish headers in row 1 (Phase 2: 7 columns with Descripción at index 4)
- Header row has bold white font and 4472C4 fill
- freeze_panes = "A2"
- debe/haber columns have accounting number format (Phase 2: columns 5 and 6)
- fecha column has DD/MM/YYYY format
- Empty journal (rows=[]) still produces a valid workbook with header row
- Column widths are set
- Negative debe values are stored correctly (not stripped)
- Phase 2: render(ContaPlusData) produces multi-sheet workbook
- Phase 2: Descripción column at index 4 in Diario sheet
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
    return ContaPlusJournal(rows=rows, skipped_memo=0)


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
    """HEADERS constant must list the Spanish column names.

    Phase 2 (D-15): Descripción inserted after Subcuenta at index 3.
    """
    from contaplus_reader.xlsx import HEADERS

    assert HEADERS == ["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]


def test_xlsx_row1_headers_are_spanish() -> None:
    """Row 1 cells must contain the Spanish header names.

    Phase 2 (D-15): 7 columns including Descripción at column 4.
    """
    from contaplus_reader.xlsx import render_journal, HEADERS

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    actual = [ws.cell(row=1, column=i + 1).value for i in range(len(HEADERS))]  # type: ignore[union-attr]
    assert actual == ["Fecha", "Cuenta", "Subcuenta", "Descripción", "Debe", "Haber", "Concepto"]


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
    """Data rows in column 5 (Debe) must have the accounting number format.

    Phase 2 (D-15): Debe moved to column 5 (Descripción inserted at column 4).
    """
    from contaplus_reader.xlsx import render_journal, ACCOUNTING_FMT

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=5).number_format == ACCOUNTING_FMT  # type: ignore[union-attr]


def test_haber_column_has_accounting_format() -> None:
    """Data rows in column 6 (Haber) must have the accounting number format.

    Phase 2 (D-15): Haber moved to column 6 (Descripción inserted at column 4).
    """
    from contaplus_reader.xlsx import render_journal, ACCOUNTING_FMT

    journal = _make_journal(_sample_row())
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    assert ws.cell(row=2, column=6).number_format == ACCOUNTING_FMT  # type: ignore[union-attr]


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
    """Negative debe values must be stored as-is (visual red comes from format, not sign removal).

    Phase 2 (D-15): Debe is now column 5 (Descripción inserted at column 4).
    """
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
    assert ws.cell(row=2, column=5).value == -52.56  # type: ignore[union-attr]


def test_negative_haber_value_stored_not_stripped() -> None:
    """Negative haber values must be stored as-is.

    Phase 2 (D-15): Haber is now column 6 (Descripción inserted at column 4).
    """
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
    assert ws.cell(row=2, column=6).value == -100.00  # type: ignore[union-attr]


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


def test_column_width_not_truncated_by_zero_values() -> None:
    """WR-02: Column with haber=0.0 must not have zero width (0.0 must not count as empty).

    Phase 2 (D-15): Haber is now column F (index 6), was column E (index 5).
    """
    from contaplus_reader.xlsx import render_journal

    row = JournalRow(
        fecha=datetime.date(2025, 1, 1),
        cuenta="4300",
        subcuenta="4300000",
        debe=1500.75,
        haber=0.0,
        concepto="Test zero haber width",
    )
    journal = _make_journal(row)
    ws = load_workbook(io.BytesIO(render_journal(journal))).active
    # Column F is Haber (index 6); header "Haber" has len=5; data 0.0 has len=3
    haber_col_width = ws.column_dimensions["F"].width  # type: ignore[union-attr]
    assert haber_col_width is not None
    assert haber_col_width > 0


# ---------------------------------------------------------------------------
# Data round-trip
# ---------------------------------------------------------------------------

def test_data_values_round_trip() -> None:
    """Values written to the sheet must match the input JournalRow.

    Phase 2 (D-15): col 4=Descripción (None->blank), col 5=debe, col 6=haber, col 7=concepto.
    """
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
    # col 4 = Descripción; subcuenta_nombre is None -> stored as None (blank cell)
    assert ws.cell(row=2, column=4).value is None  # type: ignore[union-attr]
    assert ws.cell(row=2, column=5).value == 1500.75  # type: ignore[union-attr]
    assert ws.cell(row=2, column=6).value == 0.0  # type: ignore[union-attr]
    assert ws.cell(row=2, column=7).value == "Invoice payment"  # type: ignore[union-attr]


# ===========================================================================
# Phase 2 failing tests (plan 02-01) -- all RED; GREEN in plan 02-03
# ===========================================================================

# ---------------------------------------------------------------------------
# D-12 / D-14: Multi-sheet workbook
# ---------------------------------------------------------------------------

def test_render_multi_sheet_names() -> None:
    """D-12 / D-14: render(data) must produce a workbook with 'Diario' and 'Subcuentas' sheets.

    RED: render() does not exist yet. render_journal() only produces a single 'Diario' sheet.
    GREEN when: xlsx.py gains render(data: ContaPlusData) -> bytes with multi-sheet support.
    """
    from contaplus_reader.models import ContaPlusData, SubctaTable  # type: ignore[attr-defined]

    # Import render() inside body so ImportError is a test failure, not collection failure
    try:
        from contaplus_reader.xlsx import render
    except ImportError:
        pytest.fail("render() not yet importable from contaplus_reader.xlsx")

    row = _sample_row()
    journal = _make_journal(row)

    # Build a minimal SubctaTable. WR-05: SubctaTable carries a `headers`
    # schema tuple; a zero-row table still renders a styled header row.
    subcta = SubctaTable(headers=("cod", "titulo"), rows=(), source_name=None)

    data = ContaPlusData(journal=journal, subcta=subcta)  # type: ignore[call-arg]
    result = render(data)
    wb = load_workbook(io.BytesIO(result))
    sheet_names = wb.sheetnames
    assert "Diario" in sheet_names, f"Expected 'Diario' sheet, got: {sheet_names}"
    assert "Subcuentas" in sheet_names, f"Expected 'Subcuentas' sheet, got: {sheet_names}"


def test_render_descripcion_column_present() -> None:
    """D-15: Diario sheet must have 'Descripción' header after 'Subcuenta', with values.

    RED: render() does not exist. render_journal() HEADERS has no Descripción column.
    GREEN when: xlsx.py gains render() + HEADERS includes 'Descripción' at position 4
    and journal rows write subcuenta_nombre value there.
    """
    # Import render() inside body so ImportError is a test failure, not collection failure
    try:
        from contaplus_reader.xlsx import render
    except ImportError:
        pytest.fail("render() not yet importable from contaplus_reader.xlsx")

    from contaplus_reader.models import ContaPlusData

    row = JournalRow(
        fecha=datetime.date(2025, 1, 1),
        cuenta="4300",
        subcuenta="4300000",
        debe=100.0,
        haber=0.0,
        concepto="Test",
        subcuenta_nombre="Cliente XYZ",  # type: ignore[call-arg]
    )
    journal = _make_journal(row)
    data = ContaPlusData(journal=journal)
    result = render(data)
    wb = load_workbook(io.BytesIO(result))
    ws = wb["Diario"]

    # Find the Descripción column by scanning row 1 headers
    header_row = [ws.cell(row=1, column=c).value for c in range(1, 10)]
    assert "Descripción" in header_row, (
        f"Expected 'Descripción' in Diario headers, got: {header_row}"
    )
    descripcion_col = header_row.index("Descripción") + 1  # 1-based

    # Row 2 must have the subcuenta_nombre value
    cell_value = ws.cell(row=2, column=descripcion_col).value
    assert cell_value == "Cliente XYZ", (
        f"Expected 'Cliente XYZ' in Descripción column, got: {cell_value!r}"
    )


# ---------------------------------------------------------------------------
# WR-05: Subcuentas sheet headers come from the schema, not row 0
# ---------------------------------------------------------------------------

def test_subcta_sheet_headers_from_schema_not_row0() -> None:
    """WR-05: ragged rows must not drop columns from the Subcuentas sheet.

    Headers come from SubctaTable.headers (the DBF schema). Even if a later
    row omits a key present in the schema, every schema column is rendered.
    """
    from contaplus_reader.models import ContaPlusData, SubctaRow, SubctaTable
    from contaplus_reader.xlsx import render

    journal = _make_journal(_sample_row())
    # Row 0 lacks "nif"; row 1 has it. Schema declares all three columns.
    subcta = SubctaTable(
        headers=("cod", "titulo", "nif"),
        rows=(
            SubctaRow(fields={"cod": "4300000", "titulo": "Cliente XYZ"}),
            SubctaRow(fields={"cod": "7000000", "titulo": "Ventas", "nif": "B1"}),
        ),
        source_name=None,
    )
    data = ContaPlusData(journal=journal, subcta=subcta)
    wb = load_workbook(io.BytesIO(render(data)))
    ws = wb["Subcuentas"]
    header_row = [ws.cell(row=1, column=c).value for c in range(1, 4)]
    assert header_row == ["cod", "titulo", "nif"], (
        f"Expected all schema columns, got: {header_row}"
    )


def test_subcta_sheet_empty_table_has_header_row() -> None:
    """WR-05: a zero-row SubctaTable still produces a styled header row."""
    from contaplus_reader.models import ContaPlusData, SubctaTable
    from contaplus_reader.xlsx import render

    journal = _make_journal(_sample_row())
    subcta = SubctaTable(headers=("cod", "titulo"), rows=(), source_name=None)
    data = ContaPlusData(journal=journal, subcta=subcta)
    wb = load_workbook(io.BytesIO(render(data)))
    ws = wb["Subcuentas"]
    header_row = [ws.cell(row=1, column=c).value for c in range(1, 3)]
    assert header_row == ["cod", "titulo"], (
        f"Expected header row on empty Subcuentas sheet, got: {header_row}"
    )
