---
title: PWA stays lean — vanilla UI on Pyodide, no React/shadcn
date: 2026-05-15
context: /gsd:explore session questioning the Phase 5 PWA stack
---

# PWA stays lean — vanilla UI on Pyodide

## Decision

The Phase 5 browser PWA drops React, shadcn, Tailwind, and the Vite component
pipeline. The UI is a minimal vanilla setup — an HTML page plus a small amount of
JS/TS — wiring a drop zone, a convert action, a download, and an error display.
The Python runtime stays **Pyodide** (real CPython in WASM).

## Why

The v1 PWA UI is four widgets (drop zone, convert, download, errors) and — per the
developer — will *stay* that way; anything more advanced would be a separate
project. A component framework + component library + build pipeline is machinery
with no payload for four static widgets.

The runtime is a separate axis from the UI, and it is **not** a "lighter is
better" choice — it is a trilemma:

- **Pyodide** is heavy (~7 MB core, ~17 MB with pandas) *because* it is real
  CPython compiled to WASM. That is the only reason `micropip.install("contaplus-reader")`
  runs the literal same library code as the CLI.
- **Brython** (and similar transpilers) are light (hundreds of KB) because they
  run Python *syntax* via a Python→JS transpiler — not CPython. They cannot run
  `pandas` at all, and pure-Python packages are hit-or-miss.

A featherweight runtime would force a second, browser-only reimplementation of the
reader — violating SEED architecture decision #3 ("CLI, PWA, and tax-workbench all
call the same function"). The developer chose to keep Pyodide and hold that line:
the PWA runs the exact same library as the CLI.

So "lean" applies to the **UI layer only**. The runtime weight is accepted and
mitigated where the roadmap already plans for it — service-worker caching, a
Web Worker, and the Phase 5 Pyodide spike.

## Consequences

- Phase 5 stack: HTML + minimal vanilla JS/TS + Pyodide (in a Web Worker) + a
  hand-written service worker + a PWA manifest. No React, no shadcn, no Tailwind.
- `STACK.md` / `SUMMARY.md`'s "Vite 6 + React + shadcn" recommendation is
  superseded for the PWA UI. (A no-framework Vite/TS setup, or `tsc`/`esbuild`,
  is fine if a TS build step is wanted — that is a Phase 5 detail.)
- The Phase 5 Pyodide spike narrows: it is no longer a "Pyodide vs PyScript vs
  Brython" bake-off. Pyodide is settled; the spike validates Pyodide + `micropip`
  + Web Worker + COOP/COEP + the lean static setup on Cloudflare Pages.
- PWA-V2-01 (multi-company picker UI) and PWA-V2-02 (preview table) are dropped
  from this project's scope — the developer considers anything beyond the
  four-widget app a separate project.
