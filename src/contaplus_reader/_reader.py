"""Journal reader: reads DIARIO.DBF and applies D-A1...D-E3 business rules.

Port of tw-contaplus/tw_contaplus/read_dbf.py _read_dbf() (lines 137-265)
with the following changes:
  - BlockExecutionError -> ContaPlusReadError
  - Diario -> ContaPlusJournal
  - ReadDBFParams -> simple (path, source_name) signature
  - Added _assert_journal_shaped() for D-02 check before parsing
  - list[JournalRow] collected directly (no pandas DataFrame)
  - ZIP handling removed (Phase 2)
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

from dbfread import DBF

from contaplus_reader.models import (
    ContaPlusJournal,
    ContaPlusReadError,
    JournalRow,
)

logger = logging.getLogger("contaplus_reader._reader")

# D-E1: Amount column candidates, ordered by preference (euro-era first).
# Case-insensitive -- resolved against lowercased field_names (lowernames=True).
_DEBE_COL_CANDIDATES: tuple[str, ...] = ("eurodebe", "eurdebe", "debe", "pesedebe")
_HABER_COL_CANDIDATES: tuple[str, ...] = ("eurohaber", "eurhaber", "haber", "pesehaber")


def _pick_column(
    field_set: set[str],
    candidates: tuple[str, ...],
    *,
    kind: str,
) -> str:
    """Return the first candidate name that exists in field_set.

    Raises:
        ContaPlusReadError: If none of the candidates are present.
    """
    for name in candidates:
        if name in field_set:
            return name
    raise ContaPlusReadError(
        row_index=-1,
        column=kind,
        message=(
            f"DBF has no {kind} column; tried {candidates}; "
            f"available: {sorted(field_set)}"
        ),
    )


def _assert_journal_shaped(table: DBF) -> None:
    """Check that table looks like a DIARIO.DBF before journal parsing (D-02).

    A valid DBF that is not journal-shaped is rejected here with a clear message,
    rather than failing later with a confusing "no debe column" error.

    Raises:
        ContaPlusReadError: If the table lacks FECHA (D) or debe/haber columns.
    """
    field_set = {n.lower() for n in table.field_names}
    field_type_map = {f.name.lower(): f.type for f in table.fields}

    # 1. FECHA field with type D must be present
    if "fecha" not in field_set or field_type_map.get("fecha") != "D":
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(multi-table support is planned in a future phase). "
                f"Available fields: {sorted(field_set)}"
            ),
        )

    # 2. At least one debe candidate and one haber candidate must be present
    _DEBE = {"eurodebe", "eurdebe", "debe", "pesedebe"}
    _HABER = {"eurohaber", "eurhaber", "haber", "pesehaber"}
    if not (field_set & _DEBE) or not (field_set & _HABER):
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=(
                "Input is a valid DBF but not a DIARIO.DBF journal table "
                "(no debit/credit columns found). "
                f"Available fields: {sorted(field_set)}"
            ),
        )


def _read_dbf_path(
    path: Path,
    *,
    source_name: str | None = None,
    subcta_lookup: dict[str, str | None] | None = None,
) -> ContaPlusJournal:
    """Read a DIARIO.DBF at the given path and return a validated ContaPlusJournal.

    Applies all D-A1...D-E3 business rules:
      D-C4: null FECHA -> ContaPlusReadError(column="fecha")
      D-C2: both-non-zero debe+haber -> ContaPlusReadError
      D-C3: both-zero -> skip, skipped_memo++
      D-E3: invalid subcuenta -> ContaPlusReadError(column="subcuenta")
      D-B2: cuenta = subcuenta[:4]
      D-C1: negative amounts pass through (sign preserved)
      D-D1: encoding=cp850 unconditionally
      D-E2: lowernames=True, ignore_missing_memofile=True
      D-09: subcuenta_nombre populated from subcta_lookup if provided

    Args:
        path: Path to a .dbf file (may be a temp file from bytes_to_tmppath).
        source_name: Optional provenance label for the resulting journal.
        subcta_lookup: Optional dict mapping subcuenta codes -> names (D-09/D-11).
                       If None, all subcuenta_nombre will be None.

    Returns:
        ContaPlusJournal with validated rows.

    Raises:
        ContaPlusReadError: On any invalid row, field, or file-level error.
    """
    try:
        table = DBF(
            str(path),
            lowernames=True,
            encoding="cp850",
            ignore_missing_memofile=True,
        )
        _assert_journal_shaped(table)  # D-02: reject non-journal DBF early

        field_set = {n.lower() for n in table.field_names}
        debe_col = _pick_column(field_set, _DEBE_COL_CANDIDATES, kind="debe")
        haber_col = _pick_column(field_set, _HABER_COL_CANDIDATES, kind="haber")

        rows: list[JournalRow] = []
        skipped_memo = 0

        for idx, record in enumerate(table):
            # D-C4: null FECHA is a broken row -- raise immediately
            fecha_raw = record.get("fecha")
            if fecha_raw is None:
                raise ContaPlusReadError(
                    row_index=idx,
                    column="fecha",
                    message="null FECHA",
                )

            # D-E1: convert Decimal/None to float
            debe = float(record.get(debe_col) or 0)
            haber = float(record.get(haber_col) or 0)

            # D-C2: both-non-zero (any sign) is non-standard -- raise.
            # D-C1 negatives (-10, 0) or (0, -50) still pass; (-10, 50) does not.
            if debe != 0 and haber != 0:
                raise ContaPlusReadError(
                    row_index=idx,
                    column=None,
                    message=f"both-non-zero row: debe={debe}, haber={haber}",
                )

            # D-C3: both-zero memo lines are skipped silently
            if debe == 0 and haber == 0:
                skipped_memo += 1
                continue

            # D-E3: subcuenta validation -- non-empty, all-digits, length >= 3
            subcta_raw = record.get("subcta") or ""
            subcuenta = (
                subcta_raw.rstrip()
                if isinstance(subcta_raw, str)
                else str(subcta_raw).rstrip()
            )
            if not subcuenta or not subcuenta.isdigit() or len(subcuenta) < 3:
                raise ContaPlusReadError(
                    row_index=idx,
                    column="subcuenta",
                    message=f"empty/non-numeric SUBCTA: {subcta_raw!r}",
                )

            # D-B2: cuenta is first 4 chars of subcuenta
            cuenta = subcuenta[:4]

            # concepto: strip whitespace, empty -> None
            concepto_raw = record.get("concepto") or ""
            concepto_str = (
                concepto_raw.rstrip()
                if isinstance(concepto_raw, str)
                else str(concepto_raw).rstrip()
            )
            concepto: str | None = concepto_str if concepto_str else None

            # D-09/D-10/D-11: subcuenta-level enrichment; best-effort
            subcuenta_nombre: str | None = None
            if subcta_lookup is not None:
                subcuenta_nombre = subcta_lookup.get(subcuenta)  # None if key absent

            rows.append(
                JournalRow(
                    fecha=fecha_raw,
                    cuenta=cuenta,
                    subcuenta=subcuenta,
                    debe=debe,
                    haber=haber,
                    concepto=concepto,
                    subcuenta_nombre=subcuenta_nombre,  # D-09
                )
            )

        if skipped_memo:
            logger.info(
                "_read_dbf_path skipped %d memo lines (zero amounts)", skipped_memo
            )

        return ContaPlusJournal(
            rows=tuple(rows),
            skipped_memo=skipped_memo,
            source_name=source_name,
        )

    except ContaPlusReadError:
        raise  # re-raise unchanged -- already structured
    except UnicodeDecodeError as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message="Unicode decode error — input must be cp850-encoded",
            original=exc,
        ) from exc
    except (struct.error, ValueError, OSError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"DBF read error: {exc}",
            original=exc,
        ) from exc
