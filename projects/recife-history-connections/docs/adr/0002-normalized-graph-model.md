# 0002 — Normalized graph model (nodes / edges / aliases) as the source

**Status:** Accepted · 2026-07-01 · supersedes the source model of [0001](0001-pipeline-de-dados.md)

## Context

ADR 0001 kept the wide CSV (`Nome … Interconexão 1..15 …`) as the source of truth. That
format has hard limits that surfaced as the base grew:

- **Degree cap of 15** — a node cannot have more than 15 connections.
- **Silent broken links** — ~112 interconnection values pointed at names that were not
  entries (section headers like `Locais`, accents/typos like `Arquivo Publico`). The old
  build dropped them silently, so real connections never rendered.
- **Names as keys** — correcting an accent or renaming an entry broke its links.

## Decision

1. The **source of truth** is a Google Sheet with three tabs, exported as CSV into the repo:
   - `data/nodes.csv` — one row per entity, with a **stable `id`** (type prefix + suffix,
     e.g. `FH-0493`) and `legacy_id` for traceability.
   - `data/edges.csv` — one row per connection (`origin_id`, `target_id`,
     `relationship_type`, …). No degree cap.
   - `data/aliases.csv` — name-normalization layer (`alias` → `canonical_id`), so
     accent/typo/old-name variants resolve instead of breaking.
2. **`build.py`** reads the three tabs, validates, resolves each edge endpoint
   (`id` → `nodes.name` → `aliases.alias` → broken), and generates:
   - `data/graph.json` + `data/content.json` (unchanged shape — the site consumes these);
   - `data/lista-geral-do-mapeamento.csv` — the legacy wide CSV, now a **generated
     artifact** (not a source), kept only because `diagram.html` and `stats.html` still read
     it directly. Regenerating it keeps every page on the same data.
3. **Severities** (CI): duplicate id / duplicate name / unresolved origin → **fail**;
   broken edge, alias without `canonical_id`, self-loop, missing description/city → **warn**.
4. **Sync mechanism** (see `pull_sheet.py`, `.github/workflows/sync-sheet.yml`):
   - Editing happens in the Sheet; git stays the deploy source of truth and data ledger.
   - Manual **"Run workflow"** (workflow_dispatch) pulls the tabs, builds, and commits.
   - A **daily drift check** (schedule) runs `pull_sheet.py --check` + `build.py --check`
     and fails if the sheet is ahead of the repo — an alarm, it never auto-commits.
   - Not read live at runtime: the site serves committed static JSON (offline, versioned,
     no dependency on Google availability at build/serve time).

## Consequences

**Better**
- No degree cap; broken edges are explicit and auditable (2 left, down from ~112 — the
  alias layer resolved the rest).
- Stable IDs: renaming/accent fixes no longer break links.
- One reproducible, validated pipeline; CI blocks the site from diverging from the base.
- No visual change — `graph.json`/`content.json` keep their shape.

**Pending / cost**
- The wide CSV lives on as a generated artifact until `diagram.html` and `stats.html` are
  migrated to consume `graph.json`/`content.json` directly (future ADR).
- Publishing the sheet to the web (CSV) is required for `pull_sheet.py` and the CI to read
  it. The data is public, so this is acceptable.
