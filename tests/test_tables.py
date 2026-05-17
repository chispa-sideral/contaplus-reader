"""Table reader tests for contaplus-reader (TABL-03, BAL-01).

Covers:
- read_table_raw() works for venci/prede/amoinv/nivel/balan synthetic DBFs
- GenericTable.headers matches DBF field order (WR-05)
- nivel fixture has exactly 1 row (RESEARCH.md Pitfall 6 — config singleton)
- BALAN SDO_CIERRE column readable (BAL-01 descuadre check requirement)

All tests in this file are RED: they will fail with ImportError until
Plan 02 implements the required readers and extends ContaPlusData.

Requirements: TABL-03, BAL-01
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contaplus_reader._subcta import read_table_raw
from contaplus_reader.models import GenericTable


# ---------------------------------------------------------------------------
# TABL-03: venci.dbf reader
# ---------------------------------------------------------------------------

def test_venci_returns_generic_table(venci_dbf: Path) -> None:
    """TABL-03: read_table_raw on venci.dbf returns a GenericTable."""
    table = read_table_raw(venci_dbf, "venci.dbf")
    assert isinstance(table, GenericTable)


def test_venci_headers(venci_dbf: Path) -> None:
    """TABL-03: venci GenericTable.headers[0] == 'FECHA', headers[1] == 'COD'.

    Verifies DBF field order per RESEARCH.md §Q1 schema.
    """
    table = read_table_raw(venci_dbf, "venci.dbf")
    assert table.headers[0] == "FECHA"
    assert table.headers[1] == "COD"


def test_venci_zero_rows(venci_dbf: Path) -> None:
    """TABL-03: venci fixture has 0 rows (matching real-data behaviour)."""
    table = read_table_raw(venci_dbf, "venci.dbf")
    assert len(table.rows) == 0


# ---------------------------------------------------------------------------
# TABL-03: prede.dbf reader
# ---------------------------------------------------------------------------

def test_prede_returns_generic_table(prede_dbf: Path) -> None:
    """TABL-03: read_table_raw on prede.dbf returns a GenericTable."""
    table = read_table_raw(prede_dbf, "prede.dbf")
    assert isinstance(table, GenericTable)


def test_prede_headers(prede_dbf: Path) -> None:
    """TABL-03: prede GenericTable.headers[0] == 'ASIEN', headers[1] == 'TSUBCTA'.

    Verifies DBF field order per RESEARCH.md §Q1 schema.
    """
    table = read_table_raw(prede_dbf, "prede.dbf")
    assert table.headers[0] == "ASIEN"
    assert table.headers[1] == "TSUBCTA"


# ---------------------------------------------------------------------------
# TABL-03: amoinv.dbf reader
# ---------------------------------------------------------------------------

def test_amoinv_returns_generic_table(amoinv_dbf: Path) -> None:
    """TABL-03: read_table_raw on amoinv.dbf returns a GenericTable."""
    table = read_table_raw(amoinv_dbf, "amoinv.dbf")
    assert isinstance(table, GenericTable)


def test_amoinv_headers(amoinv_dbf: Path) -> None:
    """TABL-03: amoinv GenericTable.headers[0] == 'NUMEROINV', headers[1] == 'DOCUMENTO'.

    Verifies DBF field order per RESEARCH.md §Q1 schema.
    """
    table = read_table_raw(amoinv_dbf, "amoinv.dbf")
    assert table.headers[0] == "NUMEROINV"
    assert table.headers[1] == "DOCUMENTO"


# ---------------------------------------------------------------------------
# TABL-03: nivel.dbf reader
# ---------------------------------------------------------------------------

def test_nivel_returns_generic_table(nivel_dbf: Path) -> None:
    """TABL-03: read_table_raw on nivel.dbf returns a GenericTable."""
    table = read_table_raw(nivel_dbf, "nivel.dbf")
    assert isinstance(table, GenericTable)


def test_nivel_row_count(nivel_dbf: Path) -> None:
    """TABL-03: nivel always has exactly 1 row (RESEARCH.md Pitfall 6 — config singleton)."""
    table = read_table_raw(nivel_dbf, "nivel.dbf")
    assert len(table.rows) == 1


def test_nivel_headers(nivel_dbf: Path) -> None:
    """TABL-03: nivel GenericTable.headers[0] == 'N1', headers[-1] == 'LASTCASADO'."""
    table = read_table_raw(nivel_dbf, "nivel.dbf")
    assert table.headers[0] == "N1"
    assert table.headers[-1] == "LASTCASADO"


# ---------------------------------------------------------------------------
# BAL-01: BALAN.DBF reader
# ---------------------------------------------------------------------------

def test_balan_returns_generic_table(balan_balanced_dbf: Path) -> None:
    """BAL-01: read_table_raw on BALAN.DBF returns a GenericTable."""
    table = read_table_raw(balan_balanced_dbf, "BALAN.DBF")
    assert isinstance(table, GenericTable)


def test_balan_sdo_cierre_column(balan_balanced_dbf: Path) -> None:
    """BAL-01: BALAN GenericTable.headers contains 'SDO_CIERRE'.

    Required for the descuadre check (D-09/D-10).
    """
    table = read_table_raw(balan_balanced_dbf, "BALAN.DBF")
    assert "SDO_CIERRE" in table.headers
