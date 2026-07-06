#!/usr/bin/env python3
"""Notify Claude Code that Codex left review comments on GitHub PRs.

This is a small bridge for the Codex -> Claude handoff. It does not keep a
daemon running; call it after Codex posts review comments, or from any wrapper
that detects new/updated PRs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


DEFAULT_REPO = "antonioaurel/data"
DEFAULT_LOG_DIR = ".pr-review-logs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


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
            "number,title,url,headRefName,baseRefName,author",
        ]
    )
    return json.loads(result.stdout)


def build_prompt(repo: str, info: dict[str, Any], extra: str | None) -> str:
    author = (info.get("author") or {}).get("login", "unknown")
    message = [
        "Codex reviewed a GitHub PR and left review comments.",
        "",
        f"Repository: {repo}",
        f"PR: #{info['number']} - {info['title']}",
        f"URL: {info['url']}",
        f"Branch: {info['headRefName']} -> {info['baseRefName']}",
        f"Author: {author}",
        "",
        "Please inspect the GitHub PR conversation if it is available without "
        "additional approval. If it is not available, use the review context "
        "included below instead of asking the user for permission.",
        "Address Codex's comments, and keep the fix narrowly scoped to the review findings.",
        "Do not make unrelated refactors.",
    ]
    if extra:
        message.extend(["", "Extra context:", extra])
    return "\n".join(message)


def notify_claude(prompt: str, pr: str | None, use_from_pr: bool) -> str:
    cmd = ["claude", "-p"]
    if use_from_pr and pr:
        cmd.extend(["--from-pr", pr])
    cmd.append(prompt)
    result = run(cmd)
    return result.stdout.strip()


def post_github_ping(repo: str, pr: str, body: str) -> str:
    result = run(["gh", "pr", "comment", pr, "--repo", repo, "--body", body])
    return result.stdout.strip()


def log_event(log_dir: str, pr_number: str, message: str) -> None:
    path = Path(log_dir) / f"pr-{pr_number}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now_iso()}\n\n{message.rstrip()}\n")


def append_discussion_summary(log_dir: str, pr_number: str, summary: str) -> None:
    path = Path(log_dir) / f"pr-{pr_number}-discussion-summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now_iso()}\n\n{summary.rstrip()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tell Claude Code that Codex reviewed one or more PRs."
    )
    parser.add_argument("prs", nargs="+", help="PR numbers or URLs")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo, default: {DEFAULT_REPO}")
    parser.add_argument("--extra", help="Extra context to include in the Claude prompt")
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help=f"Local execution log directory, default: {DEFAULT_LOG_DIR}",
    )
    parser.add_argument(
        "--from-pr",
        action="store_true",
        help="Pass --from-pr to Claude so it can resume a PR-linked session when available",
    )
    parser.add_argument(
        "--github-ping",
        action="store_true",
        help="Also post an @claude GitHub comment on each PR",
    )
    args = parser.parse_args()

    missing = [tool for tool in ("gh", "claude") if shutil.which(tool) is None]
    if missing:
        print("Missing required command(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    for pr in args.prs:
        info = pr_info(args.repo, pr)
        prompt = build_prompt(args.repo, info, args.extra)
        print(f"Notifying Claude about PR #{info['number']}...")
        log_event(
            args.log_dir,
            str(info["number"]),
            "Notifying Claude about Codex review.\n\nPrompt:\n\n" + prompt,
        )
        response = notify_claude(prompt, str(info["number"]), args.from_pr)
        if response:
            print(response)
            log_event(args.log_dir, str(info["number"]), "Claude response:\n\n" + response)
            append_discussion_summary(
                args.log_dir,
                str(info["number"]),
                "Claude response summary source:\n\n" + response,
            )
        if args.github_ping:
            body = (
                "@claude Codex has reviewed this PR and left comments. "
                "Please inspect the PR conversation and address the review notes."
            )
            url = post_github_ping(args.repo, str(info["number"]), body)
            print(f"Posted GitHub ping: {url}")
            log_event(args.log_dir, str(info["number"]), f"Posted GitHub ping: {url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
