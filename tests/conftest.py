"""Synthetic DBF fixture factory for contaplus-reader tests.

Port of tw-contaplus/tests/conftest.py (lines 1-170).
ZIP fixtures (lines 173-210) are omitted -- ZIP support is Phase 2.

Uses `dbf` (ethanfurman, BSD) -- a dev-only dependency declared in
[dependency-groups] dev -- to generate small, realistic ContaPlus-shaped DBFs
at test-collection time. We do NOT commit binary blobs.

Three core fixtures (D-D4):
- `cp850_basic_dbf` -- minimal DIARIO.DBF in cp850, byte-29=0x02, Spanish accents.
- `cp1252_byte29_dbf` -- same content but byte-29=0x03 (cp1252). Pins our
  `cp850 always` policy: ASCII-clean Spanish content decodes correctly with cp850
  even when the header advertises cp1252.
- `with_deleted_record_dbf` -- one record marked deleted. Pins dbfread's default
  skip-deleted behavior.

Plus helper builders for parametric tests.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Callable

import dbf
import pytest


# ContaPlus DIARIO field spec (SEED.md §1 -- minimal subset for v1):
# ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); CONCEPTO C(25);
# EURODEBE N(16,2); EUROHABER N(16,2)
_DIARIO_SPEC = (
    "ASIEN N(6,0); FECHA D; SUBCTA C(12); CONTRA C(12); "
    "CONCEPTO C(25); EURODEBE N(16,2); EUROHABER N(16,2)"
)


def _build_diario_dbf(
    target: Path,
    rows: list[dict[str, Any]],
    *,
    codepage: str = "cp850",
) -> Path:
    """Build a DIARIO.DBF at `target` with the given rows. Returns the path."""
    table = dbf.Table(
        filename=str(target),
        field_specs=_DIARIO_SPEC,
        codepage=codepage,
    )
    table.open(mode=dbf.READ_WRITE)
    try:
        for row in rows:
            table.append(row)
    finally:
        table.close()
    return target


@pytest.fixture(scope="session")
def cp850_basic_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Minimal DIARIO.DBF, cp850, Spanish accents in CONCEPTO. 3 valid rows."""
    target_dir = tmp_path_factory.mktemp("cp850_basic")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Pago cliente",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "7000000",
            "contra": "",
            "concepto": "Venta enero",
            "eurodebe": 0.0,
            "eurohaber": 100.0,
        },
        {
            "asien": 2,
            "fecha": _dt.date(2025, 2, 15),
            "subcta": "6000001",
            "contra": "",
            "concepto": "Compra papeleria",
            "eurodebe": 50.0,
            "eurohaber": 0.0,
        },
    ]
    return _build_diario_dbf(target, rows, codepage="cp850")


@pytest.fixture(scope="session")
def cp1252_byte29_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Same content as cp850_basic but byte-29 advertises cp1252.

    With ASCII-clean Spanish content, our cp850-always policy still decodes
    correctly. This fixture pins that invariant -- when v2 adds byte-29
    autodetect, this fixture's expected behaviour flips.
    """
    target_dir = tmp_path_factory.mktemp("cp1252_byte29")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Pago cliente",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        },
    ]
    return _build_diario_dbf(target, rows, codepage="cp1252")


@pytest.fixture(scope="session")
def with_deleted_record_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """DBF with one record marked deleted. dbfread default skip-deleted must hold."""
    target_dir = tmp_path_factory.mktemp("with_deleted")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "kept",
            "eurodebe": 50.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 2,
            "fecha": _dt.date(2025, 1, 2),
            "subcta": "4300000",
            "contra": "",
            "concepto": "deleted",
            "eurodebe": 25.0,
            "eurohaber": 0.0,
        },
    ]
    _build_diario_dbf(target, rows, codepage="cp850")
    # Mark second record deleted.
    table = dbf.Table(filename=str(target))
    table.open(mode=dbf.READ_WRITE)
    try:
        records = list(table)
        dbf.delete(records[1])
    finally:
        table.close()
    return target


@pytest.fixture(scope="session")
def diario_dbf_builder(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[list[dict[str, Any]]], Path]:
    """Builder: returns a function that creates a DIARIO.DBF with caller-supplied rows."""
    counter = {"n": 0}

    def _build(rows: list[dict[str, Any]]) -> Path:
        counter["n"] += 1
        target_dir = tmp_path_factory.mktemp(f"custom_{counter['n']}")
        target = target_dir / "DIARIO.DBF"
        return _build_diario_dbf(target, rows, codepage="cp850")

    return _build
