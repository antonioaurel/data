# 0001 — Derived-data pipeline (graph.json + content.json)

**Status:** Accepted · 2026-06-30

## Context

The site (matrix, diagram, stats) loaded the entire `data/lista-geral-do-mapeamento.csv`
(~812 KB, 24 columns) and only rendered after downloading and parsing all of it.
Measurements:

- `Dados consolidados` (47%) and `Fonte da descrição` (6%) are **never used** by the pages —
  the first is just a denormalized copy of what already exists in other columns; the second is
  an identical URL repeated across all 497 rows.
- `Descrição` (35%) is only used in the detail panel, when a node is clicked.
- To *draw* the graph, name + type + edges is enough (~32 KB).
- The `matrix` loaded the entire **d3** library just to use `d3.csv` (its CSV parser).
- The derived files were produced by ad-hoc, unversioned scripts (drift risk).
- The base **will be expanded**, so the process needs to be reproducible and validated.

## Decision

1. The **source of truth** remains `data/lista-geral-do-mapeamento.csv` (a Sheets export).
2. A **versioned `build.py`** reads the CSV, **validates** it, and generates two derived files:
   - `data/graph.json` (~32 KB) — nodes (name + type) + edges; enough to render.
   - `data/content.json` (~344 KB) — description/location/image per node; loaded **on demand**.
3. The **matrix** switches to `fetch` + `JSON` (no d3): it downloads `graph.json` and draws; the
   `content.json` loads in the background and only feeds the detail panel.
4. **CI** (`.github/workflows/build.yml`) runs `build.py --check` on every push: it fails if the
   committed JSON is out of sync with the CSV.
5. Unused files (the old `matrix.csv`, export dumps) moved to `../../Depreciated/`
   (outside the published folder), preserved via `git mv`.

## Consequences

**Better**
- The matrix's *first paint* drops from ~812 KB → ~32 KB (−96%); the heavy text loads afterward.
- The matrix no longer depends on d3 (−~73 KB and one blocking request to an external domain).
- Data generation becomes **a single reproducible, validated command**; CI prevents the
  published site from diverging from the base — important as the base grows.
- No visual change; the source of truth (the full CSV) is left intact.

**Pending / cost**
- There are now **committed derived files**: after editing the CSV you must run
  `python3 build.py` and commit the JSON (CI enforces this).
- The **diagram** still loads the full CSV via d3 (it uses more fields) — a future migration.
- The **15 interconnection column** limit (degree ≤ 15) remains; with the base's expansion,
  consider an explicit edge list (future ADR).
- The **inline** and **PT/EN** per-page code duplication remains (future ADR: assets/ + i18n).
