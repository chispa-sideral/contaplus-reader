"""Public result and error types for contaplus-reader.

D-03: read() returns ContaPlusData container.
D-07: ContaPlusJournal.rows is list[JournalRow] frozen dataclasses -- no pandas type.
D-09: ContaPlusJournal carries skipped_memo count and optional source_name.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal


import dataclasses as _dataclasses

# The plan requires ContaPlusReadError to be a "frozen dataclass" for immutability
# semantics.  However, Python's exception machinery (contextlib on 3.14+) needs
# to assign __traceback__, __cause__, __context__, and __suppress_context__ when
# an exception propagates through a context manager's __exit__.  frozen=True
# generates a __setattr__ that blocks ALL assignments -- the class would raise
# FrozenInstanceError at runtime whenever the exception is re-raised.
#
# Solution: use unsafe_hash + manual __setattr__/__delattr__ that block
# modification of declared fields (same semantics as frozen) but pass through
# the Python-internal exception bookkeeping attributes.  We track whether we
# are inside __init__ via a sentinel flag set before and cleared after
# __init__ runs.

# Names that the Python exception/context-manager machinery may set on any
# BaseException subclass.
_EXCEPTION_INTERNAL_ATTRS: frozenset[str] = frozenset(
    {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
)

# Sentinel flag name stored in the instance's __dict__ during __init__.
_INIT_SENTINEL = "_contaplus_init_"


@_dataclasses.dataclass(eq=True, unsafe_hash=True)
class ContaPlusReadError(Exception):
    """Structured error from the ContaPlus reader.

    Behaves as a frozen dataclass: declared fields cannot be modified after
    construction.  Python exception-machinery attrs (__traceback__ etc.) are
    intentionally allowed so the exception can propagate through context managers.

    row_index: 0-based index over non-deleted records; -1 = file-level error.
    column: field name or None when not row-specific.
    original: wrapped cause exception, if any.
    """

    message: str
    row_index: int = -1
    column: str | None = None
    original: Exception | None = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

    def __new__(cls, *args: object, **kwargs: object) -> "ContaPlusReadError":
        instance = Exception.__new__(cls)
        # Mark as being constructed so __setattr__ allows field writes.
        object.__setattr__(instance, _INIT_SENTINEL, True)
        return instance

    def __post_init__(self) -> None:
        # Clear the init sentinel -- all fields have been set by __init__.
        object.__delattr__(self, _INIT_SENTINEL)

    def __setattr__(self, name: str, value: object) -> None:
        if name in _EXCEPTION_INTERNAL_ATTRS or name == _INIT_SENTINEL:
            object.__setattr__(self, name, value)
            return
        # Allow writes while sentinel is present (i.e. during __init__).
        if self.__dict__.get(_INIT_SENTINEL):
            object.__setattr__(self, name, value)
            return
        raise _dataclasses.FrozenInstanceError("cannot assign to field " + repr(name))

    def __delattr__(self, name: str) -> None:
        if name in _EXCEPTION_INTERNAL_ATTRS or name == _INIT_SENTINEL:
            object.__delattr__(self, name)
            return
        raise _dataclasses.FrozenInstanceError("cannot delete field " + repr(name))

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
    subcuenta_nombre: subaccount description from SUBCTA.DBF, or None (D-09).
    """

    fecha: datetime.date
    cuenta: str
    subcuenta: str
    debe: float
    haber: float
    concepto: str | None
    subcuenta_nombre: str | None = None  # D-09: additive, default None


@dataclass(frozen=True)
class ContaPlusJournal:
    """Validated journal extracted from DIARIO.DBF.

    rows: immutable sequence of validated non-deleted non-memo journal lines.
    skipped_memo: count of both-zero rows skipped (D-C3).
    source_name: optional provenance label supplied by caller.
    """

    rows: tuple[JournalRow, ...]
    skipped_memo: int = 0
    source_name: str | None = None


@dataclass(frozen=True)
class SubctaRow:
    """One subaccount record from SUBCTA.DBF — all fields (D-13 full dump).

    Fields stored as a dict to support full-dump without enumerating
    the 130+ field names that real archives contain.
    """

    fields: dict[str, object]


@dataclass(frozen=True)
class SubctaTable:
    """Full dump of SUBCTA.DBF.

    headers: DBF field names in original order (WR-05). The schema is captured
             from the DBF itself, not derived from row 0 -- so a zero-row table
             still has a header list and ragged rows cannot truncate columns.
    rows: all subaccount records.
    source_name: optional provenance label.
    """

    headers: tuple[str, ...]
    rows: tuple[SubctaRow, ...]
    source_name: str | None = None


@dataclass(frozen=True)
class GenericTable:
    """Full dump of an undocumented table (grupos/usuarios/empresa).

    headers: DBF field names in original order (D-13).
    rows: tuples of raw field values.
    source_name: optional provenance label.
    """

    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    source_name: str | None = None


@dataclass(frozen=True)
class ProblemEntry:
    """One problem record from the lenient conversion path (API-03 D-02..D-05).

    table: logical table name (e.g. "DIARIO", "venci.dbf").
    row_index: 0-based row index within the table; -1 = file-level error.
    column: field/column name involved, or "" when not row-specific.
    reason: human-readable description of the problem.
    value: the raw field value that caused the problem (as string), or "".
    """

    table: str
    row_index: int
    column: str
    reason: str
    value: str


@dataclass(frozen=True)
class ProblemsReport:
    """Collection of problem entries from the lenient conversion path (API-03).

    entries: immutable tuple of all ProblemEntry records collected during
             a lenient read() call.
    """

    entries: tuple[ProblemEntry, ...]


@dataclass(frozen=True)
class BalanceRow:
    """One row of the trial balance (sumas y saldos) for a single account code.

    code: account code (4-digit cuenta code or full subcuenta code).
    suma_debe: sum of all debe amounts, computed via Decimal(str(float)) (BAL-02).
    suma_haber: sum of all haber amounts, computed via Decimal(str(float)) (BAL-02).
    saldo_deudor: max(suma_debe - suma_haber, Decimal("0")) (D-08).
    saldo_acreedor: max(suma_haber - suma_debe, Decimal("0")) (D-08).
    saldo: suma_debe - suma_haber; positive = deudor, negative = acreedor (D-08).
    descripcion: subaccount description from subcta_lookup, or None.
    """

    code: str
    suma_debe: Decimal
    suma_haber: Decimal
    saldo_deudor: Decimal
    saldo_acreedor: Decimal
    saldo: Decimal
    descripcion: str | None = None


@dataclass(frozen=True)
class BalanceTable:
    """Trial balance (sumas y saldos) for a full journal.

    rows: tuple of BalanceRow, sorted ascending by code.
    level: "cuenta" when grouped by 4-digit cuenta; "subcuenta" when grouped by
           full subcuenta code.
    """

    rows: tuple[BalanceRow, ...]
    level: str


@dataclass
class ContaPlusData:
    """Container for all extracted ContaPlus tables.

    Phase 1 populates .journal only. Phase 2 adds .subcta/.empresa/.grupos/.usuarios.
    Phase 3 adds .balan/.venci/.prede/.amoinv/.nivel/.balance_cuenta/.balance_subcuenta/.problems.
    NOT frozen -- grows new attributes in Phases 2-3.
    """

    journal: ContaPlusJournal | None = None
    subcta: SubctaTable | None = None    # D-05: present when SUBCTA.DBF found
    empresa: GenericTable | None = None  # D-05: present when empresa.dbf found
    grupos: GenericTable | None = None   # D-05: present when grupos.dbf found
    usuarios: GenericTable | None = None  # D-05: present when usuarios.dbf found
    # Phase 3 operational tables (TABL-03)
    balan: GenericTable | None = None    # BALAN.DBF — ContaPlus balance structure
    venci: GenericTable | None = None    # venci.dbf — bill maturity table
    prede: GenericTable | None = None    # prede.dbf — recurring entry templates
    amoinv: GenericTable | None = None   # amoinv.dbf — amortisation/investment table
    nivel: GenericTable | None = None    # nivel.dbf — account level configuration
    # Phase 3 computed trial balance (BAL-02)
    balance_cuenta: BalanceTable | None = None
    balance_subcuenta: BalanceTable | None = None
    # Phase 3 lenient path problems report (API-03)
    problems: ProblemsReport | None = None
