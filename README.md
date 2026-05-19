# contaplus-reader

`contaplus-reader` reads Sage **ContaPlus** accounting exports — raw `DIARIO.DBF`
tables and ContaPlus backup `.zip` archives — and extracts *all* of their data
(the journal, subaccounts, the trial balance, and the operational tables) into a
styled `.xlsx` workbook. It ships as a Python library and as the
`contaplus2xlsx` command-line tool, and is intended for anyone migrating off
Sage ContaPlus who needs their data in an open, usable format.

## Installation

Run the CLI without installing anything:

```
uvx contaplus2xlsx INPUT OUTPUT
```

Install the library (and the `contaplus2xlsx` CLI) from PyPI:

```
pip install contaplus-reader
```

## CLI Usage

Convert a raw `DIARIO.DBF` journal export to a styled Excel workbook:

```
contaplus2xlsx DIARIO.DBF out.xlsx
```

Convert a ContaPlus backup `.zip` archive:

```
contaplus2xlsx backup.zip out.xlsx
```

Select one company from a multi-company backup with `--company` (the company
directory name inside the archive, e.g. `Emp01`):

```
contaplus2xlsx backup.zip out.xlsx --company Emp01
```

Use `--lenient` to extract everything readable from a damaged or non-standard
archive — unreadable rows and tables are collected into a separate problems
sheet and reported on stdout instead of aborting the conversion:

```
contaplus2xlsx backup.zip out.xlsx --lenient
```

Add `--force` (or `--overwrite`) to overwrite an existing output file.

## Table Coverage

`contaplus-reader` extracts every table below into its own sheet of the output
workbook:

| Sheet | Source | Notes |
|-------|--------|-------|
| Diario | `DIARIO.DBF` | The accounting journal — strictly read and validated |
| Subcuentas | `SUBCTA.DBF` | Subaccount master |
| Balance bruto | `BALAN.DBF` | Raw trial balance as stored by ContaPlus |
| Sumas y Saldos — Cuentas | computed | Trial balance recomputed at account level |
| Sumas y Saldos — Subcuentas | computed | Trial balance recomputed at subaccount level |
| Vencimientos | `venci.dbf` | Due dates / maturities |
| Predefinidos | `prede.dbf` | Predefined entries |
| Amortizaciones / Inversiones | `amoinv.dbf` | Depreciation and investments |
| Niveles | `nivel.dbf` | Account level definitions |
| Empresa / Grupos / Usuarios | `empresa.dbf`, `grupos.dbf`, `usuarios.dbf` | Company, group, and user metadata |

## Strict vs. Lenient

By default the reader runs in **strict** mode: it fails on the first invalid
row, which is what a tax-grade reading of the journal requires. **Lenient** mode
(`--lenient`) instead extracts all readable data, collecting every problem
(table, row, column, and a plain-English reason) into a dedicated problems sheet
and printing the same detail on stdout — useful for recovering data from a
damaged or non-standard archive.

## Browser PWA

A no-install browser version is in development — your ContaPlus file never
leaves your machine.

## License

`contaplus-reader` is released under the [LGPL-3.0-or-later](LICENSE) license.
