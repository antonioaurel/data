# Spec — Event attendance prediction

Modern reformulation of **EVE** (*Estimation of Variables to Events*), the system
specified in the master's article in [`source-material/`](../source-material/)
(Oliveira, 2016, C.E.S.A.R). EVE estimated how many people would actually attend
events organized through Facebook. This project keeps its domain model, estimation
logic and experimental data — and replaces the manually-tuned heuristic with a
learned model.

**Scope decision:** analysis/modeling only (`notebooks/` + `src/`). No web system,
no login, no CRUD screens — see [Historical note](#historical-note) for why.

## Goal

Predict the **real attendance** of an event from its RSVP signals and features,
i.e. learn the response→attendance conversion instead of asking an operator to
supply it.

- **Target:** number of people present (`presenca`).
- **Metrics:** MAE and MAPE, backtested on events with known turnout.
- **Benchmark to beat:** the original EVE field experiment closed its final
  phase at **91.5% accuracy** (worst event 79%, best 95%) — article, table 28.
  Accuracy there ≈ `min(pred, real) / max(pred, real)` per event.

## Domain model (from EVE §4.6–4.7 → data schema)

| Entity / field | Notes |
|---|---|
| Event: date, day-of-week, physical/virtual, public/private, event group | group ≈ event type (rehearsal, show, party…) |
| RSVP counts: `confirmacoes`, `talvez`, `recusas`, `sem_resposta` | the four Facebook response states |
| `convidados_fake` | organizer-seeded confirmations; subtracted from real confirmations |
| External effects: name, ±% influence | e.g. football final −20%, competing show −5% |
| Poster/video signals: likes, shares, views | optional; absent in the field experiment |
| `presenca` | ground truth, collected at the event |

**Size classes** (table 6): Micro ≤ 200 invitees · Small 201–1500 · Medium
1501–5500 · Large ≥ 5501. The size class matters: conversion collapses as events
grow (tables 7–10: Micro events convert ~75% of invitees; Large events ~2%).

## Baseline — the original EVE formula (§4.7.8)

1. Per response type *r*, expected attendees = `count_r × proportion_r`
   (proportions per event group, e.g. table 27: confirm 90%, maybe 60%,
   decline 0%, no-answer 10%). Sum over the four types; subtract fake guests.
2. If poster (x) and video (z) estimates exist: `[(x+y) + (z+y)] / 2`, where *y*
   is the RSVP-based estimate from step 1. (Field experiment had neither, so
   the estimate is just *y*.)
3. Apply each external effect as a multiplicative percentage
   (e.g. −20%, −5%, −5%).

Implemented in `src/baseline.py`; must reproduce the four predictions of
table 28 (21, 21, 23, 32) from the digitized CSVs as a sanity check.

## What the model must improve

EVE's central weakness: the per-response proportions were **informed by the
operator** ("who must have prior knowledge of the influence and weight of each
variable"). In the experiment they were hand-adjusted after every event
(table 27). The new model **learns** conversion rates from data, conditioned on:

- response type (4 counts),
- event size class,
- event group/type, day of week,
- external effects (as features, not manual multipliers).

Candidate approaches: per-category conversion regression (start simple:
linear/logistic per RSVP type), then hierarchical/beta-binomial if the data
supports it.

## Data

- **Seed data:** digitized tables from the article, in [`data/`](../data/)
  (16 events by size class, 3 pre-EVE rounds, 4 experiment rehearsals with
  predictions and turnout). Real but tiny (n≈23).
- **Extension:** synthetic/simulated events calibrated on the seed conversion
  rates, clearly separated from real data.
- **Constraints:** respect Facebook ToS and privacy (see README) — no personal
  data in the repo; the Graph API route no longer exists anyway.

## Historical note

The original EVE was a client-server web app (.NET + MySQL, Facebook login,
14 use cases, CRUD screens for attractions/effects/guests) whose core flow
imported guest lists and per-user RSVPs via the Facebook Graph API. Those
endpoints (`/{event}/attending|maybe|declined|noreply`, `rsvp_event`,
`user_events`, third-party profile data) were removed in 2018 after Cambridge
Analytica. The system layer is therefore unrecoverable and out of scope; the
CRUD entities survive here only as columns in the dataset.
