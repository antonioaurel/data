# Prediction of attendance in events organized through Facebook

Predict how many people will **actually attend** events created on Facebook, from event
features and RSVP signals.

> **Status:** in progress. This README describes what the project will contain.

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

## Planned structure

```
event-attendance-prediction/
├── README.md
├── notebooks/       # exploration and experiments (Jupyter)
├── src/             # data collection + model code
├── data/            # local inputs/outputs (see .gitignore)
└── reports/         # results and figures
```

> This is an analysis project, so it uses `notebooks/` + `src/` — a different internal
> structure from the static-site projects. Each project has the structure that fits its type.
>
> **Note on data:** respect Facebook's Terms of Service and privacy — use only data you're
> allowed to access (e.g. your own events or public/aggregated data), and keep raw personal
> data out of the repository.
