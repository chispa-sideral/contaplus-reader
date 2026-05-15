# contaplus-reader

## What This Is

A standalone tool that reads Sage **ContaPlus** accounting exports (raw `.dbf`
tables and ContaPlus backup `.zip` archives) and extracts *all* their data into
usable formats. It ships as three artifacts from one repo: a **library**
(`contaplus-reader`, published to PyPI), a **CLI** (`contaplus2xlsx`,
`.dbf`/`.zip` → styled `.xlsx`), and a fully client-side **PWA** where anyone can
convert their ContaPlus files in the browser with no install and no upload. It is
for anyone migrating off Sage ContaPlus — and for tax-workbench, which currently
owns this logic and will become a thin consumer.

## Core Value

The library reads ContaPlus exports **correctly** — above all the journal, whose
strict, validated reading tax-workbench depends on for tax filings. Everything
else (CLI, PWA, styling) is delivery; correct extraction cannot fail.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. All are hypotheses until shipped. -->

**Library — reader core**

- [ ] Single bytes-first read API accepts raw `.dbf` or backup `.zip` (file-like / bytes, no filesystem path required)
- [ ] Typed per-table reader for the journal (`DIARIO.DBF`) porting all existing `tw-contaplus` business rules (D-A1…D-E3) and the structured error model
- [ ] Typed per-table readers for the other known ContaPlus tables (`SUBCTA.DBF`, `BALAN.DBF`, group-level tables) — schemas to be enumerated during research
- [ ] Strict typed API path — fails loudly on invalid data (preserves tax-workbench's contract)
- [ ] Lenient conversion path — extracts what it can, collects problems into a report, never aborts the whole file
- [ ] Journal output enriched with account/subaccount names when `SUBCTA.DBF` is present in a `.zip` (additive)
- [ ] ZIP handling: zip-slip-safe extraction from an in-memory buffer; recursive `DIARIO.DBF` discovery; multi-company disambiguation
- [ ] `ContaPlusReadError` — structured error carrying row/column/context, no dependency on `tw-domain`
- [ ] Self-contained result model (`ContaPlusJournal` and sibling per-table types) — no `tw-domain` types

**XLSX rendering**

- [ ] Shared, templated XLSX renderer producing nicely-styled output (one sheet per extracted table) — used by both CLI and PWA

**CLI**

- [ ] `contaplus2xlsx` converts a single `.dbf`/`.zip` to one `.xlsx`; multi-company `.zip` selected via a flag

**PWA**

- [ ] Minimal client-side PWA: drag-drop a ContaPlus file, download the styled `.xlsx`, errors surfaced clearly; conversion runs entirely in the browser

**Distribution & tests**

- [ ] Published to PyPI; `uv build` produces a wheel usable for PyPI *and* local dev (editable installs, `micropip` from a local wheel)
- [ ] Blob-free test suite — synthetic `.dbf`/`.zip` fixtures generated at collection time; existing journal coverage ported

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- tax-workbench's `tw-contaplus` rewrite as a thin adapter — that change is tracked in tax-workbench, triggered by the contaplus-reader v0.1 release
- Qt GUI / `ReadDBFWidget` — the standalone GUI is a web PWA; nothing ports from `tests/qt/`
- Encoding autodetect via header byte-29 — v1 forces `cp850` unconditionally; autodetect is a v2 concern
- Alpha-prefixed subaccount codes (e.g. `A4300001`) — v1 rejects non-numeric `SUBCTA`; explicitly deferred
- Two-pass "collect every bad row" validation in the strict API — v1 is first-fail; deferred to v2
- Batch / glob CLI input — v1 CLI is single-file
- Re-investigating the `DIARIO.DBF` format — already pinned in `SEED.md`

## Context

- The ContaPlus reading logic was built inside tax-workbench (phase 04,
  `packages/tw-contaplus/`). This project extracts it into a standalone, reusable
  tool so it can be shared via a URL and so tax-workbench's copy becomes a thin
  consumer rather than the source of truth.
- `SEED.md` (in the repo root) is self-contained: it embeds the `DIARIO.DBF`
  format reference, the journal business rules (D-A1…D-E3, error model), and the
  existing test/fixture inventory verbatim from tax-workbench's phase-04
  artifacts. The journal does not need format re-investigation.
- The user broadened scope at kickoff from "journal only" to "extract *all*
  ContaPlus data." The SEED documents `DIARIO.DBF` deeply, `SUBCTA.DBF` and
  `BALAN.DBF` only partially, and other tables (`grupos.dbf`, `usuarios.dbf`, …)
  not at all — so research must enumerate and spec the non-journal tables.
- The PWA runtime (Pyodide vs PyScript vs other) is undecided; `dbfread`,
  `pandas`, and `openpyxl` are all available in-browser. Open research questions
  in `SEED.md` cover cold-load UX, `micropip` resolution, service-worker caching,
  in-browser XLSX writing, and zip-slip-safe extraction from an in-memory buffer.

## Constraints

- **Tech stack (library + CLI)**: Python `>=3.13` — matches existing `tw-contaplus` code
- **Runtime deps**: `dbfread >=2.0.7` (pure-Python, MIT, read-only) for DBF reading; `pandas` + `openpyxl` for XLSX — all pure-Python / Pyodide-available
- **Dev deps**: `dbf` (ethanfurman, BSD) — fixture generation only, never a runtime dependency
- **Tech stack (PWA)**: shadcn UI, Pyodide/PyScript runtime (TBD by research), deployed to Cloudflare Pages (static-only hosting)
- **License**: LGPL-3.0-or-later — consistent with current `tw-contaplus`
- **Dependencies**: must NOT depend on `tw-domain` — the library returns its own result types
- **Compatibility**: read API must be bytes-first — the browser has no filesystem path; ZIP extraction must work from an in-memory buffer
- **Privacy**: PWA conversion is fully client-side — the ContaPlus file never leaves the user's machine
- **i18n**: English everything — this is an external, public project

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| All three artifacts (library + CLI + PWA) in one milestone | They share the reader; shipping together proves the single unified interface | — Pending |
| Typed reader per ContaPlus table, not a generic DBF dump | User wants *all* data extracted with real fidelity per table, not raw rows | — Pending |
| Strict typed API + lenient conversion path | tax-workbench needs fail-loud journal validation; migration users need extract-what-you-can | — Pending |
| Journal enriched with `SUBCTA.DBF` names when available | Account codes alone aren't human-readable; additive, so tax-workbench's wrapper is unaffected | — Pending |
| Shared, templated XLSX renderer for CLI and PWA | One renderer / template = consistent, nicely-styled output across both consumers | — Pending |
| PWA runtime (Pyodide vs PyScript) deferred to research | Cold-load UX and `micropip` resolution must be validated before committing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-15 after initialization*
