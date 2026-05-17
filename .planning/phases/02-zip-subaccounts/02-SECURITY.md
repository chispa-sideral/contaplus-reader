---
phase: 2
slug: zip-subaccounts
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-17
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user ZIP bytes → TemporaryDirectory | Untrusted ContaPlus backup archive contents extracted to an OS temp dir; zip-slip / symlink / zip-bomb guards run before any file is written | DBF table bytes (user's own accounting data) |
| ZIP entry names → filesystem paths | Path-traversal via `../` or absolute names; backslash-normalised then validated with `relative_to` | Archive member filenames |
| CLI `--company` flag → `read()` | User-supplied company directory name; case-insensitive match inside `_zip.py`; invalid selector raises `ContaPlusReadError` handled by the Rich panel | Short string |
| `ContaPlusData` → openpyxl Workbook → bytes | Extracted DBF field values written as literal openpyxl cell values; no formula evaluation | Accounting field values, incl. `usuarios.dbf` credential fields |
| test fixtures → filesystem | Synthetic DBF/ZIP written to `tmp_path`; no real ContaPlus data enters the repo | Synthetic test data |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering / EoP | `_zip.py` `_safe_extract_zip` | mitigate | Per-entry zip-slip guard: backslash normalisation then `target.relative_to(base)` (`_zip.py:115-126`); `ValueError` raises `ContaPlusReadError("Unsafe ZIP entry")` before any write. CR-01: validated path is written via `shutil.copyfileobj` (`_zip.py:130-131`), never `zf.extract()`. WR-01: symlink entries rejected via Unix mode bits (`_zip.py:108-113`). | closed |
| T-02-02 | Tampering | `_reader.py` / `_subcta.py` DBF parsing | mitigate | `except (struct.error, ValueError, OSError, UnicodeDecodeError)` boundary wraps every dbfread call site: `_reader.py:254,261`; `_subcta.py:111,151,194` (the `build_subcta_lookup` boundary additionally catches `AttributeError, TypeError`). All branches wrap into `ContaPlusReadError`. | closed |
| T-02-03 | DoS | ZIP bomb (huge uncompressed archive) | accept | v1 files are the user's own local ContaPlus backups; no network-facing path; out of scope. Rationale holds — and the implementation goes further: `_zip.py:69-105` enforces a 500 MB total-uncompressed cap, a 10,000-entry cap, and a 200:1 per-entry compression-ratio cap (WR-02). | closed |
| T-02-04 | Tampering | `xlsx.py` `_render_generic_sheet` | accept | DBF field values written as openpyxl cell literals via `ws.cell(..., value=...)` (`xlsx.py:113-119,146,165`); openpyxl does not interpret a leading-`=` string set through `cell.value` as a formula. No formula-construction path exists. | closed |
| T-02-05 | Information Disclosure | `usuarios.dbf` credential fields in XLSX | accept | D-18 accepted: `usuarios.dbf` dumped in full (`__init__.py:102-104` via `read_table_raw`). Conversion is fully local — no `socket`/`urllib`/`requests`/HTTP import in any Phase 2 file; `read()` works on in-memory bytes + an OS `TemporaryDirectory`; CLI does local `read_bytes`/`write_bytes` only. No network egress. User converts their own data. | closed |
| T-02-SC | Tampering (supply chain) | npm/pip/cargo installs | accept | No new packages installed in Phase 2; all three plan SUMMARYs declare `tech_stack.added: []`; all deps already in `pyproject.toml`. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-03 | T-02-03 | ZIP-bomb DoS: v1 input is the user's own local ContaPlus backup; no network-facing path. Out of scope. Implementation nonetheless caps total uncompressed size (500 MB), entry count (10,000), and per-entry compression ratio (200:1). | Phase 2 plan (02-02 threat model) | 2026-05-17 |
| AR-02-04 | T-02-04 | XLSX formula injection: openpyxl writes literal cell values via `cell.value`; a leading `=` string is not evaluated as a formula. No injection path. | Phase 2 plan (02-03 threat model) | 2026-05-17 |
| AR-02-05 | T-02-05 | `usuarios.dbf` credential fields dumped to XLSX: conversion is fully local (CLI on user's machine, PWA client-side); user converts their own data; no network egress path exists. Decision D-18. | Phase 2 plan (02-02 D-18, 02-03 threat model) | 2026-05-17 |
| AR-02-SC | T-02-SC | Supply-chain tampering via new packages: no new packages installed in Phase 2; dependency set unchanged from `pyproject.toml`. | Phase 2 plan (all three threat models) | 2026-05-17 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-17 | 6 | 6 | 0 | gsd-security-auditor |

### Unregistered Flags

None. All three Phase 2 SUMMARY files (`02-01`, `02-02`, `02-03`) report `## Threat Flags: None`. No new attack surface appeared during implementation that lacks a threat mapping.

### Notes

- T-02-01 and T-02-02 (the two `mitigate` threats) verified present in implemented code with file:line evidence; no gaps.
- The implemented zip handler exceeds its plan: it adds zip-bomb caps (WR-02) and symlink rejection (WR-01) beyond the declared zip-slip mitigation. These hardenings reduce — not raise — residual risk; T-02-03's `accept` disposition is preserved as the register of record.
- No implementation files were modified by this audit (read-only).

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-17
