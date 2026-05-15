# Feature Research

**Domain:** Legacy accounting export conversion tool (ContaPlus DBF → styled XLSX)
**Researched:** 2026-05-15
**Confidence:** MEDIUM — ContaPlus schemas are not publicly open-spec'd; field lists
are synthesized from multiple secondary sources (Sage protocol PDF, jggomez.eu,
Domatix/contaplus source, forum threads). DIARIO.DBF is HIGH confidence (pinned in
SEED + cross-corroborated). Other tables are MEDIUM-LOW and must be validated against
a real backup before a typed reader is committed.

---

## ContaPlus Table Inventory

This section is the central deliverable. It feeds the typed-reader roadmap directly:
one typed reader per table = one implementation task per row in this inventory.

### Directory layout (confirmed)

```
Group SP\ContaPlus\<grupo>\            ← group-level (shared across companies)
    grupos.dbf / grupos.cdx
    usuarios.dbf / usuarios.cdx

Group SP\ContaPlus\<grupo>\<NN>\       ← per-company directory (one per empresa)
    DIARIO.DBF / DIARIO.CDX            ← journal — primary source of truth
    SUBCTA.DBF / SUBCTA.CDX            ← chart of subaccounts
    BALAN.DBF  / BALAN.CDX             ← cached trial balance (DERIVED — unreliable)
    venci.dbf  / venci.cdx             ← due dates / vencimientos
    prede.dbf  / prede.cdx             ← predefined journal entries
    amoinv.dbf / amoinv.cdx            ← asset/amortization inventory
    nivel.dbf  / nivel.cdx             ← balance-report digit display settings
    empresa.dbf / empresa.cdx          ← company parameters
    [other config tables — see below]
```

A ContaPlus "Copia de seguridad" ZIP contains: the group folder rooted at the top,
one `EmpNN/` (or `EMPNN/`) subdirectory per exported company (some installs also
`Datos\EmpNN\`), group-level files at the root, and IMAGES + TELEMA folders
(non-accounting assets — ignore). `.cdx` index files always accompany each `.dbf`.

### Table-by-table inventory

#### Tier 1 — Primary accounting data (must read for any useful output)

| Filename | Export alias | Purpose | Key fields | Confidence | Version variance |
|----------|-------------|---------|-----------|-----------|-----------------|
| `DIARIO.DBF` | `XDIARIO.DBF` | Journal — one DBF record per journal *line*. The primary source of truth for all accounting. | `ASIEN N(6,0)`, `FECHA D`, `SUBCTA C(12)`, `CONTRA C(12)`, `CONCEPTO C(25)`, `EURODEBE N(16,2)`, `EUROHABER N(16,2)`, `BASEEURO N(16,2)`, `IVA N(5,2)`, `FACTURA C(10)`, `DOCUMENTO C(10)`, `TIPODOC C(1)`, `DEPARTAM C(4)`, `ESTADO C(1)`, `MONEDAUSO C(1)`, `CAMBIO N` | HIGH — fully pinned in SEED | Debit/credit column names: `EURODEBE`/`EUROHABER` (2002+), `DEBE`/`HABER` (generic), `PESEDEBE`/`PESEHABER` (≤2001). Width of `SUBCTA` varies: 8, 12, or 15. `CONCEPTO` sometimes a Memo field in Sage 50-era variants (requires `ignore_missing_memofile=True`). |
| `SUBCTA.DBF` | `XSUBCTA.DBF` | Chart of subaccounts — one record per subaccount code. The enrichment source for account names. | Primary key: `COD` or `CODIGO` C(12). Name: `TITULO` or `DESCRIP` C(40–50). Third-party data: `NIF` or `CIF` C(12–14), `DOMICILIO` C(35), `POBLACION` C(25), `PROVINCIA` C(20), `CODPOSTAL` C(5), `TELEFONO` C(15), `FAX` C(15), `EMAIL` C(50), `CONTACTO` C(30). Banking: `BANCO` C(4), `CCC` C(20). Config: `TIPOIVA` C(1), `ACTIVA` L. Legacy: `SALDO` N(16,2) (accumulated balance — derived, not authoritative). | MEDIUM — Domatix source code + jggomez confirmed `COD`/`TITULO` and third-party block; `DESCRIP`/`CODIGO` variants seen in older versions | Field name variants: older releases use `CODIGO`/`DESCRIP`, newer use `COD`/`TITULO`. Width of primary key: 8 or 12. NIF field is `NIF` in some versions, `CIF` in others. SALDO presence is inconsistent (may be absent in export-only copies). |

#### Tier 2 — Derived/cached data (read but flag as non-authoritative)

| Filename | Purpose | Key fields | Confidence | Notes |
|----------|---------|-----------|-----------|-------|
| `BALAN.DBF` | Cached trial balance (sumas y saldos) — rebuilt by "UTILIDADES > Refrescar datos". One record per subaccount per period. | `SUBCTA C`, `DEBE N`, `HABER N`, `SALDO N`, `EJERCICIO C/N`, `MES`/`PERIODO N`, `DEBEANT N`, `HABERANT N` | MEDIUM (jggomez source, cross-referenced in research) | UNRELIABLE: known to develop descuadres after corrections. NEVER treat as source of truth. Recompute trial balance from DIARIO instead. Surface it with a clear "may be stale" warning. |

#### Tier 3 — Configuration and operational tables (include in "all data" export; do NOT use for recomputing accounting totals)

| Filename | Purpose | Known fields / content | Confidence | When present |
|----------|---------|----------------------|-----------|--------------|
| `venci.dbf` | Due dates / vencimientos — one record per payment deadline associated with a journal entry. Links back to DIARIO by ASIEN/date. | Contains `SUBCTA` field (modified when increasing digit length). Likely: `ASIEN`, `FECHA`, `IMPORTE`, `SUBCTA`, status flag. | LOW — existence confirmed by forum sources; field layout not publicly documented | Present when the "vencimientos" feature is used. May be absent in minimal installations. |
| `prede.dbf` | Predefined journal entry templates — one record per template line. Used by ContaPlus's "Asientos predefinidos" feature. | Contains `SUBCTA` field. Likely: template id, `SUBCTA`, `CONCEPTO`, percentage/amount template, debit/credit indicator. | LOW — existence confirmed; field layout inferred from feature description | Present when predefined entries are configured. Absent in minimal installs. |
| `amoinv.dbf` | Fixed asset / amortization inventory — one record per asset. Links to DIARIO amortization entries. | Contains `SUBCTA` field. Likely: asset code, description, purchase date, cost, accumulated depreciation, depreciation method, `SUBCTA` amortization account. | LOW — existence confirmed; field layout not publicly documented | Present when fixed assets are tracked. Absent in simple installations. |
| `nivel.dbf` | Balance sheet display configuration — digit settings for balance/trial balance reports. | Config-level: level digits setting. Probably few records (one per display level). | LOW — one forum reference only | Usually present; tiny file. |
| `empresa.dbf` | Company parameter file — stores company-level settings for the active empresa. | Company name, fiscal year dates, IVA regime, decimal settings, plan contable version. | LOW — referenced in forum troubleshooting only; no field spec found | Always present (critical for ContaPlus to start). |
| `grupos.dbf` | Group-level table — one record per ContaPlus "grupo" (installation group). Sits above the company directory. | Group id, name, path. | LOW — mentioned in SEED; no field spec found | At group level, not per-company. |
| `usuarios.dbf` | User/access control table — one record per ContaPlus user. | Username, password hash (likely), permissions. | LOW — mentioned in SEED and forum; no field spec found | At group level. Path: `C:\GrupoSp\COEXXXX\EMP\usuarios.dbf` |

#### Other tables observed in the wild (LOW confidence, may appear in some installs)

Based on the ContaPlus→Sage 50 migration guide, FacturaPlus-integrated installs add article/invoice tables. These are FacturaPlus tables, NOT pure ContaPlus accounting tables, and are out of scope:

- `articulo.dbf`, `artcom.dbf`, `articulc.dbf` — product catalog (FacturaPlus integration only)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Read DIARIO.DBF with full fidelity | Core value; the reason anyone uses this tool | LOW — already implemented in tw-contaplus | Port existing rules D-A1…D-E3 verbatim. All business rules are pinned in SEED. |
| Read SUBCTA.DBF and expose account names | A journal without account names is illegible for migration review | LOW-MEDIUM | Primary key variants: `COD`/`CODIGO`. Name field variants: `TITULO`/`DESCRIP`. Must resolve defensively at parse time. |
| Enrich journal output with account names | Journal rows showing only codes require manual lookup; migration users need human-readable data | MEDIUM | Join DIARIO → SUBCTA on `SUBCTA` = `COD`/`CODIGO`. Additive: if SUBCTA not present, output codes only. |
| Accept both raw .dbf and .zip backup | ContaPlus's own export is either a raw DBF or the "Copia de seguridad" ZIP. Users have both. | MEDIUM — already implemented; port to bytes-based API | Zip-slip safety is required; already designed in existing code. |
| Multi-company ZIP disambiguation | Most firms with multiple companies use a single ZIP backup | MEDIUM — already implemented | Company picker by directory name. |
| Styled multi-sheet XLSX output | Plain CSV feels unfinished; styled XLSX is the expected deliverable for "migration audit" use | MEDIUM | One sheet per table. Header row formatting, column widths, freeze panes. Shared renderer used by CLI and PWA. |
| Lenient conversion path that never aborts | Migration users have imperfect data; an abort-on-first-error is unusable for exploratory extraction | MEDIUM | Strict path for tax-workbench; lenient path collects errors into a report sheet, extracts what it can. |
| Skipped-memo count surfaced | Zero-amount memo lines are common; user needs to know they were intentionally skipped, not lost | LOW | Already in tw-contaplus; port as `skipped_memo` count in result model. |
| Error report in XLSX output | Lenient path must show what was skipped and why — not silently | LOW | "Errors" sheet in the XLSX with row index, column, and reason. |
| CLI single-file invocation | Standard expectation for a conversion tool | LOW | `contaplus2xlsx <file> [-o output.xlsx] [--company Emp01]` |
| PWA with drag-drop and client-side conversion | Privacy requirement: the file must never leave the user's machine | HIGH — Pyodide cold-load, micropip, WASM runtime | The file never uploads; conversion runs in-browser. See PITFALLS for cold-load risk. |
| BALAN.DBF included but flagged as derived | Users expect all data extracted; omitting BALAN.DBF confuses them. But trusting it confuses them more. | LOW — read the file; add a "DERIVED — may be stale" disclaimer sheet | Recompute trial balance from DIARIO for the authoritative sheet. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Computed trial balance from DIARIO (not from BALAN.DBF) | BALAN.DBF is known-unreliable; a recomputed trial balance is authoritative | MEDIUM | Group DIARIO by SUBCTA; sum debe/haber; derive saldo. Add as a dedicated "Sumas y Saldos" sheet. |
| Third-party data enrichment from SUBCTA (NIF, address, phone) | Clients/suppliers (430x, 400x subaccounts) carry full contact info in SUBCTA; surface it for migration to CRM | LOW — just include more SUBCTA columns | Only for subaccounts with `COD` starting with 4; rest have empty NIF/address. |
| Typed readers with per-table validation reports | Tells the user exactly what's wrong with their data, per table, per row | HIGH — requires lenient path for each table | Differentiates from "open in Access and export to CSV" workaround. |
| Multi-exercise detection and labeling | Some installs have one directory per fiscal year (`\<NN>\2022\`, `\<NN>\2023\`). Surfacing all years in one XLSX is rare in competing tools. | MEDIUM | Recursive walk identifies year subdirectories; label each journal sheet with the year. |
| PWA with no install and no upload | Anyone with a browser can convert their files instantly, privately | HIGH — see open research questions | No competing open-source tool exists. The PyPI namespace `contaplus-reader` is open. |
| Version auto-detection for column name variants | Handles peseta-era (≤2001), euro-era (2002–2006), and modern (2007+) exports transparently | LOW — already in design (candidate list matching) | Most tools break on non-standard column names. |
| Summary sheet with key totals | XLSX opens to a dashboard: total entries, date range, top accounts by volume, skipped rows, error count | MEDIUM | Makes the output immediately useful for a controller reviewing data before migration. |
| venci.dbf / prede.dbf extraction | Due-date tracking and predefined entries are critical operational data that tools like "open in Access" leave behind | MEDIUM-HIGH — field schemas uncertain (LOW confidence); requires real-data validation first | V1 should output raw columns with no interpretation; v2 can add business logic. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Writing back to ContaPlus DBF | "Can I fix my data and write it back?" | Requires write access to indexed FoxPro CDX files. `dbfread` is read-only (by design). Writing CDX is a completely different problem domain (FoxPro index maintenance). Out of scope and dangerous if done wrong. | Direct ContaPlus-to-ContaPlus copy via the built-in backup/restore flow. |
| Trusting BALAN.DBF as the trial balance source | Users see it in the backup and assume it's authoritative | Known to develop descuadres. Multiple community-confirmed cases. Would produce wrong output silently. | Recompute from DIARIO (a differentiator). Surface BALAN.DBF as a reference-only sheet with a visible disclaimer. |
| Importing into another accounting system directly | "Can it import into A3, ContaSOL, or Odoo?" | Each target system has its own import format. Multiple well-funded tools (criterium.es, sdelsol, Domatix) already do this. Out of scope. | Export to XLSX and let the user use the target system's XLSX import. |
| Encoding autodetect via header byte-29 | Some modern installs use cp1252 | Unset byte-29 (common in Clipper-era files) would cause garbage decoding. v1 forces cp850. | cp850 is correct for 99% of real data. Autodetect is a v2 concern and is explicitly deferred in PROJECT.md. |
| Alpha-prefixed subaccount codes | Some installs allow `A4300001` | Requires changing all subcuenta validation rules; unknown prevalence. Explicitly deferred in PROJECT.md. | Log as a warning in the error report; user can inspect the raw column. |
| Batch/glob CLI input (`contaplus2xlsx *.zip`) | Multiple companies at once | Complicates output structure (which XLSX per company?); multi-company ZIPs already handled. Deferred in PROJECT.md. | Process each file individually; chain with a shell loop. |
| Qt GUI / desktop application | Some users prefer native UI | The standalone GUI is the PWA; a native GUI duplicates it without adding privacy or distribution benefits. Explicitly out of scope in PROJECT.md. | Use the PWA URL. |
| Two-pass "collect all bad rows" in strict mode | Useful for batch validation | First-fail is the contract for tax-workbench (D-C5). Two-pass is a v2 concern per PROJECT.md. | Use the lenient path which does collect-and-continue. |
| Real-time conversion progress bar | Large journals (millions of rows) take time | Adds significant complexity to the PWA Python runtime and requires threading or Web Workers; cold-load UX already has a loading spinner. | Surface a row-count estimate before conversion; show elapsed time after. |

---

## Feature Dependencies

```
DIARIO.DBF typed reader
    └──required by──> Journal XLSX sheet
    └──required by──> Computed trial balance (Sumas y Saldos) sheet
    └──required by──> Strict API (tax-workbench contract)
    └──required by──> Lenient conversion path

SUBCTA.DBF typed reader
    └──required by──> Account name enrichment of journal
    └──enhances──> Journal XLSX (adds NOMBRE_SUBCUENTA column)
    └──enhances──> Third-party data sheet (NIF, address for 4xx subaccounts)

ZIP handling (bytes-based, zip-slip-safe)
    └──required by──> PWA (no filesystem path available)
    └──required by──> Multi-company disambiguation
    └──required by──> Discovery of all tables in one backup

Lenient conversion path
    └──required by──> Error report sheet in XLSX
    └──conflicts-with──> Strict API (separate code paths, share the same reader primitives)

Shared XLSX renderer
    └──required by──> CLI output
    └──required by──> PWA output
    └──required by──> Consistent styling across both consumers

Pyodide/PyScript runtime (PWA)
    └──required by──> Client-side conversion
    └──required by──> micropip install of contaplus-reader wheel
    └──depends-on──> PyPI publication of contaplus-reader
```

### Dependency Notes

- **SUBCTA enrichment requires DIARIO reader:** Without a parsed journal there is nothing to enrich; SUBCTA alone is just a lookup table.
- **Computed trial balance requires DIARIO reader:** It is a group-by aggregation of journal rows — BALAN.DBF is not used.
- **PWA requires PyPI publication:** `micropip.install('contaplus-reader')` resolves from PyPI; local-dev path uses a locally built wheel. The wheel must be a pure-Python sdist/wheel with no C extensions.
- **Lenient path and strict path conflict:** They must not share validation state. The strict path raises on the first bad row (D-C5); the lenient path collects and continues. Same underlying reader primitives, different error-handling wrapper.

---

## MVP Definition

### Launch With (v1)

Minimum viable product: the tool is useful for migration review and tax-workbench handoff.

- [ ] Typed reader for `DIARIO.DBF` — all D-A1…D-E3 rules, bytes-based API, strict + lenient paths
- [ ] Typed reader for `SUBCTA.DBF` — defensive `COD`/`CODIGO` + `TITULO`/`DESCRIP` resolution; extract code + name + NIF/address block
- [ ] Journal enrichment with account names when SUBCTA present (additive)
- [ ] `BALAN.DBF` raw extraction — output columns as-is, labeled "derived/may be stale" in XLSX
- [ ] ZIP handling — zip-slip-safe, bytes-based, recursive discovery, multi-company picker
- [ ] Shared XLSX renderer — one sheet per extracted table, header formatting, freeze panes, auto-column-width
- [ ] CLI `contaplus2xlsx` — single-file invocation, `--company` flag, writes XLSX
- [ ] PWA — drag-drop, client-side conversion, download XLSX, error display; Pyodide runtime (decision pending)
- [ ] PyPI publication as `contaplus-reader`

### Add After Validation (v1.x)

Add once v1 is in real-user hands and the above is confirmed working.

- [ ] `venci.dbf` typed reader — trigger: first user who needs due-date data; requires a real-data sample to pin the schema
- [ ] `prede.dbf` typed reader — trigger: first user who needs predefined-entry templates
- [ ] Computed trial balance sheet (recomputed from DIARIO) — trigger: user feedback that BALAN.DBF disclaimer is confusing
- [ ] `empresa.dbf` / `nivel.dbf` extraction — trigger: user needs company metadata in output
- [ ] Summary/dashboard sheet in XLSX — trigger: first user review

### Future Consideration (v2+)

Defer until product-market fit is established.

- [ ] `amoinv.dbf` typed reader — fixed assets / amortization; specialized use case; field schema uncertain
- [ ] Encoding autodetect via byte-29 — explicitly deferred; cp850 covers 99% of real data
- [ ] Alpha-prefixed subaccount codes (`A4300001`) — explicitly deferred; unknown prevalence
- [ ] Multi-exercise detection and per-year journal labeling — useful but rare; needs real multi-year backup to test against
- [ ] Two-pass collect-all-bad-rows in strict mode — v2 concern per PROJECT.md
- [ ] `grupos.dbf` / `usuarios.dbf` extraction — low user value; user access control data rarely needed in migration
- [ ] Batch/glob CLI input — explicitly deferred per PROJECT.md

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| DIARIO.DBF typed reader | HIGH | LOW (port from tw-contaplus) | P1 |
| SUBCTA.DBF typed reader | HIGH | MEDIUM | P1 |
| Journal enrichment with account names | HIGH | LOW (join DIARIO + SUBCTA) | P1 |
| ZIP bytes-based handling | HIGH | MEDIUM (port + bytes API) | P1 |
| Styled XLSX output (shared renderer) | HIGH | MEDIUM | P1 |
| CLI `contaplus2xlsx` | HIGH | LOW | P1 |
| PWA client-side conversion | HIGH | HIGH (Pyodide runtime) | P1 |
| PyPI publication | HIGH | LOW | P1 |
| BALAN.DBF raw extraction (with disclaimer) | MEDIUM | LOW | P2 |
| Lenient conversion path + error report | MEDIUM | MEDIUM | P2 |
| Computed trial balance from DIARIO | MEDIUM | MEDIUM | P2 |
| `venci.dbf` typed reader | MEDIUM | MEDIUM-HIGH (schema uncertain) | P2 |
| Summary/dashboard sheet | LOW | MEDIUM | P3 |
| `prede.dbf` typed reader | LOW | MEDIUM-HIGH | P3 |
| `amoinv.dbf` typed reader | LOW | HIGH | P3 |
| Multi-exercise labeling | LOW | MEDIUM | P3 |
| `empresa.dbf` / `nivel.dbf` extraction | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

There is no direct open-source competitor. The landscape is commercial tools and Access/Excel workarounds.

| Feature | Access + manual | Domatix/contaplus (Odoo-specific) | criterium.es GeneraConta | Our approach |
|---------|----------------|-----------------------------------|--------------------------|--------------|
| Privacy (no upload) | Local | Local script | Cloud/desktop tool | Client-side PWA |
| Output format | Raw DBF rows in Access | Odoo import (not XLSX) | Proprietary format | Styled XLSX |
| Styled output | None | None | Reports only | Yes — multi-sheet |
| All tables | Possible but manual | DIARIO + SUBCTA only | DIARIO + SUBCTA | All tables (extensible) |
| Error report | None | Crash or silent skip | Unknown | Dedicated error sheet |
| Account name enrichment | Manual join in Access | Partial | Yes | Yes (automatic) |
| Trial balance recomputed | No | No | Possibly | Yes (v1.x) |
| Multi-company | Manual | Not documented | Yes | Yes (--company flag) |
| No install required | No | Python + script | Download required | URL in browser |
| Open source | — | Yes (GPL-ish) | No | Yes (LGPL-3.0) |

---

## Per-Table Typed Reader: Scope and Fidelity Notes

### `DIARIO.DBF` — HIGH confidence, fully pinned

Rules D-A1…D-E3 are law. Do not re-investigate. Port verbatim from tw-contaplus. See SEED for complete spec.

v1 output columns: `fecha`, `cuenta`, `subcuenta`, `debe`, `haber`, `concepto`
Optional enrichment: `subcuenta_nombre` (when SUBCTA available)

### `SUBCTA.DBF` — MEDIUM confidence; field name resolution is defensive

**Key rule:** Never hardcode `COD` or `CODIGO` — resolve the primary-key column at parse time from the actual `field_names`. Candidate list for code: `["cod", "codigo"]`. Candidate list for name: `["titulo", "descrip"]`. If neither resolves, fail with a structured error listing actual fields.

v1 output columns: `codigo` (resolved PK), `nombre` (resolved name). Optional columns: `nif`, `domicilio`, `poblacion`, `provincia`, `codpostal`, `telefono`, `email`.

**CIF/NIF population pattern:** Only subaccounts in the 400x–440x range (clients/suppliers/creditors) will have populated NIF/address fields. Other subaccounts (expenses, income, cash) will have blanks. This is expected behavior, not a read error.

**`SALDO` field:** May be present or absent; treat as optional. If present, output it but label as "legacy cached balance" — it is derived, not authoritative.

### `BALAN.DBF` — MEDIUM confidence on structure; LOW reliability as data

Field layout: `SUBCTA`, `DEBE`, `HABER`, `SALDO`, `EJERCICIO`, `MES`/`PERIODO`, `DEBEANT`, `HABERANT`. Actual column names may vary (use same defensive resolution pattern as SUBCTA).

**Critical warning for XLSX output:** The BALAN sheet must carry a visible header note: "This trial balance is a ContaPlus cache. It may be stale or incorrect after journal corrections. Use the Sumas y Saldos sheet (recomputed from DIARIO) for authoritative balances."

v1 strategy: raw extraction only, no business logic applied. Flag as derived.

### `venci.dbf`, `prede.dbf`, `amoinv.dbf` — LOW confidence; defer typed readers

These tables exist and are present in many backups (confirmed by forum sources). Their field layouts are not publicly documented. A v1 approach: detect their presence, output raw column dump with no interpretation. A v1.x typed reader should only be built after a real-data sample has been inspected via `DBF(...).field_names`.

**Specific risk for `venci.dbf`:** It links to DIARIO entries. If the account code digit length was ever changed, SUBCTA and venci.dbf both need updating — this means the codes in venci.dbf may be inconsistent with SUBCTA if the firm ever ran the digit-length migration tool incompletely.

### `grupos.dbf`, `usuarios.dbf` — LOW confidence; low value for migration

Group-level metadata and user access control. Users migrating off ContaPlus do not typically need these for their new accounting system. v1 should detect and output as raw dump only. Do not invest in typed readers unless user demand emerges.

---

## Version Variance Summary

| Version era | Key differences | Impact on typed readers |
|-------------|----------------|------------------------|
| Grupo SP / ContaPlus ≤2001 (peseta era) | `PESEDEBE`/`PESEHABER` amount columns; 8-char `SUBCTA` | Handled by candidate-list column resolution (D-E1). |
| ContaPlus 2002–2006 (euro cutover) | `EURODEBE`/`EUROHABER` columns added; legacy peseta columns may coexist | Candidate list picks euro columns first. |
| ContaPlus 2007–2016 (modern) | Peseta columns dropped; `SUBCTA` up to 12 chars; `CONCEPTO` may be Memo field | Standard case. `ignore_missing_memofile=True` handles missing FPT. |
| Sage ContaPlus / Sage 50 (2017+) | CSV export option added (Sage 50 prefers CSV); DBF still produced for legacy compatibility | Sage 50 may produce `DIARIO.FPT` alongside `DIARIO.DBF`. DBF format otherwise unchanged. |

All version differences in DIARIO.DBF are handled by the existing D-E1 candidate-list resolution. SUBCTA field-name variants require a similar defensive resolution (documented above). Other tables have less version documentation — treat with caution.

---

## Sources

- SEED.md (in repo root) — ContaPlus file-format reference, pinned DIARIO.DBF schema, confirmed SUBCTA and BALAN partial schema. Source-of-truth for journal rules.
- `C:\dev\tax-workbench\.planning\phases\04-contaplus-reader-tw-contaplus\04-RESEARCH.md` — original format research with full citation index.
- Sage. *Manual de protocolos de ContaPlus* (PDF). https://grupo.sage.es/ayuda/documentacion/productos/contaplus/Manual_protocolos_ContaPlus.pdf — MEDIUM confidence (binary PDF; fields partially extracted via secondary sources).
- jggomez.eu. *Ficheros MAESTROS y TEMPORALES de Contaplus* (PDF). http://jggomez.eu/F%20Sig/C%20Financ/B%20Contaplus/C%20Otras%20cuestiones/ — MEDIUM confidence. Corroborates BALAN.DBF field list.
- Domatix/contaplus (GitHub). *import_cuentas_peek.py*, *import_asientos_peek.py*. https://github.com/Domatix/contaplus — HIGH confidence for SUBCTA fields actually consumed (`COD`, `TITULO`, `NIF`, `DOMICILIO`, `CODPOSTAL`, `POBLACION`, `PROVINCIA`).
- foros.plangeneralcontable.com. *Aumentar dígitos contaplus* (thread t=43037). — Confirms existence of `venci.dbf`, `prede.dbf`, `amoinv.dbf`, `nivel.dbf`, `empresas.dbf` as containing SUBCTA fields.
- peccataminuta.wordpress.com. *Cómo extraer una contabilidad de Contaplus y pegarla en Excel* (2014). — Confirms three-file view: DIARIO + SUBCTA + BALAN sufficient for journal extraction.
- josepjane.blogspot.com. *ERROR ADSCDX/7016* (2011). — Confirms `AMOINV.DBF` as a known company-directory file.
- Sage ContaPlus R41 migration guide (PDF, 2018). http://descargas.sage.es/sage50/documentacion/ — References `articulo.dbf`, `artcom.dbf` as FacturaPlus-only files (out of scope).

---
*Feature research for: ContaPlus DBF → XLSX extraction tool*
*Researched: 2026-05-15*
