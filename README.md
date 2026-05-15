# contaplus-reader

Read Sage ContaPlus accounting exports (`DIARIO.DBF`, `.zip`) into usable formats.

## Features

- Bytes-first API: `read(data: bytes | BinaryIO)` — no filesystem path required
- Strict validated journal extraction with structured errors (`ContaPlusReadError`)
- CLI: `contaplus2xlsx DIARIO.DBF out.xlsx`

## License

LGPL-3.0-or-later
