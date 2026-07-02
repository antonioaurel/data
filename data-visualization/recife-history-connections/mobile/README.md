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

## Site (Phase 2)

`build.py` also pre-renders static HTML into `mobile/site/` (SSG) — the pages work with no
JavaScript; `site/assets/app.js` then enhances them:

| Page | Static (no-JS) | Enhanced (JS) |
|---|---|---|
| `site/index.html` (Home) | title, type chips, "comece por aqui" top-connected | live alias-aware search box |
| `site/list.html` (List) | all 567 cards (name, type badge, connections) | search, type filter chips, sort, inline connection expansion |

Pages fetch data from `../data` (no duplication). Assets are hand-written source under
`site/assets/`. **Initial route (Home) ≈ 7 KB gzip** — well under the 150 KB budget;
`list.html` ≈ 20 KB gzip; `search.json` (~11 KB gzip) loads only on first search.

View locally (from the existing server at repo root):
`…/recife-history-connections/mobile/site/index.html`

## Status

- **Phase 1 — data layer:** done, including `matrix.json`.
- **Phase 2 — Shell + Home + List:** done (SSG + search/filter/sort/inline-expand).
- Next: Phase 3 node detail (bottom sheet + `node/{id}.html` static pages). Card/name/connection
  links already target `node/{id}.html` — they resolve once Phase 3 builds those pages.
- Phases 4–8: ego-graph, map, **matrix**, browse/favorites/about, states/a11y/perf.
- The matrix is built **undirected/symmetric** — the source `relationship_type` values
  (`local`, `historical_event`, `person`, …) don't encode direction. The `pairs/` drill-down
  files are deferred to the Matrix phase.
