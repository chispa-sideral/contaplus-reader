"""Synthetic DBF fixture factory for contaplus-reader tests.

Port of tw-contaplus/tests/conftest.py (lines 1-170).
ZIP fixtures added in Phase 2 (plan 02-01).

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

Phase 2 fixtures (plan 02-01):
- `single_company_zip_with_subcta` -- ZIP with Emp01/Diario.dbf + Emp01/SubCta.dbf.
- `single_company_zip` -- ZIP with Emp01/Diario.dbf only (no SubCta).
- `multi_company_zip` -- ZIP with Emp01/Diario.dbf and Emp02/Diario.dbf.
- `zip_with_group_tables` -- ZIP with Diario, SubCta, grupos, usuarios, empresa.
- `zip_slip_zip` -- ZIP with a path-traversal entry for security tests.

Plus helper builders for parametric tests.
"""

from __future__ import annotations

import datetime as _dt
import zipfile
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

# Phase 2 DBF specs (RESEARCH.md §SUBCTA Schema + §Critical Finding):
# SUBCTA schema is VERIFIED across all real archives (cod/titulo).
# Group table schemas are [ASSUMED] -- no real archives contain these files.
_SUBCTA_SPEC = "cod C(12,0); titulo C(40,0); nif C(15,0)"
_GRUPOS_SPEC = "COD C(10,0); DESCRIP C(40,0)"
_USUARIOS_SPEC = "CODIGO C(10,0); NOMBRE C(40,0); CLAVE C(20,0)"
_EMPRESA_SPEC = "CODIGO C(10,0); NOMBRE C(60,0); NIF C(15,0)"


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


def _build_subcta_dbf(
    target: Path,
    rows: list[dict[str, Any]],
    *,
    codepage: str = "cp850",
) -> Path:
    """Build a SubCta.dbf at `target` with the given rows. Returns the path."""
    table = dbf.Table(
        filename=str(target),
        field_specs=_SUBCTA_SPEC,
        codepage=codepage,
    )
    table.open(mode=dbf.READ_WRITE)
    try:
        for row in rows:
            table.append(row)
    finally:
        table.close()
    return target


def _build_generic_dbf(
    target: Path,
    spec: str,
    rows: list[dict[str, Any]],
    *,
    codepage: str = "cp850",
) -> Path:
    """Build a generic DBF at `target` with caller-supplied spec and rows. Returns the path."""
    table = dbf.Table(
        filename=str(target),
        field_specs=spec,
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


# ---------------------------------------------------------------------------
# Phase 2 ZIP fixtures (plan 02-01)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def single_company_zip_with_subcta(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP backup with one company (Emp01): Diario.dbf + SubCta.dbf with known rows.

    SubCta contains:
      - 4300000 -> "Cliente XYZ"
      - 7000000 -> "Ventas mercaderias"
    cp850_basic_dbf rows use subcuenta 4300000, 7000000, 6000001.
    6000001 is intentionally absent from SubCta to test missing-key -> None behaviour.
    """
    zip_dir = tmp_path_factory.mktemp("single_company_zip_with_subcta")
    zip_path = zip_dir / "backup.zip"
    subcta_path = zip_dir / "SubCta.dbf"
    _build_subcta_dbf(subcta_path, [
        {"cod": "4300000", "titulo": "Cliente XYZ", "nif": ""},
        {"cod": "7000000", "titulo": "Ventas mercaderias", "nif": ""},
    ])
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")
    return zip_path


@pytest.fixture(scope="session")
def single_company_zip(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP backup with one company (Emp01), DIARIO only (no SubCta).

    Used for enrichment_no_subcta tests where all subcuenta_nombre must be None.
    """
    zip_dir = tmp_path_factory.mktemp("single_company_zip")
    zip_path = zip_dir / "backup_nosub.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
    return zip_path


@pytest.fixture(scope="session")
def multi_company_zip(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP backup with two companies (Emp01, Emp02), DIARIO only each.

    Used to test multi-company disambiguation (D-02/D-03).
    """
    zip_dir = tmp_path_factory.mktemp("multi_company_zip")
    zip_path = zip_dir / "multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(cp850_basic_dbf, arcname="Emp02/Diario.dbf")
    return zip_path


@pytest.fixture(scope="session")
def zip_with_group_tables(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP with Emp01/Diario, SubCta, grupos, usuarios, empresa using assumed schemas.

    Schemas are [ASSUMED] -- no real archives contain these files (RESEARCH.md §Critical Finding).
    Used to test TABL-02 defensive readers when group tables ARE present.
    """
    zip_dir = tmp_path_factory.mktemp("zip_with_group_tables")
    zip_path = zip_dir / "backup_groups.zip"
    subcta_path = zip_dir / "SubCta.dbf"
    grupos_path = zip_dir / "grupos.dbf"
    usuarios_path = zip_dir / "usuarios.dbf"
    empresa_path = zip_dir / "empresa.dbf"
    _build_subcta_dbf(subcta_path, [
        {"cod": "4300000", "titulo": "Cliente XYZ", "nif": ""},
    ])
    _build_generic_dbf(grupos_path, _GRUPOS_SPEC, [
        {"cod": "GRP01", "descrip": "Grupo principal"},
    ])
    _build_generic_dbf(usuarios_path, _USUARIOS_SPEC, [
        {"codigo": "USR01", "nombre": "Admin", "clave": "secret"},
    ])
    _build_generic_dbf(empresa_path, _EMPRESA_SPEC, [
        {"codigo": "EMP01", "nombre": "Mi Empresa SL", "nif": "B12345678"},
    ])
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")
        zf.write(grupos_path, arcname="Emp01/grupos.dbf")
        zf.write(usuarios_path, arcname="Emp01/usuarios.dbf")
        zf.write(empresa_path, arcname="Emp01/empresa.dbf")
    return zip_path


@pytest.fixture(scope="session")
def zip_slip_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """ZIP with a path-traversal entry '../evil.dbf' for zip-slip security tests.

    Uses zipfile.writestr() because zf.write() requires a real filesystem path;
    writestr() accepts an arcname string directly, allowing '../evil.dbf'.
    """
    zip_dir = tmp_path_factory.mktemp("zip_slip_zip")
    zip_path = zip_dir / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.dbf", b"")
    return zip_path
