# Claude ↔ Codex — design consensus (PR review loop)

Record of the exchanges between **Claude (Orchestrator/Opus)** and **Codex (reviewer/gpt-5.5)**
about the design of the review loop. Real channel: local `codex exec` (stateless, one-shot).
This file is where the operator **tracks the communication** when it is not tied to a specific PR.

> For PR-tied exchanges, the canonical channel is the **GitHub PR comments**
> (`## Codex automated review` + `<!-- claude-reply -->` replies) and the local log
> `.pr-review-logs/pr-<n>.md`.

## Round 1 — 2026-07-06 · The 3 gaps of the autonomous loop

**Claude asked** (perspective + pros/cons + what's missing), about:
1. Convergence detection (parse `[P1]/[P2]/[P3]` instead of a fixed string marker).
2. Single comment (edit the marker instead of stacking).
3. Safety lock (iterate only on P1/P2; a round ceiling).

**Codex answered** (summary):

- **Gap 1 — agrees with the direction, but disagrees with trusting the tags alone.** Recommends
  an **explicit, machine-readable verdict** emitted by Codex, with the tags serving as
  *cross-validation*, not as the primary signal:
  ```
  VERDICT: CONVERGED | CHANGES_REQUESTED | INCONCLUSIVE
  BLOCKING_FINDINGS: <n>
  NONBLOCKING_FINDINGS: <n>
  ```
  `CONVERGED` only with 0 blocking; `CHANGES_REQUESTED` with any P1/P2; `INCONCLUSIVE` when the
  verdict is missing, malformed, or conflicts with the parsed tags → escalate to the human.

- **Gap 2 — agrees.** Refines it: use a **hidden HTML marker** (not just the visible heading) to
  find the right comment unambiguously between bots:
  ```
  <!-- codex-automated-review: antonioaurel/data -->
  ## Codex automated review
  ```
  Include the round number, timestamp, base/head SHAs, and a link to the local log. Edit the most
  recent matching bot comment; warn in the log if there is more than one.

- **Gap 3 — agrees in principle, disagrees on the metric.** "The finding count stopped dropping"
  is weak (a fix can swap one problem for another). Recommends a **fingerprint of the blocking
  findings** (normalize path + line range + severity + title/body hash). Stop when: `CONVERGED`,
  or the round ceiling, or the **same fingerprint reappears** after a fix attempt, or
  `INCONCLUSIVE`. Never iterate on P3.

- **Do first:** **Gap 1** — without a reliable verdict the loop can't decide anything safely.

- **The missing gap (new, from Codex):** **SHA / stale-review guard.** Record the reviewed base
  SHA and head SHA, the head SHA after Claude's fix, and the round ID. Never treat a review as
  current if the head changed after the review started. Before re-reviewing, confirm that Claude
  actually changed the branch (or reported "no fix possible") — otherwise the loop re-reviews the
  same commit. Add an **escalation payload**: unresolved blocking findings, which ones persisted,
  what changed between rounds, and why the automation stopped.

**Consensus:** the 3 gaps + the priority (Gap 1 first) are **agreed**. Codex strengthened each
one with a concrete contract and added a 4th gap (the SHA guard) that Claude had missed.

### Agreed decisions (to implement)

1. **Convergence:** ask Codex for a `VERDICT/BLOCKING_FINDINGS/NONBLOCKING_FINDINGS` block;
   parse the `[P1/P2/P3]` tags as a consistency check; `INCONCLUSIVE` → escalate.
2. **Single comment:** hidden HTML marker + SHAs + round + link to the log; edit instead of posting.
3. **Lock:** iterate only on P1/P2; stop on `CONVERGED` / ceiling / repeated fingerprint / `INCONCLUSIVE`.
4. **SHA guard:** record base/head/post-fix SHAs + round ID; never re-review an unchanged head;
   escalation payload on stop.

---

### Operational note — how Codex is called in this environment

`codex exec` gets **blocked reading stdin** if the prompt comes as an argument and stdin stays
open (`Reading additional input from stdin...`). And macOS **has no `timeout`/`gtimeout`**.
Robust form used by the Orchestrator:

```sh
codex exec --sandbox read-only --cd <repo> --output-last-message reply.txt - < prompt.txt &
CPID=$!; # shell watchdog kills the PID after ~200s if it hasn't finished
```
