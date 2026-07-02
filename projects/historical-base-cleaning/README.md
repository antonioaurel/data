# Historical Connections — Base Cleaning

Cleaning and validating the **data quality** of the
[Conexões da História](../recife-history-connections/) base.

> **Status:** in progress. This README describes what the project will contain.

## Goal

Make sure the base (`nodes.csv`, `edges.csv`, `aliases.csv`) is clean and trustworthy:
measure completeness, catch inconsistencies, fix or flag bad records, and track how
quality evolves over time.

## Data source

Consumes the base from the sibling project:

```
../recife-history-connections/data/
├── nodes.csv
├── edges.csv
└── aliases.csv
```

> Don't duplicate the data here — read it directly from the source project's folder.

## Planned checks

| Dimension | Example rule |
|---|---|
| **Completeness** | % of nodes missing a description, city, or image (fill rate) |
| **Uniqueness** | duplicate IDs and names |
| **Integrity** | edges pointing to non-existent nodes; aliases without a canonical id |
| **Consistency** | types/sub-types outside the expected vocabulary |
| **Validity** | broken image / source URLs |

## Planned structure

```
historical-base-cleaning/
├── README.md
├── checks/          # validation & cleaning scripts (Python)
├── reports/         # generated quality reports
└── index.html       # quality dashboard (placeholder for now)
```

> Some of these checks already exist inside the source project's `build.py`;
> the idea here is to split out and expand cleaning + quality monitoring as its own project.
