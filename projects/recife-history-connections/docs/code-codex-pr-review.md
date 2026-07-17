# code-codex-pr-review — how it works

Diagram for the [`code-codex-pr-review`](../Skill/code-codex-pr-review.md)
orchestration. It drives the Claude → Codex pull-request review loop: the
orchestrator owns the queue and handoffs, Codex owns independent review judgment,
and the user owns the final merge decision.

Related: operational flow in [`pr-review-flow.md`](pr-review-flow.md) · design
consensus in [`claude-codex-consensus.md`](claude-codex-consensus.md).

## Review loop

```mermaid
flowchart TD
    A[Claude implementation agent<br/>opens or updates a PR] --> B[Reports PR number<br/>to the Orchestrator]
    B --> C{{Orchestrator: run review bridge}}
    C --> D["python3 tools/review_pr_with_codex_cli.py &lt;PR&gt;<br/>--notify-claude --notify-from-pr"]
    D --> E[Fetch PR into isolated ref<br/>+ temporary git worktree]
    E --> F[codex review --base origin/&lt;base&gt;<br/>local · stateless · one-shot]
    F --> G[Upsert single consolidated PR comment<br/>marker: codex-automated-review]
    G --> H{Read VERDICT block}

    H -- CONVERGED<br/>0 blocking --> STOP[Stop the loop]
    H -- INCONCLUSIVE<br/>missing / malformed / conflicts tags --> STOP
    H -- CHANGES_REQUESTED<br/>P1 / P2 --> I{Round ceiling reached?<br/>max 3 rounds}

    I -- Yes --> STOP
    I -- No --> J[Notify Claude<br/>claude -p --from-pr]
    J --> K[Claude pushes a fix<br/>to the same PR branch]
    K --> L{Head SHA changed?<br/>stale-review / SHA guard}
    L -- No, or same finding<br/>fingerprint repeats --> STOP
    L -- Yes, genuine change --> C

    STOP --> M[Escalation payload:<br/>unresolved blocking findings,<br/>what persisted, what changed,<br/>why it stopped]
    M --> N([User decides whether to merge<br/>merge guidance is advisory])
```

## Stop conditions (safety lock)

The orchestrator stops and escalates to the user when any of these fires. It only
iterates on **P1/P2** (blocking) findings — never on P3 nits.

```mermaid
flowchart LR
    subgraph STOP[Stop and escalate to user]
      direction TB
      S1[CONVERGED<br/>verdict = 0 blocking]
      S2[Round ceiling<br/>max 3 rounds]
      S3[Repeated fingerprint<br/>same blocking finding after fix]
      S4[INCONCLUSIVE<br/>verdict absent / malformed /<br/>conflicts with P-tags]
    end
    S1 --> U([User: merge / no-merge])
    S2 --> U
    S3 --> U
    S4 --> U
```

## Where the contact with Codex is registered

```mermaid
flowchart TD
    R[Codex review round] --> PC[GitHub PR comments<br/>canonical · durable]
    R --> LL[".pr-review-logs/<br/>local trace + dashboard"]
    R -. design-level, not PR-tied .-> CC[docs/claude-codex-consensus.md<br/>versioned]

    PC:::durable
    CC:::durable
    LL:::ephemeral

    classDef durable fill:#1b5e20,stroke:#c8e6c9,color:#fff;
    classDef ephemeral fill:#7f1d1d,stroke:#fecaca,color:#fff;
```

- **GitHub PR comments** — the record of record for PR-tied exchanges. Durable.
- **`docs/claude-codex-consensus.md`** — versioned record of Claude ↔ Codex
  design exchanges not tied to a specific PR.
- **`.pr-review-logs/`** — gitignored; lost when the container is reclaimed. Not a
  durable history.
