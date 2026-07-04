# Modules & Features Matrix

Test-planning documentation for **Conexões da História do Recife** (PC + Mobile).
A single self-contained HTML page that maps the app's structure and change-impact
across two subsystems, so test cases can be scoped from it.

Open [`matrix.html`](matrix.html) in a browser (or publish it as an artifact).

## Views

Navigate by **subsystem** (top navbar / bottom bar: Desktop · Mobile · Platform),
then by **view**:

| View | Question it answers |
|---|---|
| **Modules** | What features does each module/page have? (one column per module) |
| **Impact** | Which functionalities affect which? (functionality × functionality) |
| **Reuse** | Which components are shared hubs, and what does each functionality use? |
| **PR Impact** | Which PRs touch which functionalities? (Module / Feature separated) |

## Impact model

Impact is **derived from shared resources**: two functionalities are coupled when
they share something. The coupling type is shown on the cell:

- **C** — shared JS code / module
- **D** — shared data file / schema
- **S** — shared state (storage key / hash param)
- **N** — same route / navigation target
- **L** — shared visual component / pattern

It is symmetric (sharing a resource is mutual). PC pages are separate inline-script
files, so cross-page "code" coupling is a repeated *pattern* (L), not shared code —
only same-page functionalities share real C.

## PR Impact pipeline (fed by the review flow)

The **PR Impact** view is driven by [`pr-impact.json`](pr-impact.json). The PR review
instrument (see [`../../docs/pr-review-flow.md`](../../docs/pr-review-flow.md)) writes
which PRs touch which functionalities; regenerating the page renders the columns.

Schema:

```json
{
  "<subsystem>": {
    "prs":   [ { "id": "pr-4", "label": "#4 mobile-nav" } ],
    "marks": { "<subsystem>/<module-slug>/<feature-slug>": ["pr-4"] }
  }
}
```

Row ids are emitted on each `<tr data-fid="...">`, e.g. `desktop/top-navigation/map`.
Manual edits in the browser (add/toggle PR) override the seed and persist to
`localStorage`. The Desktop `PR 1 / PR 2` marks in the committed data are **example** data.

## Regenerate

```sh
cd projects/recife-history-connections/Quality/modules-features-matrix
python3 gen.py            # reads roboto-b64.txt + pr-impact.json → writes matrix.html
```

## Files

| File | Purpose |
|---|---|
| `gen.py` | Generator. Holds the functionality → resource data model; renders all views. |
| `matrix.html` | Generated, self-contained page (font embedded). The deliverable. |
| `pr-impact.json` | PR → functionality impact data, written by the review flow. |
| `roboto-latin.woff2` | Roboto latin subset (Apache-2.0), the embedded font source. |
| `roboto-b64.txt` | Base64 of the woff2, inlined by `gen.py` as a `@font-face` data URI. |

Scope: **structure only** — PT/EN is treated as a translation detail, not separate rows.
