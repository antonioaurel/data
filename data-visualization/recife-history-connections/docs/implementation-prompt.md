# Implementation prompt — Conexões da História (mobile progressive exploration)

> Source spec for the mobile build under [`../mobile/`](../mobile/). Build in the phases at
> the end — don't try to do everything in one pass. Stop for review between phases.

## Scope amendments (current — override the text below where they conflict)

1. **Map is out of scope.** The base has no coordinates, so the Map projection is dropped:
   no `map.html`, no `neighborhoods.json`, no `has_geo` field, and the bottom nav is
   **Explorar · Favoritos · Sobre** (3 items). Projections are **three**: List, Graph, Matrix.
2. **Types concentrated on the three that exist in the base:** `place` (Local),
   `person` (Personagem), `historical_fact` (Fato Histórico). The other four spec types
   (institution, cultural_event, work, other) are not used; the Matrix is therefore **3×3**.
3. **Mobile components are centered** (title, search, chips, section headings, cards,
   "comece por aqui"), not left-aligned.

Everything else below still applies.

## Role & objective

Implement the mobile web version of Conexões da História — a historical knowledge graph of
Recife and Pernambuco (people, places, historical facts, institutions, cultural events,
works). The interaction model is **progressive exploration**: the user starts from
search/discovery, sees a list, opens a detail, and only then sees a focused graph. The full
network is never dumped on a small screen.

Stack: static HTML/CSS/JS front end + a Python build step, deployed on GitHub Pages. No
backend server, no database at runtime — Python turns the source spreadsheet into static
artifacts at build time. Deliver a fast, lightweight, accessible site that works on
entry-level Android and flaky connections. Performance and weight are requirements.

## Audience — why the design is what it is

Primary users are lower-income and student segments in Brazil (classes C and D/E; secondary/
high-school students). Public data (TIC Domicílios 2025) drives four hard facts:

- **Mobile-only.** 67% of class C and 87% of class D/E access the internet exclusively by
  phone (73% of high-school-level users). The phone is the product.
- **Entry-level devices.** HD+ Android (~360 px CSS width, weak CPU, old WebView). Design
  target is 360 px, validated up to 414 px.
- **Scarce, interruptible data.** Prepaid dominates; ~39% run out of data within 3 months.
  Heavy first loads mean a large share never opens the site.
- **Weak CPU.** Force-directed simulation stutters — the graph is a focused ego-graph,
  lazy-loaded, and never the entry point.

Design implication: **list-first, lightweight-first, graph and map on demand.**

## Non-negotiable constraints

- **Layout:** single column, base width 360 px, fluid to 414+; content max-width ~440 px
  centered on wider screens. Assume only ~600 px reliably above the fold.
- **Touch:** targets ≥ 48×48 px, ≥ 8 px apart. Body text ≥ 16 px.
- **Performance budget (measure and report actual sizes):**
  - Initial route (shell + home + list index): ≤ ~150 KB transferred (gzip), hard ceiling
    200 KB. No render-blocking third-party.
  - Graph engine loaded only on first graph open (lazy). Map library + tiles loaded only on
    explicit map open (lazy).
  - Per-node detail fetched on demand as small JSON; never load the whole graph for the list.
  - System font stack, or one self-hosted subset woff2 ≤ 30 KB with `font-display: swap`.
  - Lighthouse mobile (Moto-G-class, "Slow 4G"): Performance ≥ 90, FCP ≤ 2.0 s, TTI ≤ 3.5 s.
- Core content must render and be navigable **without JavaScript** (static HTML); JS is
  progressive enhancement.
- Ship a **service worker** caching shell + list index + visited nodes, so a user who runs
  out of data can still browse what they've seen.
- **Compatibility:** older Android WebView. Avoid bleeding-edge JS or transpile/polyfill; no
  framework unless justified.
- **Motion:** respect `prefers-reduced-motion`; minimal animation.
- **Language:** `lang="pt-BR"`. UI copy in Portuguese; code, identifiers, comments in English.

## Architecture — one model, four projections, two transversal patterns

One data model: the historical graph — nodes (`CH-xxxx`) + edges (`CX-xxxx`).

Four projections (views over the same data):

- **List** — default view. Covers all nodes. Sortable, filterable, inline connection
  expansion. The accessible spine of the app.
- **Graph** — ego-graph of one node. Tap a neighbor to recenter. Not the entry point.
- **Map** — only nodes with a validated neighborhood (Bairros_PE). Layer toggles by type.
- **Matrix** — the same connections as an adjacency matrix. Answers the aggregate question the
  ego-graph can't ("how densely do these groups connect?"). On mobile it renders aggregated by
  node type (7×7); on wide screens the same page expands to the dense node×node matrix. See its
  contract below.

Two transversal patterns (cut across all views):

- **Entry / discovery** — search (alias-aware), category chips, explore-by-neighborhood, and a
  "start here" of highly-connected nodes for serendipity.
- **Detail** — a bottom sheet opened from any view (list card, graph node, map pin, matrix
  cell → list → node).

This is **one responsive app**, not a separate mobile and desktop product. Larger screens
enrich the same code (multi-panel, denser matrix, full graph reachable) — never a second site.
Do **not** build a timeline view — the data is not inherently temporal (the Matrix is an
adjacency matrix of connections, not a period×theme grid).

## Data model & data layer (Python build)

Source spreadsheet sheets → English identifiers:

| Source sheet | Meaning | Key | Core fields (→ English) |
|---|---|---|---|
| Base | Canonical nodes | CH-xxxx | id, name, type, subtype, short_description, period, reference_location, municipality, notes, curation_status |
| Interconexoes | Consolidated edges | CX-xxxx | id, origin_id, destination_id, type, subtype, strength, description, period, notes, curation_status |
| Expansao_PE | Candidate edges | EX-xxxx | (same as edges) + evidence — **excluded from the public graph by default** |
| Bairros_PE | Neighborhood mapping | node ref | node_id, neighborhood, reference_location, municipality, scope, curation_status |
| Aliases | Name variants | AL-xxxx | id, node_id, canonical_name, alias, alias_type |
| Fontes | Source registry | FT-xxxx | id, title, source_type, author, year, url, notes |

Node type values: `place, person, historical_fact, institution, cultural_event, work, other`.

`build.py` reads the spreadsheet and emits deterministic static artifacts:

- `data/index.json` — `[{id, name, type, conn_count, has_geo}]`
- `data/search.json` — `[{id, name, type, aliases:[…]}]` (names/aliases normalized: lowercased,
  diacritics stripped)
- `data/node/{id}.json` — per-node detail: description, period, reference_location, sources
  (resolved FT), aliases, direct edges `[{target_id, target_name, target_type, type, strength}]`
- `data/neighborhoods.json` — validated-only geo: `[{node_id, name, type, lat, lng, neighborhood}]`
- `data/sources.json` — full FT registry
- `data/matrix.json` — aggregated type×type adjacency: for each unordered pair of node types
  (including same-type), `{type_a, type_b, count, strength_sum}`. Tiny (≤ 28 pairs). Connections
  undirected by default → symmetric. For the drill-down, either filter edges client-side by
  type pair or emit `data/pairs/{type_a}-{type_b}.json` listing those edges
  `[{origin_id, destination_id, type, strength}]` — keep it light.

Keep the data-quality step (fill-rate / validation report) and **fail the build (or warn
loudly) on broken references** — an edge to a non-existent node id, or a Bairros_PE row flagged
validated but missing coordinates.

**Static site generation:** the build should also pre-render static HTML (home, list, per-node,
per-category, per-neighborhood, about) from the JSON, so the site works without JS and loads
instantly. JS then enhances (live search, graph, map, bottom sheet). Treat SSG as the primary
architecture.

## Information architecture — all pages

Global chrome on every page: a fixed bottom nav (~56 px, safe-area insets) with
**Explorar · Mapa · Favoritos · Sobre**, a skip link, and an offline indicator when the
service worker serves cached content.

1. **Home / Explore (`/`)** — search bar, category chips, explore-by-neighborhood, "start
   here" most-connected nodes.
2. **List / Search results (`/list.html`)** — default projection. Cards (name, type,
   connection count). Sort + type filter chips. Doubles as search results.
3. **Node detail (`/node/{id}.html` + bottom sheet)** — description, type, period, reference
   location, sources, main connections. Buttons: "Ver conexões" (→ graph), "Abrir no mapa"
   (only if `has_geo`). Deep-linkable & shareable.
4. **Connections / ego-graph (`/graph.html#node={id}`)** — center node + direct neighbors.
   Direct/All toggle. Tap neighbor → recenter. Breadcrumb/back. Lazy-loaded.
5. **Map (`/map.html`)** — validated-geo nodes only, pins by type, layer toggles. Tap pin →
   mini detail. Lazy-loaded.
6. **Matrix (`/matriz.html`)** — adjacency matrix of connections. Mobile: aggregated 7×7
   type×type, tappable cell-by-cell. Wide screens: same page expands to dense node×node. Cell →
   filtered List → node detail.
7. **Categories browse (`/categorias.html`, `/categoria/{type}.html`)** — browse by type →
   filtered List.
8. **Neighborhoods browse (`/bairros.html`, `/bairro/{slug}.html`)** — browse by validated
   neighborhood → List or Map.
9. **Favorites (`/favoritos.html`)** — localStorage, no account.
10. **About / Sources (`/sobre.html`)** — context, methodology, credibility, full FT registry.
11. **Advanced: full graph (`/graph-completo.html`)** — optional whole-network view, clearly
    marked advanced, heavily lazy — never a primary path.

The four projections (List, Graph, Map, Matrix) are reachable via a **view switcher** on the
same data, not four disconnected tabs; keep the bottom nav to four items and expose projections
through the switcher and contextual entry points.

System states to design everywhere: initial loading (skeletons, not spinners), empty, no
search results, offline / data-depleted (serve cached, tell the user), node without geography
(hide "Abrir no mapa").

## Component & interaction contracts

- **List** — cards show name, type badge (color + icon + text), connection count. Sort:
  name / connection count / type. Filter: type chips (multi-select). Inline connection
  expansion reveals direct neighbors as a sub-list without leaving the list.
- **Search** — matches canonical names and aliases; diacritic-insensitive, case-insensitive;
  debounced. Renders through the List component.
- **Node detail (bottom sheet)** — opened from any view. ARIA dialog, focus trap, dismiss on
  backdrop/escape, safe-area aware. Always show sources. "Abrir no mapa" only when `has_geo`.
  Each node also has a full static page for sharing/SEO/no-JS.
- **Ego-graph (the most important behavior)** — center = selected node; direct neighbors
  fanned around it. Toggle "Diretas (n)" vs "Todas (m)". Tap neighbor → it becomes the new
  center, push previous onto a history stack. Breadcrumb + back restores prior centers
  (**required** — without recenter+breadcrumb the graph is a dead end). Edge stroke width ∝
  strength; node color = type (+ shape/icon as non-color cue). Provide a text-equivalent (the
  detail's connections list).
- **Map** — pins only for validated-geo nodes; color by type; layer toggles. Tap pin → mini
  bottom sheet + link to detail. Lazy-load library and tiles; consider a static preview
  fallback.
- **Matrix (reuse List + detail, don't reimplement):**
  - *What it is:* an adjacency matrix over the same nodes/edges; cell intensity from aggregated
    strength. Undirected/symmetric by default.
  - *Two responsive zoom levels, same URL `/matriz.html`, same app:* **mobile (primary)** =
    aggregated type×type (7×7), fits/readable/tappable; **wide (advanced)** = same page expands
    to dense node×node (responsive expansion, not a separate desktop site — if hinting on
    mobile, say "abre melhor em tela maior," never "acesse a versão desktop").
  - *Cell content (accessibility-critical):* always show the **number** (connection count);
    color/intensity is a secondary cue only — never color alone. Empty pairs render muted and
    non-interactive. Diagonal cells (same-type↔same-type) are valid.
  - *Drill-down:* tap cell → List filtered to the connections between those two types → tap a
    node → node-detail bottom sheet → "Ver conexões" opens the ego-graph. Every hop reuses
    existing components. The cell is the interactive asset; the full grid need not be "usable
    whole" on mobile.
  - *Rendering:* semantic HTML `<table>` (or CSS grid), no charting library; sticky headers
    using type badges; each cell a `<button>`/link ≥ 48×48 px with an `aria-label` like
    "Personagem ↔ Local: 12 conexões"; full keyboard nav. On narrowest widths may collapse to a
    triangle (symmetric). The dense node×node renderer (wide only) may need virtualization/
    canvas — lazy-load only when that view opens and only above the breakpoint.
  - *Direction:* if origin→destination direction is meaningful in Interconexoes (e.g.
    "influenced", "gave rise to"), the matrix is **directed** — do not mirror it; keep both
    triangles. **Confirm before assuming undirected.**

## Routing & shareable URLs

Static per-node pages (`/node/{id}.html`) are canonical and shareable. Filters use hash params
(`/list.html#type=person&sort=connections`); graph uses `/graph.html#node={id}`. Client JS may
intercept navigation for smoother transitions but must degrade to plain page loads. GitHub
Pages has no server rewrites — don't rely on them.

## Design system

Tokens for spacing, radius, and a node-type color palette; every type is **color + icon +
text label** (never color alone). Suggested type colors (adjust freely): place = teal,
person = purple, historical_fact = amber, institution = blue, cultural_event = pink,
work = coral, other = gray. Single column, generous touch targets, high contrast (WCAG AA),
no heavy shadows/gradients. Bottom nav fixed; content padded to clear it.

## Accessibility

Semantic HTML; core content usable without JS. Keyboard operable; visible focus;
skip-to-content link. Bottom sheet as a proper dialog; announce view changes. Contrast AA;
not color-only; `prefers-reduced-motion` honored. Images: meaningful alt; explicit
width/height to avoid layout shift; many nodes have no image — handle gracefully.

## Suggested repo structure

Project-first, kebab-case, lowercase. (Adapted here under `mobile/` inside the existing
`recife-history-connections/` project, sharing the source CSVs.)

```
mobile/
  README.md
  build/
    build.py          # CSV -> JSON + static HTML (SSG)
    quality.py        # fill-rate / reference-integrity report
  data/               # generated JSON (index, search, node/, neighborhoods, sources, matrix, pairs/)
  src/
    templates/        # page templates used by the build
    css/
    js/               # progressive enhancement (search, graph [lazy], map [lazy], sheet, sw)
  site/               # generated static site = GitHub Pages output
```

## Build & deploy

One command builds everything: `python build/build.py` → validates data, emits `data/*.json`
and static HTML into `site/`. GitHub Pages serves `site/` (or `docs/`). Keep the build
reproducible; commit generated output or build it in CI. Print a build report: node/edge
counts, fill rates, broken references, and transferred size of the initial route against the
budget.

## Phased delivery (in order; stop for review between phases)

1. **Data layer** — `build.py` + `quality.py`: source → JSON, integrity checks, build report.
2. **Shell + Home + List** — static HTML, tiny JS, alias-aware search, type filter, sort.
   Meet the performance budget here and report actual sizes.
3. **Node detail** — bottom sheet + static per-node pages, with sources and connections list.
4. **Ego-graph** — lazy engine, recenter + breadcrumb + direct/all toggle + strength-weighted
   edges.
5. **Map** — lazy Leaflet (or lighter), validated-geo pins, layer toggles.
5. ~~**Map**~~ — **dropped** (see Scope amendments: no coordinates in the base).
6. **Matrix** — `data/matrix.json` in the build; **3×3** type×type on mobile with cell →
   filtered List drill-down; dense node×node expansion on wide screens (lazy, above breakpoint).
7. **Browse + Favorites + About** — categories, neighborhoods, localStorage favorites,
   sources/methodology page.
8. **States + a11y + perf pass** — service worker/offline, empty/no-result states,
   Lighthouse run, real entry-level device test.

## Guardrails

- Prefer vanilla JS + tiny libraries. Before adding any dependency > ~30 KB or any framework,
  **stop and ask**, with the size cost stated. Justify every KB against the budget.
- Measure and report bundle/route sizes after phases 2, 4, 5.
- kebab-case, lowercase paths; consistent names between README and folders.
- Keep the pipeline reproducible; don't hardcode secrets; don't commit anything private.
- Git: propose commits with clear messages. Do not force-push, rewrite history, or delete
  branches/files without explicit confirmation.
- Write a short project `README.md`.

## Out of scope (MVP)

Backend/server, authentication, a content-management/editing UI, candidate edges
(Expansao_PE) in the public graph, and a timeline view. Note these as future work if relevant.
```
