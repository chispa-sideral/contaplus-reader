"""bytes_to_tmppath: write in-memory bytes to a NamedTemporaryFile, yield its Path.

Windows-safe: NamedTemporaryFile cannot be reopened while open (WinError 32).
Strategy: delete=False + explicit unlink in finally (Pitfall 1 in RESEARCH.md).
"""

from __future__ import annotations

import io
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


@contextmanager
def bytes_to_tmppath(data: bytes | io.IOBase) -> Generator[Path, None, None]:
    """Write bytes or file-like to a NamedTemporaryFile and yield its Path.

    After the context exits (normally or via exception) the temp file is
    deleted. On Windows, the file must be closed before dbfread can open it --
    so we close() before yielding.

    Args:
        data: Raw bytes or a file-like object (BinaryIO). If file-like, it is
              read in full (data.read()) before writing.

    Yields:
        Path to the temp .dbf file (already closed, readable by dbfread).
    """
    raw: bytes = data if isinstance(data, bytes) else data.read()
    tmp = tempfile.NamedTemporaryFile(suffix=".dbf", delete=False)
    try:
        tmp.write(raw)
        tmp.close()  # close before yielding -- required on Windows
        yield Path(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
