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

from contaplus_reader._balance import compute_balance
from contaplus_reader._bridge import bytes_to_tmppath
from contaplus_reader._reader import _read_dbf_path
from contaplus_reader._sniffer import sniff
from contaplus_reader._subcta import build_subcta_lookup, read_subcta_table, read_table_raw
from contaplus_reader._zip import _find_sibling_dbf, _resolve_company_diario, _safe_extract_zip
from contaplus_reader.models import (
    BalanceTable,
    ContaPlusData,
    ContaPlusJournal,
    ContaPlusReadError,
    GenericTable,
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

# TABL-04 D-12: the 10 catalogued DBF names (all lowercase for case-insensitive comparison).
# Any .dbf file in the archive that is NOT in this set is "uncatalogued" and produces
# an informational ProblemEntry in lenient mode (D-13).
_CATALOGUE: frozenset[str] = frozenset({
    "diario.dbf",
    "subcta.dbf",
    "balan.dbf",
    "grupos.dbf",
    "usuarios.dbf",
    "empresa.dbf",
    "venci.dbf",
    "prede.dbf",
    "amoinv.dbf",
    "nivel.dbf",
})


def _read_secondary_table(
    path: Path | None,
    table_name: str,
    *,
    lenient: bool,
    problems: list[ProblemEntry],
) -> GenericTable | None:
    """Read one optional secondary table, applying lenient error handling.

    Strict mode (lenient=False): any ContaPlusReadError propagates (Phase-2 D-06 unchanged).
    Lenient mode (lenient=True): ContaPlusReadError -> set table=None, append ProblemEntry (D-04).

    Args:
        path: Resolved path to the DBF file, or None if the file was not found.
        table_name: Logical table name used for error messages and ProblemEntry.table.
        lenient: If True, file-level errors produce a ProblemEntry and return None.
        problems: Mutable list to append ProblemEntry records to (used when lenient=True).

    Returns:
        GenericTable on success, or None if path is None or if lenient and error occurred.
    """
    if path is None:
        return None
    if not lenient:
        return read_table_raw(path, table_name)
    try:
        return read_table_raw(path, table_name)
    except ContaPlusReadError as exc:
        problems.append(
            ProblemEntry(
                table=table_name.lower(),
                row_index=-1,
                column="",
                reason=exc.message,
                value="",
            )
        )
        return None


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
        lenient: If True, per-row journal errors and secondary table errors are
                 collected into ContaPlusData.problems rather than raising
                 ContaPlusReadError.  File-level journal errors (D-03) are also
                 collected in lenient mode (journal=None, conversion continues).
                 Default False (strict mode -- unchanged behaviour for existing callers).

    Returns:
        ContaPlusData with .journal populated (ContaPlusJournal).
        For ZIP input: .subcta, .empresa, .grupos, .usuarios, .balan, .venci,
        .prede, .amoinv, .nivel also populated when the corresponding DBF files
        are present in the archive.
        When lenient=True: .problems is a ProblemsReport if any issues were
        collected; None if the input was clean.
        .balance_cuenta and .balance_subcuenta are populated whenever journal
        is not None.

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
    collected_problems: list[ProblemEntry] = []

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

            # Journal read with enrichment (lenient mode passes problem collector).
            # D-03: in lenient mode, a wholly-unreadable DIARIO produces a ProblemEntry
            # and journal=None; all other tables are still extracted.
            journal: ContaPlusJournal | None
            if lenient:
                try:
                    journal = _read_dbf_path(
                        diario_path,
                        source_name=source_name,
                        subcta_lookup=lookup,
                        lenient=True,
                        problems=collected_problems,
                    )
                except ContaPlusReadError as exc:
                    collected_problems.append(
                        ProblemEntry(
                            table="DIARIO",
                            row_index=-1,
                            column="",
                            reason=exc.message,
                            value="",
                        )
                    )
                    journal = None
            else:
                journal = _read_dbf_path(
                    diario_path,
                    source_name=source_name,
                    subcta_lookup=lookup,
                    lenient=False,
                    problems=None,
                )

            # Optional secondary tables (D-05/D-06): absent -> None, present -> GenericTable.
            # Phase 2 tables (grupos, usuarios, empresa) plus Phase 3 tables
            # (balan, venci, prede, amoinv, nivel) — TABL-04 D-12 10-table catalogue.
            # In strict mode: ContaPlusReadError propagates (D-06 unchanged).
            # In lenient mode: error -> None + ProblemEntry (D-04).

            grupos_path = _find_sibling_dbf(diario_path, "grupos.dbf")
            usuarios_path = _find_sibling_dbf(diario_path, "usuarios.dbf")
            empresa_path = _find_sibling_dbf(diario_path, "empresa.dbf")
            balan_path = _find_sibling_dbf(diario_path, "balan.dbf")
            venci_path = _find_sibling_dbf(diario_path, "venci.dbf")
            prede_path = _find_sibling_dbf(diario_path, "prede.dbf")
            amoinv_path = _find_sibling_dbf(diario_path, "amoinv.dbf")
            nivel_path = _find_sibling_dbf(diario_path, "nivel.dbf")

            grupos = _read_secondary_table(
                grupos_path, "grupos.dbf", lenient=lenient, problems=collected_problems
            )
            usuarios = _read_secondary_table(
                usuarios_path, "usuarios.dbf", lenient=lenient, problems=collected_problems
            )
            empresa = _read_secondary_table(
                empresa_path, "empresa.dbf", lenient=lenient, problems=collected_problems
            )
            balan = _read_secondary_table(
                balan_path, "BALAN.DBF", lenient=lenient, problems=collected_problems
            )
            venci = _read_secondary_table(
                venci_path, "venci.dbf", lenient=lenient, problems=collected_problems
            )
            prede = _read_secondary_table(
                prede_path, "prede.dbf", lenient=lenient, problems=collected_problems
            )
            amoinv = _read_secondary_table(
                amoinv_path, "amoinv.dbf", lenient=lenient, problems=collected_problems
            )
            nivel = _read_secondary_table(
                nivel_path, "nivel.dbf", lenient=lenient, problems=collected_problems
            )

            # D-13: in lenient mode, scan for uncatalogued .dbf files and report each.
            if lenient:
                for candidate in diario_path.parent.iterdir():
                    if (
                        candidate.is_file()
                        and candidate.suffix.lower() == ".dbf"
                        and candidate.name.lower() not in _CATALOGUE
                    ):
                        collected_problems.append(
                            ProblemEntry(
                                table=candidate.name.upper(),
                                row_index=-1,
                                column="",
                                reason="unrecognized table — not extracted",
                                value="",
                            )
                        )

            # BAL-02: compute trial balance when journal is available.
            # Reuse the `lookup` dict already built above via build_subcta_lookup
            # (which uses lowernames=True + _pick_column for robust field resolution).
            balance_cuenta: BalanceTable | None = None
            balance_subcuenta: BalanceTable | None = None
            if journal is not None:
                balance_cuenta = compute_balance(journal, by_subcuenta=False)
                balance_subcuenta = compute_balance(
                    journal,
                    by_subcuenta=True,
                    subcta_lookup=lookup,
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
                balan=balan,
                venci=venci,
                prede=prede,
                amoinv=amoinv,
                nivel=nivel,
                balance_cuenta=balance_cuenta,
                balance_subcuenta=balance_subcuenta,
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
            # D-03 lenient handling on raw DBF: only journal is available here.
            if lenient:
                try:
                    journal = _read_dbf_path(
                        path,
                        source_name=source_name,
                        lenient=True,
                        problems=collected_problems,
                    )
                except ContaPlusReadError as exc:
                    collected_problems.append(
                        ProblemEntry(
                            table="DIARIO",
                            row_index=-1,
                            column="",
                            reason=exc.message,
                            value="",
                        )
                    )
                    journal = None
            else:
                journal = _read_dbf_path(
                    path,
                    source_name=source_name,
                    lenient=False,
                    problems=None,
                )

        # BAL-02: compute trial balance from the raw-DBF journal when available.
        balance_cuenta = None
        balance_subcuenta = None
        if journal is not None:
            balance_cuenta = compute_balance(journal, by_subcuenta=False)
            balance_subcuenta = compute_balance(journal, by_subcuenta=True)

        problems_report = (
            ProblemsReport(entries=tuple(collected_problems))
            if collected_problems
            else None
        )
        return ContaPlusData(
            journal=journal,
            balance_cuenta=balance_cuenta,
            balance_subcuenta=balance_subcuenta,
            problems=problems_report,
        )
