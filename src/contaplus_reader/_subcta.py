"""SUBCTA.DBF and generic table readers for ContaPlus archives.

Provides:
  build_subcta_lookup  -- cod -> titulo dict for journal enrichment (API-05)
  read_subcta_table    -- full SubctaTable (all fields, D-13)
  read_table_raw       -- GenericTable for grupos/usuarios/empresa (D-13)

Decision refs:
  D-06: Present-but-unreadable table aborts conversion; absent table is silent.
  D-11: Missing subcuenta key in lookup -> None (best-effort, no error).
  D-13: Full dump -- every field in DBF field order.
  D-16: Defensive field-name resolution via _pick_column candidate lists.
  D-17: Schemas discovered from pii-test-data/ before this module was committed.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

from dbfread import DBF

from contaplus_reader._reader import _pick_column
from contaplus_reader.models import (
    ContaPlusReadError,
    GenericTable,
    SubctaRow,
    SubctaTable,
)

logger = logging.getLogger("contaplus_reader._subcta")

# SUBCTA field-name variants (RESEARCH.md §SUBCTA Schema, D-16).
# Real archives use cod/titulo; codigo/descrip are defensive fallbacks.
_SUBCTA_COD_CANDIDATES: tuple[str, ...] = ("cod", "codigo")
_SUBCTA_TITULO_CANDIDATES: tuple[str, ...] = ("titulo", "descrip")


def _as_str(value: object) -> str:
    """Coerce a dbfread field value to a right-stripped str (CR-02).

    Character fields decode to ``str``; numeric (type ``N``) fields decode to
    ``int``/``Decimal``. Calling ``.rstrip()`` directly on a non-str crashes
    with ``AttributeError``. This mirrors the ``isinstance(..., str)`` guards
    in ``_reader.py`` so a numeric SUBCTA ``cod`` cannot escape as an
    unstructured crash.
    """
    if isinstance(value, str):
        return value.rstrip()
    if value is None:
        return ""
    return str(value).rstrip()


def _as_key(value: object) -> str:
    """Coerce a dbfread field value to a fully-stripped lookup key (WR-04).

    Unlike ``_as_str`` (right-strip only, for display text), this strips
    *both* ends. SUBCTA ``cod`` and journal ``subcuenta`` must be normalised
    identically or a leading-space ``cod`` survives in the lookup but never
    matches the digit-only journal key -- a silent enrichment miss.
    """
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def build_subcta_lookup(subcta_path: Path) -> dict[str, str | None]:
    """Build a cod -> titulo lookup dict from SUBCTA.DBF.

    D-11: Returns a populated dict; caller passes {} when subcta_path is None
          (absent SUBCTA means all subcuenta_nombre are None, no error).
    D-06: Present-but-unreadable SUBCTA raises ContaPlusReadError (aborts conversion).
    D-16: Field names resolved defensively via _pick_column candidate lists.

    Args:
        subcta_path: Path to SUBCTA.DBF (must exist).

    Returns:
        dict mapping rstrip()ed cod -> rstrip()ed titulo (or None if titulo is empty).

    Raises:
        ContaPlusReadError: If the file exists but cannot be read.
    """
    try:
        table = DBF(
            str(subcta_path),
            lowernames=True,
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        field_set = {f.name for f in table.fields}
        cod_col = _pick_column(field_set, _SUBCTA_COD_CANDIDATES, kind="subcta.cod")
        titulo_col = _pick_column(
            field_set, _SUBCTA_TITULO_CANDIDATES, kind="subcta.titulo"
        )
        # CR-02: coerce defensively -- a numeric SUBCTA `cod`/`titulo` field
        # must not crash with AttributeError on `.rstrip()`.
        # WR-04: the key is fully stripped (both ends) so it normalises
        # identically to the digit-only journal `subcuenta` key.
        return {
            _as_key(rec.get(cod_col)): (_as_str(rec.get(titulo_col)) or None)
            for rec in table
            if rec.get(cod_col)
        }
    except ContaPlusReadError:
        raise  # present-but-unreadable -> abort (D-06); already structured
    except (struct.error, ValueError, OSError, UnicodeDecodeError, AttributeError, TypeError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"SUBCTA.DBF read error: {exc}",
            original=exc,
        ) from exc


def read_subcta_table(subcta_path: Path) -> SubctaTable:
    """Read all records from SUBCTA.DBF as a SubctaTable (full dump, D-13).

    Uses lowernames=False to preserve original DBF field names in each SubctaRow.

    Args:
        subcta_path: Path to SUBCTA.DBF (must exist).

    Returns:
        SubctaTable with all rows.

    Raises:
        ContaPlusReadError: If the file exists but cannot be read.
    """
    try:
        table = DBF(
            str(subcta_path),
            lowernames=False,  # preserve original field names for full dump (D-13)
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        return SubctaTable(
            rows=tuple(SubctaRow(fields=dict(rec)) for rec in table),
            source_name=str(subcta_path),
        )
    except ContaPlusReadError:
        raise
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"SUBCTA.DBF read error: {exc}",
            original=exc,
        ) from exc


def read_table_raw(path: Path, table_name: str) -> GenericTable:
    """Read all records from a DBF as a GenericTable (full dump, D-13).

    Uses lowernames=False to preserve original DBF field names as headers.
    Used for grupos/usuarios/empresa tables.

    D-06: Raises ContaPlusReadError if present but unreadable.

    Args:
        path: Path to the DBF file (must exist).
        table_name: Human-readable table name for error messages.

    Returns:
        GenericTable with headers tuple and rows tuple.

    Raises:
        ContaPlusReadError: If the file exists but cannot be read.
    """
    try:
        table = DBF(
            str(path),
            lowernames=False,  # keep original field names for raw headers (D-13)
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        headers = tuple(f.name for f in table.fields)
        rows = tuple(tuple(rec[h] for h in headers) for rec in table)
        return GenericTable(
            headers=headers,
            rows=rows,
            source_name=str(path),
        )
    except ContaPlusReadError:
        raise
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"{table_name} read error: {exc}",
            original=exc,
        ) from exc
