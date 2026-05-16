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
) -> None:
    """Convert a ContaPlus DIARIO.DBF or backup .zip to a styled .xlsx workbook."""
    from contaplus_reader import ContaPlusReadError, read
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
        data = read(raw_bytes, source_name=str(input_file), company=company)
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

    # D-16: Concise success summary with row count, sheet count, and optional skip count.
    journal = data.journal
    row_count = len(journal.rows) if journal else 0
    sheet_count = sum(
        1 for t in [data.journal, data.subcta, data.empresa, data.grupos, data.usuarios]
        if t is not None
    )
    skip_msg = (
        f" ({journal.skipped_memo} memo lines skipped)"
        if journal and journal.skipped_memo
        else ""
    )
    typer.echo(f"{output_file} — {row_count} journal rows, {sheet_count} sheet(s){skip_msg}")
