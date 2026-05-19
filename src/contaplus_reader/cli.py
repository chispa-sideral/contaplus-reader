"""Typer CLI entry point for contaplus-reader.

Provides the `contaplus2xlsx` command:
    contaplus2xlsx <input_file> <output_file> [--company COMPANY] [--force]

D-07: --company flag accepts a company directory name for multi-company ZIP backups.
D-08: Multi-company ZIP without --company exits 1 with a Rich error panel listing company names.
D-14: Both arguments are required positionals -- no auto-derived default output path.
D-15: CLI refuses to overwrite an existing output file; --force/--overwrite permits.
D-16: On success, prints a concise one-line summary with row count, sheet count, and skip count.
D-17: ContaPlusReadError is shown as a Rich error panel with no traceback; exits 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(add_completion=False)


def _print_report(data: ContaPlusData, output_file: Path) -> None:
    """Print the conversion report to stdout (D-01/D-02/D-03)."""
    typer.echo(f"Converted: {output_file}")
    typer.echo("")

    # Per-table row counts (D-02) -- order matches render() in xlsx.py
    if data.journal:
        typer.echo(f"  Diario:                {len(data.journal.rows):>8} rows")
        if data.journal.skipped_memo:
            typer.echo(f"  Memo lines skipped:    {data.journal.skipped_memo:>8}")
    if data.subcta:
        typer.echo(f"  Subcuentas:            {len(data.subcta.rows):>8} rows")
    if data.balan:
        typer.echo(f"  Balance (raw):         {len(data.balan.rows):>8} rows")
    if data.balance_cuenta:
        typer.echo(f"  Sumas y Saldos (ctas): {len(data.balance_cuenta.rows):>8} rows")
    if data.balance_subcuenta:
        typer.echo(f"  Sumas y Saldos (subs): {len(data.balance_subcuenta.rows):>8} rows")
    for attr, label in [
        ("venci",    "Vencimientos"),
        ("prede",    "Predefinidos"),
        ("amoinv",   "Amortizaciones"),
        ("nivel",    "Niveles"),
        ("empresa",  "Empresa"),
        ("grupos",   "Grupos"),
        ("usuarios", "Usuarios"),
    ]:
        table = getattr(data, attr, None)
        if table is not None:
            typer.echo(f"  {label + ':':<22} {len(table.rows):>8} rows")

    # Problem entries inline (D-03 -- lenient mode only)
    if data.problems and data.problems.entries:
        typer.echo("")
        typer.echo(f"  Problems ({len(data.problems.entries)}):")
        for entry in data.problems.entries:
            row_ref = f"row {entry.row_index}" if entry.row_index >= 0 else "file level"
            typer.echo(
                f"    [{entry.table}] {row_ref}"
                + (f", col {entry.column}" if entry.column else "")
                + f": {entry.reason}"
                + (f" (value: {entry.value!r})" if entry.value else "")
            )


@app.command()
def main(
    input_file: Annotated[Path, typer.Argument(help="Path to DIARIO.DBF file or backup .zip")],
    output_file: Annotated[Path, typer.Argument(help="Path to write .xlsx output")],
    company: Annotated[
        str | None,
        typer.Option(
            "--company",
            help="Company directory name (e.g. Emp01) for multi-company ZIP backups",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "--overwrite",
            help="Overwrite output file if it already exists",
        ),
    ] = False,
    lenient: Annotated[
        bool,
        typer.Option(
            "--lenient",
            help="Extract all readable data; skip unreadable rows/tables into a problems sheet",
        ),
    ] = False,
) -> None:
    """Convert a ContaPlus DIARIO.DBF or backup .zip to a styled .xlsx workbook."""
    from contaplus_reader import ContaPlusData, ContaPlusReadError, read
    from contaplus_reader.xlsx import render

    # Console writes to stderr so it doesn't pollute stdout (D-17).
    console = Console(stderr=True)

    # D-15: Refuse to overwrite unless --force is given.
    if output_file.exists() and not force:
        console.print(
            f"[red]Error:[/red] {output_file} already exists. Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Read the raw bytes from disk (guards against missing/unreadable files).
    try:
        raw_bytes = input_file.read_bytes()
    except OSError as exc:
        console.print(
            Panel(
                str(exc),
                title="File Read Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    # Parse the bytes (bytes-first API).
    try:
        data = read(raw_bytes, source_name=str(input_file), company=company, lenient=lenient)
    except ContaPlusReadError as exc:
        # D-17 / D-08: Structured Rich panel -- no Python traceback.
        console.print(
            Panel(
                f"{exc.message}\n"
                f"Row: {exc.row_index if exc.row_index >= 0 else 'n/a'}\n"
                f"Column: {exc.column or 'n/a'}",
                title="ContaPlus Read Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None  # `from None` suppresses the traceback chain.

    # WR-06 / D-17: render and write are outside the read() handler -- an
    # OSError on write (read-only dir, disk full, permission denied) or any
    # failure inside openpyxl must surface as a Rich panel, never a traceback.
    try:
        xlsx_bytes = render(data)
    except Exception as exc:  # noqa: BLE001 -- openpyxl raises a broad set
        console.print(
            Panel(
                str(exc),
                title="XLSX Render Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    try:
        output_file.write_bytes(xlsx_bytes)
    except OSError as exc:
        console.print(
            Panel(
                str(exc),
                title="File Write Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    _print_report(data, output_file)
