# Phase 1: Journal Slice - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 1-journal-slice
**Areas discussed:** Read API shape, Journal result representation, XLSX output styling, CLI surface & behavior, Phase scope (raised mid-discussion)

---

## Read API shape

### `read()` return type

| Option | Description | Selected |
|--------|-------------|----------|
| Container object | `read()` returns a `ContaPlusData` container; Phase 1 populates `.journal`, later phases add `.subcta`/`.balance`. Return type stable across all 5 phases. | ✓ |
| Journal directly | `read()` returns a `ContaPlusJournal`. Minimal now, but Phase 2 must change the return type — breaking. | |

### Strict/lenient parameter

| Option | Description | Selected |
|--------|-------------|----------|
| Strict-only now, add param in Phase 3 | No mode parameter in Phase 1; `read()` always raises. Phase 3 adds `lenient=`/`mode=` with a strict default — additive, non-breaking. | ✓ |
| Add the parameter now | `read()` takes the mode parameter from day 1; lenient raises `NotImplementedError` until Phase 3. | |

### Input type detection

| Option | Description | Selected |
|--------|-------------|----------|
| Sniff content magic bytes | Inspect leading bytes (DBF version byte; `PK` for ZIP). Accept DBF signatures, reject others with a structured error. No caller hint needed. | ✓ |
| Caller passes a format hint | `read()` takes an optional `filename`/`format` argument; trusts the caller. | |

**User's choice:** All three recommended options.
**Notes:** Container return type chosen explicitly to absorb the Phase 2/3 table readers without an API break.

---

## Journal result representation

### Per-row representation

| Option | Description | Selected |
|--------|-------------|----------|
| pandas DataFrame | `.frame` DataFrame with SEED-pinned dtypes; zero conversion for renderer/adapter/PWA; memory-efficient for huge journals. | |
| List of typed row objects | `.rows: list[JournalRow]` of frozen dataclasses; fully static-typed, no pandas in the public type. | ✓ |
| Both — typed rows + `.to_dataframe()` | Typed rows canonical, DataFrame on demand. | |

### Source metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Optional caller-supplied label | `read()` accepts an optional `source_name`; CLI/PWA pass the file's name for provenance. | ✓ |
| No source metadata in Phase 1 | Result carries only rows + skipped-memo count. | |

**User's choice:** Typed row objects (diverged from the DataFrame recommendation); optional caller-supplied label.
**Notes:** Type safety prioritised — pandas is kept out of the public API surface; the renderer and tax-workbench adapter convert internally.

---

## XLSX output styling

### Styling level

| Option | Description | Selected |
|--------|-------------|----------|
| Polished but restrained | Bold colored header, frozen header, auto-sized columns, proper number/date formats. | ✓ |
| Functional minimum | Bold header, frozen header, correct formats, default widths, no color. | |

### Amount column format

| Option | Description | Selected |
|--------|-------------|----------|
| Accounting, negatives in red | 2-decimal numbers, thousands separators; negatives in red. | ✓ |
| Accounting, negatives in parentheses | 2-decimal numbers, thousands separators; negatives as `(1.234,56)`. | |
| Plain 2-decimal number | `1234.56`, no thousands separator, plain minus. | |

### Header label language

| Option | Description | Selected |
|--------|-------------|----------|
| English headers | `Date, Account, Subaccount, Debit, Credit, Concept` — honors the English-everything rule. | |
| Spanish headers | `Fecha, Cuenta, Subcuenta, Debe, Haber, Concepto` — matches ContaPlus terms and the Spanish-speaking audience. | ✓ |

### Footer totals

| Option | Description | Selected |
|--------|-------------|----------|
| Rows only | Clean rectangular data block; totals/trial-balance are Phase 3. | ✓ |
| Include a totals footer | Footer row summing Debit and Credit. | |

**User's choice:** Polished but restrained; accounting format with red negatives; Spanish headers; rows only.
**Notes:** Spanish headers are a deliberate exception to the project i18n rule — the headers label Spanish-statutory accounting data; code/docs/CLI/errors stay English.

---

## CLI surface & behavior

### Output path argument

| Option | Description | Selected |
|--------|-------------|----------|
| Optional, auto-derive when omitted | `contaplus2xlsx DIARIO.DBF` → `DIARIO.xlsx`; explicit arg overrides. | |
| Required positional | Both arguments mandatory; omitting output is a usage error. | ✓ |

### Overwrite behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse unless `--force` | Error if target exists; `--force`/`--overwrite` allows replacement. Script-safe. | ✓ |
| Overwrite silently | Always write, replacing any existing file. | |
| Prompt to confirm | Ask interactively before overwriting. | |

### Success output

| Option | Description | Selected |
|--------|-------------|----------|
| Concise one-line summary | e.g. `out.xlsx — 3 journal rows (1 memo line skipped)`. | ✓ |
| Just confirm the file | e.g. `Wrote out.xlsx` — no counts. | |
| Silent on success | Print nothing, exit 0. | |

### Error presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Clean Rich error panel | Red panel with message, row, column, context; no traceback; exit 1. | ✓ |
| Plain stderr line | Single-line `error: …` to stderr, exit 1. | |

**User's choice:** Required positionals; refuse unless `--force`; concise one-line summary; clean Rich error panel.
**Notes:** —

---

## Phase scope (raised mid-discussion)

The user interjected: *"you only mention diario... there are more DBF files!"*

### Phase 1 scope

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Phase 1 journal-only | Honor the roadmap's vertical-slice design — `DIARIO.DBF` only. SUBCTA + group tables Phase 2; BALAN + operational tables Phase 3. | ✓ |
| Expand Phase 1 to more tables | Bring additional readers into Phase 1; requires a roadmap amendment. | |

### Non-journal DBF handling

| Option | Description | Selected |
|--------|-------------|----------|
| Detect and reject clearly | Check the DBF field signature; if not journal-shaped, raise a structured error naming it a non-journal table with multi-table support planned. | ✓ |
| Attempt to parse, fail on the rules | Treat any DBF as a journal; a SUBCTA file fails at D-E1 (no debe/haber column). | |

**User's choice:** Keep Phase 1 journal-only; detect and reject non-journal DBFs clearly.
**Notes:** The container return type (D-03) was already chosen to future-proof the API for the Phase 2/3 tables. The "detect and reject" choice added decision D-02 and a research pointer for the minimal journal field signature.

---

## Claude's Discretion

- Exact class names, package/module layout, and the `dbfread` bytes→temp-path bridge mechanism.
- Precise styling values — fill color, fonts, column-width algorithm, exact Excel number-format strings.

## Deferred Ideas

None — the other ContaPlus tables, ZIP input, the lenient path, and the PWA all sit in Phases 2–5 per the existing roadmap. No roadmap amendment needed.
