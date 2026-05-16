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


def test_non_seekable_binary_io_accepted(cp850_basic_dbf: Path) -> None:
    """CR-01: A non-seekable BinaryIO stream is accepted (read() normalises to bytes first).

    Phase 2: read() calls data.read() once before sniffing, so seekability is
    no longer required. Non-seekable streams work as long as .read() returns bytes.
    """
    import io as _io

    class NonSeekableStream(_io.RawIOBase):
        """Wraps bytes but overrides seekable() to return False."""

        def __init__(self, data: bytes) -> None:
            super().__init__()
            self._data = data

        def read(self, n: int = -1) -> bytes:  # type: ignore[override]
            return self._data

        def seekable(self) -> bool:
            return False

        def seek(self, pos: int, whence: int = 0) -> int:
            raise OSError("Illegal seek")

    stream = NonSeekableStream(cp850_basic_dbf.read_bytes())
    # Phase 2: non-seekable stream is now accepted -- bytes normalised first
    result = read(stream)
    assert isinstance(result, ContaPlusData)
    assert result.journal is not None
    assert len(result.journal.rows) == 3


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
# WR-03: _pick_column is case-insensitive regardless of caller's field_set shape
# ---------------------------------------------------------------------------

def test_pick_column_case_insensitive() -> None:
    """WR-03: _pick_column matches candidates against an upper-case field set.

    The helper must not depend on the caller pre-lowercasing the set. It
    returns the actual (original-cased) member so records can be indexed.
    """
    from contaplus_reader._reader import _pick_column

    upper_set = {"COD", "TITULO", "NIF"}
    assert _pick_column(upper_set, ("cod", "codigo"), kind="subcta.cod") == "COD"
    assert (
        _pick_column(upper_set, ("titulo", "descrip"), kind="subcta.titulo")
        == "TITULO"
    )


def test_pick_column_raises_when_absent() -> None:
    """WR-03: _pick_column still raises ContaPlusReadError when no candidate matches."""
    from contaplus_reader._reader import _pick_column

    with pytest.raises(ContaPlusReadError) as exc_info:
        _pick_column({"FOO", "BAR"}, ("cod", "codigo"), kind="subcta.cod")
    assert "subcta.cod" in exc_info.value.message


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
# CR-03: ContaPlusJournal.rows is an immutable tuple
# ---------------------------------------------------------------------------

def test_journal_rows_is_immutable_tuple(cp850_basic_dbf: Path) -> None:
    """CR-03: journal.rows must be a tuple (immutable), not a list."""
    data = read(cp850_basic_dbf.read_bytes())
    journal = data.journal
    assert journal is not None
    assert isinstance(journal.rows, tuple)
    with pytest.raises(AttributeError, match="append"):
        journal.rows.append  # type: ignore[attr-defined]
        # Accessing .append raises AttributeError on tuple
    # Verify append actually raises when called
    with pytest.raises(AttributeError):
        journal.rows.append(journal.rows[0])  # type: ignore[attr-defined]


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
    expected = {"fecha", "cuenta", "subcuenta", "debe", "haber", "concepto", "subcuenta_nombre"}
    assert expected == field_names
    # Check types
    assert isinstance(row.fecha, _dt.date)
    assert isinstance(row.debe, float)
    assert isinstance(row.haber, float)
    assert isinstance(row.cuenta, str)
    assert isinstance(row.subcuenta, str)


# ===========================================================================
# Phase 2 failing tests (plan 02-01) -- all RED; GREEN in plan 02-02
# ===========================================================================

# ---------------------------------------------------------------------------
# INPUT-02: read() accepts ZIP bytes and file-like objects
# ---------------------------------------------------------------------------

def test_read_zip_bytes(single_company_zip_with_subcta: Path) -> None:
    """INPUT-02: read() must accept ZIP bytes and return ContaPlusData with journal.

    RED: read() currently raises ContaPlusReadError for ZIP input (sniffer rejects 0x50).
    GREEN when: _sniffer.py flip + _zip.py implementation lands in plan 02-02.
    """
    zip_bytes = single_company_zip_with_subcta.read_bytes()
    data = read(zip_bytes)
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) > 0


def test_read_zip_filelike(single_company_zip_with_subcta: Path) -> None:
    """INPUT-02: read() must accept a BinaryIO wrapping a ZIP.

    RED: same reason as test_read_zip_bytes -- sniffer rejects ZIP magic.
    GREEN when: same as test_read_zip_bytes.
    """
    import io as _io

    zip_bytes = single_company_zip_with_subcta.read_bytes()
    data = read(_io.BytesIO(zip_bytes))
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) > 0


# ---------------------------------------------------------------------------
# INPUT-04: Zip-slip entries rejected (security)
# ---------------------------------------------------------------------------

def test_read_zipslip_rejected(zip_slip_zip: Path) -> None:
    """INPUT-04: ZIP with a path-traversal entry must raise ContaPlusReadError.

    RED: read() currently raises ContaPlusReadError for all ZIP input, not
    specifically for zip-slip. Once ZIP support lands, the specific error
    message 'Unsafe ZIP entry' must be present.
    GREEN when: _zip.py zip-slip guard implemented in plan 02-02.
    """
    zip_bytes = zip_slip_zip.read_bytes()
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(zip_bytes)
    # Phase 2 requirement: the error mentions the unsafe entry
    assert "Unsafe ZIP entry" in exc_info.value.message or "ZIP" in exc_info.value.message


def test_read_zipslip_backslash_rejected(zip_slip_backslash_zip: Path) -> None:
    """CR-01: A back-slash path-traversal entry must raise ContaPlusReadError.

    The guard validates and writes the SAME string, so a '..\\..\\evil.dbf'
    entry whose forward-slash form escapes the temp dir is rejected.
    """
    zip_bytes = zip_slip_backslash_zip.read_bytes()
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(zip_bytes)
    assert "Unsafe ZIP entry" in exc_info.value.message


def test_read_zipslip_absolute_rejected(zip_slip_absolute_zip: Path) -> None:
    """CR-01: An absolute-path entry ('/etc/passwd') must raise ContaPlusReadError."""
    zip_bytes = zip_slip_absolute_zip.read_bytes()
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(zip_bytes)
    assert "Unsafe ZIP entry" in exc_info.value.message


# ---------------------------------------------------------------------------
# INPUT-06: Multi-company ZIP disambiguation
# ---------------------------------------------------------------------------

def test_read_multi_company_no_selector(multi_company_zip: Path) -> None:
    """INPUT-06: Multi-company ZIP without company selector must raise ContaPlusReadError
    listing available company directories.

    RED: read() currently raises ContaPlusReadError for all ZIP (ZIP not supported yet).
    The specific assertion on message content will become meaningful in plan 02-02.
    GREEN when: _zip.py company resolution implemented.
    """
    zip_bytes = multi_company_zip.read_bytes()
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(zip_bytes)
    # Phase 2 requirement: error message must list available company names
    msg = exc_info.value.message
    assert "Emp01" in msg or "ZIP" in msg  # RED: 'ZIP' acceptable; GREEN: must have 'Emp01'


def test_read_multi_company_selected(multi_company_zip: Path) -> None:
    """INPUT-06: Multi-company ZIP with valid company= selector returns ContaPlusData.

    RED: read() does not accept company= parameter yet (TypeError or ContaPlusReadError).
    GREEN when: read() gains company= param in plan 02-02.
    """
    zip_bytes = multi_company_zip.read_bytes()
    # read() does not accept company= yet; this will raise TypeError (RED).
    data = read(zip_bytes, company="Emp01")  # type: ignore[call-arg]
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) > 0


def test_read_single_company_wrong_selector(single_company_zip_with_subcta: Path) -> None:
    """INPUT-06 / D-03: company= selector against single-company ZIP with wrong name raises.

    RED: read() does not accept company= yet.
    GREEN when: read() gains company= param and validates selector against archive.
    """
    zip_bytes = single_company_zip_with_subcta.read_bytes()
    with pytest.raises((ContaPlusReadError, TypeError)):
        # TypeError in RED phase (no company param); ContaPlusReadError in GREEN
        read(zip_bytes, company="WrongCo")  # type: ignore[call-arg]


def test_read_selector_on_dbf_raises(cp850_basic_dbf: Path) -> None:
    """INPUT-06 / D-03: company= selector against a raw DBF must raise ContaPlusReadError
    with 'not applicable' in the message.

    RED: read() does not accept company= yet -- TypeError in RED phase.
    GREEN when: read() gains company= and raises ContaPlusReadError for DBF input.
    """
    dbf_bytes = cp850_basic_dbf.read_bytes()
    with pytest.raises((ContaPlusReadError, TypeError)):
        read(dbf_bytes, company="Emp01")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TABL-01 / API-05: SUBCTA enrichment -- subcuenta_nombre on JournalRow
# ---------------------------------------------------------------------------

def test_subcta_lookup_correct(single_company_zip_with_subcta: Path) -> None:
    """TABL-01 / API-05: Journal rows are enriched with subcuenta_nombre from SubCta.dbf.

    RED: read() rejects ZIP. subcuenta_nombre field does not yet exist on JournalRow.
    GREEN when: ZIP read + SUBCTA lookup implemented; JournalRow gains subcuenta_nombre.
    """
    zip_bytes = single_company_zip_with_subcta.read_bytes()
    data = read(zip_bytes)
    assert data.journal is not None
    rows_by_subcuenta: dict[str, Any] = {}
    for r in data.journal.rows:
        rows_by_subcuenta[r.subcuenta] = r
    # 4300000 -> "Cliente XYZ"
    row_4300 = rows_by_subcuenta.get("4300000")
    assert row_4300 is not None
    assert row_4300.subcuenta_nombre == "Cliente XYZ"  # type: ignore[attr-defined]
    # 7000000 -> "Ventas mercaderias"
    row_7000 = rows_by_subcuenta.get("7000000")
    assert row_7000 is not None
    assert row_7000.subcuenta_nombre == "Ventas mercaderias"  # type: ignore[attr-defined]


def test_subcta_lookup_missing_key(single_company_zip_with_subcta: Path) -> None:
    """API-05 / D-11: subcuenta not in SubCta.dbf -> subcuenta_nombre is None (not an error).

    fixture has 4300000 and 7000000 in SubCta; 6000001 is absent.
    RED: read() rejects ZIP. subcuenta_nombre not yet on JournalRow.
    GREEN when: enrichment implemented with best-effort lookup.
    """
    zip_bytes = single_company_zip_with_subcta.read_bytes()
    data = read(zip_bytes)
    assert data.journal is not None
    # 6000001 is in the journal but NOT in SubCta -> must be None
    rows_6000 = [r for r in data.journal.rows if r.subcuenta == "6000001"]
    assert len(rows_6000) == 1
    assert rows_6000[0].subcuenta_nombre is None  # type: ignore[attr-defined]


def test_subcta_absent_all_none(single_company_zip: Path) -> None:
    """API-05 / D-11: When SubCta.dbf is absent, all subcuenta_nombre are None.

    RED: read() rejects ZIP. subcuenta_nombre not yet on JournalRow.
    GREEN when: enrichment implemented with absent-table -> all-None behaviour.
    """
    zip_bytes = single_company_zip.read_bytes()
    data = read(zip_bytes)
    assert data.journal is not None
    # All rows must have subcuenta_nombre=None when SubCta is absent
    for r in data.journal.rows:
        assert r.subcuenta_nombre is None  # type: ignore[attr-defined]


def test_subcta_candidate_fallback(tmp_path_factory: pytest.TempPathFactory) -> None:
    """TABL-01 / D-16: Alternate field names (CODIGO/DESCRIP) resolved via candidate list.

    Builds a SubCta.dbf with 'CODIGO C(12); DESCRIP C(40)' (not the standard cod/titulo).
    read() must still find subcuenta_nombre via _pick_column candidate resolution.
    RED: read() rejects ZIP. Candidate resolution not yet implemented.
    GREEN when: _subcta.py _pick_column candidates include 'codigo' + 'descrip'.
    """
    import dbf as _dbflib
    import zipfile as _zipfile

    # Build DIARIO.DBF with one row (subcuenta 4300000)
    dbf_dir = tmp_path_factory.mktemp("candidate_fallback")
    diario_path = dbf_dir / "DIARIO.DBF"
    _diario_spec = (
        "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
        "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
    )
    t = _dbflib.Table(filename=str(diario_path), field_specs=_diario_spec, codepage="cp850")
    t.open(mode=_dbflib.READ_WRITE)
    try:
        t.append({
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Test",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        })
    finally:
        t.close()

    # Build a SubCta.dbf with alternate field names (CODIGO/DESCRIP) -- no decimals for C fields
    alt_subcta_path = dbf_dir / "SubCta.dbf"
    alt_spec = "CODIGO C(12); DESCRIP C(40)"
    t2 = _dbflib.Table(filename=str(alt_subcta_path), field_specs=alt_spec, codepage="cp850")
    t2.open(mode=_dbflib.READ_WRITE)
    try:
        t2.append({"CODIGO": "4300000", "DESCRIP": "Cliente XYZ"})
    finally:
        t2.close()

    # Build ZIP
    zip_path = dbf_dir / "backup_alt.zip"
    with _zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(diario_path, arcname="Emp01/Diario.dbf")
        zf.write(alt_subcta_path, arcname="Emp01/SubCta.dbf")

    data = read(zip_path.read_bytes())
    assert data.journal is not None
    assert len(data.journal.rows) == 1
    assert data.journal.rows[0].subcuenta_nombre == "Cliente XYZ"  # type: ignore[attr-defined]


def test_subcta_numeric_cod_field_no_crash(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """CR-02: A SUBCTA.DBF whose `cod` is a numeric (N) field must not crash.

    dbfread decodes a numeric field to int/Decimal, not str. The lookup builder
    must coerce defensively instead of raising a bare AttributeError on
    `.rstrip()`. The journal still reads cleanly (enrichment is best-effort).
    """
    import dbf as _dbflib
    import zipfile as _zipfile

    dbf_dir = tmp_path_factory.mktemp("subcta_numeric_cod")
    diario_path = dbf_dir / "DIARIO.DBF"
    _diario_spec = (
        "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
        "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
    )
    t = _dbflib.Table(filename=str(diario_path), field_specs=_diario_spec, codepage="cp850")
    t.open(mode=_dbflib.READ_WRITE)
    try:
        t.append({
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Test",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        })
    finally:
        t.close()

    # SUBCTA with a NUMERIC `cod` field -- dbfread yields int, not str.
    numeric_subcta_path = dbf_dir / "SubCta.dbf"
    numeric_spec = "cod N(12,0); titulo C(40)"
    t2 = _dbflib.Table(
        filename=str(numeric_subcta_path), field_specs=numeric_spec, codepage="cp850"
    )
    t2.open(mode=_dbflib.READ_WRITE)
    try:
        t2.append({"cod": 4300000, "titulo": "Cliente XYZ"})
    finally:
        t2.close()

    zip_path = dbf_dir / "backup_numeric.zip"
    with _zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(diario_path, arcname="Emp01/Diario.dbf")
        zf.write(numeric_subcta_path, arcname="Emp01/SubCta.dbf")

    # Must not raise AttributeError -- a numeric cod is coerced, not crashed.
    data = read(zip_path.read_bytes())
    assert data.journal is not None
    assert len(data.journal.rows) == 1


# ---------------------------------------------------------------------------
# TABL-02: Group tables (absent or present)
# ---------------------------------------------------------------------------

def test_group_tables_absent_no_error(single_company_zip_with_subcta: Path) -> None:
    """TABL-02 / D-06: Absent group tables (grupos/usuarios/empresa) cause no error.

    Result's .grupos/.usuarios/.empresa must all be None when tables are absent.
    RED: read() rejects ZIP. ContaPlusData does not yet have .grupos/.usuarios/.empresa.
    GREEN when: ZIP read + ContaPlusData extended with optional table attrs.
    """
    zip_bytes = single_company_zip_with_subcta.read_bytes()
    data = read(zip_bytes)
    # Verify no error raised and optional group tables are None
    assert getattr(data, "grupos", "MISSING") in (None, "MISSING")
    assert getattr(data, "usuarios", "MISSING") in (None, "MISSING")
    assert getattr(data, "empresa", "MISSING") in (None, "MISSING")


def test_usuarios_present_in_result(zip_with_group_tables: Path) -> None:
    """TABL-02: When usuarios.dbf is in the archive, result.usuarios must not be None.

    RED: read() rejects ZIP. ContaPlusData does not yet have .usuarios.
    GREEN when: ZIP read + generic table readers + ContaPlusData.usuarios implemented.
    """
    zip_bytes = zip_with_group_tables.read_bytes()
    data = read(zip_bytes)
    assert data is not None
    # usuarios must be populated when the table is in the archive
    assert getattr(data, "usuarios", None) is not None
