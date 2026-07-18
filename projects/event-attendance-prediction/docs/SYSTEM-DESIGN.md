# System design

How the pieces fit and the contracts between them. Complements
[`ARCHITECTURE.md`](ARCHITECTURE.md) (the *why* of the structure) and
[`FLOW.md`](FLOW.md) (movement through it).

## Overview

Two decoupled halves that meet at one file:

- **Offline analysis** (Python): digitized data → fitted model → coefficients.
- **Client apps** (static HTML/JS): a wizard tool and a dashboard that *embed*
  those coefficients and run entirely in the browser.

```
data/*.csv ─► src/model.py ─► data/model_coefficients.json ─► app/ + reports/
```

There is no server, no database, no API. The coefficient JSON is the seam.

## Components and responsibilities

| Component | Responsibility | Does **not** |
|---|---|---|
| `data/*.csv` | Single source of truth (digitized article data) | compute anything |
| `src/baseline.py` | EVE formula, as a reference/benchmark | learn anything |
| `src/model.py` | Fit learned rates, evaluate, export JSON | serve or persist |
| `data/model_coefficients.json` | The shared contract (rates + metrics + ranges) | — |
| `app/index.html` | 4-step estimation tool; local history | fit the model |
| `reports/index.html` | Read-only results dashboard (F2) | write data |
| `notebooks/` | EDA + model-vs-baseline narrative | ship to users |
| `tests/` | Formula units, data integrity, pinned metrics | test the UI |
| `scripts/` | Matrices sync check + git hook install | run the app |

## Data contracts

### Coefficient JSON (`model_coefficients.json`)

The critical contract — two consumers depend on its exact shape.

```json
{
  "version": 1,
  "response_types": ["confirmed", "maybe", "declined", "no_reply"],
  "rates": { "micro|small|medium|large": { "<type>": 0.0 } },
  "metrics": { "mae": 0.0, "mape_pct": 0.0 },
  "size_ranges": { "micro": [0, 200], "...": [] }
}
```

Rules: keys `micro/small/medium/large` × `confirmed/maybe/declined/no_reply` are
frozen; adding a size class or response type is a breaking change for both pages.
`declined` rate is always 0 (nobody who declined attends).

### History record (`localStorage["eve-history-v1"]`, and CSV export)

```
{ name, date, type, size, counts:{confirmed,maybe,declined,no_reply},
  effects:[{desc, pct}], estimate, range:[lo,hi], attendance|null }
```

The CSV export flattens this to feed `src/model.py` on the next refit — the
column names match the CSV vocabulary in `data/README.md`.

## Estimation logic (client)

`estimate = Σ_type count_type × rate[size][type]`, then multiplied by each
external effect `(1 + pct/100)`. The size class is derived from total invited via
`size_ranges`. The likely range is `± RANGE_PCT[size]`, the mean percent error
observed per class in the in-sample evaluation. This mirrors `src/model.py`
`predict()` exactly — the browser re-implements the same arithmetic on the
embedded rates rather than calling out.

## State management

- **Tool:** transient wizard state in memory (`current`, `last`); durable event
  history in `localStorage`. No cross-tab sync; export CSV is the escape hatch to
  version control and the retrain pipeline.
- **Dashboard:** pure view over embedded constants (`ROWS`, `CONV`, `META`);
  `filter` and `selected` are the only UI state, both derived, both recomputed on
  every interaction (no partial repaint bugs by construction).

## Constraints & non-goals

- **No backend / DB** — n≈20 events; CSVs in git are the store. Revisit only if
  the tool gains real multi-user history.
- **No Facebook Graph API** — the endpoints EVE relied on were removed in 2018;
  input is manual counts, not imported RSVPs.
- **In-sample metrics** — the model is a v1 calibration, honest about it; the
  retrain loop is the path to better numbers, not a bigger model today.
