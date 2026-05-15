# contaplus-reader

Read Sage ContaPlus accounting exports (DIARIO.DBF, .zip) into usable formats.

## Installation

Recommended — run the CLI without installing anything:

```
uvx contaplus2xlsx
```

Install as a library:

```
pip install contaplus-reader
```

## Usage

Convert a ContaPlus journal export to a styled Excel file:

```
contaplus2xlsx DIARIO.DBF out.xlsx
```

Use `--force` (or `--overwrite`) to overwrite an existing output file:

```
contaplus2xlsx DIARIO.DBF out.xlsx --force
```

## License

LGPL-3.0-or-later
