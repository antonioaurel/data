# Architecture Decision Records (ADR)

Record of the project's architecture decisions. Each relevant decision becomes a
`NNNN-title.md` file (sequential numbering, never rewrite history — a decision that changes
another creates a **new** ADR that *supersedes* the previous one).

Format (short, based on Michael Nygard's template):

```
# NNNN — Title
Status: Proposed | Accepted | Superseded by ADR-XXXX
Context: why the decision had to be made
Decision: what was decided
Consequences: what gets better, what gets worse, what stays pending
```

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-derived-data-pipeline.md) | Derived-data pipeline (graph.json + content.json) | Accepted (source model superseded by 0002) |
| [0002](0002-normalized-graph-model.md) | Normalized graph model (nodes / edges / aliases) as the source | Accepted |
| [0003](0003-retire-wide-csv.md) | Retire the wide CSV (`lista-geral-do-mapeamento.csv`) | Accepted |

## Decisions still to record (planned)

Discussed but not yet implemented — they become ADRs once done:

- **Extract shared CSS/JS** into `assets/` (today everything is inline and duplicated per page).
- **i18n**: unify PT/EN into a single page with a text file, instead of two copies.
