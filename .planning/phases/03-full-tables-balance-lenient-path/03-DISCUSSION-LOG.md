# Phase 3: Full Tables, Balance & Lenient Path - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 3-full-tables-balance-lenient-path
**Areas discussed:** Lenient & the journal, Problems report contents, Recomputed trial balance, Table extraction scope

---

## Lenient & the journal

### Q1 — In lenient mode, what happens to a bad journal row?

| Option | Description | Selected |
|--------|-------------|----------|
| Journal goes best-effort too | Lenient also relaxes the journal: bad rows skipped → problems report, good rows kept. tax-workbench always calls strict, so its fail-loud contract is untouched. | ✓ |
| Journal stays strict always | Lenient relaxes only the other tables; a bad journal row still aborts the whole conversion even in lenient mode. | |

**User's choice:** Journal goes best-effort too.

### Q2 — How does the CLI expose lenient mode?

| Option | Description | Selected |
|--------|-------------|----------|
| Strict default, --lenient opt-in | CLI runs strict by default (matches the library read() default); --lenient opts into never-abort + problems sheet. | ✓ |
| Lenient default, --strict opt-in | CLI runs lenient by default; --strict opts into fail-loud. Friendlier for migration users but diverges from the library default. | |

**User's choice:** Strict default, --lenient opt-in.

### Q3 — In lenient mode, what if the journal can't be read at all?

| Option | Description | Selected |
|--------|-------------|----------|
| Record problem, continue without it | A whole-journal failure becomes one problems entry; conversion continues, still produces sheets for every other readable table. | ✓ |
| Journal failure still aborts | Lenient tolerates bad rows, but a structurally unreadable/absent journal is still a hard abort. | |

**User's choice:** Record problem, continue without it.

**Notes:** tax-workbench is the strict-only consumer — its contract is the reason
the journal can safely go best-effort in lenient mode without compromising the
project's core value.

---

## Problems report contents

### Q1 — Should the problems sheet include by-design memo-line skips?

| Option | Description | Selected |
|--------|-------------|----------|
| Genuine defects only | Problems sheet lists only things that went wrong; both-zero memo lines stay a separate surfaced count. | ✓ |
| Everything skipped, including memo lines | Every dropped row appears, tagged with its reason; literal reading of criterion #2 but produces huge sheets of non-problems. | |

**User's choice:** Genuine defects only.

### Q2 — What should each problems-sheet entry contain?

| Option | Description | Selected |
|--------|-------------|----------|
| Table, row, column, reason, value | Adds the offending value so a migrating user can locate and fix the bad record in ContaPlus. | ✓ |
| Table, row, column, reason | Minimal context; satisfies criterion #2 exactly but no specific bad value. | |

**User's choice:** Table, row, column, reason, value.

---

## Recomputed trial balance

### Q1 — At what level should the trial balance group the journal?

| Option | Description | Selected |
|--------|-------------|----------|
| Subcuenta level | One row per full subaccount code — canonical Spanish Sumas y Saldos. | |
| Cuenta level | One row per 4-digit cuenta — summarized Balance de comprobación. | |
| Both levels, one sheet | Hierarchical: cuenta subtotals + subcuenta detail in one sheet. | |
| Both levels, two sheets (free text) | Two separate flat sheets, one per level. | ✓ |

**User's choice:** Both levels, two sheets (free-text "Other" response).
**Notes:** Refines criterion #3's singular "sheet" → two sheets; still the same
BAL-02 recomputed balance, presented at both granularities.

### Q2 — What columns should the trial-balance sheets carry?

| Option | Description | Selected |
|--------|-------------|----------|
| Classic sumas y saldos | Code / Suma Debe / Suma Haber / Saldo Deudor / Saldo Acreedor; subcuenta sheet adds Descripción. | |
| Single signed saldo | Code / Total Debe / Total Haber / Saldo (one signed column). | |
| Classic + signed saldo (free text) | Both the classic split columns AND a signed Saldo column. | ✓ |

**User's choice:** Classic sumas y saldos plus the signed saldo (free-text "Other").

### Q3 — How should the BALAN "unreliable" disclaimer appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Banner row + tab name | Merged colored banner row + a signalling tab name. | |
| Banner row only | Just the in-sheet banner; plain tab name. | |
| Tab name only | Disclaimer only in the tab name. | |
| Conditional banner (free text) | Banner shown only when BALAN does not sum to zero (descuadre). | ✓ |

**User's choice:** Conditional banner — "If the Balance Sheet sums to zero, then
it's fine. Only when the balance sheet does not add up to zero we show the banner
row." (free-text "Other").

**Notes (follow-up clarification, plain text):**
- Descuadre check compares BALAN against *itself* (its own debit/credit totals),
  not BALAN vs the recomputed balance.
- Tolerance ("exact zero" vs a configurable `--precision=0.01`-style flag)
  explicitly delegated to research: "no idea really. let research decide what is
  feasible and practical in this context."
- Tab name stays plain `Balance`; recomputed Sumas y Saldos sheets always trusted
  (no pushback on these proposed defaults).

---

## Table extraction scope

### Q1 — What happens with a .dbf outside the known 10-table catalogue?

| Option | Description | Selected |
|--------|-------------|----------|
| Discover-and-dump everything | Every .dbf becomes a sheet; uncatalogued ones get a generic full-dump sheet. | |
| Known catalogue only | Only the 10 recognized tables produce sheets; an uncatalogued .dbf is ignored. | ✓ |

**User's choice:** Known catalogue only.

### Q2 — Should an uncatalogued .dbf at least be mentioned?

| Option | Description | Selected |
|--------|-------------|----------|
| Note it in lenient mode | One informational problems-sheet entry in lenient mode; strict mode silent. | ✓ |
| Fully silent | No sheet, no problems entry, no mention anywhere. | |

**User's choice:** Note it in lenient mode.

---

## Claude's Discretion

- Exact new type names and `ContaPlusData` attribute names; module/package layout.
- The `lenient` parameter name and the lenient problems-report type shape.
- Exact Spanish sheet-tab labels, sheet ordering, problems-sheet tab name and headers.
- Internal trial-balance computation mechanics (`Decimal` vs `float`).
- Whether the operational tables need anything beyond a `GenericTable` full dump.

## Deferred Ideas

None — discussion stayed within phase scope.

**ROADMAP criterion refinements noted (not new scope):**
- Criterion #3 singular "trial-balance sheet" → two sheets (cuenta + subcuenta).
- Criterion #3 unconditional BALAN disclaimer → conditional on a detected descuadre.
