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

The app is concentrated on the **three node types that exist in the base** — `Local`→`place`,
`Personagem`→`person`, `Fato Histórico`→`historical_fact`. The **Map projection is out of
scope** (no coordinates in the data): no `neighborhoods.json`, no `has_geo`, and the bottom nav
is Explorar · Favoritos · Sobre.

## Build

```bash
cd mobile/build
python3 build.py     # reads ../../data/*.csv, writes mobile/data/*.json, prints the report
python3 quality.py   # data-quality / reference-integrity report only (exit 1 on errors)
```

Standard library only, deterministic. Outputs (into `mobile/data/`):

| File | Shape | Purpose |
|---|---|---|
| `index.json` | `[{id,name,type,conn_count}]` | list rendering + fast filter/sort |
| `search.json` | `[{id,name,type,norm,aliases:[…]}]` | alias-aware, diacritic-insensitive search |
| `sources.json` | `[{id,title,source_type,author,year,url,notes}]` | source (FT) registry |
| `matrix.json` | `[{type_a,type_b,count,strength_sum}]` | type×type adjacency (symmetric), **3×3 = 6 rows** |
| `node/{id}.json` | detail + resolved edges/sources/aliases | fetched on demand per node |

`type` maps `Local→place`, `Personagem→person`, `Fato Histórico→historical_fact`
(see `common.TYPE_MAP`); `strength` defaults to `1`.

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
- **Phase 3 — Node detail (static pages):** done. `site/node/{id}.html` for every node
  (description, location, aliases, sources, connections grouped by type). Connection links
  resolve. Bottom-sheet (in-place detail) still to add.
- **Phase 5 — Matriz (3×3):** done. `site/matriz.html` renders the type×type table (semantic
  `<table>`, number always shown, neutral sqrt-scaled intensity, cells ≥ 60px with aria-labels).
  Each cell links to `list.html#pair=<a>-<b>`; `app.js` lazy-loads `data/pairs/{a}-{b}.json`
  (distinct nodes in that pair) and filters the list, with a "limpar" clear. Reachable from
  Home and List.
- **Phase 6 — Type colors unified with desktop:** done. Single source of truth in
  `app.css :root` (`--type-*` = desktop hues #4a90d9 / #e8833a / #5cb85c, + `--type-other`
  #9b59b6, each with `-bg` tint and AA `-ink`). No type hex outside `:root`; `app.js` reads none.
- **Phase 9 — Favoritos + Sobre/Fontes:** done. `sobre.html` (project context, methodology,
  FT source registry from `sources.json`) and `favoritos.html` (localStorage, rendered from
  `index.json`). Node pages get a ☆ Favoritar toggle; the bottom nav (Explorar · Favoritos ·
  Sobre) now points to real pages. Fixed the `.js-only` rule so it no longer clobbers each
  element's display (search/toolbar/fav-btn).
- **Phase 4 — Grafo (simplified):** done. `graph.html` reads `#node={id}` and renders a
  **radial SVG** (center node + up to 18 neighbors, no force simulation — cheap on weak CPUs,
  zero dependencies). Node color = type (JS reads the `:root` vars); edge width ∝ strength. Tap
  a neighbor → bottom panel (badge, name, short description) with "Ver detalhes" / "Ver
  conexões"; the latter recenters via `#node=` (hashchange, normal back). Node pages link to it.
- **Phase 8 — View switcher:** done. A segmented control (`role=tablist`) **Lista · Grafo ·
  Matriz** on the three projection pages, current tab `aria-selected`. Context is preserved via
  `sessionStorage`: `ctxNode` (set on graph/detail) drives the Grafo tab from anywhere (greyed
  with a reason when absent), and `ctxList` (the list's filter/search hash, kept in sync) makes
  the Lista tab return to your filtered list. Static default = plain navigation (no-JS safe).
- **Phase 10 — Offline + states/a11y:** done. `mobile/sw.js` (scope `mobile/` so it covers
  both `site/` and `data/`) precaches the shell + `index/search/matrix.json` and
  stale-while-revalidates everything else, so visited nodes stay browsable offline. `app.js`
  registers it (path computed per page depth) and shows an offline banner (`role=status`) on
  `offline`. Loading skeletons on graph/favorites; empty/no-result states throughout.
- **Phase 7 — Responsive layer:** done. Breakpoints are a **single source in CSS**
  (compact <640 · medium 640–1023 · expanded ≥1024), exposed via `body::after` content that
  `app.js` reads (`getMode`) with a `matchMedia` reactive hook (rAF-debounced). Medium → 2-col
  card grid. Expanded → header top-nav (bottom nav hidden), and the **List becomes multi-panel**:
  a card opens its detail in a right-hand pane (reusing the card/detail components, drill within
  the pane), instead of navigating. Same URL, no UA sniffing; static default is mobile-first
  single column (SSG-safe). The Grafo is reached from the pane's "Ver conexões" (link), not yet
  a simultaneous third panel.
- Remaining (optional polish): Phase 3 bottom-sheet (compact in-place detail); manual
  compact/expanded override toggle. (Map dropped.)
- The matrix is built **undirected/symmetric** — the source `relationship_type` values
  (`local`, `historical_event`, `person`, …) don't encode direction. The `pairs/` drill-down
  files are deferred to the Matrix phase.
