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
# Note: dbf (ethanfurman) uses C(n) not C(n,0) for character fields.
_SUBCTA_SPEC = "cod C(12); titulo C(40); nif C(15)"
_GRUPOS_SPEC = "COD C(10); DESCRIP C(40)"
_USUARIOS_SPEC = "CODIGO C(10); NOMBRE C(40); CLAVE C(20)"
_EMPRESA_SPEC = "CODIGO C(10); NOMBRE C(60); NIF C(15)"


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


@pytest.fixture(scope="session")
def zip_slip_backslash_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """ZIP with a back-slash path-traversal entry (CR-01).

    On POSIX a back-slash is an ordinary filename character, so the raw entry
    name and its forward-slash-normalised form differ. The extractor must
    validate and write the SAME string -- this fixture pins that.
    """
    zip_dir = tmp_path_factory.mktemp("zip_slip_backslash_zip")
    zip_path = zip_dir / "evil_backslash.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("..\\..\\evil.dbf", b"")
    return zip_path


@pytest.fixture(scope="session")
def zip_slip_absolute_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """ZIP with an absolute-path entry for zip-slip security tests (CR-01).

    A POSIX-style absolute entry '/etc/passwd' must be rejected: it resolves
    outside the extraction directory.
    """
    zip_dir = tmp_path_factory.mktemp("zip_slip_absolute_zip")
    zip_path = zip_dir / "evil_absolute.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("/etc/passwd", b"")
    return zip_path


# ---------------------------------------------------------------------------
# Phase 3 DBF specs (RESEARCH.md §Q1 / §Q2 — VERIFIED from pii-test-data/)
# All schemas are identical across all 5 real archives.
# ---------------------------------------------------------------------------

_VENCI_SPEC = (
    "FECHA D; COD C(12); ACPA C(1); CONTRA C(12); CONCEPTO C(25); "
    "PTA N(16,2); TIPO C(2); PREPROCESO L; ESTADO L; DOCUMENTO C(10); "
    "IMPMONEX N(16,2); CODDIVISA C(5); MONEDAUSO C(1); LFACTPLUS L; "
    "FECHAPAG D; REMESA C(12); NCOBRO N(2,0); NPAGARE N(2,0); "
    "EURO N(16,2); NUMRECFAC C(12); METALIMP N(16,2)"
)

_PREDE_SPEC = (
    "ASIEN N(4,0); TSUBCTA C(1); SUBCTA C(12); NSUBCTA N(3,0); "
    "TCONTRA C(1); CONTRA C(12); NCONTRA N(3,0); CIMPORTE C(1); "
    "TIMPORTE C(1); IMPORTE C(50); NIMPORTE N(3,0); TCONCEPTO C(1); "
    "CONCEPTO C(25); TPROYECTO C(1); PROYECTO C(9); TDOCUM C(1); "
    "DOCUM C(10); FACTURA L; TBASEIMPO C(1); BASEIMPO C(50); "
    "NBASEIMPO N(3,0); IVA N(5,2); RECEQUIV N(5,2); "
    "DSUBCTA N(3,0); DCONTRA N(3,0); DCONCEPTO N(3,0); NCONCEPTO N(3,0); "
    "LVENCIMIEN L; LMONEX L; TCAMBIO C(1); CAMBIO N(16,6); "
    "NCAMBIO N(3,0); DCAMBIO N(3,0); LREGULA L; ORIGEN L; "
    "MOD347 L; TSEGMENTO C(1); SEGMENTO C(12); TOPERACION C(1); "
    "TIPOOPE C(1); OPBIENES N(1,0)"
)

_AMOINV_SPEC = (
    "NUMEROINV C(10); DOCUMENTO C(10); FECHACOMP D; FECPRIAM D; "
    "CODNAT C(10); IMPORTCOM N(16,2); FACTURA C(15); CONCEPTO C(25); "
    "UBICACION C(10); GRUPO C(2); SUBCTAAM C(12); SUBCTADO C(12); "
    "IMPORTAM N(16,2); FECULTAM D; TPCA N(6,2); MESES N(2,0); "
    "PROVEEDOR C(12); FECHAFIN D; FECHABAJA D; CODBAJ C(2); "
    "MONEDAUSO C(1); IMPAMEURO N(16,2); IMPCOEURO N(16,2); "
    "TIPOOPE C(1); BASEIMPO N(16,2); TIPOIMPO N(16,2); CUOTAIMP N(16,2); "
    "IMPTOFACT N(16,2); PRORRATA N(7,2); ANOREGULA N(2,0); "
    "FACTTRAN C(15); CUOTABINV N(16,2); ANOFINREG N(2,0); "
    "LIBRO L; TRANSPRO N(1,0)"
)

_NIVEL_SPEC = (
    "N1 L; N2 L; N3 L; N4 L; N5 L; N6 L; "
    "N7 L; N8 L; N9 L; N10 L; N11 L; N12 L; LASTCASADO N(6,0)"
)

_BALAN_SPEC = (
    "NATURALEZA C(2); CODBAL C(10); DESCRIP C(100); CTA C(11); "
    "TIPO N(1,0); BITMAP C(10); DOBLE C(1); FORMULA C(255); "
    "NIVEL N(2,0); DESGLOSE N(2,0); ACPA C(1); NUMERO C(6); "
    "CTAPGC C(12); SDO_CIERRE N(19,2); NIV_CIERRE N(2,0); "
    "LINTERRUMP L; NOTMEMORIA C(50)"
)


# ---------------------------------------------------------------------------
# Phase 3 fixtures — operational tables (TABL-03 / BAL-01)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def venci_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """venci.dbf synthetic fixture — 21 fields, 0 rows (matches real data)."""
    target_dir = tmp_path_factory.mktemp("venci_dbf")
    target = target_dir / "venci.dbf"
    return _build_generic_dbf(target, _VENCI_SPEC, [])


@pytest.fixture(scope="session")
def prede_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """prede.dbf synthetic fixture — 41 fields, 0 rows (matches real data)."""
    target_dir = tmp_path_factory.mktemp("prede_dbf")
    target = target_dir / "prede.dbf"
    return _build_generic_dbf(target, _PREDE_SPEC, [])


@pytest.fixture(scope="session")
def amoinv_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """amoinv.dbf synthetic fixture — 35 fields, 0 rows (matches real data)."""
    target_dir = tmp_path_factory.mktemp("amoinv_dbf")
    target = target_dir / "amoinv.dbf"
    return _build_generic_dbf(target, _AMOINV_SPEC, [])


@pytest.fixture(scope="session")
def nivel_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """nivel.dbf synthetic fixture — 13 fields, exactly 1 row (RESEARCH.md Pitfall 6).

    nivel is a configuration singleton: N1..N12 are level-active booleans,
    LASTCASADO is the last-reconciled entry counter.
    """
    target_dir = tmp_path_factory.mktemp("nivel_dbf")
    target = target_dir / "nivel.dbf"
    return _build_generic_dbf(target, _NIVEL_SPEC, [
        {
            "n1": True, "n2": True, "n3": False, "n4": False,
            "n5": False, "n6": False, "n7": False, "n8": False,
            "n9": False, "n10": False, "n11": False, "n12": False,
            "lastcasado": 0,
        },
    ])


@pytest.fixture(scope="session")
def balan_balanced_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """BALAN.DBF synthetic fixture — 3 rows with SDO_CIERRE summing to 0.00.

    sum(SDO_CIERRE) = 100.00 + (-60.00) + (-40.00) = 0.00 — no descuadre.
    """
    target_dir = tmp_path_factory.mktemp("balan_balanced")
    target = target_dir / "BALAN.DBF"
    rows = [
        {
            "naturaleza": "A", "codbal": "10000", "descrip": "Caja",
            "cta": "10000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "A",
            "numero": "001000", "ctapgc": "", "sdo_cierre": 100.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
        {
            "naturaleza": "P", "codbal": "40000", "descrip": "Proveedores",
            "cta": "40000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "P",
            "numero": "002000", "ctapgc": "", "sdo_cierre": -60.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
        {
            "naturaleza": "P", "codbal": "41000", "descrip": "Otros acreedores",
            "cta": "41000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "P",
            "numero": "003000", "ctapgc": "", "sdo_cierre": -40.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
    ]
    return _build_generic_dbf(target, _BALAN_SPEC, rows)


@pytest.fixture(scope="session")
def balan_unbalanced_dbf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """BALAN.DBF synthetic fixture — 3 rows with SDO_CIERRE summing to 10.00.

    sum(SDO_CIERRE) = 100.00 + (-60.00) + (-30.00) = 10.00 — descuadre!
    """
    target_dir = tmp_path_factory.mktemp("balan_unbalanced")
    target = target_dir / "BALAN.DBF"
    rows = [
        {
            "naturaleza": "A", "codbal": "10000", "descrip": "Caja",
            "cta": "10000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "A",
            "numero": "001000", "ctapgc": "", "sdo_cierre": 100.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
        {
            "naturaleza": "P", "codbal": "40000", "descrip": "Proveedores",
            "cta": "40000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "P",
            "numero": "002000", "ctapgc": "", "sdo_cierre": -60.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
        {
            "naturaleza": "P", "codbal": "41000", "descrip": "Otros acreedores",
            "cta": "41000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "P",
            "numero": "003000", "ctapgc": "", "sdo_cierre": -30.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
    ]
    return _build_generic_dbf(target, _BALAN_SPEC, rows)


# ---------------------------------------------------------------------------
# Phase 3 fixtures — defect-bearing DBFs for lenient path tests (API-03)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def diario_with_bad_row(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """DIARIO.DBF with 3 rows: row 0 valid, row 1 bad subcta="BADCODE", row 2 valid.

    Row 1 has subcta="BADCODE" which triggers D-E3 (malformed subcuenta):
    not purely numeric, so strict mode raises ContaPlusReadError(row_index=1).
    Lenient mode skips row 1, returns 2 good rows, and records one ProblemEntry.
    """
    target_dir = tmp_path_factory.mktemp("diario_bad_row")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Good row one",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 2,
            "fecha": _dt.date(2025, 1, 2),
            "subcta": "BADCODE",  # triggers D-E3 malformed subcuenta
            "contra": "",
            "concepto": "Bad subcta",
            "eurodebe": 50.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 3,
            "fecha": _dt.date(2025, 1, 3),
            "subcta": "7000000",
            "contra": "",
            "concepto": "Good row three",
            "eurodebe": 0.0,
            "eurohaber": 100.0,
        },
    ]
    return _build_diario_dbf(target, rows, codepage="cp850")


@pytest.fixture(scope="session")
def zip_with_all_tables(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP with all 10 catalogued tables under Emp01/ prefix (TABL-04 integration fixture).

    Contains: DIARIO.DBF, SUBCTA.DBF, BALAN.DBF, grupos.dbf, usuarios.dbf,
    empresa.dbf, venci.dbf, prede.dbf, amoinv.dbf, nivel.dbf.
    """
    zip_dir = tmp_path_factory.mktemp("zip_all_tables")
    zip_path = zip_dir / "backup_full.zip"

    # Build each sibling
    subcta_path = zip_dir / "SubCta.dbf"
    _build_subcta_dbf(subcta_path, [
        {"cod": "4300000", "titulo": "Cliente XYZ", "nif": ""},
    ])
    balan_path = zip_dir / "BALAN.DBF"
    _build_generic_dbf(balan_path, _BALAN_SPEC, [
        {
            "naturaleza": "A", "codbal": "10000", "descrip": "Caja",
            "cta": "10000000000", "tipo": 2, "bitmap": "", "doble": "",
            "formula": "", "nivel": 1, "desglose": 0, "acpa": "A",
            "numero": "001000", "ctapgc": "", "sdo_cierre": 0.00,
            "niv_cierre": 0, "linterrump": False, "notmemoria": "",
        },
    ])
    grupos_path = zip_dir / "grupos.dbf"
    _build_generic_dbf(grupos_path, _GRUPOS_SPEC, [
        {"cod": "GRP01", "descrip": "Grupo principal"},
    ])
    usuarios_path = zip_dir / "usuarios.dbf"
    _build_generic_dbf(usuarios_path, _USUARIOS_SPEC, [
        {"codigo": "USR01", "nombre": "Admin", "clave": "secret"},
    ])
    empresa_path = zip_dir / "empresa.dbf"
    _build_generic_dbf(empresa_path, _EMPRESA_SPEC, [
        {"codigo": "EMP01", "nombre": "Mi Empresa SL", "nif": "B12345678"},
    ])
    venci_path = zip_dir / "venci.dbf"
    _build_generic_dbf(venci_path, _VENCI_SPEC, [])
    prede_path = zip_dir / "prede.dbf"
    _build_generic_dbf(prede_path, _PREDE_SPEC, [])
    amoinv_path = zip_dir / "amoinv.dbf"
    _build_generic_dbf(amoinv_path, _AMOINV_SPEC, [])
    nivel_path = zip_dir / "nivel.dbf"
    _build_generic_dbf(nivel_path, _NIVEL_SPEC, [
        {
            "n1": True, "n2": True, "n3": False, "n4": False,
            "n5": False, "n6": False, "n7": False, "n8": False,
            "n9": False, "n10": False, "n11": False, "n12": False,
            "lastcasado": 0,
        },
    ])

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")
        zf.write(balan_path, arcname="Emp01/BALAN.DBF")
        zf.write(grupos_path, arcname="Emp01/grupos.dbf")
        zf.write(usuarios_path, arcname="Emp01/usuarios.dbf")
        zf.write(empresa_path, arcname="Emp01/empresa.dbf")
        zf.write(venci_path, arcname="Emp01/venci.dbf")
        zf.write(prede_path, arcname="Emp01/prede.dbf")
        zf.write(amoinv_path, arcname="Emp01/amoinv.dbf")
        zf.write(nivel_path, arcname="Emp01/nivel.dbf")
    return zip_path


# ---------------------------------------------------------------------------
# Phase 4 fixtures — CLI-03 memo fixture (plan 04-01)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def diario_with_memo_dbf(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """DIARIO.DBF with 2 valid rows + 1 both-zero memo row.

    The both-zero row (eurodebe=0.0, eurohaber=0.0) is treated by the reader
    as a memo line and skipped, setting skipped_memo=1 on the journal.
    Used by CLI-03 tests to verify 'Memo lines skipped:' appears in the report.
    """
    target_dir = tmp_path_factory.mktemp("diario_with_memo")
    target = target_dir / "DIARIO.DBF"
    rows = [
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "4300000",
            "contra": "",
            "concepto": "Valid row one",
            "eurodebe": 100.0,
            "eurohaber": 0.0,
        },
        {
            "asien": 1,
            "fecha": _dt.date(2025, 1, 1),
            "subcta": "7000000",
            "contra": "",
            "concepto": "Valid row two",
            "eurodebe": 0.0,
            "eurohaber": 100.0,
        },
        {
            "asien": 2,
            "fecha": _dt.date(2025, 1, 2),
            "subcta": "1000000",
            "contra": "",
            "concepto": "Memo line zero",
            "eurodebe": 0.0,
            "eurohaber": 0.0,
        },
    ]
    return _build_diario_dbf(target, rows, codepage="cp850")


@pytest.fixture(scope="session")
def zip_with_uncatalogued(
    cp850_basic_dbf: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """ZIP with DIARIO.DBF plus an unrecognized extra.dbf (D-13 lenient test).

    extra.dbf has a minimal 1-field spec and 0 rows. Its name is not in the
    10-table catalogue, so lenient mode must produce one informational ProblemEntry.
    """
    zip_dir = tmp_path_factory.mktemp("zip_uncatalogued")
    zip_path = zip_dir / "backup_extra.zip"

    extra_path = zip_dir / "extra.dbf"
    _build_generic_dbf(extra_path, "CAMPO C(10)", [])

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/Diario.dbf")
        zf.write(extra_path, arcname="Emp01/extra.dbf")
    return zip_path
