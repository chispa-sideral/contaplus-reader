"""Typer CLI entry point for contaplus-reader.

Provides the `contaplus2xlsx` command:
    contaplus2xlsx <input_file> <output_file> [--force]

D-14: Both arguments are required positionals -- no auto-derived default output path.
D-15: CLI refuses to overwrite an existing output file; --force/--overwrite permits.
D-16: On success, prints a concise one-line summary with row count and skip count.
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
    input_file: Annotated[Path, typer.Argument(help="Path to DIARIO.DBF file")],
    output_file: Annotated[Path, typer.Argument(help="Path to write .xlsx output")],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "--overwrite",
            help="Overwrite output file if it already exists",
        ),
    ] = False,
) -> None:
    """Convert a ContaPlus DIARIO.DBF journal to a styled .xlsx workbook."""
    from contaplus_reader import ContaPlusReadError, read
    from contaplus_reader.xlsx import render_journal

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
        data = read(raw_bytes, source_name=str(input_file))
    except ContaPlusReadError as exc:
        # D-17: Structured Rich panel -- no Python traceback.
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

    journal = data.journal
    xlsx_bytes = render_journal(journal)
    output_file.write_bytes(xlsx_bytes)

    # D-16: Concise success summary with row count and optional skip count.
    skip_msg = (
        f" ({journal.skipped_memo} memo lines skipped)" if journal.skipped_memo else ""
    )
    typer.echo(f"{output_file} — {len(journal.rows)} journal rows{skip_msg}")
