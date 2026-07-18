# Architecture

The structural decisions and their rationale. For the contracts between pieces
see [`SYSTEM-DESIGN.md`](SYSTEM-DESIGN.md); for movement see [`FLOW.md`](FLOW.md).

## Shape

Two loosely-coupled tiers that meet at one artifact:

```
┌── offline (Python) ─────────────┐        ┌── client (static, browser) ──┐
│ data/*.csv                      │        │ app/index.html    (tool)     │
│   └─ src/model.py ─► coeff.json ─┼──embed─┤ reports/index.html (dashboard)│
│      src/baseline.py (benchmark) │        │  localStorage (tool history) │
│ notebooks/  tests/  scripts/     │        └──────────────────────────────┘
└─────────────────────────────────┘
```

No server, no database, no build step. The offline tier produces
`model_coefficients.json`; the client tier embeds it and runs standalone.

## Module boundaries

| Directory | Role | Depends on |
|---|---|---|
| `data/` | CSVs (truth) + generated coefficient JSON | — |
| `src/` | `baseline.py`, `model.py` | `data/` |
| `tests/` | unit / data-integrity / regression | `src/`, `data/` |
| `notebooks/` | EDA + model narrative | `src/`, `data/` |
| `app/`, `reports/` | client apps | embedded coefficients |
| `scripts/` | matrices check + git hook | `app/`, `reports/`, `Skills/` |
| `Skills/`, `docs/`, `source-material/` | documentation | — |

Dependencies point one way (client never imports Python; Python never touches the
DOM). The only coupling is the embedded JSON, versioned by `model_coefficients.json.version`.

## Technology choices

### Why Python (offline tier)

- **Fit for the job.** This is data digitization, tabular modeling, and
  backtesting — Python's core strength. The whole pipeline (`csv`, arithmetic,
  a small fit) needs no more than the standard library; `pandas`/`matplotlib`
  appear only in the notebooks for exploration.
- **Notebook-native.** The project's deliverable includes an EDA/model narrative
  (`notebooks/`); Jupyter + Python is the standard, reviewable medium for that,
  and it's the structure the README commits to for analysis projects.
- **Testable and dependency-light.** `baseline.py`/`model.py` are pure functions
  over CSVs — `pytest` pins the formula, data integrity, and metrics with zero
  runtime services. `src/model.py` runs on a bare interpreter (no third-party
  import) so regenerating coefficients is a one-command, reproducible step.
- **Path to more.** If modeling grows (hierarchical/Bayesian rates on simulated
  data — see SPEC), the ecosystem (scikit-learn, statsmodels, PyMC) is already
  where the data lives — no language switch.
- **Continuity.** It reimplements a 2016 requirements-era system as *analysis*;
  Python keeps the model, tests, and narrative in one toolchain rather than
  splitting logic across a server language and a notebook language.

### Why static HTML + vanilla JS (client tier)

- The apps are small, self-contained, and must run **without a backend** (the
  coefficient JSON is embedded). A framework/build step would add weight and
  tooling for no gain at this size.
- Fits the host repo, which serves static project pages; the dashboard and tool
  drop into that hub with no infrastructure and can be published via the pinned
  githack link used elsewhere in the repo.
- Theme-aware, accessible, dependency-free pages are easy to keep correct and to
  screenshot-verify.

### Why CSV + JSON (no database)

- n≈20 events. CSVs in git *are* the database — with history, diff, and review
  for free. The coefficient JSON is a generated build product, small enough to
  embed. A DB would be infrastructure with nothing to store. (Revisit only if the
  tool accrues real multi-user history.)

### Why no Facebook Graph API

- The endpoints EVE imported guest lists and RSVPs from were removed in 2018
  (post–Cambridge Analytica). The system layer is unrecoverable, so the project
  is analysis over digitized/manual data, not live import.

## Deployment

Static files served as-is (locally `python -m http.server`; in the hub via the
project's static-page mechanism). The offline tier is developer-run: edit CSVs →
`python src/model.py` → the new coefficients are embedded on the next page edit.

## Cross-cutting: docs stay in sync with the UI

`scripts/check_matrices.py` + a pre-commit hook keep the component matrices
aligned with the two pages, and the `/sync-matrices` skill regenerates them.
See [`../Skills/COMPONENT-MATRICES.md`](../Skills/COMPONENT-MATRICES.md).
