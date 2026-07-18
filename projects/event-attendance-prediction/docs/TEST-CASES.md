# Test cases

Derived from the operation flow and the component matrices
([`../Skills/COMPONENT-MATRICES.md`](../Skills/COMPONENT-MATRICES.md)). Two tiers:
**automated** (Python, in `tests/`) and **manual UI** (the two pages). Selector
roots reference the identification matrix (matrix 4).

Run automated: `python -m pytest tests/` (22 tests).

## A · Automated — formula & data (`tests/`)

| ID | Area | Scenario | Expected |
|---|---|---|---|
| A1 | baseline | Σ count×prop, truncated per type | 12 for the fixture |
| A2 | baseline | per-type truncation `19×0.5` | 9 (not 9.5) |
| A3 | baseline | fake guests subtracted | 20×1.0 − 5 = 15 |
| A4 | baseline | effects multiplicative | −20% → 80; −50%,−50% → 25 |
| A5 | baseline | zero counts | 0 (no divide error) |
| A6 | baseline | **regression** over CSVs | estimates 22/20/29/32; MAE 3.0 vs article 4.0 |
| A7 | data | size CSV shape | 16 events, 4 per class |
| A8 | data | RSVP sums close | no_reply+maybe+confirmed = invited |
| A9 | data | attendance ≤ invited | holds for all |
| A10 | data | size ranges (table 6) | in range, except documented medium event 3 (6506) |
| A11 | data | present ≤ responses | holds per type |
| A12 | data | **documented inconsistency** 05-26 | responses sum 70 ≠ invited 69 (kept as printed) |
| A13 | data | **documented inconsistency** 05-26 | per-type attendance 37 ≠ article 35 |
| A14 | data | effect dates & % valid | dates ∈ experiment; −100…100 |
| A15 | model | rates fall with size | micro > small > medium; medium≈large |
| A16 | model | declined rate = 0, bounds | 0 ≤ rate ≤ 1 |
| A17 | model | predict with effects | −20% = ×0.8 |
| A18 | model | **metrics regression** | MAE 34.4, MAPE 24.4; experiment MAE < 4 |
| A19 | model | JSON contract | version 1; size × type keys present |

## B · Manual UI — estimation tool (`app/index.html`)

| ID | Screen | Precondition | Steps | Expected |
|---|---|---|---|---|
| B1 | APP-RSVP | step 2, all counts 0 | click **Next** | blocked; size badge reads "enter the counts" |
| B2 | APP-RSVP | — | enter counts totalling 100 / 250 / 2000 / 6000 | size = micro / small / medium / large |
| B3 | APP-EFF | valid counts | add effect −20%, Compute | estimate = base × 0.8; effect listed under result |
| B4 | APP-EFF | one effect added | click × on the row | row removed; effect no longer applied |
| B5 | APP-RES | after Compute | read decomposition | bars sum to Σ count×rate; range = ±RANGE_PCT[size] |
| B6 | APP-RES → HIST | after Compute | click **Save to history** | row appears with estimate and (lo–hi); button flashes "Saved ✓" |
| B7 | APP-HIST | a saved row | type a number in **Actual attendance** | error column = \|actual − estimate\| |
| B8 | APP-HIST | a saved row | click × delete | row removed; count updates |
| B9 | APP-RES | after Compute | click **New event** | all inputs reset; wizard back to step 1; no state leak (B2 re-derives cleanly) |
| B10 | APP-HIST | ≥1 row | click **Export CSV** | downloads `eve-history.csv`; header + one row per event, English columns |
| B11 | APP-HIST | empty history | click **Export CSV** | no-op (no empty file) |
| B12 | APP-HIST | ≥1 row | **Clear history** → confirm | history emptied; empty-state message shown |
| B13 | APP-NAV | any step | Back / Next | stepper dot state (`on`/`done`) tracks the active step |

## C · Manual UI — dashboard (`reports/index.html`, F2)

| ID | Screen | Precondition | Steps | Expected |
|---|---|---|---|---|
| C1 | DSH-KPI | default (All) | read KPIs | n=20; MAE 34.4; MAPE 24.4%; field-experiment MAE ≈3.10 |
| C2 | DSH-META | default | read metrics rail | mean accuracy ≈76%; events-by-size 7/5/4/4; model v1 |
| C3 | DSH-FLT | — | click a size chip | list + KPIs + charts + meter recompute for that size; chip `aria-pressed=true` |
| C4 | DSH-LIST | — | click an event row | detail banner shows predicted/actual/error; row `aria-selected=true` |
| C5 | DSH-SCAT | an event selected | observe scatter | selected point enlarged; other points dimmed |
| C6 | DSH-META | an event selected | read Error card | predicted / actual / abs error / % error match the row |
| C7 | DSH-LIST | an event selected | click the same row again (or Clear) | selection cleared; detail banner hidden |
| C8 | DSH-FLT+LIST | event selected in size X | filter to a different size | selection cleared (hidden event doesn't linger) |
| C9 | DSH-SCAT/CONV | — | hover a mark / bar | tooltip shows label + predicted/actual/error (scatter) or conversion % (bars) |
| C10 | layout | narrow viewport (<900px) | resize | rails stack; body scrolls; no horizontal overflow |
| C11 | theme | toggle OS/theme | switch light/dark | palette, charts, and text remain legible in both |

## Coverage notes

- **Guards/resets** (B1, B9) and **filter↔selection** (C7, C8) are the branch
  risks flagged in the operation flow — highest priority.
- The **coefficient contract** (A19 + embedded `RATES`/`ROWS`) is the
  cross-page seam; when `model_coefficients.json` changes, re-run A18–A19 and
  re-verify C1–C2 against the new numbers.
- UI cases are manual today; the identification matrix's `data-testid` roots are
  the anchor points if/when these are automated (Playwright/Cypress).
