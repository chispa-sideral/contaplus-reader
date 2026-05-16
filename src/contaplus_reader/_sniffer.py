"""Magic-byte sniffer: detect input format from magic bytes.

D-01/D-05: Input type is detected by content magic-byte sniffing -- not file suffix.
Returns "dbf" for recognized DBF version bytes (0x03, 0x30, etc.).
Returns "zip" for ZIP PK magic (0x50).
Raises ContaPlusReadError for anything else.
"""

from __future__ import annotations

import io

from contaplus_reader.models import ContaPlusReadError

# DBF version bytes at offset 0 -- all known dBASE/FoxPro variants.
# Source: independent-software.com/dbase-dbf-dbt-file-format.html [VERIFIED]
_KNOWN_DBF_VERSION_BYTES: frozenset[int] = frozenset({
    0x02,  # FoxBase 1.0
    0x03,  # FoxBase 2.x / dBASE III without memo -- most common ContaPlus
    0x83,  # FoxBase 2.x / dBASE III with memo
    0x30,  # Visual FoxPro -- modern Sage 50 ContaPlus exports
    0x31,  # Visual FoxPro with autoincrement
    0x32,  # Visual FoxPro with varchar/varbinary
    0x43,  # dBASE IV SQL Table without memo
    0x63,  # dBASE IV SQL System without memo
    0x8B,  # dBASE IV with memo
    0xCB,  # dBASE IV SQL Table with memo
    0xF5,  # FoxPro 2.x with memo
    0xFB,  # FoxBase
})


def sniff(data: bytes | io.IOBase) -> str:
    """Detect input format from magic bytes. Returns "dbf" or "zip".

    For bytes/bytearray: reads offset 0 directly.
    For BinaryIO: reads 1 byte then seeks back to 0 if seekable.

    Args:
        data: Input to inspect.

    Returns:
        "dbf" if first byte is a recognized DBF version byte.
        "zip" if first byte is 0x50 (ZIP PK magic).

    Raises:
        ContaPlusReadError: If data is any unrecognized format (neither DBF nor ZIP).
    """
    if isinstance(data, (bytes, bytearray)):
        first_byte: int | None = data[0] if data else None
    else:
        first_byte_bytes = data.read(1)
        if hasattr(data, "seekable") and data.seekable():
            data.seek(0)
        elif hasattr(data, "seekable") and not data.seekable():
            raise ContaPlusReadError(
                row_index=-1,
                column=None,
                message="Input stream is not seekable; provide bytes or a seekable BinaryIO",
            )
        else:
            # Safety fallback: no seekable attribute -- try seek, wrap OSError
            try:
                data.seek(0)
            except OSError:
                raise ContaPlusReadError(
                    row_index=-1,
                    column=None,
                    message="Input stream is not seekable; provide bytes or a seekable BinaryIO",
                ) from None
        first_byte = first_byte_bytes[0] if first_byte_bytes else None

    # D-01: ZIP PK magic byte -- return "zip" (no longer raises)
    if first_byte == 0x50:
        return "zip"

    # Known DBF version byte -- return "dbf"
    if first_byte is not None and first_byte in _KNOWN_DBF_VERSION_BYTES:
        return "dbf"

    raise ContaPlusReadError(
        row_index=-1,
        column=None,
        message="Unsupported input format: not a DBF file",
    )
