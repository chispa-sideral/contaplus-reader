# Phase 2: ZIP & Subaccounts - Research

**Researched:** 2026-05-16
**Domain:** Python zipfile, dbfread, openpyxl multi-sheet, ContaPlus ZIP structure
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ZIP Input & Discovery**
- D-01: ZIP detection by magic-byte sniffing (`0x50` branch flips from reject to accept). No suffix-based detection.
- D-02: Multi-company disambiguation by raw directory name (`Emp01`, `Emp02`, ...). Case-insensitive matching. Single-company ZIP without selector uses the one company. Multi-company without selector raises `ContaPlusReadError` listing available directory names.
- D-03: Selector supplied against a single-company ZIP validates against that company; mismatch raises. Selector supplied against a raw DBF input raises ("selector not applicable").

**Read API & Result Model**
- D-04: `read()` gains `company: str | None = None` parameter additively. No filesystem path argument ever.
- D-05: `ContaPlusData` gains `.subcta`, `.empresa`, `.grupos`, `.usuarios` attributes (each its own typed result type). Container return type stays stable.
- D-06: Uniform strict. Table present-but-unreadable aborts the whole conversion. Table absent from archive is silent (no sheet, no error).

**CLI**
- D-07: `--company` flag pulled into Phase 2. `CLI-02` reassigned Phase 4 -> Phase 2.
- D-08: Multi-company ZIP without `--company` surfaced as Rich error panel, exit 1.

**Journal Name Enrichment**
- D-09: `JournalRow` gains `subcuenta_nombre: str | None = None` (additive, defaulted).
- D-10: Enrichment subcuenta-level only. `cuenta` stays code-only.
- D-11: Enrichment best-effort at row/lookup level. Missing key -> `None`. Missing table -> all `None`. Present-but-unreadable SUBCTA still aborts (D-06).

**Multi-Sheet XLSX**
- D-12: Renderer becomes data-driven, one sheet per populated table on `ContaPlusData`.
- D-13: Full dump. Every field, DBF field order. Non-journal sheet headers are raw DBF field names.
- D-14: Spanish sheet tabs: `Diario`, `Subcuentas`, `Empresa`, `Grupos`, `Usuarios`.
- D-15: `Diario` sheet gains name column from `subcuenta_nombre` immediately after `Subcuenta`.

**Table Readers**
- D-16: Typed readers for all four tables with defensive field-name resolution via `_pick_column` candidate-list pattern.
- D-17: Phase 2 research MUST include `pii-test-data/` schema-discovery before typed readers are committed.
- D-18: `usuarios.dbf` extracted in full including credentials. Local-only, no privacy concern.

### Claude's Discretion
- Exact new type names and attribute names on `ContaPlusData`, the company-selector parameter name, and module/package layout.
- ZIP extraction mechanism: extract-all-to-temp-dir vs. per-entry `bytes_to_tmppath`. `dbfread` is path-only, so some bridging is unavoidable.
- Exact journal name-column header text (D-15) and multi-sheet ordering.
- CLI one-line summary format for multi-sheet conversion.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INPUT-02 | Reader accepts a ContaPlus backup `.zip` as bytes or a file-like object | `zipfile.ZipFile(BytesIO(...))` confirmed working; see §ZIP reading |
| INPUT-04 | ZIP extraction works from an in-memory buffer and is zip-slip-safe | `target.relative_to(base)` pattern confirmed; all 101 real archive entries pass; 4 attack vectors correctly blocked |
| INPUT-05 | Reader recursively locates tables inside a backup ZIP regardless of nesting depth | `rglob` or `extractall` + recursive walk; real archives are flat (one `EmpNN/` dir) but recursive walk is still correct |
| INPUT-06 | Multi-company ZIP disambiguated by caller-supplied company selector | Case-insensitive match on parent dir name; confirmed with real multi-company archive (4 companies: Emp64, Emp65, Emp66, Emp68) |
| TABL-01 | Typed reader for `SUBCTA.DBF` with defensive field-name resolution | VERIFIED: field schema identical across all 4 single-company archives. Key fields: `cod` C(12), `titulo` C(40). Full schema in §SUBCTA Schema. |
| TABL-02 | Typed readers for `grupos.dbf`, `usuarios.dbf`, `empresa.dbf` | CRITICAL FINDING: none of these files exist in any of the 5 real archives. See §Critical Finding: Missing Group Tables. |
| API-05 | Journal result enriched with subaccount names from `SUBCTA.DBF` | Lookup `cod` -> `titulo`; best-effort per D-11; `subcuenta_nombre: str | None = None` on `JournalRow` |
| CLI-02 | CLI selects a company in a multi-company backup via a flag | `--company` added to `contaplus2xlsx`; Typer `Option` with Rich error panel on missing selector |
</phase_requirements>

---

## Summary

Phase 2 extends the reader from a single `DIARIO.DBF` to a full ContaPlus backup `.zip`. The research confirms all the core technical mechanisms are sound and available in the existing stack.

The ZIP reading path is straightforward: `zipfile.ZipFile` accepts a `BytesIO` directly, the zip-slip validation pattern (`target.relative_to(base)`) blocks all known attack vectors, and `dbfread` reads without its CDX sibling when `ignore_missing_memofile=True`. The extraction strategy of "extract all to a `TemporaryDirectory` then walk" (the tw-contaplus pattern) preserves CDX siblings beside DBF files — important for correctness even though CDX absence doesn't crash dbfread. Alternatively, per-entry extraction to a temp file (the `bytes_to_tmppath` pattern) also works, and avoids extracting 61+ files when only 2-3 are needed.

The most significant research finding — and a design-impacting one — is that **`grupos.dbf`, `usuarios.dbf`, and `empresa.dbf` are absent from all 5 real ContaPlus backup archives**. These files were mentioned in the original SEED as "some installs include" group metadata; they appear to be from an older ContaPlus installation type or a group-level backup that is distinct from the per-company backups we have. This has direct consequences for the typed readers and the multi-sheet workbook: Phase 2 should implement the TABL-02 readers as purely defensive/optional — present-when-found, no-error-when-absent — which is already consistent with D-06 ("table simply absent from the archive is fine").

The SUBCTA schema is completely consistent across all 4 single-company archives and all companies in the multi-company archive. The primary key field is `cod` (not `codigo`), and the description field is `titulo` (not `descrip`). The SEED's mention of `CODIGO`/`COD` and `DESCRIP`/`TITULO` variants is validated: the real archives use `cod` and `titulo`. The candidate list for defensive resolution should prefer `cod` first, `codigo` second; `titulo` first, `descrip` second.

**Primary recommendation:** Use `TemporaryDirectory` + `extractall` + `rglob` walk (the tw-contaplus pattern) rather than per-entry extraction. Reasons: CDX siblings are co-located for free, the zip-slip check runs per-entry before extraction, and no extra state management is needed. The per-entry approach requires tracking which siblings to also extract. SUBCTA is always in the same company directory as DIARIO, so one `rglob` finds both.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ZIP bytes acceptance and sniffing | Library (`_sniffer.py`) | — | Bytes-first API; sniffer already has the `0x50` branch |
| Zip-slip-safe extraction | Library (`_zip.py` or `__init__.py`) | — | Security concern belongs at extraction boundary, not CLI |
| Company directory discovery/disambiguation | Library (new `_zip.py` module) | — | Same logic needed by CLI and future PWA |
| SUBCTA lookup dict construction | Library (`_reader.py` or `_subcta.py`) | — | Pure reader concern; enrichment applied at journal-build time |
| Journal row enrichment (`subcuenta_nombre`) | Library (`_reader.py`) | — | Applied during journal construction, not post-hoc |
| Multi-sheet XLSX rendering | Library (`xlsx.py`) | — | Renderer is shared; stays in library per XLSX-04 |
| `--company` CLI flag | CLI (`cli.py`) | — | User-facing flag; passes selector into `read()` |
| Rich error panel for missing `--company` | CLI (`cli.py`) | — | Presentation concern; follows D-08/D-17 pattern |
| Typed result types for SUBCTA/grupos/etc. | Library (`models.py`) | — | Same self-contained result model principle as Phase 1 |

---

## Standard Stack

### Core (no new runtime dependencies needed)

All Phase 2 work uses stdlib `zipfile`, `tempfile`, and the existing runtime dependencies. No new packages are required.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zipfile` | stdlib | ZIP reading, extraction, entry validation | Standard library; `ZipFile(BytesIO)` confirmed working [VERIFIED: Python 3.13 docs] |
| `tempfile.TemporaryDirectory` | stdlib | Scoped temp dir for ZIP extraction | Context manager; auto-cleanup on exit or exception; used in tw-contaplus [VERIFIED: codebase] |
| `dbfread` | >=2.0.7 (current install) | DBF reading from temp path | Already runtime dep; `ignore_missing_memofile=True` covers CDX absence [VERIFIED: codebase] |
| `openpyxl` | >=3.1.5 (current install) | Multi-sheet workbook via `wb.create_sheet()` | Already runtime dep; `create_sheet()` confirmed working [VERIFIED: live test] |
| `typer` | 0.25.1 (current install) | `--company` CLI option via `typer.Option` | Already runtime dep [VERIFIED: codebase] |

### No New Dependencies

Phase 2 requires zero new PyPI packages. All needed functionality is in stdlib or existing deps.

**Package Legitimacy Audit:** Not applicable — no new packages installed.

---

## Critical Finding: Missing Group Tables (D-17 Schema Discovery)

**D-17 mandates schema discovery in `pii-test-data/` before typed readers are committed. This discovery has been completed.**

### ZIP Structure Across All 5 Real Archives

| Archive | Companies | Nesting | DIARIO.dbf | SubCta.dbf | grupos.dbf | usuarios.dbf | empresa.dbf |
|---------|-----------|---------|-----------|------------|------------|--------------|-------------|
| MELO25.zip | 1 (Emp68) | `EmpNN/file` | `Emp68/Diario.dbf` | `Emp68/SubCta.dbf` | ABSENT | ABSENT | ABSENT |
| cmmarina25.zip | 1 (Emp64) | `EmpNN/file` | `Emp64/Diario.dbf` | `Emp64/SubCta.dbf` | ABSENT | ABSENT | ABSENT |
| lluntania25.zip | 1 (Emp66) | `EmpNN/file` | `Emp66/Diario.dbf` | `Emp66/SubCta.dbf` | ABSENT | ABSENT | ABSENT |
| spaimedic25.zip | 1 (Emp65) | `EmpNN/file` | `Emp65/Diario.dbf` | `Emp65/SubCta.dbf` | ABSENT | ABSENT | ABSENT |
| multi-company.zip | 4 (Emp64–68) | `EmpNN/file` | `EmpNN/Diario.dbf` (×4) | `EmpNN/SubCta.dbf` (×4) | ABSENT | ABSENT | ABSENT |

**Key observations:**
- All 5 archives use `EmpNN/` (no `Datos\EmpNN\` nesting in this dataset).
- All entry names use **mixed case** (`SubCta.dbf`, `Diario.dbf`) — case-insensitive matching is mandatory.
- All archives are single-level: `EmpNN/<files>`, no further nesting.
- `grupos.dbf`, `usuarios.dbf`, and `empresa.dbf` are **absent from all 5 real archives**. [VERIFIED: pii-test-data enumeration]
- The SEED note "some installs include adjacent group metadata files" refers to a different ContaPlus installation type (likely group-level backup, not per-company). These files may appear in archives from older ContaPlus versions or group-level exports.

**Consequence for TABL-02:** The typed readers for `grupos`, `usuarios`, and `empresa` MUST be written defensively — absent table is not an error (D-06). Since no real schemas were found, the field specs for synthetic test fixtures must be minimal placeholders. The `dbf` spec for synthetic fixtures can use a generic field structure. If these tables appear in a future real archive, the `_pick_column`-style defensive resolution will handle field name variants.

**Synthetic fixture field specs (minimum viable schemas for testing):**
- `grupos.dbf`: `COD C(10,0); DESCRIP C(40,0)` (generic code+description pattern seen in `depart.dbf`, `concep.dbf`)
- `usuarios.dbf`: `CODIGO C(10,0); NOMBRE C(40,0); CLAVE C(20,0)` (plausible user table with credential field per D-18)
- `empresa.dbf`: `CODIGO C(10,0); NOMBRE C(60,0); NIF C(15,0)` (company name/NIF pattern)

These synthetic schemas are `[ASSUMED]` — no real data confirms them. The reader must not hard-fail on field absence; `_pick_column` handles this.

---

## SUBCTA Schema (VERIFIED across 4 archives)

All 4 single-company archives and all 4 companies in the multi-company archive have **identical SUBCTA schemas**. [VERIFIED: pii-test-data enumeration]

### Key Fields for Phase 2 (name enrichment)

| Field | Type | Width | Purpose |
|-------|------|-------|---------|
| `cod` | C | 12 | Subaccount code (primary key for journal join) |
| `titulo` | C | 40 | Subaccount name/description |
| `nif` | C | 15 | Tax ID |
| `domicilio` | C | 35 | Address |
| `poblacion` | C | 25 | City |
| `provincia` | C | 20 | Province |

**Field name variants for defensive resolution:**
- Code field: `cod` (found in all real archives), `codigo` (SEED mentions as variant — not seen in real data but include for robustness)
- Description field: `titulo` (found in all real archives), `descrip` (SEED mentions as variant — not seen but include)
- NIF field: `nif` (found in all real archives), `cif` (older variant per SEED)

**Candidate lists for `_pick_column`:**
```python
_SUBCTA_COD_CANDIDATES = ("cod", "codigo")
_SUBCTA_TITULO_CANDIDATES = ("titulo", "descrip")
_SUBCTA_NIF_CANDIDATES = ("nif", "cif")
```

The full SUBCTA schema is wide (~130+ fields including per-month debit/credit accumulators `sdb01`–`shb12`, euro equivalents `sdb01eu`–`shb12eu`). The typed reader only needs `cod` and `titulo` for the enrichment lookup. Full dump (D-13) emits all fields.

### File Name Casing
Real archives use `SubCta.dbf` (mixed case). Case-insensitive matching via `.lower() == 'subcta.dbf'` is mandatory. No `XSUBCTA.DBF` variant found in any of the 5 archives.

---

## Architecture Patterns

### System Architecture Diagram

```
bytes / BinaryIO (ZIP)
        |
        v
  sniff() [_sniffer.py]
   0x50 -> ZipFormat (Phase 2: accept)
   0xNN -> DbfFormat (Phase 1: pass through)
        |
        v
[ZipFormat path]                   [DbfFormat path (unchanged)]
  |                                   |
  v                                   v
_extract_zip(data, company)      bytes_to_tmppath(data)
  TemporaryDirectory                  |
  safe_extractall (zip-slip check)    v
  rglob for diario.dbf           _read_dbf_path(path) -> ContaPlusJournal
  company disambiguation         ContaPlusData(journal=...)
  |
  +-- find diario.dbf path
  +-- find subcta.dbf path (optional)
  +-- find grupos/usuarios/empresa paths (optional)
  |
  v
build_subcta_lookup(subcta_path) -> dict[str, str]  # cod -> titulo
  |
  v
_read_dbf_path(diario_path,        _read_table_raw(path) -> list[dict]
  subcta_lookup=lookup)              (for grupos/usuarios/empresa -- full dump)
  -> ContaPlusJournal                |
  (rows with subcuenta_nombre)       v
                              ContaPlusData extended:
                                .journal
                                .subcta (SubctaTable | None)
                                .grupos (GenericTable | None)
                                .usuarios (GenericTable | None)
                                .empresa (GenericTable | None)
        |
        v
  render(data) -> bytes  [xlsx.py]
    ws "Diario"     -- journal rows + Descripcion column
    ws "Subcuentas" -- SUBCTA all fields
    ws "Grupos"     -- if present
    ws "Usuarios"   -- if present
    ws "Empresa"    -- if present
```

### Recommended Module Structure

```
src/contaplus_reader/
├── __init__.py          # read() gains company= param; dispatches to _zip or _bridge
├── _sniffer.py          # flip 0x50 branch: accept ZIP
├── _bridge.py           # unchanged (bytes_to_tmppath)
├── _reader.py           # gains subcta_lookup param; _read_dbf_path enriches rows
├── _zip.py              # NEW: _extract_zip(), zip-slip check, company resolution
├── _subcta.py           # NEW: read_subcta_lookup() -> dict[str, str | None]
├── models.py            # JournalRow += subcuenta_nombre; ContaPlusData += 4 attrs
├── xlsx.py              # render() replaces render_journal(); multi-sheet
└── cli.py               # --company option; ZIP success summary
```

Alternative: fold `_subcta.py` into `_reader.py` as a private helper. The reader already owns all the DBF-parsing logic; the lookup is a one-shot dict built from a single DBF pass. The planner can decide.

### Pattern 1: ZIP Extraction with Zip-Slip Guard

```python
# Source: tw-contaplus/read_dbf.py _safe_extractall (adapted for bytes-first API)
import io, zipfile, tempfile
from pathlib import Path

def _extract_zip(
    data: bytes | io.IOBase,
    *,
    company: str | None = None,
) -> tuple[Path, ...]:  # returns (diario_path, subcta_path | None, ...)
    raw = data if isinstance(data, bytes) else data.read()
    bio = io.BytesIO(raw)
    tmpdir = tempfile.TemporaryDirectory(prefix="contaplus_")
    extract_dir = Path(tmpdir.name)
    base = extract_dir.resolve()

    with zipfile.ZipFile(bio) as zf:
        for member in zf.infolist():
            # Normalize Windows backslash (seen in some archives)
            clean = member.filename.replace("\\", "/")
            target = (extract_dir / clean).resolve()
            try:
                target.relative_to(base)
            except ValueError:
                raise ContaPlusReadError(
                    row_index=-1, column=None,
                    message=f"Unsafe ZIP entry escapes temp dir: {member.filename!r}",
                )
            zf.extract(member, extract_dir)

    # Walk for all DIARIO.DBF (case-insensitive)
    diarios = [p for p in extract_dir.rglob("*") if p.name.lower() == "diario.dbf"]
    # ... company disambiguation, SUBCTA/group table discovery ...
    return tmpdir, diarios, ...
```

**Critical:** `TemporaryDirectory` must be kept alive while callers read from the extracted paths. Return it (or use a context manager) so it is not garbage-collected prematurely.

### Pattern 2: SUBCTA Lookup Dict

```python
# Source: pii-test-data schema discovery (this research session)
def _build_subcta_lookup(subcta_path: Path) -> dict[str, str | None]:
    """Build cod -> titulo lookup from SUBCTA.DBF. Returns empty dict if path is None."""
    try:
        table = DBF(str(subcta_path), lowernames=True, encoding="cp850",
                    ignore_missing_memofile=True)
        field_set = {f.name for f in table.fields}
        cod_col = _pick_column(field_set, _SUBCTA_COD_CANDIDATES, kind="subcta.cod")
        titulo_col = _pick_column(field_set, _SUBCTA_TITULO_CANDIDATES, kind="subcta.titulo")
        return {
            rec[cod_col].rstrip(): (rec[titulo_col] or "").rstrip() or None
            for rec in table
            if rec.get(cod_col)
        }
    except ContaPlusReadError:
        raise  # present-but-unreadable -> abort (D-06)
    except (struct.error, ValueError, OSError, UnicodeDecodeError) as exc:
        raise ContaPlusReadError(row_index=-1, column=None,
                                  message=f"SUBCTA.DBF read error: {exc}",
                                  original=exc) from exc
```

### Pattern 3: Journal Row Enrichment

```python
# D-09/D-10/D-11 - subcuenta_nombre is additive, defaulted, best-effort
# Applied in _read_dbf_path after subcuenta is validated
subcuenta_nombre = subcta_lookup.get(subcuenta)  # None if key absent (D-11)

rows.append(JournalRow(
    fecha=fecha_raw,
    cuenta=cuenta,
    subcuenta=subcuenta,
    debe=debe,
    haber=haber,
    concepto=concepto,
    subcuenta_nombre=subcuenta_nombre,  # D-09 new field
))
```

### Pattern 4: Data-Driven Multi-Sheet Renderer

```python
# Source: openpyxl multi-sheet confirmed working (this research session)
def render(data: ContaPlusData) -> bytes:
    wb = Workbook()

    # Sheet order: Diario first (journal), then secondary tables
    _render_journal_sheet(wb.active, data.journal)  # wb.active is already sheet 1

    if data.subcta is not None:
        _render_generic_sheet(wb.create_sheet("Subcuentas"), data.subcta)
    if data.empresa is not None:
        _render_generic_sheet(wb.create_sheet("Empresa"), data.empresa)
    if data.grupos is not None:
        _render_generic_sheet(wb.create_sheet("Grupos"), data.grupos)
    if data.usuarios is not None:
        _render_generic_sheet(wb.create_sheet("Usuarios"), data.usuarios)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

### Pattern 5: CLI `--company` Option

```python
# D-07/D-08: --company flag; Rich error panel when multi-company requires it
@app.command()
def main(
    input_file: Annotated[Path, typer.Argument(...)],
    output_file: Annotated[Path, typer.Argument(...)],
    company: Annotated[str | None, typer.Option(
        "--company",
        help="Company directory name (e.g. Emp01) for multi-company ZIP backups",
    )] = None,
    force: Annotated[bool, typer.Option("--force", "--overwrite", ...)] = False,
) -> None:
    ...
    data = read(raw_bytes, source_name=str(input_file), company=company)
```

### Anti-Patterns to Avoid

- **Holding TemporaryDirectory only in a local variable:** If the tmpdir object is not kept alive (e.g., returned paths are used after the context exits), Windows will delete the directory while paths are still being read. Pass the tmpdir ownership to the caller explicitly.
- **Using `zipfile.extractall()` without per-entry validation:** The stdlib `extractall` has no `filter=` parameter (Python 3.13). Iterate `infolist()` manually.
- **Hardcoding `CODIGO` or `DESCRIP` for SUBCTA:** Real archives use `cod` and `titulo`. The candidate list handles variants.
- **Using `XSUBCTA.DBF`:** Not found in any real archive. `SUBCTA.DBF`/`SubCta.dbf` (case-insensitive) is the correct target.
- **Assuming `grupos.dbf`/`usuarios.dbf`/`empresa.dbf` are present:** Absent from all 5 real archives. Treat as optional.
- **Looking for group tables at archive root:** All files are inside `EmpNN/` directories. Group tables (if they ever appear) would also be inside a company dir, not at the archive root.
- **Using `io.BytesIO` instead of a real temp file for dbfread:** `dbfread` requires a filesystem path. `BytesIO` cannot be passed to `DBF()`. Must bridge via temp file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ZIP path traversal defense | Custom path parsing | `target.relative_to(base)` (stdlib pathlib) | `Path.resolve()` + `relative_to` handles `..`, absolute paths, and platform-specific separators |
| ZIP reading from bytes | Custom ZIP parser | `zipfile.ZipFile(io.BytesIO(raw))` | stdlib; handles all ZIP format variants |
| Temp dir lifecycle | Custom cleanup | `tempfile.TemporaryDirectory` context manager | Auto-cleans on exit and exception; OS-safe on Windows |
| Multi-sheet workbook | Per-sheet file merge | `openpyxl.Workbook.create_sheet()` | Already in stack; confirmed working |
| SUBCTA lookup | External lookup service | In-memory `dict[str, str]` from single DBF pass | All data local; dict is O(1) lookup; ~35–342 records across real archives |

**Key insight:** The entire Phase 2 feature is achievable with stdlib + existing deps. The stdlib `zipfile` module handles everything from bytes reading to safe extraction.

---

## Runtime State Inventory

Not applicable — Phase 2 is a pure code addition. No renames, no migrations, no stored state to update.

---

## Common Pitfalls

### Pitfall 1: TemporaryDirectory Premature Cleanup
**What goes wrong:** `TemporaryDirectory` is created inside a function, paths are returned, but the `TemporaryDirectory` object is garbage-collected before callers finish reading from the paths.
**Why it happens:** Python's reference counting collects the `TemporaryDirectory` object when its name goes out of scope; on Windows, this triggers `shutil.rmtree` immediately.
**How to avoid:** Return the `TemporaryDirectory` object alongside the paths, or use a context manager that keeps it alive for the full extraction-read-render pipeline. The `__init__.py` `read()` function should own the lifecycle: create tmpdir, extract, read all tables, close tmpdir.
**Warning signs:** `FileNotFoundError` on a temp path that was valid moments before.

### Pitfall 2: ZIP Entry Name Backslash on Windows
**What goes wrong:** `zipfile.ZipInfo.filename` on Python/Windows may contain backslashes in some archives. `Path(extract_dir / member.filename)` constructs an incorrect path on Windows when the entry name has backslashes that look like directory separators.
**Why it happens:** Some ContaPlus backups were created on Windows and stored `Emp01\DIARIO.DBF` as the entry name.
**How to avoid:** Normalize before `relative_to` check: `clean = member.filename.replace("\\", "/")`. The real archives use forward slashes, but the normalization is a cheap safety guard. [VERIFIED: pii-test-data uses forward slashes]
**Warning signs:** `target.relative_to(base)` raises `ValueError` on valid-looking entries.

### Pitfall 3: CDX File Absence With Per-Entry Extraction
**What goes wrong:** Per-entry extraction (extracting only `diario.dbf`) leaves the CDX sibling behind. `dbfread` silently ignores missing CDX/FPT via `ignore_missing_memofile=True` but this option name only mentions memofile — some DBF variants fail without CDX.
**Why it happens:** Misreading `ignore_missing_memofile` as covering CDX too.
**How to avoid:** `ignore_missing_memofile=True` DOES cover CDX in dbfread 2.0.7 [VERIFIED: live test with SUBCTA without CDX: 35 records read cleanly]. However, extracting-all-to-temp-dir is simpler and avoids the question entirely.
**Warning signs:** Error during DBF read after per-entry extraction.

### Pitfall 4: Case-Sensitive File Matching in ZIP
**What goes wrong:** Checking `entry.name == "DIARIO.DBF"` misses `Diario.dbf`, `diario.dbf`.
**Why it happens:** ContaPlus stores files with mixed case (`SubCta.dbf`, `Diario.dbf`). [VERIFIED: all real archives use `Diario.dbf` / `SubCta.dbf`]
**How to avoid:** Always normalize: `entry.filename.replace("\\", "/").lower()` and compare to `"diario.dbf"`, `"subcta.dbf"`.
**Warning signs:** Zero DIARIO.DBF found in an archive that obviously contains one.

### Pitfall 5: `JournalRow` Frozen Dataclass Adding Fields
**What goes wrong:** `@dataclass(frozen=True)` with a new field `subcuenta_nombre` added — `frozen=True` still works fine, but existing callers constructing `JournalRow` positionally will break.
**Why it happens:** `JournalRow` is a frozen dataclass; adding a new required field without a default breaks callers.
**How to avoid:** D-09 specifies `subcuenta_nombre: str | None = None` — the default `None` makes the new field optional. All existing `JournalRow(...)` calls that don't pass `subcuenta_nombre` continue to work. Confirm the field is keyword-only or placed after existing fields.
**Warning signs:** `TypeError: JournalRow() takes N positional arguments`.

### Pitfall 6: `ZipFile(BytesIO)` Exhausted After Read
**What goes wrong:** After calling `data.read()` on a file-like input and wrapping in `BytesIO`, the original stream is positioned at EOF. If `data` is passed by reference and re-read elsewhere, it returns empty bytes.
**Why it happens:** Stream position is not reset.
**How to avoid:** The `_extract_zip` function should call `data.read()` once, store as `raw: bytes`, then construct `io.BytesIO(raw)`. The `read()` entry point should handle both `bytes` (no read needed) and `BinaryIO` (read once). The existing `bytes_to_tmppath` pattern already handles this correctly — model after it.

---

## Code Examples

### ZIP-Slip-Safe Extraction from BytesIO

```python
# Source: tw-contaplus/read_dbf.py _safe_extractall (ported + adapted)
# Verified against 101 real archive entries and 4 simulated attack vectors
import io, zipfile, tempfile
from pathlib import Path
from contaplus_reader.models import ContaPlusReadError

def _safe_extract_zip(raw: bytes, extract_dir: Path) -> None:
    """Extract ZIP bytes to extract_dir, rejecting any zip-slip entries."""
    base = extract_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for member in zf.infolist():
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
```

### Company Directory Resolution

```python
# Source: tw-contaplus/read_dbf.py _resolve_dbf_in_zip (adapted for D-02/D-03)
def _resolve_company_diario(
    extract_dir: Path,
    company: str | None,
) -> Path:
    """Find the DIARIO.DBF for the selected company."""
    diarios = [
        p for p in extract_dir.rglob("*")
        if p.name.lower() == "diario.dbf"
    ]
    if not diarios:
        raise ContaPlusReadError(row_index=-1, column=None,
                                  message="No DIARIO.DBF found in ZIP")

    if len(diarios) == 1:
        if company is not None:
            # D-03: validate selector even for single-company (catches typos)
            if diarios[0].parent.name.lower() != company.lower():
                available = [diarios[0].parent.name]
                raise ContaPlusReadError(
                    row_index=-1, column=None,
                    message=f"Company {company!r} not found; available: {available}",
                )
        return diarios[0]

    # Multi-company
    company_dirs = sorted({p.parent.name for p in diarios})
    if company is None:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"Multi-company ZIP: pass --company to select one of {company_dirs}",
        )
    matches = [p for p in diarios if p.parent.name.lower() == company.lower()]
    if len(matches) != 1:
        raise ContaPlusReadError(
            row_index=-1, column=None,
            message=f"Company {company!r} not found; available: {company_dirs}",
        )
    return matches[0]
```

### Finding SUBCTA and Group Tables Relative to DIARIO

```python
# SUBCTA is in the same directory as DIARIO (confirmed in all real archives)
def _find_sibling_dbf(diario_path: Path, basename_lower: str) -> Path | None:
    """Find a sibling DBF in the same directory as DIARIO.DBF (case-insensitive)."""
    parent = diario_path.parent
    for candidate in parent.iterdir():
        if candidate.is_file() and candidate.name.lower() == basename_lower:
            return candidate
    return None

# Usage:
subcta_path = _find_sibling_dbf(diario_path, "subcta.dbf")   # None if absent
grupos_path = _find_sibling_dbf(diario_path, "grupos.dbf")    # None if absent
```

### Synthetic ZIP Fixture for Tests

```python
# Pattern: extend conftest.py (mirrors tw-contaplus conftest lines 173-210)
@pytest.fixture(scope="session")
def single_company_zip(cp850_basic_dbf: Path,
                       tmp_path_factory: pytest.TempPathFactory) -> Path:
    zip_dir = tmp_path_factory.mktemp("single_company_zip")
    zip_path = zip_dir / "backup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(cp850_basic_dbf, arcname="Emp01/DIARIO.DBF")
        # Add synthetic SubCta.dbf sibling for enrichment tests
        subcta_path = _build_subcta_dbf(zip_dir / "SubCta.dbf", [
            {"cod": "4300000", "titulo": "Cliente XYZ"},
        ])
        zf.write(subcta_path, arcname="Emp01/SubCta.dbf")
    return zip_path
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `zipfile.extractall(filter=...)` | `zipfile.extractall` has no `filter=`; manual per-entry validation | Python 3.13 (tarfile got `filter=`, zipfile did not) | Must validate manually with `relative_to` |
| `zipfile` path-only input | `zipfile.ZipFile(io.BytesIO(raw))` | Python stdlib always supported this | Enables bytes-first API with no temp file for the ZIP container |
| `tempfile.NamedTemporaryFile` | Use for individual DBF entries | Phase 1 established this pattern | Works on Windows (delete=False + explicit unlink) |
| `TemporaryDirectory` for ZIP extraction | Use for whole-archive extraction | Established in tw-contaplus | Auto-cleanup; co-locates CDX siblings |

**Deprecated/outdated:**
- `extractall(path)` without per-entry check: zip-slip unsafe, do not use.
- Checking `SUBCTA.DBF` for `CODIGO`/`DESCRIP` field names: real archives use `cod`/`titulo`. Both are in the candidate list for robustness, but don't assume `CODIGO`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `grupos.dbf` field spec: `COD C(10,0); DESCRIP C(40,0)` | Critical Finding | Typed reader would fail on real `grupos.dbf` if it exists with different schema; mitigated by D-06 + `_pick_column` defensive resolution |
| A2 | `usuarios.dbf` field spec: `CODIGO C(10,0); NOMBRE C(40,0); CLAVE C(20,0)` | Critical Finding | Same as A1; D-18 requires full dump but D-06 aborts if unreadable; worst case: hard failure on a real archive with `usuarios.dbf` |
| A3 | `empresa.dbf` field spec: `CODIGO C(10,0); NOMBRE C(60,0); NIF C(15,0)` | Critical Finding | Same as A1/A2 |
| A4 | Group tables (grupos/usuarios/empresa) live inside `EmpNN/` dir, not at archive root | Critical Finding | If they are at root, `_find_sibling_dbf` won't find them; needs a root-level search instead |
| A5 | `ignore_missing_memofile=True` suppresses CDX-missing warnings (not just FPT/DBT) | Pitfall 3 | Confirmed empirically for SubCta.dbf; assumed for grupos/usuarios/empresa synthetic DBFs |

---

## Open Questions

1. **Where do `grupos.dbf`, `usuarios.dbf`, `empresa.dbf` live in archives that DO contain them?**
   - What we know: absent from all 5 real archives; SEED says "some installs include adjacent group metadata"
   - What's unclear: are they in `EmpNN/` or at the archive root?
   - Recommendation: implement search in `EmpNN/` directory (same as SUBCTA); if a future real archive has them at root, the `_find_sibling_dbf` helper is easy to extend. Plan a "search sibling dir AND root" fallback.

2. **Should `TemporaryDirectory` be owned by `read()` or by a private extraction function?**
   - What we know: tmpdir must outlive all DBF reads; the entire pipeline (extract, build lookup, read journal, read secondary tables) must complete before cleanup
   - What's unclear: planner decision — `read()` owns lifecycle, or extraction function returns (tmpdir, paths) tuple
   - Recommendation: `read()` owns the tmpdir via a `with tempfile.TemporaryDirectory() as tmpdir:` block enclosing the entire pipeline.

3. **Does the `render_journal()` name become `render()` or does `render_journal()` remain as an alias?**
   - What we know: D-12 says the renderer "generalizes"; Phase 1 tests import `render_journal`
   - What's unclear: breaking-change policy for Phase 2
   - Recommendation: Add `render(data: ContaPlusData)` as the new entrypoint; keep `render_journal(journal: ContaPlusJournal)` as a convenience wrapper calling `render(ContaPlusData(journal=journal))` for backward compatibility in Phase 1 tests.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.13 | — |
| `zipfile` | ZIP extraction | ✓ | stdlib | — |
| `tempfile` | Temp dir/file | ✓ | stdlib | — |
| `dbfread` | DBF reading | ✓ | 2.0.7 | — |
| `openpyxl` | Multi-sheet XLSX | ✓ | 3.1.5 | — |
| `typer` | CLI `--company` | ✓ | 0.25.1 | — |
| `rich` | Rich error panels | ✓ | 15.0.0 | — |
| `dbf` (ethanfurman) | Synthetic fixtures | ✓ | 0.99.11 | — |
| `pytest` | Test runner | ✓ | 8.x | — |

**Missing dependencies with no fallback:** None.
**No new packages are required for Phase 2.**

Note: `pyproject.toml` still declares `typer[all]>=0.13` but STATE.md records that `typer[all]` extras are no longer published in 0.25.1 (generates a uvx warning). The effective install is `typer` + `rich` separately. This is a cosmetic issue; no functional impact on Phase 2.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest` |

**Baseline:** 55 tests pass in 0.80s. [VERIFIED: live test run]

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPUT-02 | `read()` accepts ZIP bytes | unit | `uv run pytest tests/test_reader.py -k zip -x` | ❌ Wave 0 |
| INPUT-02 | `read()` accepts ZIP file-like | unit | `uv run pytest tests/test_reader.py -k zip_filelike -x` | ❌ Wave 0 |
| INPUT-04 | Zip-slip entry raises `ContaPlusReadError` | unit | `uv run pytest tests/test_reader.py -k zipslip -x` | ❌ Wave 0 |
| INPUT-05 | Recursive DIARIO.DBF discovery | unit | `uv run pytest tests/test_reader.py -k nested_zip -x` | ❌ Wave 0 |
| INPUT-06 | Multi-company without `--company` raises listing dirs | unit | `uv run pytest tests/test_reader.py -k multi_company_no_selector -x` | ❌ Wave 0 |
| INPUT-06 | Multi-company with valid `--company` reads correct company | unit | `uv run pytest tests/test_reader.py -k multi_company_selected -x` | ❌ Wave 0 |
| INPUT-06 | Selector against single-company validates | unit | `uv run pytest tests/test_reader.py -k single_company_wrong_selector -x` | ❌ Wave 0 |
| INPUT-06 | Selector against raw DBF raises | unit | `uv run pytest tests/test_reader.py -k selector_on_dbf -x` | ❌ Wave 0 |
| TABL-01 | `subcta` reader builds correct lookup | unit | `uv run pytest tests/test_reader.py -k subcta_lookup -x` | ❌ Wave 0 |
| TABL-01 | Defensive field resolution (cod/codigo, titulo/descrip) | unit | `uv run pytest tests/test_reader.py -k subcta_candidates -x` | ❌ Wave 0 |
| TABL-02 | `grupos/usuarios/empresa` absent -> no sheet, no error | unit | `uv run pytest tests/test_reader.py -k group_tables_absent -x` | ❌ Wave 0 |
| TABL-02 | `usuarios` present -> sheet rendered with all fields | unit | `uv run pytest tests/test_reader.py -k usuarios_present -x` | ❌ Wave 0 |
| API-05 | Journal rows enriched with `subcuenta_nombre` from SUBCTA | unit | `uv run pytest tests/test_reader.py -k enrichment -x` | ❌ Wave 0 |
| API-05 | Missing SUBCTA key -> `subcuenta_nombre=None` (no error) | unit | `uv run pytest tests/test_reader.py -k enrichment_missing_key -x` | ❌ Wave 0 |
| API-05 | SUBCTA absent -> all `subcuenta_nombre=None` | unit | `uv run pytest tests/test_reader.py -k enrichment_no_subcta -x` | ❌ Wave 0 |
| CLI-02 | `--company` passed to `read()` | unit | `uv run pytest tests/test_cli.py -k company_flag -x` | ❌ Wave 0 |
| CLI-02 | Multi-company ZIP without `--company` exits 1 with Rich panel | unit | `uv run pytest tests/test_cli.py -k multi_company_error -x` | ❌ Wave 0 |
| XLSX (D-12) | Multi-sheet workbook has correct sheet names | unit | `uv run pytest tests/test_xlsx.py -k multi_sheet -x` | ❌ Wave 0 |
| XLSX (D-15) | Diario sheet has Descripcion column after Subcuenta | unit | `uv run pytest tests/test_xlsx.py -k descripcion_column -x` | ❌ Wave 0 |

**Success criteria tests (end-to-end, use synthetic ZIP fixtures):**

| Criterion | Test | Command |
|-----------|------|---------|
| #1: zip -> xlsx with SUBCTA names | e2e ZIP conversion | `uv run pytest tests/test_cli.py -k zip_to_xlsx_enriched -x` |
| #2: Multi-company without --company lists dirs | CLI error test | `uv run pytest tests/test_cli.py -k multi_company_error -x` |
| #3: Zip-slip entry rejected | unit | `uv run pytest tests/test_reader.py -k zipslip -x` |
| #4: Sheets for present tables | XLSX test | `uv run pytest tests/test_xlsx.py -k multi_sheet -x` |

### Sampling Rate
- **Per task commit:** `uv run pytest -q` (55 baseline + new tests, < 5s)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — add `single_company_zip_with_subcta`, `multi_company_zip`, `subcta_dbf_builder`, synthetic `grupos`/`usuarios`/`empresa` DBF builders
- [ ] `tests/test_reader.py` — all ZIP/SUBCTA/enrichment/group-table tests listed above
- [ ] `tests/test_cli.py` — `--company` flag tests
- [ ] `tests/test_xlsx.py` — multi-sheet and Descripcion column tests

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | **yes** | Zip-slip: `target.relative_to(base)` — reject entries that escape the temp dir |
| V6 Cryptography | no | n/a |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Zip-slip path traversal | Tampering / EoP | `Path.resolve()` + `relative_to(base)` per entry before extraction; confirmed blocks `../`, absolute paths, `Emp01/../../../../tmp/evil.dbf` |
| Malicious DBF (truncated/malformed) | Tampering | `except (struct.error, ValueError, OSError)` boundary already in `_read_dbf_path` — wraps in `ContaPlusReadError` |
| Enormous ZIP (zip bomb) | DoS | Not mitigated in v1; files are user's own ContaPlus backups; out of scope |

**Note on `usuarios.dbf` (D-18):** Extracting credential fields is an accepted design decision (local-only conversion, user's own data). No mitigation required. The XLSX renderer writes whatever fields the DBF contains.

---

## Sources

### Primary (HIGH confidence)
- `pii-test-data/` — 5 real ContaPlus backup ZIPs; enumerated for ZIP structure, SUBCTA schema, group table presence. [VERIFIED: this research session]
- `SEED.md` §4 "ZIP backup archive structure" — canonical ZIP layout reference [VERIFIED: matches real archive observations]
- `SEED.md` §1 "Related ContaPlus files" — SUBCTA field-name variants (`CODIGO`/`COD`, `DESCRIP`/`TITULO`) [PARTIALLY VERIFIED: real archives use `cod`/`titulo`; `codigo`/`descrip` are candidates only]
- `src/contaplus_reader/_reader.py`, `_bridge.py`, `_sniffer.py`, `models.py`, `xlsx.py`, `cli.py` — Phase 1 implementation; all patterns carried forward [VERIFIED: code read]
- `C:/dev/tax-workbench/packages/tw-contaplus/tw_contaplus/read_dbf.py` — source of the zip-slip pattern and company resolution logic [VERIFIED: code read]
- Python 3.13 `zipfile` stdlib — `ZipFile(BytesIO)` pattern [VERIFIED: live test]
- Python 3.13 `tempfile.TemporaryDirectory` — context manager lifecycle [VERIFIED: existing tw-contaplus usage]
- openpyxl multi-sheet — `create_sheet()` and workbook ordering [VERIFIED: live test]

### Secondary (MEDIUM confidence)
- `SEED.md` note on `grupos.dbf`/`usuarios.dbf` being present "in some installs" — consistent with not finding them in our sample
- `tw-contaplus/tests/conftest.py` — `single_company_zip`/`multi_company_zip` fixture pattern confirmed intact

### Tertiary (LOW confidence / ASSUMED)
- Synthetic schemas for `grupos.dbf`, `usuarios.dbf`, `empresa.dbf` — no real data; inferred from similar tables in the archives. Marked `[ASSUMED]` throughout.

---

## Metadata

**Confidence breakdown:**
- ZIP reading mechanism (stdlib, BytesIO, TemporaryDirectory): HIGH — verified with real archives
- SUBCTA schema (cod/titulo, candidate lists): HIGH — identical across all 5 archives
- Group table absence: HIGH — verified across all 5 archives; ASSUMED for "some installs have them"
- Synthetic schemas for grupos/usuarios/empresa: LOW — no real data
- Multi-sheet openpyxl: HIGH — confirmed working
- Zip-slip defense pattern: HIGH — confirmed blocks 4 attack vectors + all 101 real entries safe
- JournalRow frozen-dataclass field addition: HIGH — defaulted field is backward-compatible

**Research date:** 2026-05-16
**Valid until:** 2026-06-16 (stable domain; only risk is a new ContaPlus archive appearing with grupos/usuarios/empresa)
