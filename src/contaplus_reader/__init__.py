"""contaplus-reader: read Sage ContaPlus accounting exports into usable formats.

Public API:
    read(data, source_name, company) -> ContaPlusData

D-06: Signature is read(data: bytes | BinaryIO, source_name: str | None = None,
                        company: str | None = None).
      No filesystem-path argument.
D-04: Strict-only in Phase 1/2. read() always raises ContaPlusReadError on invalid data.
D-03: Returns ContaPlusData container (not the journal directly).
D-04: company param added in Phase 2 for multi-company ZIP disambiguation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import BinaryIO

from contaplus_reader._bridge import bytes_to_tmppath
from contaplus_reader._reader import _read_dbf_path
from contaplus_reader._sniffer import sniff
from contaplus_reader._subcta import build_subcta_lookup, read_subcta_table, read_table_raw
from contaplus_reader._zip import _find_sibling_dbf, _resolve_company_diario, _safe_extract_zip
from contaplus_reader.models import (
    ContaPlusData,
    ContaPlusJournal,
    ContaPlusReadError,
    JournalRow,
    ProblemEntry,
    ProblemsReport,
)

__all__ = [
    "read",
    "ContaPlusData",
    "ContaPlusJournal",
    "JournalRow",
    "ContaPlusReadError",
]


def read(
    data: bytes | BinaryIO,
    source_name: str | None = None,
    company: str | None = None,
    *,
    lenient: bool = False,
) -> ContaPlusData:
    """Read a ContaPlus file from bytes or a file-like object.

    Accepts both raw DIARIO.DBF bytes and ContaPlus backup .zip archives.
    The format is detected by magic-byte sniffing (D-01/D-05).

    Args:
        data: Raw bytes or a file-like object opened in binary mode.
              Both .dbf bytes and .zip bytes are accepted.
        source_name: Optional label for provenance in errors and journal metadata.
        company: Company directory name for multi-company ZIP archives (D-04).
                 Example: "Emp01". Required when ZIP contains multiple companies.
                 Not applicable to raw DBF input (raises ContaPlusReadError if supplied).
        lenient: If True, per-row journal errors are collected into
                 ContaPlusData.problems rather than raising ContaPlusReadError.
                 File-level errors (row_index == -1) always propagate.
                 Default False (strict mode -- unchanged behaviour for existing callers).

    Returns:
        ContaPlusData with .journal populated (ContaPlusJournal).
        For ZIP input: .subcta, .empresa, .grupos, .usuarios also populated
        when the corresponding DBF files are present in the archive.
        When lenient=True: .problems is a ProblemsReport if any issues were
        collected; None if the input was clean.

    Raises:
        ContaPlusReadError: On any invalid input, malformed DBF, or bad journal row
                            (strict mode), or on file-level errors in lenient mode.
                            Also raised when company= is required but not supplied
                            (multi-company ZIP), or when company= is supplied on
                            a raw DBF input.
    """
    # Pitfall 6: normalise input to raw bytes once before any read
    raw: bytes = data if isinstance(data, bytes) else data.read()

    fmt = sniff(raw)  # returns "dbf" or "zip"; raises on unrecognised format

    # Lenient mode: accumulate ProblemEntry records across the whole conversion.
    collected_problems: list[ProblemEntry] = [] if lenient else []

    if fmt == "zip":
        # ZIP path -- TemporaryDirectory lifecycle owned here (RESEARCH.md Pitfall 1)
        with tempfile.TemporaryDirectory(prefix="contaplus_") as tmpdir_str:
            extract_dir = Path(tmpdir_str)
            _safe_extract_zip(raw, extract_dir)
            diario_path = _resolve_company_diario(extract_dir, company)

            # SUBCTA enrichment (D-09/D-11): best-effort, absent -> empty lookup
            subcta_path = _find_sibling_dbf(diario_path, "subcta.dbf")
            lookup: dict[str, str | None] = (
                build_subcta_lookup(subcta_path) if subcta_path else {}
            )
            subcta_table = read_subcta_table(subcta_path) if subcta_path else None

            # Journal read with enrichment (lenient mode passes problem collector)
            journal = _read_dbf_path(
                diario_path,
                source_name=source_name,
                subcta_lookup=lookup,
                lenient=lenient,
                problems=collected_problems if lenient else None,
            )

            # Optional group tables (D-05/D-06): absent -> None, present -> GenericTable
            grupos_path = _find_sibling_dbf(diario_path, "grupos.dbf")
            usuarios_path = _find_sibling_dbf(diario_path, "usuarios.dbf")
            empresa_path = _find_sibling_dbf(diario_path, "empresa.dbf")

            grupos = read_table_raw(grupos_path, "grupos.dbf") if grupos_path else None
            usuarios = (
                read_table_raw(usuarios_path, "usuarios.dbf") if usuarios_path else None
            )
            empresa = (
                read_table_raw(empresa_path, "empresa.dbf") if empresa_path else None
            )

            problems_report = (
                ProblemsReport(entries=tuple(collected_problems))
                if collected_problems
                else None
            )

            return ContaPlusData(
                journal=journal,
                subcta=subcta_table,
                empresa=empresa,
                grupos=grupos,
                usuarios=usuarios,
                problems=problems_report,
            )
    else:
        # DBF path (unchanged from Phase 1, uses bytes_to_tmppath bridge)
        if company is not None:
            raise ContaPlusReadError(
                row_index=-1,
                column=None,
                message="company selector is not applicable to a raw DBF input",
            )
        with bytes_to_tmppath(raw) as path:
            journal = _read_dbf_path(
                path,
                source_name=source_name,
                lenient=lenient,
                problems=collected_problems if lenient else None,
            )

        problems_report = (
            ProblemsReport(entries=tuple(collected_problems))
            if collected_problems
            else None
        )
        return ContaPlusData(journal=journal, problems=problems_report)
