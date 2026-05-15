"""Public result and error types for contaplus-reader.

D-03: read() returns ContaPlusData container.
D-07: ContaPlusJournal.rows is list[JournalRow] frozen dataclasses -- no pandas type.
D-09: ContaPlusJournal carries skipped_memo count and optional source_name.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass


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
