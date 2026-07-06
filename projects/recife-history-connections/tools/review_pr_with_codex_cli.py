#!/usr/bin/env python3
"""Review GitHub PRs with the local Codex CLI and post the result back to GitHub.

Intended handoff:
  Claude opens a PR, then runs:
    python3 tools/review_pr_with_codex_cli.py 123

The script creates a temporary git worktree for the PR branch, runs
`codex review --base origin/<base>`, and posts the review as a PR comment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_REPO = "antonioaurel/data"
DEFAULT_INSTRUCTIONS = (
    "Review this PR in a strict code-review stance. Prioritize bugs, regressions, "
    "edge cases, security/data issues, and missing tests. Lead with findings ordered "
    "by severity and include file/line references when possible. If there are no "
    "blocking findings, say that clearly and mention residual risk or test gaps."
)
DEFAULT_LOG_DIR = ".pr-review-logs"
# Hidden marker identifying the single consolidated review comment so re-review
# rounds edit it in place instead of stacking new comments.
REVIEW_MARKER = "<!-- codex-automated-review -->"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(
    cmd: list[str],
    *,
    cwd: str | Path | None = None,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def ensure_tools() -> None:
    missing = [tool for tool in ("gh", "git", "codex") if shutil.which(tool) is None]
    if missing:
        raise SystemExit("Missing required command(s): " + ", ".join(missing))


def git_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip())


def pr_info(repo: str, pr: str) -> dict[str, Any]:
    result = run(
        [
            "gh",
            "pr",
            "view",
            pr,
            "--repo",
            repo,
            "--json",
            "number,title,url,headRefName,baseRefName,author,body,headRefOid",
        ]
    )
    return json.loads(result.stdout)


def linked_issue(info: dict[str, Any]) -> str | None:
    """Issue number linked to a PR: from a '#<n> \u00b7 ...' title or a 'Part of #<n>' body."""
    m = re.match(r"#(\d+)\b", info.get("title", ""))
    if m:
        return m.group(1)
    m = re.search(r"[Pp]art of #(\d+)", info.get("body", "") or "")
    return m.group(1) if m else None


def issue_header(repo: str, number: str | None) -> str:
    if not number:
        return ""
    try:
        data = json.loads(
            run(["gh", "issue", "view", number, "--repo", repo, "--json", "number,title,url"]).stdout
        )
        return (
            f"**Task:** {data['title']} \u2014 [issue #{data['number']}]({data['url']}) "
            "\u00b7 tracked in `docs/task-evolution.md` + board #3"
        )
    except Exception:
        return f"**Task:** issue #{number}"


def fetch_pr(root: Path, info: dict[str, Any]) -> str:
    pr_number = str(info["number"])
    pr_ref = f"refs/remotes/origin/pr-{pr_number}"
    # Force-update the ref (leading '+'): a stale `pr-<n>` ref left from a prior
    # review round would otherwise make us review an old commit. Then assert the
    # fetched SHA matches the PR's current head — GitHub's `pull/<n>/head` can lag
    # a branch push by a few seconds, and reviewing a stale head produces
    # phantom findings (the stale-SHA guard).
    # Update the base's remote-tracking ref explicitly (`+<base>:refs/remotes/...`)
    # so `codex review --base origin/<base>` always compares against the current
    # base. A standard clone's fetch refspec already keeps `origin/<base>` current,
    # but making it explicit removes that dependency and any stale-base risk.
    base = info["baseRefName"]
    run(
        [
            "git", "fetch", "origin",
            f"+{base}:refs/remotes/origin/{base}",
            f"+pull/{pr_number}/head:{pr_ref}",
        ],
        cwd=root,
    )
    fetched = run(["git", "rev-parse", pr_ref], cwd=root).stdout.strip()
    expected = info.get("headRefOid")
    if expected and fetched != expected:
        raise SystemExit(
            f"Stale PR head for #{pr_number}: fetched {fetched[:9]} but the PR head is "
            f"{expected[:9]}. `pull/{pr_number}/head` has not caught up with the branch yet — "
            "retry in a few seconds so the review runs against the current commit."
        )
    return pr_ref


def add_worktree(root: Path, pr_ref: str, pr_number: str) -> Path:
    temp_parent = Path(tempfile.mkdtemp(prefix=f"codex-pr-{pr_number}-"))
    worktree = temp_parent / "worktree"
    run(["git", "worktree", "add", "--detach", str(worktree), pr_ref], cwd=root)
    return worktree


def remove_worktree(root: Path, worktree: Path) -> None:
    run(["git", "worktree", "remove", "--force", str(worktree)], cwd=root, check=False)
    shutil.rmtree(worktree.parent, ignore_errors=True)


def extract_review(raw: str, worktree: Path) -> str:
    """Pull the final review text out of a `codex review` transcript.

    `codex review` streams the whole session to stdout (workdir banner, every
    `exec` tool call, the full diff). The agent's final message is everything
    after the last standalone `codex` marker line. Codex also sometimes prints
    that final message twice back-to-back, and file references carry the
    temporary worktree path, so we collapse the duplicate and rewrite paths to
    be repo-relative.
    """
    lines = raw.splitlines()
    marker_idxs = [i for i, line in enumerate(lines) if line.strip() == "codex"]
    block = "\n".join(lines[marker_idxs[-1] + 1 :]).strip() if marker_idxs else raw.strip()

    # Collapse an exact/near-exact duplication that restarts with the same line.
    first_line = block.splitlines()[0] if block else ""
    if first_line:
        pos = block.find(first_line, len(first_line))
        if pos != -1:
            head, tail = block[:pos].strip(), block[pos:].strip()
            if tail[:80] == head[:80] and abs(len(tail) - len(head)) <= max(20, len(head) // 5):
                block = head

    # Rewrite the temporary worktree path back to repo-relative file references.
    # codex reports realpath'd paths, so on macOS `/var/folders/...` comes back
    # as `/private/var/folders/...`; strip every variant, longest first.
    variants = {str(worktree), str(worktree.resolve()), "/private" + str(worktree)}
    for wt in sorted((v.rstrip("/") for v in variants), key=len, reverse=True):
        block = block.replace(wt + "/", "").replace(wt, "")
    return block.strip()


def codex_review(worktree: Path, base: str, instructions: str) -> str:
    base_cmd = ["codex", "review", "--base", f"origin/{base}"]
    # Older codex accepted custom instructions as a positional PROMPT alongside
    # --base. codex >= ~0.142 makes `--base <BRANCH>` and `[PROMPT]` mutually
    # exclusive, so try with instructions and fall back to a base-only review
    # (codex's built-in review) when that combination is rejected.
    result = run(base_cmd + [instructions], cwd=worktree, check=False)
    if result.returncode != 0:
        combined = (result.stderr or "") + (result.stdout or "")
        if "cannot be used with" in combined:
            result = run(base_cmd, cwd=worktree)
        else:
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
    # codex review streams the full session (banner + exec traces + diff) to
    # stdout; keep only the final review so the PR comment stays within GitHub's
    # 65536-char limit and reads cleanly.
    review = extract_review(result.stdout, worktree)
    if not review and result.stderr.strip():
        review = "Codex produced no review text.\n\nCodex stderr:\n" + result.stderr.strip()
    return review


def post_comment(repo: str, pr_number: str, body: str) -> str:
    result = run(["gh", "pr", "comment", pr_number, "--repo", repo, "--body", body])
    return result.stdout.strip()


def upsert_review_comment(
    repo: str, pr_number: str, review_body: str, head_sha: str, base_ref: str
) -> tuple[str, int]:
    """Post or update the single consolidated Codex review comment.

    Finds the newest comment carrying REVIEW_MARKER and edits it in place so
    repeated review rounds don't stack new comments; otherwise creates one.
    Prepends the marker plus a round/timestamp/head-SHA line. Returns
    (comment_url, round_number).
    """
    listed = run(["gh", "api", f"repos/{repo}/issues/{pr_number}/comments?per_page=100"])
    try:
        comments = json.loads(listed.stdout or "[]")
    except json.JSONDecodeError:
        comments = []
    marked = [c for c in comments if REVIEW_MARKER in (c.get("body") or "")]
    target = marked[-1] if marked else None  # GitHub returns comments oldest-first

    round_number = 1
    if target:
        m = re.search(r"[Rr]ound (\d+)", target.get("body") or "")
        round_number = (int(m.group(1)) if m else 1) + 1

    meta = (
        f"_Codex review round {round_number} · head `{head_sha[:9] or '?'}` "
        f"vs `{base_ref}` · {now_iso()}_"
    )
    body = f"{REVIEW_MARKER}\n{meta}\n\n{review_body}"

    if target:
        run(
            ["gh", "api", "-X", "PATCH",
             f"repos/{repo}/issues/comments/{target['id']}", "-f", f"body={body}"]
        )
        return target.get("html_url", ""), round_number
    return post_comment(repo, pr_number, body), round_number


def notify_claude(
    root: Path,
    repo: str,
    pr_number: str,
    log_dir: str,
    *,
    from_pr: bool,
    github_ping: bool,
) -> None:
    # This tool lives in projects/recife-history-connections/tools/, not at the
    # git root; resolve the sibling handoff script relative to THIS file so it is
    # found regardless of the repo root or the caller's cwd.
    script = Path(__file__).resolve().parent / "notify_claude_pr_review.py"
    cmd = [
        "python3",
        str(script),
        pr_number,
        "--repo",
        repo,
        "--log-dir",
        log_dir,
    ]
    if from_pr:
        cmd.append("--from-pr")
    if github_ping:
        cmd.append("--github-ping")
    run(cmd, cwd=root)


def discussion_summary(review: str) -> str:
    text = review.strip()
    if not text:
        return (
            "Codex produced no review output. There is no substantive review "
            "discussion yet; treat this as inconclusive."
        )

    lowered = text.lower()
    no_findings_markers = (
        "no blocking findings",
        "no findings",
        "no issues found",
        "no blocking issues",
    )
    if any(marker in lowered for marker in no_findings_markers):
        outcome = "Codex did not report blocking findings in the automated review."
    else:
        outcome = "Codex reported review findings that need triage."

    first_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            first_lines.append(stripped)
        if len(first_lines) == 5:
            break
    excerpt = "\n".join(f"- {line}" for line in first_lines)
    return (
        f"Outcome: {outcome}\n\n"
        "Main discussion points:\n"
        f"{excerpt or '- No excerpt available.'}\n\n"
        "Pending decision: the user should decide whether the PR is ready to merge "
        "after Claude addresses any findings or explicitly accepts the residual risk."
    )


def merge_guidance(review: str) -> str:
    text = review.strip().lower()
    if not text:
        return "Treat this review as inconclusive; do not merge based on automation alone."
    no_findings_markers = (
        "no blocking findings",
        "no findings",
        "no issues found",
        "no blocking issues",
    )
    if any(marker in text for marker in no_findings_markers):
        return "Merge can proceed if required CI and human checks are also green."
    return "Merge only after the findings are resolved or explicitly accepted by the user."


def work_summary(info: dict[str, Any], posted_review_url: str | None) -> str:
    lines = [
        f"- Reviewed PR #{info['number']}: {info['title']}",
        f"- Compared `{info['headRefName']}` against `{info['baseRefName']}`",
        "- Fetched the PR branch into an isolated local ref",
        "- Created a temporary git worktree for the review",
        "- Ran `codex review` against the base branch",
    ]
    if posted_review_url:
        lines.append(f"- Posted the full automated review comment: {posted_review_url}")
    lines.extend(
        [
            "- Posted this completion summary for the operator",
            "- Removed the temporary worktree",
        ]
    )
    return "\n".join(lines)


def log_event(root: Path, log_dir: str, pr_number: str, message: str) -> None:
    path = root / log_dir / f"pr-{pr_number}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now_iso()}\n\n{message.rstrip()}\n")


def update_dashboard(
    root: Path,
    log_dir: str,
    info: dict[str, Any],
    status: str,
    detail: str,
) -> None:
    path = root / log_dir / "dashboard.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# PR Review Operator Dashboard",
        "",
        f"Last updated: {now_iso()}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Status | {status} |",
        f"| PR | #{info['number']} - {info['title']} |",
        f"| URL | {info['url']} |",
        f"| Branch | {info['headRefName']} -> {info['baseRefName']} |",
        "",
        "## Detail",
        "",
        detail.rstrip(),
        "",
        "## Where to look",
        "",
        f"- Execution log: `{log_dir}/pr-{info['number']}.md`",
        "- Canonical discussion: GitHub PR comments",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex CLI review for one or more PRs.")
    parser.add_argument("prs", nargs="+", help="PR numbers or URLs")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo, default: {DEFAULT_REPO}")
    parser.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS)
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"Local execution log directory, default: {DEFAULT_LOG_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the review instead of posting it to GitHub",
    )
    parser.add_argument(
        "--notify-claude",
        action="store_true",
        help="After posting the Codex review, invoke the Claude handoff script.",
    )
    parser.add_argument(
        "--notify-from-pr",
        action="store_true",
        help="When notifying Claude, pass --from-pr so Claude can resume a PR-linked session.",
    )
    parser.add_argument(
        "--notify-github-ping",
        action="store_true",
        help="When notifying Claude, also post an @claude ping on the PR.",
    )
    args = parser.parse_args()

    ensure_tools()
    root = git_root()

    for pr in args.prs:
        info = pr_info(args.repo, pr)
        number = str(info["number"])
        print(f"Codex PR review started for #{number}: {info['title']}", flush=True)
        update_dashboard(
            root,
            args.log_dir,
            info,
            "RUNNING",
            "Codex review has started. The bridge is fetching the PR, creating an isolated worktree, and running `codex review`.",
        )
        log_event(
            root,
            args.log_dir,
            number,
            "\n".join(
                [
                    "Codex PR review started.",
                    "",
                    f"- Repository: {args.repo}",
                    f"- PR: #{number} - {info['title']}",
                    f"- URL: {info['url']}",
                    f"- Branch: {info['headRefName']} -> {info['baseRefName']}",
                ]
            ),
        )
        post_url = ""
        worktree: Path | None = None
        try:
            pr_ref = fetch_pr(root, info)
            log_event(root, args.log_dir, number, f"Fetched PR ref `{pr_ref}`.")
            worktree = add_worktree(root, pr_ref, number)
            log_event(root, args.log_dir, number, f"Created temporary worktree `{worktree}`.")
            review = codex_review(worktree, info["baseRefName"], args.instructions)
            log_event(root, args.log_dir, number, "Codex review output:\n\n" + (review or "No output."))
            # One consolidated comment: linked task info + the Codex review + merge guidance.
            header = issue_header(args.repo, linked_issue(info))
            review_body = (
                (header + "\n\n" if header else "")
                + "## Codex automated review\n\n"
                + f"{review or 'No review output was produced.'}\n\n"
                + "### Merge guidance\n\n"
                + f"{merge_guidance(review)}"
            )
            if args.dry_run:
                print(REVIEW_MARKER + "\n" + review_body)
            else:
                post_url, round_number = upsert_review_comment(
                    args.repo, number, review_body, info.get("headRefOid", ""), info["baseRefName"]
                )
                print(f"Posted Codex review (round {round_number}): {post_url}", flush=True)
                log_event(root, args.log_dir, number, f"Posted GitHub review comment: {post_url}")
                update_dashboard(
                    root,
                    args.log_dir,
                    info,
                    "COMPLETED",
                    "Codex review completed.\n\n"
                    "What was done:\n\n"
                    f"{work_summary(info, post_url or None)}\n\n"
                    "Discussion summary:\n\n"
                    f"{discussion_summary(review)}\n\n"
                    "Merge guidance:\n\n"
                    f"{merge_guidance(review)}",
                )
                if args.notify_claude:
                    notify_claude(
                        root,
                        args.repo,
                        number,
                        args.log_dir,
                        from_pr=args.notify_from_pr,
                        github_ping=args.notify_github_ping,
                    )
                    print(f"Notified Claude about Codex review for #{number}", flush=True)
                    log_event(root, args.log_dir, number, "Notified Claude about Codex review.")
        except Exception as exc:
            update_dashboard(
                root,
                args.log_dir,
                info,
                "FAILED",
                f"Codex review failed before completion.\n\nError: `{type(exc).__name__}: {exc}`",
            )
            log_event(root, args.log_dir, number, f"Codex PR review failed: {type(exc).__name__}: {exc}")
            raise
        finally:
            if worktree is not None:
                remove_worktree(root, worktree)
                log_event(root, args.log_dir, number, f"Removed temporary worktree `{worktree}`.")
        if post_url:
            print(f"Codex PR review finished for #{number}", flush=True)
            log_event(root, args.log_dir, number, "Codex PR review finished.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
