# ADR 0001 — No backend database: static JSON built from a spreadsheet source

- **Status:** Accepted
- **Date:** 2026-07-03
- **Scope:** The public site (the "Data" hub and `recife-history-connections`). Does **not**
  bind future, separately-deployed services (see "Revisit when").

## Context

The site is a **static site hosted on GitHub Pages** — there is no server runtime and no
place to run server-side queries. The dataset is small and curated (~556 nodes, ~3.8k
edges) and is **read-only** at runtime.

The data pipeline today is:

```
Google Sheet (nodes, edges, aliases)      ← human editing surface / source of truth
   │  pull_sheet.py            (download the published tabs)
   ▼
data/*.csv                                 ← versioned in git (history + reproducibility)
   │  build.py                 (validate + resolve edges by id→name→alias; generate)
   ▼
data/*.json  (graph, content, map, matrix, node/*, i18n)   ← what the frontend fetches
   │  deploy-pages.yml
   ▼
GitHub Pages (static)
```

Data integrity is enforced **at build time** (`build.py` fails on duplicate id/name and
unresolved origins; warns on broken edges / missing fields) and a **daily drift-check**
(`sync-sheet.yml`) fails if the committed data diverges from the sheet.

## Decision

**We will not introduce a backend database for the site.** The canonical data stays as
spreadsheet → git-versioned CSV → generated JSON. The static frontend consumes JSON only.

## Rationale

- **No runtime for it.** GitHub Pages serves static files; a DB would require separate
  hosting, ops, and cost for zero runtime benefit on a read-only visualization.
- **The data is small.** At this scale JSON loads instantly; a DB solves a scale/query
  problem we do not have.
- **Reproducible & offline.** CSV-in-git + a standard-library `build.py` means the whole
  build is deterministic, diffable, and runnable with no network or services.
- **Integrity is already covered** at build time and by the CI drift-check.
- **Editing stays accessible.** A spreadsheet is a friendly editing surface for a
  non-developer maintainer; a DB would need an admin tool or UI.

## Consequences

**Positive:** zero infrastructure and cost; reproducible/offline builds; full git history
of the data; simple mental model.

**Negative / accepted trade-offs:** no ad-hoc querying at runtime; validation is custom
Python rather than DB constraints (FKs/unique/enums); the editing surface is a spreadsheet,
not a typed store.

## Revisit when

This decision is about the **static site**. Reconsider a database if any of these appear:

- A **services / API layer** is added (dynamic runtime, writes, auth). Such a service would
  be a **separate, independently-deployed project** and may bring its own database
  (e.g. Postgres behind an API) — that is out of scope here and would get its own ADR.
- The dataset grows past what static JSON serves comfortably, or the client needs real
  querying — then evaluate **SQLite as a build-time source of truth** (still exporting the
  same JSON) or **SQLite-in-the-browser (sql.js)** before any server DB.
