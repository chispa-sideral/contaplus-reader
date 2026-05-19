"""Tests for contaplus_reader.cli -- Typer CLI entry point.

Tests cover:
- Happy path: produces .xlsx file and prints row count summary
- Refuses to overwrite existing output without --force (D-15)
- --force flag permits overwrite (D-15)
- --overwrite alias also permits overwrite (D-15)
- Exit code 1 for ContaPlusReadError (D-17)
- Rich error panel shown -- no Python traceback (D-17)
- Success output format: "out.xlsx -- N journal rows" (D-16)
- Success output includes memo skip count when > 0 (D-16)
- --help shows --force/--overwrite option (Pitfall 6)
- Single positional arg exits with usage error (D-14)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from contaplus_reader.cli import app

runner = CliRunner()

# Matches ANSI CSI escape sequences (color/style codes). Rich emits these when
# color output is enabled (e.g. in CI, where FORCE_COLOR is set). With color on,
# Rich's --help highlighter styles the leading dash of an option separately from
# the rest of the name, so the literal substring "--force" is interrupted by an
# escape sequence. Stripping ANSI codes restores the plain text for assertions.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Return *text* with ANSI CSI escape sequences removed."""
    return _ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_cli_happy_path(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """Invoking with valid DBF and non-existent output exits 0 and creates XLSX file."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
    assert out.exists(), "Output .xlsx file was not created"


def test_cli_happy_path_output_is_valid_xlsx(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """The produced file must be parseable by openpyxl."""
    import io as _io
    from openpyxl import load_workbook

    out = tmp_path / "out.xlsx"
    runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    wb = load_workbook(_io.BytesIO(out.read_bytes()))
    assert wb.active is not None


# ---------------------------------------------------------------------------
# Success output format (D-16)
# ---------------------------------------------------------------------------

def test_cli_success_output_format(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """Success output must start with 'Converted:' and include per-table counts (D-01/D-02)."""
    out = tmp_path / "result.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 0
    # D-01/D-02: report block starts with 'Converted:' and includes 'Diario:' row count line
    assert "Converted:" in result.output
    assert "Diario:" in result.output


def test_cli_success_output_contains_filename(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """Success output must contain the output file name."""
    out = tmp_path / "myoutput.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 0
    assert "myoutput.xlsx" in result.output


# ---------------------------------------------------------------------------
# Overwrite guard (D-15)
# ---------------------------------------------------------------------------

def test_cli_refuses_overwrite(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """Without --force, CLI must exit 1 when output file already exists."""
    out = tmp_path / "out.xlsx"
    out.touch()  # pre-exist
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 1
    # Error message must mention the file exists
    combined = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    assert "already exists" in combined


def test_cli_force_overwrites(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """With --force, CLI must exit 0 even when output file already exists."""
    out = tmp_path / "out.xlsx"
    out.touch()  # pre-exist
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out), "--force"])
    assert result.exit_code == 0, f"Expected exit 0 with --force, got {result.exit_code}. Output: {result.output}"


def test_cli_overwrite_alias(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """--overwrite alias must behave identically to --force (D-15)."""
    out = tmp_path / "out.xlsx"
    out.touch()  # pre-exist
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out), "--overwrite"])
    assert result.exit_code == 0, f"Expected exit 0 with --overwrite, got {result.exit_code}. Output: {result.output}"


# ---------------------------------------------------------------------------
# Error handling (D-17)
# ---------------------------------------------------------------------------

def test_cli_error_exit_code(tmp_path: Path) -> None:
    """CLI must exit 1 when given invalid/unsupported input bytes."""
    bad_file = tmp_path / "bad.dbf"
    bad_file.write_bytes(b"\xff\xfe")  # not a DBF magic byte
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(bad_file), str(out)])
    assert result.exit_code == 1


def test_cli_error_panel_shown(tmp_path: Path) -> None:
    """Error output must contain the 'ContaPlus Read Error' panel title (D-17)."""
    bad_file = tmp_path / "bad.dbf"
    bad_file.write_bytes(b"\xff\xfe")
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(bad_file), str(out)], catch_exceptions=False)
    combined = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    assert "ContaPlus Read Error" in combined


def test_cli_error_panel_no_traceback(tmp_path: Path) -> None:
    """No Python traceback must appear in the output for ContaPlusReadError (D-17)."""
    bad_file = tmp_path / "bad.dbf"
    bad_file.write_bytes(b"\xff\xfe")
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(bad_file), str(out)])
    combined = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    # Traceback signature: "Traceback (most recent call last):"
    assert "Traceback" not in combined
    assert "most recent call last" not in combined


# ---------------------------------------------------------------------------
# Required positional arguments (D-14)
# ---------------------------------------------------------------------------

def test_cli_missing_both_args_exits_nonzero() -> None:
    """Invoking with no arguments must exit with a non-zero code (usage error)."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0


def test_cli_missing_output_arg_exits_nonzero(cp850_basic_dbf: Path) -> None:
    """Invoking with only input arg (missing output) must exit with a non-zero code."""
    result = runner.invoke(app, [str(cp850_basic_dbf)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CR-02: Non-existent input file exits 1 with no traceback
# ---------------------------------------------------------------------------

def test_cli_nonexistent_input_exits_nonzero(tmp_path: Path) -> None:
    """CR-02: Invoking CLI with a non-existent input file exits 1 with no Python traceback."""
    result = runner.invoke(app, [str(tmp_path / "no_such_file.dbf"), str(tmp_path / "out.xlsx")])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "Traceback" not in combined
    # typer.Exit(1) raises SystemExit(1) -- raw OSError/FileNotFoundError must NOT leak
    if result.exception is not None:
        assert isinstance(result.exception, SystemExit), (
            f"Expected SystemExit (from typer.Exit), got raw exception: {result.exception!r}"
        )


# ---------------------------------------------------------------------------
# WR-06: Output write failure exits 1 with a Rich panel, no traceback
# ---------------------------------------------------------------------------

def test_cli_unwritable_output_exits_nonzero(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """WR-06: A write failure on the output file exits 1 with no Python traceback.

    Pointing the output at a path inside a non-existent directory makes
    write_bytes() raise OSError -- which must be caught and surfaced as a
    Rich panel (D-17 'no traceback' contract), not leaked as a traceback.
    """
    # Parent directory does not exist -> write_bytes() raises OSError.
    out = tmp_path / "no_such_dir" / "out.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 1
    combined = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    assert "Traceback" not in combined
    assert "most recent call last" not in combined
    # The write failure must be surfaced via the Rich panel.
    assert "File Write Error" in combined
    if result.exception is not None:
        assert isinstance(result.exception, SystemExit), (
            f"Expected SystemExit (from typer.Exit), got raw exception: {result.exception!r}"
        )


# ---------------------------------------------------------------------------
# --help output (Pitfall 6)
# ---------------------------------------------------------------------------

def test_cli_help_shows_force_option() -> None:
    """--help must mention --force/--overwrite in the options section."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Strip ANSI codes: with color enabled (CI), Rich styles the leading dash of
    # an option separately, splitting the literal "--force" substring.
    plain = _strip_ansi(result.output)
    assert "--force" in plain
    assert "--overwrite" in plain


# ===========================================================================
# Phase 2 failing tests (plan 02-01) -- all RED; GREEN in plan 02-03
# ===========================================================================

# ---------------------------------------------------------------------------
# CLI-02: --company flag
# ---------------------------------------------------------------------------

def test_cli_company_flag_accepted(
    tmp_path: Path,
    single_company_zip_with_subcta: Path,
) -> None:
    """CLI-02: --company flag must be accepted and passed to read().

    RED: --company option does not exist on the CLI yet (typer unknown option error).
    GREEN when: cli.py gains --company Annotated[str | None, typer.Option()] parameter.
    """
    out = tmp_path / "out.xlsx"
    result = runner.invoke(
        app, [str(single_company_zip_with_subcta), str(out), "--company", "Emp01"]
    )
    # Verify the option is accepted (not rejected as unknown)
    assert "--company" not in (result.output or ""), (
        "--company was reported as unknown option -- not yet implemented"
    )
    assert result.exit_code == 0, (
        f"Expected exit 0 with valid --company, got {result.exit_code}. Output: {result.output}"
    )
    assert out.exists()


def test_cli_multi_company_no_flag_exits_1(
    tmp_path: Path,
    multi_company_zip: Path,
) -> None:
    """CLI-02 / D-08: Multi-company ZIP without --company exits 1 with Rich error panel.

    RED: CLI currently raises ContaPlusReadError for all ZIP (sniffer rejection),
    which DOES exit 1 -- but for the wrong reason. Once ZIP support lands,
    the error panel must list available company names ('Emp01', 'Emp02').
    GREEN when: ZIP read implemented and multi-company error surfaced via Rich panel.
    """
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(multi_company_zip), str(out)])
    assert result.exit_code == 1
    # Phase 2 requirement: error output mentions available company names
    combined = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
    assert "Emp01" in combined, (
        f"Expected 'Emp01' in error output for multi-company ZIP, got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# Report output (CLI-03 D-01/D-02/D-03)
# ---------------------------------------------------------------------------

def test_report_shows_diario_row_count(tmp_path: Path, cp850_basic_dbf: Path) -> None:
    """D-02: Report must include 'Diario:' line with correct row count."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 0
    assert "Diario:" in result.output
    assert "3" in result.output  # cp850_basic_dbf has 3 rows


def test_report_shows_skipped_memo_count(
    tmp_path: Path, diario_with_memo_dbf: Path
) -> None:
    """D-02: Report must include 'Memo lines skipped:' when skipped_memo > 0."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(diario_with_memo_dbf), str(out)])
    assert result.exit_code == 0
    assert "Memo lines skipped:" in result.output


def test_report_shows_problem_entries_in_lenient(
    tmp_path: Path, diario_with_bad_row: Path
) -> None:
    """D-03: Lenient mode report must list each problem entry inline on stdout."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(diario_with_bad_row), str(out), "--lenient"])
    assert result.exit_code == 0
    assert "Problems" in result.output
    # Problem entry must include the table name
    assert "DIARIO" in result.output


def test_report_no_problems_section_in_strict(
    tmp_path: Path, cp850_basic_dbf: Path
) -> None:
    """D-03: Strict mode (default) must not print a 'Problems' section."""
    out = tmp_path / "out.xlsx"
    result = runner.invoke(app, [str(cp850_basic_dbf), str(out)])
    assert result.exit_code == 0
    assert "Problems" not in result.output
