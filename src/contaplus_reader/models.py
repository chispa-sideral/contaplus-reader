"""Public result and error types for contaplus-reader.

D-03: read() returns ContaPlusData container.
D-07: ContaPlusJournal.rows is list[JournalRow] frozen dataclasses -- no pandas type.
D-09: ContaPlusJournal carries skipped_memo count and optional source_name.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class ContaPlusReadError(Exception):
    """Structured error from the ContaPlus reader.

    row_index: 0-based index over non-deleted records; -1 = file-level error.
    column: field name or None when not row-specific.
    original: wrapped cause exception, if any.
    """

    message: str
    row_index: int = -1
    column: str | None = None
    original: Exception | None = None

    def __str__(self) -> str:
        loc = f"row {self.row_index}" if self.row_index >= 0 else "file level"
        col = f", column '{self.column}'" if self.column else ""
        return f"ContaPlusReadError [{loc}{col}]: {self.message}"


@dataclass(frozen=True)
class JournalRow:
    """One journal line from DIARIO.DBF.

    cuenta: subcuenta[:4], 3-4 digits (D-B2).
    subcuenta: full subaccount code, >=3 digits.
    debe/haber: Python float; negatives preserved (D-C1 amendment).
    concepto: stripped CONCEPTO value or None if empty.
    """

    fecha: datetime.date
    cuenta: str
    subcuenta: str
    debe: float
    haber: float
    concepto: str | None


@dataclass(frozen=True)
class ContaPlusJournal:
    """Validated journal extracted from DIARIO.DBF.

    rows: all non-deleted, non-memo journal lines.
    skipped_memo: count of both-zero rows skipped (D-C3).
    source_name: optional provenance label supplied by caller.
    """

    rows: list[JournalRow]
    skipped_memo: int = 0
    source_name: str | None = None


@dataclass
class ContaPlusData:
    """Container for all extracted ContaPlus tables.

    Phase 1 populates .journal only; later phases add .subcta, .balance, etc.
    NOT frozen -- grows new attributes in Phases 2-3.
    """

    journal: ContaPlusJournal | None = None
