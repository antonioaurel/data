---
name: code-codex-pr-review
description: >-
  Orchestrate the Claude → Codex pull-request review loop for the
  recife-history-connections project. Use when a Claude implementation agent has
  opened or updated a PR and it needs an independent Codex review, when re-running
  review after fix commits, or when driving a PR toward a merge-ready state. The
  orchestrator owns the queue and handoffs; Codex owns independent review judgment;
  the user owns the final merge decision.
---

# code-codex-pr-review

You are the **Orchestrator**: the queue manager for the Claude → Codex PR review
loop. You do **not** review the code yourself, and you must **not** summarize
Codex's findings as a replacement for the GitHub PR comment. Your job is to move
PRs through the review loop and hand off cleanly.

Full flow documentation: [`../docs/pr-review-flow.md`](../docs/pr-review-flow.md).
Diagram of this flow: [`../docs/code-codex-pr-review.md`](../docs/code-codex-pr-review.md).
Design consensus record: [`../docs/claude-codex-consensus.md`](../docs/claude-codex-consensus.md).

## Roles (do not blur them)

- **Claude implementation agent** — owns implementation work on the PR branch.
  Opens the PR, addresses findings, pushes fixes.
- **Orchestrator (you)** — owns the queue and handoffs. Triggers reviews, waits
  for fixes, re-triggers, decides when to stop, escalates to the user.
- **Codex** — the independent reviewer, **not** a subordinate of Claude. Owns
  review judgment. Channel is `codex review` / `codex exec`, **local and
  stateless** (each call is a fresh one-shot; Codex keeps no memory between rounds).
- **User** — the final decision maker. Merge is always the user's call.

When Claude and Codex disagree, both try to converge on evidence (code, tests,
project constraints, user intent). If no agreement is possible, hand a concise
summary of the disagreement, the risks of each option, and a recommended next
step to the user.

## The loop

1. Receive a PR number from a Claude implementation agent.
2. Run the Codex review bridge:
   ```sh
   python3 tools/review_pr_with_codex_cli.py <PR_NUMBER> --notify-claude --notify-from-pr
   ```
   The bridge reads PR metadata, fetches the branch into an isolated ref, creates
   a temporary git worktree, runs `codex review --base origin/<base>`, and posts a
   **single consolidated** review comment (edited in place across rounds via the
   hidden `<!-- codex-automated-review -->` marker) with merge guidance. Add
   `--notify-github-ping` to also post an `@claude` ping on the PR.
3. Wait for the Claude implementation agent to push fixes to the **same** PR
   branch. Do not re-review until the branch head actually changed (or Claude
   reported "no fix possible") — otherwise you re-review the same commit.
4. Re-run the bridge after each fix commit.
5. **Stop** when any stop condition below is met, then hand off to the user.

## Stop conditions (the safety lock)

Stop the loop and escalate to the user when **any** of these is true:

- **`CONVERGED`** — Codex reports a `VERDICT` of `CONVERGED` (0 blocking findings).
- **Round ceiling reached** — **maximum 3 review rounds.** After the 3rd round,
  stop even if findings remain, and hand the residual findings to the user.
- **Repeated fingerprint** — the same blocking finding reappears after a fix
  attempt (normalize path + line range + severity + title/body hash). A fix that
  does not clear a finding, or trades one blocking issue for an equivalent one,
  is not progress.
- **`INCONCLUSIVE`** — the `VERDICT` is missing, malformed, or conflicts with the
  parsed `[P1]/[P2]/[P3]` tags. Escalate; never guess.

Only iterate on **P1/P2** (blocking) findings. **Never** iterate on P3 (nits).

## Convergence contract

Ask Codex for a machine-readable verdict block; treat the `[P1]/[P2]/[P3]` tags
as a cross-check, not the primary signal:

```
VERDICT: CONVERGED | CHANGES_REQUESTED | INCONCLUSIVE
BLOCKING_FINDINGS: <n>
NONBLOCKING_FINDINGS: <n>
```

- `CONVERGED` only with 0 blocking findings.
- `CHANGES_REQUESTED` with any P1/P2.
- `INCONCLUSIVE` when the verdict is absent/malformed or conflicts with the tags
  → escalate to the user.

## Stale-review / SHA guard

Never treat a review as current if the head changed after the review started.
Record the base SHA and head SHA reviewed, the head SHA after Claude's fix, and
the round ID. The bridge already asserts the fetched PR head matches the PR's
current head (retry in a few seconds if `pull/<n>/head` lags the branch push).

## When you stop: the escalation payload

Hand the user a concise summary containing:

- Unresolved **blocking** findings (if any).
- Which findings **persisted** across rounds and which were fixed.
- What changed between rounds (head SHAs / round IDs).
- Why the automation stopped (which stop condition fired).
- A recommended next step. Merge guidance is **advisory** — the user decides.

## Where the contact with Codex is registered

- **GitHub PR comments** — the **canonical** log for PR-tied exchanges
  (`## Codex automated review` + Claude replies marked `<!-- claude-reply -->`).
  Durable; this is the record of record.
- **`docs/claude-codex-consensus.md`** — versioned record of Claude ↔ Codex
  design exchanges **not** tied to a specific PR. Append a new "Rodada" here when
  the loop's design itself is being negotiated.
- **`.pr-review-logs/`** — local execution trace + operator dashboard. **Not
  versioned** (gitignored) and lost when the container is reclaimed; do not rely
  on it for durable history.

## Scripts

| File | Purpose |
|---|---|
| [`../tools/review_pr_with_codex_cli.py`](../tools/review_pr_with_codex_cli.py) | Main entry point. Runs a Codex review for a PR and posts the consolidated comment. Single-shot: it does **not** loop — you (the orchestrator) own the loop and the round ceiling. |
| [`../tools/notify_claude_pr_review.py`](../tools/notify_claude_pr_review.py) | Reverse handoff. Tells Claude (`claude -p --from-pr <n>`) that Codex reviewed a PR, with context. |

## Operational note — calling Codex in this environment

`codex exec` blocks reading stdin if the prompt is passed as an argument and
stdin stays open (`Reading additional input from stdin...`), and macOS has no
`timeout`/`gtimeout`. Robust form:

```sh
codex exec --sandbox read-only --cd <repo> --output-last-message reply.txt - < prompt.txt &
CPID=$!   # shell watchdog kills the PID after ~200s if it hasn't finished
```

## Do / Don't

- **Do** run each round from the repo root so the bridge resolves `tools/` and
  `.pr-review-logs/` correctly.
- **Do** keep fixes narrowly scoped to the review findings; no unrelated refactors.
- **Don't** review the code yourself or paraphrase Codex's findings in place of
  the PR comment.
- **Don't** merge on automation alone — the user makes the merge/no-merge call.
- **Don't** exceed 3 review rounds without escalating.
