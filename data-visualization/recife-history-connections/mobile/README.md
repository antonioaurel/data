# Conexões da História — mobile

Mobile-first, progressive-exploration front end for the historical knowledge graph of
Recife/Pernambuco. Built for entry-level Android on scarce, interruptible data:
**list-first, lightweight-first, graph and map on demand.** Static HTML/CSS/JS + a Python
build step, served on GitHub Pages — no runtime backend.

The full spec (audience, constraints, performance budget, information architecture,
phased delivery) lives in [`../docs/implementation-prompt.md`](../docs/implementation-prompt.md).

## Data source

This subproject **shares the existing source of truth** — the CSVs in
[`../data/`](../data/) (`nodes.csv`, `edges.csv`, `aliases.csv`), themselves synced from
the Google Sheet. The mobile build only *reads* them and derives its own JSON; it never
edits the base.

Today the data has 3 node types (`Local`, `Personagem`, `Fato Histórico`), no coordinates
and no edge weights, so the spec's richer model degrades gracefully (see the build report).

## Build

```bash
cd mobile/build
python3 build.py     # reads ../../data/*.csv, writes mobile/data/*.json, prints the report
python3 quality.py   # data-quality / reference-integrity report only (exit 1 on errors)
```

Standard library only, deterministic. Outputs (into `mobile/data/`):

| File | Shape | Purpose |
|---|---|---|
| `index.json` | `[{id,name,type,conn_count,has_geo}]` | list rendering + fast filter/sort |
| `search.json` | `[{id,name,type,norm,aliases:[…]}]` | alias-aware, diacritic-insensitive search |
| `sources.json` | `[{id,title,source_type,author,year,url,notes}]` | source (FT) registry |
| `neighborhoods.json` | `[{node_id,name,type,lat,lng,neighborhood}]` | validated-geo pins (empty until coords exist) |
| `matrix.json` | `[{type_a,type_b,count,strength_sum}]` | type×type adjacency (symmetric), ≤ 28 rows |
| `node/{id}.json` | detail + resolved edges/sources/aliases | fetched on demand per node |

`type` maps `Local→place`, `Personagem→person`, `Fato Histórico→historical_fact`
(see `common.TYPE_MAP`); `strength` defaults to `1`; `has_geo` is `false` everywhere until
coordinates are added.

## Status

- **Phase 1 — data layer:** done (this build), including `matrix.json`.
- Phase 2+ (shell/home/list, detail, ego-graph, map, **matrix**, browse/favorites/about,
  states/a11y/perf) add `src/` templates/css/js and generated static HTML under `site/`.
- The matrix is built **undirected/symmetric** — the source `relationship_type` values
  (`local`, `historical_event`, `person`, …) don't encode direction. The `pairs/` drill-down
  files are deferred to the Matrix phase (edges can be filtered client-side meanwhile).
