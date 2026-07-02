# Implementation prompt — Conexões da História (consolidated)

> Single source of truth for the build (mobile app under [`../mobile/`](../mobile/)).
> Build in the phases at the end — don't do everything at once. Stop for review between
> phases; skip what's already done. UI copy in Portuguese; code, identifiers, comments in
> English.

## 1. Role & objective

Implement Conexões da História — a historical knowledge graph of Recife and Pernambuco. The
interaction model is **progressive exploration**: start from search/discovery → list → detail
→ only then a focused graph. The full network is never dumped on a small screen.

- **One responsive app, one URL, one codebase.** Larger screens expand the same code
  (multi-panel, denser matrix, full graph). Never a separate desktop site.
- Stack: static HTML/CSS/JS + a Python build step, deployed on GitHub Pages. No backend, no
  runtime database — Python turns the source into static artifacts at build time (SSG).
- Fast, lightweight, accessible on entry-level Android and flaky connections. Performance and
  weight are requirements (see §3).

## 2. Audience — why the design is what it is

Primary users: lower-income and student segments in Brazil (classes C and D/E; high-school
students). TIC Domicílios 2025 gives four hard facts:

- **Mobile-only.** 67% of class C and 87% of class D/E access the internet exclusively by
  phone (73% at high-school level). The phone is the product.
- **Entry-level devices.** HD+ Android (~360px CSS width, weak CPU, old WebView). Design
  target 360px, validated to 414px.
- **Scarce, interruptible data.** Prepaid dominates; ~39% run out of data within 3 months.
- **Weak CPU.** Force-directed simulation stutters — the graph is focused, lazy, never the
  entry point.

Design implication: **list-first, lightweight-first, graph and matrix on demand.**

## 3. Non-negotiable constraints

- **Layout:** single column on mobile, base 360px, fluid to 414+; content max-width ~440px
  centered on wider compact screens. Assume only ~600px reliably above the fold.
- **Touch:** targets ≥ 48×48px, ≥ 8px apart. Body text ≥ 16px.
- **Performance budget (measure and report):**
  - Initial compact route ≤ ~150KB gzip (currently ~7KB — stay well under). No render-blocking
    third-party.
  - Graph engine and Matrix dense renderer load only on demand / when their view opens.
  - Per-node detail fetched on demand as small JSON; never load the whole graph for the list.
  - System font stack, or one self-hosted subset woff2 ≤ 30KB with `font-display: swap`.
  - Lighthouse mobile (Moto-G-class, "Slow 4G"): Performance ≥ 90, FCP ≤ 2.0s, TTI ≤ 3.5s.
- Core content renders and is navigable **without JavaScript**; JS enhances.
- Ship a **service worker** caching shell + list index + visited nodes.
- **Compatibility:** older Android WebView. Avoid bleeding-edge JS / transpile; no framework
  unless justified.
- **Motion:** respect `prefers-reduced-motion`. **Language:** `lang="pt-BR"`.

## 4. Current scope (keep the prompt aligned)

- **Node types: 3 only** — `place` (Local), `person` (Personagem), `historical_fact`
  (Fato Histórico), plus a safe `other` (Outro) fallback in code. Applies to UI, build, app.js.
- **Map is OUT of scope.** No `neighborhoods.json`, no `has_geo`, no "Mapa" nav item, no
  map-coordinate quality metric.
- **Projections: 3** — Lista · Grafo · Matriz.
- **Matrix is 3×3** (6 unordered type pairs, all non-empty). Edge total must reconcile
  (e.g. 3881). Distribution example: place 351 · person 163 · historical_fact 53.
- **Mobile components are centered** — title, search, chips, section titles, list cards,
  "Comece por aqui". Cards stack name + (badge · connection count), centered.

## 5. Architecture — one model, three projections, two transversal patterns

- **One data model:** nodes (`CH-xxxx`) + edges (`CX-xxxx`).
- **Three projections** via an in-content **view switcher**:
  - **Lista** — default. All nodes. Sortable, filterable, inline connection expansion. The
    accessible spine.
  - **Grafo** — focused graph + bottom panel (§10). Not the entry point.
  - **Matriz** — the same connections as a 3×3 adjacency matrix by node type.
- **Two transversal patterns:** *Entry/discovery* (search, category chips, "comece por aqui")
  and *Detail* (a bottom sheet opened from any view).

Do not build a Map or a timeline view.

## 6. Responsive mobile ↔ desktop transition

Detect the **viewport & capabilities**, not the "device."

- Layout from the CSS viewport via media queries + `window.matchMedia`.
- **No** User-Agent sniffing, device DB, or `screen.width/height` (physical pixels break
  layout at DPR ~3).
- **Breakpoints (single source, shared CSS+JS):** compact < 640px (base 360) · medium
  640–1024px · expanded ≥ 1024px.
- **What changes:** compact = single column, one view, bottom nav. Expanded = multi-panel
  (List + detail + Graph), persistent switcher, full graph more reachable. Matrix stays 3×3
  (expand spacing, not content).
- **Reactive & state-preserving:** `matchMedia(q).addEventListener('change', …)` to react to
  resize/rotation live; preserve current node, projection, search, filters, scroll. Re-render
  layout, not state. Debounce with rAF. Prefer container queries with a media-query fallback.
- **SSG-safe:** static default is mobile-first single column, works with no JS.
- **Honest fallback:** never redirect to a desktop site / `m.` subdomain — same URL always.
  Heavy expanded views hint "abre melhor em tela maior." Optional manual "modo
  compacto/expandido" toggle persisted in localStorage.

## 7. Navigation & menus

Separate three concepts — do not merge:

- **Sections (where you are)** → bottom nav, **3 items: Explorar · Favoritos · Sobre**.
- **Projections (ways to view)** → in-content **view switcher** (segmented control):
  **Lista · Grafo · Matriz**. Switching preserves current node/search/filters.
- **Entry modes (ways in)** → inside Explorar, not the menu: search, category chips, "comece
  por aqui".

**Bottom nav (compact chrome):** fixed ~56px, `safe-area-inset-bottom`; icon + short label;
tap ≥ 48×48px; `aria-current` on active. Hidden on expanded (sidebar/top nav replaces it).
Bottom sheets and the graph render above the nav or temporarily hide it; never overlap.

**Top bar (per screen):** back affordance when drilled down; centered title; one contextual
action. Back follows the in-app history stack (matrix→list→node, graph navigation), not just
browser back.

**Screen map (mobile):**

| Screen | In bottom nav? | Reached from | Notes |
|---|---|---|---|
| Explorar (home) | Yes | Bottom nav | Search + chips + "comece por aqui". The hub. |
| Lista | No (projection) | Explorar / switcher | Default; also = search results. Sort + type filter + inline expansion. |
| Detalhe do nó | No | Tap any node (card, graph node, matrix→list) | Bottom sheet: description, period, sources, connections; "Ver conexões". Also `/node/{id}.html`. |
| Grafo | No (projection) | Detail "Ver conexões" / switcher | Focused graph + bottom panel (§10). Lazy. |
| Matriz | No (projection) | View switcher | 3×3 type×type; cell → filtered Lista → detail. |
| Categorias | No (entry mode) | Chip → `/categoria/{type}` | Leads into filtered Lista. |
| Favoritos | Yes | Bottom nav | localStorage nodes; empty state explains saving. |
| Sobre / Fontes | Yes | Bottom nav | Context, methodology, full FT registry. |
| Grafo completo (avançado) | No | Link in Grafo/Sobre | Advanced, heavily lazy; "abre melhor em tela maior". Not primary. |

**Back / history contract:** an in-app stack so back is predictable (graph navigation,
matrix→list→node, filter states push/pop). Device/browser back and top-bar back follow the
same stack. Deep links (`/node/{id}.html`, `/matriz.html#pair=person-place`) open directly
with Explorar as the root.

## 8. Data model & data layer (Python build)

Source spreadsheet sheets → English identifiers:

| Source sheet | Meaning | Key | Core fields |
|---|---|---|---|
| Base | Canonical nodes | CH-xxxx | id, name, type, subtype, short_description, period, reference_location, municipality, notes, curation_status |
| Interconexoes | Consolidated edges | CX-xxxx | id, origin_id, destination_id, type, subtype, strength, description, period, notes, curation_status |
| Expansao_PE | Candidate edges | EX-xxxx | (same as edges) + evidence — **excluded from the public graph** |
| Aliases | Name variants | AL-xxxx | id, node_id, canonical_name, alias, alias_type |
| Fontes | Source registry | FT-xxxx | id, title, source_type, author, year, url, notes |

Node type values: `place, person, historical_fact` (+ `other` fallback). Bairros_PE/geography
out of scope.

`build.py` emits deterministic static artifacts:

- `data/index.json` — `[{id, name, type, conn_count}]` (no `has_geo`).
- `data/search.json` — `[{id, name, type, aliases:[…]}]`, normalized (lowercased, diacritics
  stripped).
- `data/node/{id}.json` — per-node detail: description, period, reference_location, sources
  (resolved FT), aliases, direct edges `[{target_id, target_name, target_type, type, strength}]`.
- `data/sources.json` — full FT registry.
- `data/matrix.json` — 3×3 adjacency: per unordered type pair (incl. same-type)
  `{type_a, type_b, count, strength_sum}` (6 pairs). Undirected/symmetric; counts reconcile to
  the edge total. Drill-down: filter client-side or emit `data/pairs/{type_a}-{type_b}.json`.

Keep the data-quality step (fill-rate + reference integrity); fail/warn on broken references
(edge → unknown node id). No map/coordinate metrics.

**SSG:** the build also pre-renders static HTML (home, list, per-node, per-category, about) so
the site works without JS and loads instantly. JS enhances. SSG is the primary architecture.

## 9. Colors — single source of truth (mobile == desktop)

Type colors identical on mobile and desktop via one definition. No duplicated hex.

- Define the palette once as CSS custom properties on `:root`, using **desktop values as
  canonical**: `--type-place`, `--type-person`, `--type-historical_fact`, `--type-other`, plus
  readable on-color text vars `--type-*-ink` (darkest same-family stop).
- CSS consumes the vars via one utility (e.g. `[data-type="place"]` → `var(--type-place)`),
  applied the same in list, chips, matrix, graph legend.
- JS **reads from the vars, never hardcodes hex**:
  `getComputedStyle(document.documentElement).getPropertyValue('--type-'+type).trim() || …other`.
  Prefer setting `data-type` and letting CSS color; use JS lookup only where canvas/SVG needs
  an explicit color string.
- **Delete the old duplicate hex set** so there is exactly one place to change a color.
- Keep the non-color cue (icon + text label). Text on a type color uses `--type-*-ink`.
  Contrast AA. Dark mode overrides the same vars in one place.

## 10. Component & interaction contracts

**Lista (centered on mobile):** cards stack name + (badge · connection count), centered.
Sort: name / connections / type. Filter: type chips (multi-select). Inline connection
expansion reveals direct neighbors without leaving the list.

**Search (alias-aware):** matches names + aliases; diacritic-insensitive, case-insensitive,
debounced; renders through the Lista card.

**Node detail (bottom sheet):** opened from any view. ARIA dialog, focus trap, dismiss on
backdrop/escape, safe-area aware. Shows description, type, period, reference location, sources,
connections; "Ver conexões". Also a full static `/node/{id}.html`.

**Grafo — simplified (replaces the earlier elaborate ego-graph):**
- Focused graph: current node centered + direct connections.
- Tap a node → bottom sheet with summary (name, badge, short description) + "Ver detalhes" and
  "Ver conexões". Panel doesn't cover the whole screen; graph stays visible above it.
- Navigation through the panel, not in-graph state: "Ver conexões" recenters on the tapped node
  (plain navigation + normal back/history).
- **Dropped:** the "Diretas/Todas" toggle and in-graph breadcrumb stack. Back = standard.
- **Kept:** edge stroke width ∝ strength; node color = type (shared CSS vars + icon/shape);
  lazy-load the engine on first open. Provide a text-equivalent (the detail's connections list).

**Matriz (3×3):** cells = connections between two types; intensity from aggregated strength;
undirected/symmetric. **Always show the number**; color is secondary, never alone. Diagonal
cells valid. Drill-down: tap cell → Lista filtered to that type pair → node → detail →
"Ver conexões". Reuse components. Rendering: semantic `<table>`/grid, no charting library;
sticky headers with type badges; each cell a `<button>`/link ≥ 48×48px with an `aria-label`
like "Personagem ↔ Local: 12 conexões"; keyboard operable. Narrowest widths may collapse to a
triangle. Expanded: expand spacing, content stays 3×3. **Confirm direction:** if
origin→destination is meaningful in Interconexoes, the matrix is directed — keep both
triangles.

## 11. Routing & shareable URLs

Static per-node pages (`/node/{id}.html`) are canonical/shareable. Filters use hash params
(`/list.html#type=person&sort=connections`); graph `/graph.html#node={id}`; matrix
`/matriz.html#pair=person-place`. Client JS may intercept navigation but must degrade to plain
page loads. GitHub Pages has no server rewrites.

## 12. Design system

Tokens for spacing/radius; the type color palette lives **only** in `:root` (§9). Every type =
color + icon + text label. Mobile: single column, centered components (§4), generous touch
targets, high contrast (WCAG AA), no heavy shadows/gradients. Bottom nav fixed; content padded
to clear it.

## 13. Accessibility

Semantic HTML; core content usable without JS. Keyboard operable; visible focus; skip link.
Bottom nav as a `<nav>` landmark with `aria-current`. View switcher as a tablist/segmented
control. Bottom sheet as a dialog. Announce screen/projection changes politely; sensible focus
after navigation. Contrast AA; not color-only; `prefers-reduced-motion`. Images: meaningful
alt, explicit width/height; many nodes have no image — handle gracefully.

## 14. States

Loading: skeletons, not spinners. Empty Favoritos: explain how to save; link to Explorar. No
search results: offer to clear filters / browse categories. Projection N/A: greyed switcher
item with a one-line reason. Offline/data-depleted: nav still works for cached screens;
indicate cached mode.

## 15. Suggested repo structure

Project-first, kebab-case, lowercase. (Adapted here under `mobile/` inside the existing
`recife-history-connections/` project, sharing the source CSVs.)

```
mobile/
  README.md
  build/  build.py (CSV -> JSON + static HTML) · quality.py · common.py · sitegen.py
  data/   generated JSON (index, search, node/, sources, matrix, pairs/)
  src/    templates / css (single :root palette) / js (search, graph [lazy], matrix, sheet, sw)
  site/   generated static site = GitHub Pages output
```

## 16. Build & deploy

One command: `python build/build.py` → validates data, emits `data/*.json` + static HTML into
`site/`. GitHub Pages serves `site/`. Reproducible; commit generated output or build in CI.
Print a build report: node/edge counts, type distribution, matrix reconciliation, fill rates,
broken references, initial-route size vs budget.

## 17. Phased delivery (in order; stop for review; skip what's done)

1. **Data layer** — build.py + quality.py: source → JSON (3 types, matrix 3×3, no geo),
   integrity checks, report. ✅ done
2. **Shell + Explorar + Lista** — static HTML, tiny JS, alias-aware search, type filter, sort,
   centered components. Report sizes. ✅ done
3. **Node detail** — bottom sheet + static per-node pages, with sources and connections list.
   ✅ static pages done; bottom sheet pending
4. **Grafo (simplified)** — focused graph + bottom panel; tap node → sheet → "Ver conexões"
   recenters; edge thickness by strength; lazy.
5. **Matriz** — `data/matrix.json` 3×3; cell → filtered Lista → node detail.
6. **Colors unification** — single `:root` palette; JS reads vars; delete duplicate hex; verify
   identical rendered hex on 360px and ≥1024px. ✅ done
7. **Responsive layer** — viewport/matchMedia detection, shared breakpoints, state-preserving
   transition, multi-panel on expanded.
8. **Navigation** — bottom nav (Explorar·Favoritos·Sobre), view switcher (Lista·Grafo·Matriz),
   back/history stack.
9. **Favoritos + Sobre/Fontes** — localStorage favorites, methodology + source registry.
10. **States + a11y + perf pass** — service worker/offline, empty/no-result states, Lighthouse,
    real entry-level device test.

## 18. Guardrails

- Prefer vanilla JS + tiny libraries. Before any dependency > ~30KB or a framework, **stop and
  ask** with the size cost.
- Measure and report route/bundle sizes after phases 2, 4, 5, 6.
- One app, one URL, one codebase. No UA sniffing, no device DB, no separate desktop build.
- Type colors: one `:root` definition only; grep for stray hex on type elements → none remain.
- Reuse the existing Lista and detail components in every drill-down; don't reimplement.
- kebab-case, lowercase paths; consistent names. Reproducible pipeline; no secrets/private data.
- Git: clear commit messages. No force-push, history rewrite, or deleting branches/files without
  explicit confirmation.

## 19. Out of scope

Map/geography, timeline, candidate edges (Expansao_PE) in the public graph, backend/server,
authentication, a content-management/editing UI, native apps, server-side redirects, and any
User-Agent / device-based detection.
