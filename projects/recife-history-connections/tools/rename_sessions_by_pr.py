#!/usr/bin/env python3
"""Prefix Claude Code (desktop) chat session titles with PR + module taxonomy.

Part of the Data PR-review flow. Canonical rule (v2 — taxonomy from the modules &
features matrix, Quality/modules-features-matrix/modules.json, issue #19):

    with PR:  "<Subsystem>/<Module> · #PR<N> - <title>"
    no PR:    "<Subsystem>/<Module> · [no PR] - <title>"

The path-like "<Subsystem>/<Module> · " prefix groups sessions by impacted
screen/module (alphabetical, like dir/subdir). The module is SEMANTIC and cannot
be derived from the session file, so it comes from a session->module map
(session_taxonomy.json); sessions absent from that map get only the "#PR<N> - " /
"[no PR] - " core. Multi-module sessions pick a primary; orchestration/tooling ->
Service/DevOps & Review; cross-cutting -> Platform/<module>.

NOTE: an agent has NO tool to rename its own (or another live) session — the only
live rename is the user in the app UI. This script is the automatable path: run
it with the app CLOSED to reconcile every session in one pass, then reopen.

There is no MCP/API to rename a session, so this edits the app's session-store
JSON files directly. These JSON files are the ONLY place titles are persisted
(there is no parallel leveldb/sqlite). Titles live in:

    ~/Library/Application Support/Claude/claude-code-sessions/<user>/<workspace>/local_<id>.json

Relevant fields per file: title, titleSource, cwd, originCwd, isArchived,
prNumber, prs[].

IMPORTANT — the app reads these files only at startup and then keeps titles in
memory. Editing a file while the app is running does NOT update the sidebar, and
an active session flushes its in-memory (old) title back to disk, reverting the
edit. So the ONLY reliable way to make a rename visible is:

    1. Quit the Claude desktop app completely (not just reload the window).
    2. Run this script (app closed -> nothing overwrites the files).
    3. Reopen the app -> it loads the new titles.

Running it while the app is open still writes correct files, but the change won't
show until the next full app restart, and running sessions may revert.

Other notes:
  * We set titleSource="user" so the app's classifier does not regenerate the
    title and wipe the prefix on the next run.
  * The prefix is idempotent: any existing "#<N> · " / "[no PR] · " is stripped
    before reapplying.
  * --skip-running (default) leaves sessions with a live process alone; with the
    app quit there are none, so everything in scope gets written.
  * Scope defaults to the Data project (cwd or originCwd under --repo-root),
    which includes .claude/worktrees/... sessions. Archived sessions are skipped.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime
from typing import Any

DEFAULT_REPO_ROOT = "/Users/antonio/git/Data"
DEFAULT_SESSIONS_DIR = (
    Path.home()
    / "Library/Application Support/Claude/claude-code-sessions"
)
LIVE_PID_DIR = Path.home() / ".claude/sessions"
BACKUP_ROOT = Path.home() / ".claude/backups"
DEFAULT_TAXONOMY = Path(__file__).with_name("session_taxonomy.json")

# Canonical module vocabulary (from modules.json) + provisional gaps. Used to
# validate the taxonomy map so typos surface as warnings instead of silent drift.
VALID_MODULES = {
    "Desktop": {"Top Navigation", "Home", "Diagram", "Matrix", "Fill Rate",
                "Sources", "Map"},
    "Mobile": {"Bottom Bar", "Top Header", "View Switcher", "Home", "List",
               "Graph", "Matrix", "Fill rate", "Sources", "About", "Node Detail",
               "Map"},  # Map = provisional gap (MOB-03/#28)
    "Platform": {"Theme", "Language / i18n", "Offline / PWA", "Responsiveness"},
    "Service": {"Entry & Navigation", "DevOps & Review", "API"},  # API = provisional gap
}

# Strip any prior prefix so re-runs stay idempotent. Tolerates stacked/corrupted
# prefixes (e.g. "#PR19 - #PR220- ...") and both separators/spacing variants:
# "#PR<N> - ", "#<N> · ", "[no PR] - ", "[no PR] · ", "#PR220- " (no space).
PREFIX_RE = re.compile(r"^((#PR\d+|#\d+|\[no PR\])\s*[·-]\s*)+")
# A leading "<Subsystem>/<Module> · " taxonomy prefix (anchored on the 4 subsystems).
TAXO_RE = re.compile(r"^(Desktop|Mobile|Platform|Service)/[^·]*·\s*")


def strip_prefix(title: str) -> str:
    """Strip taxonomy prefix then PR/no-PR prefix, so re-runs stay idempotent."""
    t = TAXO_RE.sub("", title or "")
    return PREFIX_RE.sub("", t)


def validate_taxonomy(taxo: str) -> str | None:
    """Return a warning string if `taxo` is not '<Subsystem>/<Module>' in the vocab."""
    sub, _, mod = taxo.partition("/")
    if sub not in VALID_MODULES:
        return f"unknown subsystem {sub!r}"
    if mod not in VALID_MODULES[sub]:
        return f"unknown module {mod!r} for {sub}"
    return None


# Main GUI binary of the desktop app: .../Claude.app/Contents/MacOS/Claude (capital
# C). Deliberately excludes the lowercase claude-code CLI
# (.../claude.app/Contents/MacOS/claude) and the "Claude Helper" subprocesses,
# whose executables end in "Claude Helper" / live under /Contents/Frameworks/.
CLAUDE_APP_BINARY_SUFFIX = "Claude.app/Contents/MacOS/Claude"


def _process_table() -> list[tuple[int, str]]:
    """(pid, executable-path) for every process, from `ps` (macOS `comm` = full path)."""
    try:
        r = subprocess.run(["ps", "-A", "-o", "pid=,comm="], capture_output=True, text=True)
    except OSError:
        return []
    table: list[tuple[int, str]] = []
    for line in r.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            try:
                table.append((int(parts[0]), parts[1]))
            except ValueError:
                pass
    return table


def claude_pids() -> set[int]:
    """PIDs currently owned by a real Claude process (GUI app or claude-code CLI).

    Used to tie session liveness to process IDENTITY: a bare os.kill(pid, 0) only
    proves *some* process holds the pid, so a stale pid file (process gone, file
    left behind) or a recycled pid would falsely read as "alive". Matching the pid
    against actual Claude processes avoids that false abort. See PR #42 review.
    """
    return {pid for pid, comm in _process_table() if "claude" in comm.lower()}


def desktop_app_running() -> bool:
    """True if the Claude desktop (Electron) GUI process is running.

    Checked IN ADDITION to live CLI sessions: the app can be open with no active
    session (e.g. sitting on the home screen), yet it still holds every session's
    title in memory and rewrites the files on save — so an app-closed guard that
    only looks at CLI sessions gives a false guarantee. See PR #42 review.

    Matches on `ps` process paths (macOS `comm` is the full executable path);
    pgrep -f can miss the GUI process depending on cmdline visibility.
    """
    return any(comm.endswith(CLAUDE_APP_BINARY_SUFFIX) for _, comm in _process_table())


def live_cli_session_ids(alive_pids: set[int] | None = None) -> set[str]:
    """cliSessionIds whose pid file points at a process that is alive AND Claude.

    `alive_pids` (from claude_pids()) is computed once by the caller and passed in
    to avoid re-scanning the process table per pid file. A pid file whose pid is
    not a current Claude process is treated as stale/recycled and ignored.
    """
    claude = claude_pids() if alive_pids is None else alive_pids
    live: set[str] = set()
    for pid_file in LIVE_PID_DIR.glob("*.json"):
        try:
            info = json.loads(pid_file.read_text())
            pid = int(info["pid"])
        except (ValueError, KeyError, OSError, json.JSONDecodeError):
            continue
        if pid in claude:
            sid = info.get("sessionId")
            if sid:
                live.add(sid)
    return live


def in_scope(data: dict[str, Any], repo_root: str) -> bool:
    return repo_root in (data.get("cwd"), data.get("originCwd"))


def session_pr_numbers(data: dict[str, Any]) -> set[int]:
    """All PR numbers the session is linked to (top-level + parsed from prs[] urls)."""
    nums: set[int] = set()
    if data.get("prNumber"):
        nums.add(int(data["prNumber"]))
    for p in data.get("prs") or []:
        m = re.search(r"/pull/(\d+)", p.get("url") or "")
        if m:
            nums.add(int(m.group(1)))
    return nums


def desired_title(data: dict[str, Any], taxo: str | None) -> tuple[str | None, str | None]:
    """Return (new_title, warning). new_title is None when we must not touch it.

    `taxo` is the '<Subsystem>/<Module>' prefix for this session (or None).
    """
    title = data.get("title") or ""
    base = strip_prefix(title)
    nums = session_pr_numbers(data)
    prefix = f"{taxo} · " if taxo else ""

    # Respect a deliberate self-label: if the title already picks a #PR<N> that is
    # one of the session's real PRs, keep that N (multi-PR sessions choose which).
    m = re.search(r"#PR(\d+)\s*-", title)
    if m and int(m.group(1)) in nums:
        return f"{prefix}#PR{m.group(1)} - {base}", None

    pr = data.get("prNumber")
    if not pr and len(nums) == 1:
        # App hasn't set the top-level prNumber yet, but there's exactly one linked
        # PR -> unambiguous, use it.
        pr = next(iter(nums))
    if pr:
        return f"{prefix}#PR{pr} - {base}", None
    if nums:
        # Several PRs and no primary pick -> ambiguous, don't guess.
        return None, f"linked to PRs {sorted(nums)} but no top-level prNumber; resolve manually"
    return f"{prefix}[no PR] - {base}", None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=DEFAULT_REPO_ROOT,
                    help="only rename sessions whose cwd/originCwd is this path")
    ap.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR,
                    help="claude-code-sessions store directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the before -> after diff without writing")
    ap.add_argument("--no-skip-running", dest="skip_running", action="store_false",
                    help="also rename sessions with a live process (they may revert)")
    ap.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY,
                    help="session-id -> '<Subsystem>/<Module>' map (v2 prefix)")
    ap.add_argument("--require-closed", action="store_true",
                    help="abort (write nothing) if the app / any live session is running")
    ap.set_defaults(skip_running=True)
    args = ap.parse_args()

    if not args.sessions_dir.is_dir():
        print(f"sessions dir not found: {args.sessions_dir}")
        return 1

    # "Is the app open?" — check the desktop GUI process AND any live CLI session.
    # The app process is the authoritative signal (it can be open with no active
    # session); live CLI sessions are a secondary signal and drive --skip-running.
    live = live_cli_session_ids()
    if args.require_closed:
        reasons = []
        if desktop_app_running():
            reasons.append("the Claude desktop app")
        if live:
            reasons.append(f"{len(live)} live CLI session(s)")
        if reasons:
            print(
                f"⚠️  {' and '.join(reasons)} still running.\n"
                "    Quit the Claude app completely (Cmd+Q) and run this again — while it's\n"
                "    open, the app keeps titles in memory and only re-reads these files at startup."
            )
            return 1
    if not args.skip_running:
        live = set()

    taxonomy: dict[str, Any] = {}
    if args.taxonomy.is_file():
        taxonomy = json.loads(args.taxonomy.read_text()).get("sessions", {})
    backup_dir = BACKUP_ROOT / f"session-titles-{datetime.now():%Y%m%d-%H%M%S}"

    files = sorted(args.sessions_dir.glob("*/*/local_*.json"))
    changed = skipped_running = warnings = unchanged = 0

    for f in files:
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not in_scope(data, args.repo_root) or data.get("isArchived"):
            continue

        taxo = taxonomy.get(data.get("sessionId"))
        if taxo:
            bad = validate_taxonomy(taxo)
            if bad:
                print(f"[warn] {data.get('title')!r}: taxonomy {bad} — skipping taxo prefix")
                taxo = None
        new_title, warning = desired_title(data, taxo)
        if warning:
            print(f"[warn] {data.get('title')!r}: {warning}")
            warnings += 1
            continue
        old = data.get("title") or ""
        if new_title == old:
            unchanged += 1
            continue
        if args.skip_running and data.get("cliSessionId") in live:
            print(f"[running] skip {old!r} -> {new_title!r} (rerun when idle)")
            skipped_running += 1
            continue

        print(f"{old!r} -> {new_title!r}")
        if not args.dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, backup_dir / f.name)
            data["title"] = new_title
            data["titleSource"] = "user"
            # Match the app's own compact format (no indent) to minimize risk.
            f.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        changed += 1

    verb = "would change" if args.dry_run else "changed"
    print(
        f"\n{verb}: {changed} | unchanged: {unchanged} | "
        f"skipped running: {skipped_running} | warnings: {warnings}"
    )
    if changed and not args.dry_run:
        print(f"backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
