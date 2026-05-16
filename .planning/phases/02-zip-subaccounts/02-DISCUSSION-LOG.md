# Phase 2: ZIP & Subaccounts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 2-zip-subaccounts
**Areas discussed:** Company selector & identity, Journal name enrichment, Multi-sheet workbook layout, Group tables: strictness & privacy

---

## Company selector & identity

### Q1 — Company identification (selector value + "available companies" error)

| Option | Description | Selected |
|--------|-------------|----------|
| Directory name, human label in error | Selector matches directory name (Emp01/Emp02); error also shows razón social from empresa.dbf, e.g. `Emp01 (ACME S.L.)`. | |
| Directory name only | Selector and error both use the raw directory name. Zero dependency on empresa.dbf parsing — matches SEED D-A2. | ✓ |
| Human name is the selector | Caller passes the razón social; matching resolves against that. Breaks if empresa.dbf missing. | |

**User's choice:** Directory name only.

### Q2 — `--company` CLI flag timing

| Option | Description | Selected |
|--------|-------------|----------|
| Pull the flag into Phase 2 | Phase 2 CLI gains `--company`; ROADMAP SC #2 testable; CLI-02 moves Phase 4 → Phase 2. | ✓ |
| API-only in Phase 2 | read() gets the selector param; CLI errors on multi-company until Phase 4. | |

**User's choice:** Pull the flag into Phase 2.

**Notes:** Resolves an inconsistency — ROADMAP Phase 2 SC #2 references a `--company` flag while REQUIREMENTS mapped CLI-02 to Phase 4. CLI-02 is reassigned to Phase 2. Selector-edge behavior (selector vs single-company ZIP → validate; selector vs raw `.dbf` → error) taken as Claude's discretion, unobjected.

---

## Journal name enrichment

### Q1 — Where SUBCTA names live (vs D-07's locked JournalRow shape)

| Option | Description | Selected |
|--------|-------------|----------|
| Lookup on ContaPlusJournal | JournalRow untouched; ContaPlusJournal gains a subcuenta→name map. | |
| Optional field on JournalRow | Add `subcuenta_nombre: str \| None = None`; tax-workbench adapter ignores it. | ✓ |
| Renderer-side join only | JournalRow/ContaPlusJournal untouched; only the workbook is enriched. | |

**User's choice:** Optional field on JournalRow.

### Q2 — Which account level gets a name

| Option | Description | Selected |
|--------|-------------|----------|
| Subcuenta only | Name the full subaccount code only — the level SUBCTA.DBF actually contains. | ✓ |
| Subcuenta + opportunistic cuenta | Also name the 4-digit cuenta when present as a SUBCTA row — inconsistent coverage. | |

**User's choice:** Subcuenta only.

**Notes:** `subcuenta_nombre` is an additive, defaulted field — recorded as a documented extension of Phase-1 D-07. Unresolved/absent → `None`, never an error (Claude's discretion, distinct from the uniform-strict table rule).

---

## Multi-sheet workbook layout

### Q1 — How much of each table goes into its sheet

| Option | Description | Selected |
|--------|-------------|----------|
| Full dump — every field | Each sheet reproduces every field, in DBF order; raw DBF field names as headers. | ✓ |
| Curated subset | Hand-picked subset per table — cleaner but silently drops data. | |

**User's choice:** Full dump — every field.

### Q2 — Sheet tab naming

| Option | Description | Selected |
|--------|-------------|----------|
| Spanish names | `Diario`, `Subcuentas`, `Empresa`, `Grupos`, `Usuarios` — consistent with the existing `Diario` tab and D-12. | ✓ |
| Raw DBF table names | `DIARIO`, `SUBCTA`, `GRUPOS`, … uppercase — inconsistent with the existing `Diario` tab. | |

**User's choice:** Spanish names.

**Notes:** Renderer must grow data-driven multi-sheet support even though no XLSX-numbered requirement is mapped to Phase 2 — SC #4 requires it. Journal name-column header text and sheet order taken as Claude's discretion.

---

## Group tables: strictness & privacy

### Q1 — Behavior when an auxiliary table is present but unreadable

| Option | Description | Selected |
|--------|-------------|----------|
| Journal strict, auxiliaries best-effort | Journal fail-loud; unreadable SUBCTA/group table skipped at table granularity, conversion continues. | |
| Uniform strict — any failure aborts | Any unreadable table raises ContaPlusReadError; whole conversion fails. Consistent with D-04. | ✓ |

**User's choice:** Uniform strict — any failure aborts.

### Q2 — usuarios.dbf extraction (likely holds credentials)

| Option | Description | Selected |
|--------|-------------|----------|
| Full dump like any table | Extract every field including credential-looking ones; conversion is fully local. | ✓ |
| Dump but drop credential fields | Omit password/credential-looking columns — fragile heuristic on an undocumented table. | |

**User's choice:** Full dump like any table.

### Q3 — Reader type for the undocumented group tables

| Option | Description | Selected |
|--------|-------------|----------|
| Typed SUBCTA, generic group tables | SUBCTA typed; grupos/usuarios/empresa generic column-preserving — no pii-test-data discovery. | |
| Typed readers for all four | Full typed readers for all four — requires pii-test-data schema discovery in Phase 2. | ✓ |

**User's choice:** Typed readers for all four.

**Notes:** Choosing typed readers for all four expands Phase 2 research scope — `pii-test-data/` schema discovery for grupos/usuarios/empresa, a gate STATE.md's init note only anticipated for Phase 3. Combined with uniform strict, schema drift in an undocumented table becomes a hard failure; thorough variant enumeration + defensive field resolution are the mitigation.

---

## Claude's Discretion

- Exact new type/attribute names on `ContaPlusData`, the company-selector parameter name, module layout.
- The ZIP extraction mechanism (extract-to-temp-dir vs. read entries from BytesIO + per-DBF temp bridging).
- Journal name-column header text and multi-sheet ordering.
- The CLI one-line summary format for multi-sheet conversions.
- Company-selector edge behavior: validate against a single-company ZIP; error on a raw `.dbf` input.

## Deferred Ideas

None — discussion stayed within phase scope. Roadmap/requirements adjustments noted (not new scope): CLI-02 reassigned Phase 4 → Phase 2; Phase 2 research scope expanded to include `pii-test-data/` schema discovery for the group tables.
