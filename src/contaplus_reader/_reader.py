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
    ProblemEntry,
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

    Case-insensitive: both ``field_set`` and ``candidates`` are compared in
    lower case, so callers need not pre-lowercase their input (WR-03). The
    returned name is the actual member of ``field_set`` (original casing
    preserved), so it can be used to index records directly.

    Raises:
        ContaPlusReadError: If none of the candidates are present.
    """
    # WR-03: lower-case both sides so the helper does not depend on an
    # unstated "caller pre-lowercased the set" invariant.
    lower_to_original = {name.lower(): name for name in field_set}
    for candidate in candidates:
        original = lower_to_original.get(candidate.lower())
        if original is not None:
            return original
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


def _raw_value(record: object, column: str | None) -> str:
    """Return str(record.get(column, '')) if column is set, else ''.

    Used in lenient mode to capture the raw field value for a ProblemEntry.
    """
    if not column:
        return ""
    if hasattr(record, "get"):
        return str(record.get(column, ""))  # type: ignore[union-attr]
    return ""


def _build_journal_row(
    record: object,
    idx: int,
    debe_col: str,
    haber_col: str,
    subcta_lookup: dict[str, str | None] | None,
    enrichment_misses_ref: list[int],
) -> JournalRow | None:
    """Extract and validate one journal row from a DBF record.

    This is the per-row validation logic extracted from the D-C5 loop in
    _read_dbf_path. It applies all D-C* and D-E* rules:
      D-C4: null FECHA -> ContaPlusReadError(row_index=idx, column="fecha")
      D-C2: both-non-zero debe+haber -> ContaPlusReadError(row_index=idx)
      D-C3: both-zero -> returns None (caller increments skipped_memo)
      D-E3: invalid subcuenta -> ContaPlusReadError(row_index=idx, column="subcuenta")
      D-B2: cuenta = subcuenta[:4]
      D-C1: negative amounts pass through (sign preserved)
      D-09: subcuenta_nombre populated from subcta_lookup if provided

    Args:
        record: DBF record dict from dbfread (lowernames=True).
        idx: 0-based record index within the DBF iteration.
        debe_col: Column name for debit amounts.
        haber_col: Column name for credit amounts.
        subcta_lookup: Optional subcuenta -> title lookup dict (D-09).
        enrichment_misses_ref: Single-element list used as a mutable reference
                               for the enrichment miss counter (avoids nonlocal).

    Returns:
        JournalRow on success, or None for a both-zero memo row (D-C3).

    Raises:
        ContaPlusReadError: On any validation failure (row_index=idx for per-row
                            errors; the outer caller handles file-level errors).
    """
    # D-C4: null FECHA is a broken row -- raise immediately
    fecha_raw = record.get("fecha")  # type: ignore[union-attr]
    if fecha_raw is None:
        raise ContaPlusReadError(
            row_index=idx,
            column="fecha",
            message="null FECHA",
        )

    # D-E1: convert Decimal/None to float
    debe = float(record.get(debe_col) or 0)  # type: ignore[union-attr]
    haber = float(record.get(haber_col) or 0)  # type: ignore[union-attr]

    # D-C2: both-non-zero (any sign) is non-standard -- raise.
    # D-C1 negatives (-10, 0) or (0, -50) still pass; (-10, 50) does not.
    if debe != 0 and haber != 0:
        raise ContaPlusReadError(
            row_index=idx,
            column=None,
            message=f"both-non-zero row: debe={debe}, haber={haber}",
        )

    # D-C3: both-zero memo lines are skipped silently (caller increments counter)
    if debe == 0 and haber == 0:
        return None

    # D-E3: subcuenta validation -- non-empty, all-digits, length >= 3
    subcta_raw = record.get("subcta") or ""  # type: ignore[union-attr]
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
    concepto_raw = record.get("concepto") or ""  # type: ignore[union-attr]
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
        # WR-04: track misses against a non-empty lookup.
        if subcuenta_nombre is None and subcta_lookup:
            enrichment_misses_ref[0] += 1

    return JournalRow(
        fecha=fecha_raw,
        cuenta=cuenta,
        subcuenta=subcuenta,
        debe=debe,
        haber=haber,
        concepto=concepto,
        subcuenta_nombre=subcuenta_nombre,  # D-09
    )


def _read_dbf_path(
    path: Path,
    *,
    source_name: str | None = None,
    subcta_lookup: dict[str, str | None] | None = None,
    lenient: bool = False,
    problems: list[ProblemEntry] | None = None,
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
        lenient: If True, per-row errors (row_index >= 0) are collected into
                 ``problems`` and the bad row is skipped rather than aborting.
                 File-level errors (row_index == -1) always propagate regardless.
                 If False (default), any ContaPlusReadError propagates immediately
                 (strict mode -- unchanged behaviour for existing callers).
        problems: Mutable list that receives ProblemEntry records when lenient=True.
                  Caller must pass a list; each skipped row appends one entry.
                  Ignored when lenient=False.

    Returns:
        ContaPlusJournal with validated rows.

    Raises:
        ContaPlusReadError: On any invalid row, field, or file-level error
                            (strict mode), or on file-level errors in lenient mode.
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
        # WR-04: count journal rows whose subcuenta is absent from a
        # *non-empty* lookup -- a high miss rate signals a key-normalisation
        # bug rather than genuinely-absent codes.
        # Use a single-element list so _build_journal_row can update it.
        enrichment_misses_ref = [0]

        for idx, record in enumerate(table):
            try:
                row = _build_journal_row(
                    record, idx, debe_col, haber_col, subcta_lookup,
                    enrichment_misses_ref,
                )
            except ContaPlusReadError as exc:
                if lenient and exc.row_index >= 0:
                    # Per-row error in lenient mode: collect and skip (D-02)
                    # D-05: memo skips (row=None) are NOT collected here;
                    # only genuine errors reach this branch.
                    if problems is not None:
                        problems.append(
                            ProblemEntry(
                                table="DIARIO",
                                row_index=idx,
                                column=exc.column or "",
                                reason=exc.message,
                                value=_raw_value(record, exc.column),
                            )
                        )
                    continue
                # Strict mode, or file-level error (row_index == -1): re-raise
                raise

            if row is None:
                # D-C3: both-zero memo skip -- increment counter, no ProblemEntry
                skipped_memo += 1
                continue

            rows.append(row)

        if skipped_memo:
            logger.info(
                "_read_dbf_path skipped %d memo lines (zero amounts)", skipped_memo
            )

        # WR-04: surface enrichment miss rate so a near-total miss (likely a
        # key-normalisation bug) is visible rather than silently masked.
        enrichment_misses = enrichment_misses_ref[0]
        if enrichment_misses:
            logger.info(
                "_read_dbf_path: %d of %d journal rows had no SUBCTA match",
                enrichment_misses,
                len(rows),
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
