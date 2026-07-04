# Modules & Features Matrix

Test-planning documentation for **Conexões da História do Recife** (PC + Mobile).
Two self-contained HTML pages generated from one data model.

| File | Doc | Role |
|---|---|---|
| [`matrix.html`](matrix.html) | **Modules & Features — reference** | Stable per release. Views: Modules · Impact · Reuse. |
| [`pr-impact.html`](pr-impact.html) | **PR Impact Tracking** | Living tracker, fed by the review flow. |

Open either in a browser (or publish as an artifact). Both share the same
subsystem navigation (top navbar / bottom bar): **Desktop · Mobile · Platform**.

## Reference doc — `matrix.html`

| View | Question it answers |
|---|---|
| **Modules** | What features does each module/page have? (one column per module) |
| **Impact** | Which functionalities affect which? (functionality × functionality) |
| **Reuse** | Which components are shared hubs, and what does each functionality use? |

**Impact model** — impact is *derived from shared resources*: two functionalities
are coupled when they share something. The coupling type shows on the cell:

- **C** shared JS code · **D** shared data · **S** shared state · **N** same route · **L** shared component/pattern

Symmetric (sharing is mutual). PC pages are separate inline-script files, so
cross-page "code" coupling is a repeated *pattern* (L), not shared code — only
same-page functionalities share real C.

## Tracking doc — `pr-impact.html`

One row per functionality, **Module and Feature in separate columns**, plus:

- **Total** — how many PRs have touched that feature (× + × + … ), live.
- **PR columns** — one per **real pull request** (number + title), **newest-first**.
  A mark means that PR's diff impacts that functionality.

Driven by [`pr-impact.json`](pr-impact.json), written by the PR review flow
(see [`../../docs/pr-review-flow.md`](../../docs/pr-review-flow.md)) — the board's
*Linked pull requests*. The committed seed is an **illustration** on the current
open PRs (#15/#16) and previous merged PRs (#7/#5/#4/#3/#2); the review flow keeps
it current. Manual edits in the browser override the seed and persist to `localStorage`.

Schema:

```json
{
  "<subsystem>": {
    "prs":   [ { "id": "pr-16", "label": "#16", "title": "Mobile interactive diagram" } ],
    "marks": { "<subsystem>/<module-slug>/<feature-slug>": ["pr-16"] }
  }
}
```

Row ids are emitted on each `<tr data-fid="...">`, e.g. `desktop/top-navigation/map`.

## Regenerate

```sh
cd projects/recife-history-connections/Quality/modules-features-matrix
python3 gen.py     # reads roboto-b64.txt + pr-impact.json → writes matrix.html AND pr-impact.html
```

## Files

| File | Purpose |
|---|---|
| `gen.py` | Generator. Functionality → resource data model; renders both docs. |
| `matrix.html` | Reference doc (generated). |
| `pr-impact.html` | PR tracking doc (generated). |
| `pr-impact.json` | PR → functionality impact data, written by the review flow. |
| `roboto-latin.woff2` / `roboto-b64.txt` | Embedded font (Roboto latin, Apache-2.0). |

## Known taxonomy gaps

The reference taxonomy predates two merged PRs: **Mobile Map page** (#5) and the
**Desktop About page** (#7) are not yet modelled as their own modules. Update
`gen.py` (the `MOBILE` / `DESKTOP` column lists) when reconciling.

Scope: **structure only** — PT/EN is treated as a translation detail.
