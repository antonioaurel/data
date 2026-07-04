# Project Dashboard — Tasks × PRs × Impact

One self-contained operator dashboard that joins the three views of the work
into a single page: **task state**, **pull-request state**, and the **app
impact** of each PR. The three sections are cross-linked — click any `#PR`
chip (or an impact count) to highlight that PR across all of them.

| File | Role |
|---|---|
| [`dashboard.html`](dashboard.html) | Generated dashboard (self-contained, embedded Roboto). |
| `gen_dashboard.py` | Generator. Joins the three sources below and renders the page. |

## Data sources (joined live)

| Section | Source | Notes |
|---|---|---|
| **Tasks** | [`../docs/task-evolution.md`](../docs/task-evolution.md) | Parsed from the pipe table — one row per GitHub issue, ordered by Merge Status. |
| **Pull Requests** | `gh pr list --json …` | Live state (open/draft/merged/closed), review decision, comment count, last-updated. Falls back to the task table's PR links when `gh` is offline. |
| **Impacts** | [`../Quality/modules-features-matrix/pr-impact.json`](../Quality/modules-features-matrix/pr-impact.json) | PR → functionality marks, written by the [review flow](../docs/pr-review-flow.md). |

The join key is the **PR number**: a task links to its live PR, and the PR links
to the functionalities its diff touches.

## Regenerate

```sh
cd projects/recife-history-connections/dashboard
python3 gen_dashboard.py            # live — queries gh
python3 gen_dashboard.py --no-gh    # offline — rebuild PR state from the task table only
```

Re-run after tasks change, a PR opens/merges, or `pr-impact.json` is updated by
the review flow. The `Generated … · PR data: live/offline` badge in the header
records which mode produced the current file.

## How it reads

- **Summary** — totals: tasks by status, open PRs, shipped (merged) tasks, distinct functionalities impacted.
- **1 · Tasks** — table by merge status, each row showing its issue, PR (with live state), and impact count. A subsystem filter at the top scopes all three sections.
- **2 · Pull Requests** — live PRs in bands by state (Open / Draft / Merged / Closed), newest first, each card linked back to its task.
- **3 · Impacts** — per PR, the functionalities it touches, grouped by subsystem (Desktop / Mobile / Platform).

Scope note: impact labels are derived from the `pr-impact.json` functionality
ids (`<subsystem>/<module>/<feature>`); the canonical taxonomy lives in
[`../Quality/modules-features-matrix`](../Quality/modules-features-matrix).
