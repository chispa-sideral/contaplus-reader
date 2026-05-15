# Walking Skeleton — contaplus-reader

**Phase:** 1
**Generated:** 2026-05-15

## Capability Proven End-to-End

A user runs `contaplus2xlsx DIARIO.DBF out.xlsx` and receives a styled `.xlsx`
workbook containing a validated journal sheet — proving the full pipeline
`bytes → DBF reader → ContaPlusJournal → XLSX renderer → CLI` connects end to end.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Package layout | `src/contaplus_reader/` (src-layout) | uv_build default for pure-Python; keeps package importable only when installed or editable; avoids accidental imports from repo root |
| Build backend | `uv_build>=0.11.14,<0.12` | Zero-config pure-Python src-layout; 10-35x faster than hatchling; locked in CLAUDE.md |
| DBF reader | `dbfread 2.0.7` | Path-only library; pure-Python MIT; lazy iteration mandatory for large journals; bytes→path bridge pattern handles in-memory input |
| Bytes→path bridge | `tempfile.NamedTemporaryFile(suffix=".dbf", delete=False)` + `finally: unlink()` | Windows cannot open same file twice while open; delete=False + explicit cleanup is the cross-platform pattern |
| Input detection | Magic-byte sniffer at offset 0 (content, not suffix) | API is bytes-first; callers have no filename; 12-value accept-set covers all dBASE/FoxPro variants |
| Encoding | `cp850` unconditionally | DOS/Clipper-lineage; header byte-29 is frequently unset; `latin-1` decodes accent bytes wrong |
| Result model | Frozen dataclasses `JournalRow`, `ContaPlusJournal`; mutable `ContaPlusData` container | Container grows new table attributes in Phases 2–3 without breaking existing callers; individual rows are immutable read results |
| Public API | `read(data: bytes \| BinaryIO, source_name: str \| None = None) -> ContaPlusData` | Bytes-first unifies CLI (path.read_bytes()), PWA (File API), and tax-workbench adapter; source_name carries provenance into errors |
| Error model | `ContaPlusReadError(message, row_index, column, original)` frozen dataclass+Exception | Structured: row_index=-1 for file-level errors, ≥0 for row-level; no traceback surfaced to users |
| XLSX renderer | Direct `openpyxl.Workbook` (not pandas.ExcelWriter) | Per-cell format control for accounting number format + red negatives; returns `bytes` (BytesIO) with no filesystem assumption |
| CLI framework | Typer 0.13+ with `typer[all]` (Rich included) | Type-hint driven; automatic `--help`; `uvx contaplus2xlsx` works out of box; Rich error panels for ContaPlusReadError |
| CLI overwrite policy | Refuse by default; `--force`/`--overwrite` flag required | Script-safe; never clobbers silently (D-15) |
| XLSX column headers | Spanish (`Fecha, Cuenta, Subcuenta, Debe, Haber, Concepto`) | These label Spanish-statutory accounting data (PGC); audience is Spanish-speaking ContaPlus migrants; documented exception to "English everything" rule |
| Test fixtures | Synthetic DBFs generated at collection time via `dbf` (ethanfurman) | Keeps repo blob-free; schema explicit in code; `pii-test-data/` archives are gitignored and never committed |
| Deployment target (CLI) | `uvx contaplus2xlsx` (from PyPI wheel) | Modern pipx replacement; isolated env; no user venv pollution |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, `uv_build`, `uv sync`, `src/` layout)
- [x] Reader — real DBF read via `dbfread` with bytes→path bridge, journal business rules D-A1…D-E3, ContaPlusReadError model
- [x] XLSX output — `openpyxl` Workbook written to `bytes` (no filesystem path required)
- [x] CLI — `contaplus2xlsx` Typer entry point, `--force` flag, Rich error panel, success summary
- [x] Distribution — `uv build` produces wheel; `uvx contaplus2xlsx` installs and runs from it

## Out of Scope (Deferred to Later Slices)

- ZIP input, zip-slip safety, multi-company disambiguation → Phase 2
- `SUBCTA.DBF` reader + journal name enrichment → Phase 2
- `grupos.dbf`, `usuarios.dbf`, `empresa.dbf` readers → Phase 2
- Lenient conversion path + problems sheet → Phase 3
- Operational table readers (`venci`, `prede`, `amoinv`, `nivel`) → Phase 3
- `BALAN.DBF` reader + trial balance recomputation → Phase 3
- Multi-company `--company` flag → Phase 4
- Stdout row-count/problems report (CLI-03) → Phase 4
- PyPI publication (DIST-01) → Phase 4
- Browser PWA (Pyodide + Cloudflare Pages) → Phase 5
- Encoding autodetect via header byte-29 → v2
- Alpha-prefixed subaccount codes (`A4300001`) → v2
- Two-pass "collect all bad rows" validation → v2

## Subsequent Slice Plan

- Phase 2: User can convert a ContaPlus backup `.zip` and get a multi-sheet `.xlsx` including subaccount names
- Phase 3: User running lenient conversion gets every readable table including a computed trial balance and a problems sheet
- Phase 4: Tool is installable from PyPI; CLI handles all v1 flags; wheel ready for `micropip`
- Phase 5: Any user can drag-drop a ContaPlus file on a public URL, convert in-browser, and download the `.xlsx`
