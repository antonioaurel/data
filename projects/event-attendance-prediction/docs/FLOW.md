# Flow document

How things move through the system — user actions, data, and the retrain loop.
The per-step spine (operation → screen → component → state → selector) lives in
[`../Skills/COMPONENT-MATRICES.md`](../Skills/COMPONENT-MATRICES.md#operation-flow);
this document is the higher-level picture.

## 1. User flow — estimation tool

```mermaid
flowchart TD
    A([Open tool]) --> B["Step 1 · Event\nname · date · type"]
    B -->|Next| C["Step 2 · RSVP\nconfirmed · maybe · declined · no_reply"]
    C -->|"total = 0"| G{{guard: Next blocked}}
    G --> C
    C -->|"total > 0 → size derived"| D["Step 3 · Effects\nadd ± % effects"]
    D -->|Compute| E["Step 4 · Result\nestimate + range + decomposition"]
    E -->|New event| B
    E -->|Save| F["History\nrow in localStorage"]
    F -->|after event| H["Register actual attendance → error"]
    F -->|Export CSV| I[(eve-history.csv)]
```

Guards and resets are the fragile points: the `total = 0` guard on steps 2–3,
and **New event** clearing all inputs.

## 2. Data flow — analysis pipeline

```mermaid
flowchart LR
    T["Article tables\n(source-material/)"] --> C["data/*.csv\n(digitized)"]
    C --> B["src/baseline.py\nEVE formula"]
    C --> M["src/model.py\nlearned rates"]
    M --> J[(data/model_coefficients.json)]
    B --> E["evaluation\nMAE · MAPE"]
    M --> E
    J --> APP["app/index.html\nRATES"]
    J --> RPT["reports/index.html\nROWS · CONV · META"]
    C --> N["notebooks 01 · 02\nEDA + comparison"]
```

The CSVs are the single source of truth; `model.py` is the only writer of the
coefficient JSON; the two pages are read-only consumers of it.

## 3. System flow — the recalibration loop

The one cross-boundary cycle, and the highest-value thing to keep intact:

```mermaid
flowchart LR
    U["Organizer uses tool"] --> R["logs actual attendance"]
    R --> X["Export CSV"]
    X --> D[(data/*.csv)]
    D --> F["src/model.py refit"]
    F --> J[(model_coefficients.json)]
    J --> U
```

The tool's output (real attendance) becomes the retrain input; the retrain
output (rates) is embedded back into the tool and dashboard. The coefficient
JSON is therefore a **shared contract** — see the cross-dependence matrix.

## 4. Dashboard flow (F2)

```mermaid
flowchart LR
    O([Open dashboard]) --> FL["Pick size filter"]
    FL --> RP["Repaint list + KPIs + charts + metrics rail"]
    RP --> SE["Select an event in the list"]
    SE --> DT["Detail banner + focus point in scatter + error breakdown"]
    RP --> HO["Hover a mark → tooltip"]
```

Interaction risk: a filter that hides the currently selected event must clear
the selection (otherwise the detail banner goes stale).
