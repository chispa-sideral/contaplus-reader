"""Magic-byte sniffer: validate that input bytes look like a DBF file.

D-05: Input type is detected by content magic-byte sniffing -- not file suffix.
Rejects ZIP (PK magic) with a specific message; rejects anything else as "not a DBF".
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


def sniff(data: bytes | io.IOBase) -> None:
    """Raise ContaPlusReadError if data is not a recognized DBF file.

    For bytes/bytearray: reads offset 0 directly.
    For BinaryIO: reads 1 byte then seeks back to 0 if seekable.

    Args:
        data: Input to inspect.

    Raises:
        ContaPlusReadError: If data is ZIP bytes or any unrecognized format.
    """
    if isinstance(data, (bytes, bytearray)):
        first_byte: int | None = data[0] if data else None
    else:
        first_byte_bytes = data.read(1)
        if hasattr(data, "seek"):
            data.seek(0)
        first_byte = first_byte_bytes[0] if first_byte_bytes else None

    if first_byte is None or first_byte not in _KNOWN_DBF_VERSION_BYTES:
        hint = (
            "ZIP archive detected — ZIP input is supported in a future phase"
            if first_byte == 0x50  # 'P' -- PK magic byte
            else "not a DBF file"
        )
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Unsupported input format: {hint}",
        )
