"""contaplus-reader: read Sage ContaPlus accounting exports into usable formats.

Public API:
    read(data, source_name) -> ContaPlusData

D-06: Signature is read(data: bytes | BinaryIO, source_name: str | None = None).
      No filesystem-path argument.
D-04: Strict-only in Phase 1. read() always raises ContaPlusReadError on invalid data.
D-03: Returns ContaPlusData container (not the journal directly).
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, BinaryIO

from contaplus_reader._bridge import bytes_to_tmppath
from contaplus_reader._reader import _read_dbf_path
from contaplus_reader._sniffer import sniff
from contaplus_reader.models import (
    ContaPlusData,
    ContaPlusJournal,
    ContaPlusReadError,
    JournalRow,
)

if TYPE_CHECKING:
    pass

__all__ = [
    "read",
    "ContaPlusData",
    "ContaPlusJournal",
    "JournalRow",
    "ContaPlusReadError",
]


def read(
    data: bytes | BinaryIO,
    source_name: str | None = None,
) -> ContaPlusData:
    """Read a ContaPlus DIARIO.DBF from bytes or a file-like object.

    Args:
        data: Raw bytes or a file-like object opened in binary mode.
              ZIP bytes are rejected with a structured error (D-05).
        source_name: Optional label for provenance in errors and journal metadata.

    Returns:
        ContaPlusData with .journal populated (ContaPlusJournal).

    Raises:
        ContaPlusReadError: On any invalid input, malformed DBF, or bad journal row.
    """
    sniff(data)  # raises ContaPlusReadError on unsupported format
    with bytes_to_tmppath(data) as path:
        journal = _read_dbf_path(path, source_name=source_name)
    return ContaPlusData(journal=journal)
