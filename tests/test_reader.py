"""Journal reader tests for contaplus-reader.

Port of tw-contaplus/tests/test_read_dbf.py with:
  - Imports adapted: BlockExecutionError->ContaPlusReadError, ReadDBF->read()
  - Invocation: read(path.read_bytes(), source_name=str(path))
  - Assertions: journal.rows[i].field instead of diario.df["field"].iloc[i]
  - Tests dropped: ReadDBFParams, block contract, Qt-free, ZIP, DataFrame dtype
  - Tests added: bytes/BinaryIO inputs, ZIP rejection, tw_domain import check,
                 error context, non-journal DBF rejection

Coverage: ~18+ tests covering INPUT-01/03, JRNL-01/02/03, API-01/02/04.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from contaplus_reader import ContaPlusReadError, read
from contaplus_reader.models import ContaPlusData, ContaPlusJournal, JournalRow


# ---------------------------------------------------------------------------
# INPUT-01: read() accepts bytes and BinaryIO
# ---------------------------------------------------------------------------

def test_read_accepts_bytes(cp850_basic_dbf: Path) -> None:
    """INPUT-01: read() works when given raw bytes."""
    data = read(cp850_basic_dbf.read_bytes(), source_name=str(cp850_basic_dbf))
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) == 3


def test_read_accepts_binary_io(cp850_basic_dbf: Path) -> None:
    """INPUT-01: read() works when given a binary file-like object."""
    with open(cp850_basic_dbf, "rb") as fh:
        data = read(fh, source_name=str(cp850_basic_dbf))
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) == 3


# ---------------------------------------------------------------------------
# INPUT-03: Unsupported formats rejected with structured error
# ---------------------------------------------------------------------------

def test_rejects_zip_bytes() -> None:
    """INPUT-03: ZIP magic bytes produce ContaPlusReadError with 'ZIP' in message."""
    zip_magic = b"PK\x03\x04" + b"\x00" * 20
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(zip_magic)
    assert "ZIP" in exc_info.value.message


def test_rejects_unknown_magic() -> None:
    """INPUT-03: Non-DBF, non-ZIP bytes produce ContaPlusReadError."""
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(b"\xff\xfe unknown bytes")
    assert exc_info.value.row_index == -1


# ---------------------------------------------------------------------------
# API-04: No tw_domain import anywhere in contaplus_reader
# ---------------------------------------------------------------------------

def test_no_tw_domain_import() -> None:
    """API-04: contaplus_reader must not import or depend on tw_domain."""
    importlib.import_module("contaplus_reader")
    tw_domain_modules = {
        name for name in sys.modules if name.startswith("tw_domain")
    }
    assert tw_domain_modules == set(), (
        f"tw_domain leaked into sys.modules: {tw_domain_modules}"
    )


# ---------------------------------------------------------------------------
# API-02: ContaPlusReadError carries row_index and column context
# ---------------------------------------------------------------------------

def test_error_carries_context(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
) -> None:
    """API-02: ContaPlusReadError has row_index and column attributes."""
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "x",
            "eurodebe": 50.0,
            "eurohaber": 50.0,  # both-non-zero: triggers D-C2
        },
    ])
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(path.read_bytes())
    exc = exc_info.value
    assert exc.row_index >= 0
    assert hasattr(exc, "message")
    assert hasattr(exc, "column")


# ---------------------------------------------------------------------------
# D-02: Non-journal DBF is rejected with clear message
# ---------------------------------------------------------------------------

def test_non_journal_dbf_rejected(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """D-02: A valid DBF without FECHA+debe/haber raises ContaPlusReadError."""
    import dbf as _dbflib

    # Build a DBF that looks like SUBCTA.DBF -- no FECHA (Date), no debe/haber columns
    target_dir = tmp_path_factory.mktemp("non_journal")
    target = target_dir / "SUBCTA.DBF"
    spec = "CODIGO C(12); DESCRIP C(40)"
    table = _dbflib.Table(filename=str(target), field_specs=spec, codepage="cp850")
    table.open(mode=_dbflib.READ_WRITE)
    try:
        table.append({"codigo": "4300000", "descrip": "Clientes"})
    finally:
        table.close()

    with pytest.raises(ContaPlusReadError) as exc_info:
        read(target.read_bytes())
    assert "not a DIARIO.DBF" in exc_info.value.message


# ---------------------------------------------------------------------------
# JRNL-01: Happy path -- 3-row read, correct field values
# ---------------------------------------------------------------------------

def test_reads_cp850_basic_dbf(cp850_basic_dbf: Path) -> None:
    """JRNL-01: 3-row DBF produces journal with correct cuenta/subcuenta."""
    data = read(cp850_basic_dbf.read_bytes(), source_name=str(cp850_basic_dbf))
    journal = data.journal
    assert journal is not None
    assert len(journal.rows) == 3
    # D-B2: cuenta = subcuenta[:4]
    assert [r.cuenta for r in journal.rows] == ["4300", "7000", "6000"]
    assert [r.subcuenta for r in journal.rows] == ["4300000", "7000000", "6000001"]


def test_reads_cp850_basic_dbf_has_correct_amounts(cp850_basic_dbf: Path) -> None:
    """JRNL-01: debe/haber totals match fixture values."""
    journal = read(cp850_basic_dbf.read_bytes()).journal
    assert journal is not None
    total_debe = sum(r.debe for r in journal.rows)
    total_haber = sum(r.haber for r in journal.rows)
    assert total_debe == pytest.approx(150.0)
    assert total_haber == pytest.approx(100.0)


def test_reads_cp850_basic_dbf_concepto_not_empty(cp850_basic_dbf: Path) -> None:
    """JRNL-01: All rows have non-None concepto in the basic fixture."""
    journal = read(cp850_basic_dbf.read_bytes()).journal
    assert journal is not None
    assert all(r.concepto is not None for r in journal.rows)
    assert "Pago cliente" in [r.concepto for r in journal.rows]


# ---------------------------------------------------------------------------
# JRNL-02: Encoding policy -- cp850 unconditionally (D-D1)
# ---------------------------------------------------------------------------

def test_reads_cp1252_byte29_dbf_with_cp850_decode(cp1252_byte29_dbf: Path) -> None:
    """JRNL-02 / D-D1: cp850-always policy; ASCII-clean content decodes correctly
    even when the DBF header byte-29 advertises cp1252."""
    journal = read(cp1252_byte29_dbf.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) == 1
    assert journal.rows[0].concepto == "Pago cliente"


# ---------------------------------------------------------------------------
# JRNL-02: Deleted records skipped
# ---------------------------------------------------------------------------

def test_reads_skips_deleted_records(with_deleted_record_dbf: Path) -> None:
    """JRNL-02: dbfread default skips deleted records -- only 'kept' row surfaces."""
    journal = read(with_deleted_record_dbf.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) == 1
    assert journal.rows[0].concepto == "kept"


# ---------------------------------------------------------------------------
# JRNL-02 / D-C1: Negative amounts pass through (Gap #3 amendment)
# ---------------------------------------------------------------------------

def test_negative_debe_passes_through(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
) -> None:
    """D-C1: Negative debe is preserved with sign intact."""
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "x",
            "eurodebe": -1.0,
            "eurohaber": 0.0,
        },
    ])
    journal = read(path.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) == 1
    assert journal.rows[0].debe == -1.0
    assert journal.rows[0].haber == 0.0


def test_negative_haber_passes_through(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
) -> None:
    """D-C1: Negative haber is preserved with sign intact.

    Real ContaPlus row-410 case: haber=-52.56 must survive with sign.
    """
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "x",
            "eurodebe": 0.0,
            "eurohaber": -52.56,
        },
    ])
    journal = read(path.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) == 1
    assert journal.rows[0].haber == -52.56
    assert journal.rows[0].debe == 0.0


def test_negative_debe_positive_haber_raises(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
) -> None:
    """D-C2: row with negative debe AND positive haber is still both-non-zero — must raise."""
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "x",
            "eurodebe": -10.0,
            "eurohaber": 50.0,
        },
    ])
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(path.read_bytes())
    assert exc_info.value.row_index >= 0


# ---------------------------------------------------------------------------
# JRNL-03 / D-C2: Both-non-zero raises ContaPlusReadError
# ---------------------------------------------------------------------------

def test_both_non_zero_raises(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
) -> None:
    """D-C2: Row with both debe>0 and haber>0 raises ContaPlusReadError."""
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "x",
            "eurodebe": 50.0,
            "eurohaber": 50.0,
        },
    ])
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(path.read_bytes())
    assert exc_info.value.row_index == 0


# ---------------------------------------------------------------------------
# JRNL-02 / D-C3: Both-zero memo lines skipped with log
# ---------------------------------------------------------------------------

def test_both_zero_skips_silently_with_log(
    diario_dbf_builder: Callable[[list[dict[str, Any]]], Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-C3: Both-zero row is skipped; skipped_memo count incremented; INFO logged."""
    path = diario_dbf_builder([
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "real",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "memo",
            "eurodebe": 0.0,
            "eurohaber": 0.0,
        },
    ])
    with caplog.at_level(logging.INFO, logger="contaplus_reader._reader"):
        journal = read(path.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) == 1  # memo line skipped
    assert journal.skipped_memo == 1
    assert any("memo lines" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# JRNL-02 / D-E1: Defensive column resolution
# ---------------------------------------------------------------------------

def test_column_resolution_falls_back_to_debe_haber(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """D-E1: If DBF only has DEBE/HABER (no EURODEBE), reader still works."""
    import dbf as _dbflib

    target_dir = tmp_path_factory.mktemp("debe_haber")
    target = target_dir / "DIARIO.DBF"
    spec = "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONCEPTO C(25); DEBE N(16,2); HABER N(16,2)"
    table = _dbflib.Table(filename=str(target), field_specs=spec, codepage="cp850")
    table.open(mode=_dbflib.READ_WRITE)
    try:
        table.append({
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "concepto": "x",
            "debe": 100.0,
            "haber": 0.0,
        })
    finally:
        table.close()

    journal = read(target.read_bytes()).journal
    assert journal is not None
    total_debe = sum(r.debe for r in journal.rows)
    assert total_debe == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# API-04: Output shape -- JournalRow has expected fields
# ---------------------------------------------------------------------------

def test_output_df_has_correct_columns(cp850_basic_dbf: Path) -> None:
    """API-04: JournalRow has the expected 6 fields."""
    journal = read(cp850_basic_dbf.read_bytes()).journal
    assert journal is not None
    assert len(journal.rows) > 0
    row = journal.rows[0]
    # Check all required fields exist on JournalRow
    field_names = {f.name for f in dataclasses.fields(row)}
    expected = {"fecha", "cuenta", "subcuenta", "debe", "haber", "concepto"}
    assert expected == field_names
    # Check types
    assert isinstance(row.fecha, _dt.date)
    assert isinstance(row.debe, float)
    assert isinstance(row.haber, float)
    assert isinstance(row.cuenta, str)
    assert isinstance(row.subcuenta, str)
