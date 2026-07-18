# Prediction of attendance in events organized through Facebook

Predict how many people will **actually attend** events created on Facebook, from event
features and RSVP signals.

> **Status:** in progress. Spec, seed data, baseline and a first learned-rates
> model are in place, with a wizard tool and a results dashboard.
>
> **Origin:** this project modernizes **EVE** (*Estimation of Variables to Events*),
> the system proposed in my 2016 master's article (C.E.S.A.R) — see
> [`source-material/`](source-material/) for the article and
> [`docs/SPEC.md`](docs/SPEC.md) for the translated spec.

## Goal

Facebook events collect "Going" / "Interested" responses, but real attendance is usually
a fraction of those. The goal is to model the gap: given an event's features and its RSVP
counts, estimate how many people will actually show up.

## Idea

| Step | What it does |
|---|---|
| **Collect** | event data (date, time, location, category, page/organizer, "Going"/"Interested" counts) |
| **Features** | lead time, day/hour, event type, organizer history, weather (optional), price |
| **Model** | regression to predict real attendance (or the going→attendance conversion rate) |
| **Evaluate** | backtest against events with known real turnout (MAE / MAPE) |

The project is in English (code, data, docs, and UI).

## Structure

```
event-attendance-prediction/
├── README.md
├── docs/             # SPEC · ARCHITECTURE · SYSTEM-DESIGN · FLOW · TEST-CASES
├── Skills/           # COMPONENT-MATRICES — module/impact/reuse/id matrices
├── source-material/  # the 2016 master's article (EVE)
├── notebooks/        # 01 EDA+baseline · 02 learned-rates model vs baseline
├── src/              # baseline.py (EVE formula) · model.py (learned rates)
├── data/             # CSVs digitized from the article + model_coefficients.json
├── tests/            # pytest: formula units, data validation, regression
├── scripts/          # matrices sync-check + git hook installer
├── app/              # estimation tool — 4-step wizard (static, no backend)
└── reports/          # results dashboard — F2 three-pane (static)
```

Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

| Command | What it does |
|---|---|
| `python src/baseline.py` | EVE formula on the digitized data (MAE 3.0 vs article's 4.0) |
| `python src/model.py` | fits learned rates, exports `data/model_coefficients.json` |
| `python -m pytest tests/` | 22 tests — formula, data integrity, pinned metrics |
| `python -m http.server 8000` | serve locally, then open `/app/` and `/reports/` |

The two HTML pages are self-contained (no backend): the model ships as
coefficients embedded from `data/model_coefficients.json`. The tool keeps its
event history in the browser (`localStorage`) and exports CSV to feed back into
the data / recalibration loop.

### Docs

| Doc | What it covers |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | goal, domain model, baseline, benchmark, constraints |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | structure & technology choices (incl. why Python) |
| [docs/SYSTEM-DESIGN.md](docs/SYSTEM-DESIGN.md) | components, data contracts, state |
| [docs/FLOW.md](docs/FLOW.md) | user / data / system / dashboard flows |
| [docs/TEST-CASES.md](docs/TEST-CASES.md) | automated + manual test cases |
| [Skills/COMPONENT-MATRICES.md](Skills/COMPONENT-MATRICES.md) | module-feature, cross-dependence, reuse, identification matrices |

### Modeling status

The learned-rates model replaces EVE's operator-informed proportions with rates
estimated from data. On the field experiment it matches the hand-tuned baseline
(MAE ≈ 3) **without** any manual input; across all 20 events MAE is 34 / MAPE 24%,
dominated by the medium/large classes where only 4 events each exist. Next:
simulated data calibrated on the seed rates to strengthen those classes.

> This is an analysis project, so it uses `notebooks/` + `src/` — a different internal
> structure from the static-site projects. Each project has the structure that fits its type.
>
> **Note on data:** respect Facebook's Terms of Service and privacy — use only data you're
> allowed to access (e.g. your own events or public/aggregated data), and keep raw personal
> data out of the repository.
