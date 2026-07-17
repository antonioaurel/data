# shared/ — shared layer (ADR 0002)

Single source of truth for what **desktop** (`pages/`) and **mobile** (`mobile/site/`)
share, to end the duplication (repeated colors, parallel dictionaries).

## What already exists
- **`tokens.json`** — canonical colors per **type** (local/personagem/evento/other) and per
  **category** (all 15). Edit here.
- **`build_shared.py`** — generates `tokens.css` from `tokens.json`.
  - `python3 shared/build_shared.py` → (re)generates `tokens.css`
  - `python3 shared/build_shared.py --check` → fails if out of sync (for CI)
- **`tokens.css`** — **generated** (do not edit by hand): exposes `--type-*` and `--cat-*`.

## How to consume it
Each frontend does `<link rel="stylesheet" href=".../shared/tokens.css">` and uses
`var(--type-local)`, `var(--cat-igreja)`, … instead of hardcoding hex. That way a color changes
in **one place only**.

## Migration (incremental, next steps)
1. Wire `tokens.css` into mobile (`app.css`) and desktop (`pages/*.html`) and swap the hex values
   for the variables. Done page by page, no big-bang.
2. Extract the **i18n dictionary** (PT/EN strings for navigation/labels) into `shared/i18n.json`
   and a small module both frontends consume (today it lives inside `app.js`).
3. Extract the **graph data model** (loading/adjacency) into a shared module.

See `docs/adr/0002-normalized-graph-model.md` and `0003-retire-wide-csv.md`.
