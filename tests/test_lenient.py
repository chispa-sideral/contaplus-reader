"""Lenient conversion path tests for contaplus-reader (API-03).

Covers:
- D-02: lenient=True skips bad journal rows; ProblemEntry produced per skipped row
- D-03: lenient=True on wholly-unreadable DIARIO: journal=None, conversion continues
- D-04: lenient=True on corrupt secondary table: table=None, ProblemEntry produced
- D-05: both-zero memo skips do NOT appear in problems (only genuine defects)
- D-13: uncatalogued .dbf in lenient mode produces one informational ProblemEntry
- Strict mode (default) still raises ContaPlusReadError on bad rows

All tests in this file are RED: they will fail with ImportError or TypeError
until Plans 02-04 implement the lenient path, models, and ContaPlusData extension.

Requirements: API-03
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from contaplus_reader import ContaPlusReadError, read
from contaplus_reader.models import ContaPlusData


# ---------------------------------------------------------------------------
# D-02: lenient skips bad journal rows
# ---------------------------------------------------------------------------

def test_lenient_bad_journal_row_skipped(diario_with_bad_row: Path) -> None:
    """API-03 D-02: lenient=True skips bad journal rows and adds to problems.

    The fixture has 3 rows: good / bad-subcta / good.
    Lenient must skip row 1 (index 1, subcta='BADCODE') and return 2 good rows.
    """
    data = read(diario_with_bad_row.read_bytes(), lenient=True)
    assert isinstance(data, ContaPlusData)
    assert data.journal is not None
    assert len(data.journal.rows) == 2  # bad row skipped
    assert data.problems is not None
    assert len(data.problems.entries) == 1
    entry = data.problems.entries[0]
    assert entry.table == "DIARIO"
    assert entry.row_index == 1  # 0-based index of the bad row
    assert entry.column  # non-empty column name (e.g. "subcuenta" or "SUBCTA")


def test_lenient_good_rows_preserved(diario_with_bad_row: Path) -> None:
    """API-03 D-02: Good rows before/after the bad row are preserved intact."""
    data = read(diario_with_bad_row.read_bytes(), lenient=True)
    assert data.journal is not None
    # First good row has debe=100.0
    assert data.journal.rows[0].debe == 100.0


def test_strict_still_raises_on_bad_row(diario_with_bad_row: Path) -> None:
    """API-03: strict mode (default) still raises ContaPlusReadError on bad row.

    The fix for D-02 must not break the strict path — tax-workbench relies on it.
    """
    with pytest.raises(ContaPlusReadError) as exc_info:
        read(diario_with_bad_row.read_bytes())  # strict = default
    assert exc_info.value.row_index == 1  # bad row index


# ---------------------------------------------------------------------------
# D-04: lenient on corrupt secondary table
# ---------------------------------------------------------------------------

def test_lenient_corrupt_table(tmp_path: Path) -> None:
    """API-03 D-04: lenient=True on corrupt venci.dbf: venci=None, ProblemEntry added.

    Build a ZIP with a valid DIARIO.DBF but a corrupt venci.dbf (b'NOT A DBF').
    read() must continue, set data.venci=None, and record one ProblemEntry.
    """
    import dbf as _dbf
    import datetime as _dt

    # Build valid DIARIO.DBF
    diario_path = tmp_path / "DIARIO.DBF"
    diario_spec = (
        "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
        "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
    )
    t = _dbf.Table(filename=str(diario_path), field_specs=diario_spec, codepage="cp850")
    t.open(mode=_dbf.READ_WRITE)
    try:
        t.append({
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "test",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        })
    finally:
        t.close()

    # Build ZIP with corrupt venci.dbf
    zip_path = tmp_path / "backup_corrupt_venci.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(diario_path, arcname="Emp01/Diario.dbf")
        zf.writestr("Emp01/venci.dbf", b"NOT A DBF")

    data = read(zip_path.read_bytes(), lenient=True)
    assert isinstance(data, ContaPlusData)
    assert getattr(data, "venci", "MISSING") is None
    assert data.problems is not None
    assert any(
        e.table == "VENCI" and e.row_index == -1
        for e in data.problems.entries
    )


# ---------------------------------------------------------------------------
# D-03: lenient on wholly-unreadable DIARIO
# ---------------------------------------------------------------------------

def test_lenient_corrupt_journal(tmp_path: Path) -> None:
    """API-03 D-03: lenient=True on corrupt DIARIO.DBF: journal=None, conversion continues.

    Build a ZIP with a corrupt DIARIO.DBF and a valid SUBCTA.DBF.
    read() must: set journal=None, add ProblemEntry for DIARIO, still populate subcta.
    """
    import dbf as _dbf

    # Build valid SUBCTA.DBF
    subcta_path = tmp_path / "SubCta.dbf"
    subcta_spec = "cod C(12); titulo C(40); nif C(15)"
    t = _dbf.Table(filename=str(subcta_path), field_specs=subcta_spec, codepage="cp850")
    t.open(mode=_dbf.READ_WRITE)
    try:
        t.append({"cod": "4300000", "titulo": "Cliente XYZ", "nif": ""})
    finally:
        t.close()

    # Build ZIP with corrupt DIARIO.DBF
    zip_path = tmp_path / "backup_corrupt_diario.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Emp01/Diario.dbf", b"NOT A DBF")
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")

    data = read(zip_path.read_bytes(), lenient=True)
    assert isinstance(data, ContaPlusData)
    assert data.journal is None  # unreadable journal
    assert data.problems is not None
    assert any(
        e.table == "DIARIO" and e.row_index == -1
        for e in data.problems.entries
    )
    assert data.subcta is not None  # conversion continued; subcta was populated


# ---------------------------------------------------------------------------
# D-13: lenient reports uncatalogued .dbf files
# ---------------------------------------------------------------------------

def test_lenient_uncatalogued_dbf(zip_with_uncatalogued: Path) -> None:
    """API-03 D-13: uncatalogued extra.dbf in lenient mode produces one ProblemEntry.

    The entry must have: table name containing 'EXTRA.DBF' (case-insensitive),
    row_index == -1, and 'unrecognized' in the reason.
    """
    data = read(zip_with_uncatalogued.read_bytes(), lenient=True)
    assert isinstance(data, ContaPlusData)
    assert data.problems is not None
    matching = [
        e for e in data.problems.entries
        if e.table == "EXTRA" and e.row_index == -1
    ]
    assert len(matching) == 1
    assert "unrecognized" in matching[0].reason.lower()


# ---------------------------------------------------------------------------
# D-05: memo skips do NOT appear in problems
# ---------------------------------------------------------------------------

def test_memo_skips_not_in_problems(tmp_path: Path) -> None:
    """API-03 D-05: Both-zero memo rows are not added to problems in lenient mode.

    A clean DIARIO with one both-zero row: lenient read must have
    problems=None (or empty) and skipped_memo=1.
    """
    import dbf as _dbf
    import datetime as _dt

    diario_path = tmp_path / "DIARIO.DBF"
    spec = (
        "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
        "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
    )
    t = _dbf.Table(filename=str(diario_path), field_specs=spec, codepage="cp850")
    t.open(mode=_dbf.READ_WRITE)
    try:
        t.append({
            "asien": 1, "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000", "contra": "", "concepto": "memo",
            "eurodebe": 0.0, "eurohaber": 0.0,  # both-zero memo row
        })
    finally:
        t.close()

    data = read(diario_path.read_bytes(), lenient=True)
    # Memo skips must NOT appear in problems
    assert data.problems is None or len(data.problems.entries) == 0
    # The memo skip counter must be incremented
    assert data.journal is not None
    assert data.journal.skipped_memo == 1


# ---------------------------------------------------------------------------
# No problems when input is clean
# ---------------------------------------------------------------------------

def test_no_problems_when_clean(single_company_zip: Path) -> None:
    """API-03: A clean ZIP with lenient=True produces no problems report."""
    data = read(single_company_zip.read_bytes(), lenient=True)
    assert isinstance(data, ContaPlusData)
    assert data.problems is None


# ---------------------------------------------------------------------------
# WR-05: dbfread ValueError during per-row iteration skipped in lenient mode
# ---------------------------------------------------------------------------

def test_lenient_dbfread_valueerror_skipped(diario_with_bad_row: Path) -> None:
    """WR-05: lenient=True with _build_journal_row raising ValueError on idx==1.

    Patch _build_journal_row to raise ValueError("simulated dbfread error") on
    the second call (idx==1). Lenient mode must skip that row, return 2 good rows,
    and record one ProblemEntry(table="DIARIO", row_index==1).

    RED: inner except only catches ContaPlusReadError; ValueError escapes to outer
         except (struct.error, ValueError, OSError) which creates a file-level
         error with row_index=-1, aborting the whole journal rather than skipping
         the bad row.
    GREEN when: inner except catches (ContaPlusReadError, ValueError).
    """
    from unittest.mock import patch, call as _call
    import contaplus_reader._reader as _reader_mod

    # The original _build_journal_row function — we need to call it for non-patched rows.
    original_fn = _reader_mod._build_journal_row
    call_count = [0]

    def _patched(*args, **kwargs):  # type: ignore[no-untyped-def]
        idx = args[1]  # positional arg 1 is idx
        call_count[0] += 1
        if idx == 1:
            raise ValueError("simulated dbfread field error")
        return original_fn(*args, **kwargs)

    with patch.object(_reader_mod, "_build_journal_row", side_effect=_patched):
        data = read(diario_with_bad_row.read_bytes(), lenient=True)

    assert data.journal is not None, "Expected journal to be returned in lenient mode"
    assert len(data.journal.rows) == 2, (
        f"Expected 2 rows (bad row skipped), got {len(data.journal.rows)}"
    )
    assert data.problems is not None, "Expected problems to be collected"
    matching = [e for e in data.problems.entries if e.row_index == 1]
    assert len(matching) == 1, (
        f"Expected one ProblemEntry with row_index=1, got: {data.problems.entries}"
    )
    assert matching[0].table == "DIARIO", (
        f"Expected table='DIARIO', got {matching[0].table!r}"
    )
    assert matching[0].row_index == 1


def test_lenient_dbfread_valueerror_strict_raises(diario_with_bad_row: Path) -> None:
    """WR-05: strict mode with _build_journal_row raising ValueError must propagate as an error.

    In strict mode (lenient=False), a ValueError from _build_journal_row during
    iteration must NOT be silently swallowed — it must propagate (either as the
    raw ValueError or wrapped as ContaPlusReadError via the outer handler).
    """
    from unittest.mock import patch
    import contaplus_reader._reader as _reader_mod

    original_fn = _reader_mod._build_journal_row

    def _patched(*args, **kwargs):  # type: ignore[no-untyped-def]
        idx = args[1]
        if idx == 1:
            raise ValueError("simulated dbfread field error")
        return original_fn(*args, **kwargs)

    with patch.object(_reader_mod, "_build_journal_row", side_effect=_patched):
        with pytest.raises((ContaPlusReadError, ValueError)):
            read(diario_with_bad_row.read_bytes())  # strict = default
