---
status: partial
phase: 02-zip-subaccounts
source: [02-VERIFICATION.md]
started: 2026-05-16T12:30:00Z
updated: 2026-05-16T12:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end conversion with a real ContaPlus archive
expected: Running `uv run contaplus2xlsx pii-test-data/<single-company>.zip /tmp/out.xlsx` produces a success message like `out.xlsx — N journal rows, 2 sheet(s)` (more sheets if group tables present); no traceback. XLSX has a Diario sheet plus a Subcuentas sheet with all SUBCTA fields.
result: [pending]

### 2. Visual XLSX inspection of the Descripción column
expected: Opening the generated `/tmp/out.xlsx` shows a Diario tab with headers `Fecha, Cuenta, Subcuenta, Descripción, Debe, Haber, Concepto`; the Descripción column shows Spanish subaccount names (not blank) for rows whose subcuenta code exists in SUBCTA.DBF.
result: [pending]

### 3. Multi-company error with a real archive (if a multi-company archive exists)
expected: Running `uv run contaplus2xlsx pii-test-data/<multi-company>.zip /tmp/out2.xlsx` without `--company` exits with code 1 and a Rich error panel listing the actual company directory names from the archive.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
