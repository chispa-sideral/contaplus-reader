"""ZIP extraction and company resolution for ContaPlus backup archives.

Decision refs:
  D-01: ZIP detection by magic-byte sniff (0x50 branch accepts, no longer raises).
  D-02: Multi-company disambiguation by raw directory name (case-insensitive);
        error lists available directory names.
  D-03: company= selector on single-company ZIP validates; mismatch raises.
        company= selector on a raw DBF raises "not applicable".
  D-04: read() gains company= param; no filesystem-path arg ever added.

RESEARCH.md Pitfall references:
  Pitfall 1: TemporaryDirectory lifecycle is owned by read() in __init__.py --
             _safe_extract_zip receives an already-created extract_dir.
  Pitfall 2: Normalize entry name backslashes before resolve() check.
  Pitfall 4: Case-insensitive file matching -- compare lowercased names.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from contaplus_reader.models import ContaPlusReadError


def _safe_extract_zip(raw: bytes, extract_dir: Path) -> None:
    """Extract ZIP bytes to extract_dir, rejecting any zip-slip entries.

    Per-entry zip-slip check: normalize backslashes then use
    target.relative_to(base) before calling zf.extract().
    Raises ContaPlusReadError on any entry that would escape the temp dir.

    Args:
        raw: ZIP file contents as bytes.
        extract_dir: Directory to extract into (must already exist).

    Raises:
        ContaPlusReadError: If any entry name escapes extract_dir (zip-slip),
                            or if the bytes are not a valid ZIP file.
    """
    try:
        base = extract_dir.resolve()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for member in zf.infolist():
                # Pitfall 2: normalize Windows backslash before resolve
                clean = member.filename.replace("\\", "/")
                target = (extract_dir / clean).resolve()
                try:
                    target.relative_to(base)
                except ValueError:
                    raise ContaPlusReadError(
                        row_index=-1,
                        column=None,
                        message=f"Unsafe ZIP entry: {member.filename!r}",
                    )
                zf.extract(member, extract_dir)
    except ContaPlusReadError:
        raise  # re-raise structured errors unchanged
    except (zipfile.BadZipFile, OSError) as exc:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Invalid or unreadable ZIP file: {exc}",
            original=exc,
        ) from exc


def _resolve_company_diario(
    extract_dir: Path,
    company: str | None,
) -> Path:
    """Find the DIARIO.DBF path for the selected company.

    Single-company ZIP without selector: returns the one diario path.
    Single-company ZIP with matching selector: returns the one diario path.
    Single-company ZIP with wrong selector: raises listing available dir names.
    Multi-company ZIP without selector: raises listing available dir names.
    Multi-company ZIP with matching selector: returns matching diario path.
    Multi-company ZIP with non-matching selector: raises listing available names.
    No DIARIO.DBF found at all: raises ContaPlusReadError.

    Args:
        extract_dir: Root directory of extracted ZIP contents.
        company: Company directory name to select, or None for auto-detect.

    Returns:
        Path to the selected DIARIO.DBF file.

    Raises:
        ContaPlusReadError: On disambiguation failure or missing DIARIO.DBF.
    """
    # Pitfall 4: case-insensitive match for DIARIO.DBF
    diarios = [
        p for p in extract_dir.rglob("*")
        if p.is_file() and p.name.lower() == "diario.dbf"
    ]

    if not diarios:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message="No DIARIO.DBF found in ZIP",
        )

    if len(diarios) == 1:
        if company is not None:
            # D-03: validate selector even for single-company ZIP
            if diarios[0].parent.name.lower() != company.lower():
                available = [diarios[0].parent.name]
                raise ContaPlusReadError(
                    row_index=-1,
                    column=None,
                    message=f"Company {company!r} not found; available: {available}",
                )
        return diarios[0]

    # Multi-company: company selector is required (D-02)
    company_dirs = sorted({p.parent.name for p in diarios})
    if company is None:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Multi-company ZIP: pass --company to select one of {company_dirs}",
        )
    matches = [p for p in diarios if p.parent.name.lower() == company.lower()]
    if len(matches) != 1:
        raise ContaPlusReadError(
            row_index=-1,
            column=None,
            message=f"Company {company!r} not found; available: {company_dirs}",
        )
    return matches[0]


def _find_sibling_dbf(diario_path: Path, basename_lower: str) -> Path | None:
    """Find a sibling DBF file in the same directory as DIARIO.DBF (case-insensitive).

    Used to locate SUBCTA.DBF, grupos.dbf, usuarios.dbf, empresa.dbf relative
    to the DIARIO.DBF that was selected for the company (D-05).

    Args:
        diario_path: Path to the DIARIO.DBF file.
        basename_lower: Lowercase filename to search for (e.g. "subcta.dbf").

    Returns:
        Path to the sibling file, or None if not found.
    """
    for candidate in diario_path.parent.iterdir():
        if candidate.is_file() and candidate.name.lower() == basename_lower:
            return candidate
    return None
