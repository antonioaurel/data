# -*- coding: utf-8 -*-
"""Project dashboard generator — Tasks x Pull Requests x Impacts.

Joins three live sources into ONE self-contained HTML dashboard:

  * Tasks    -> parsed from ../docs/task-evolution.md (the operational task table)
  * PRs      -> live from `gh pr list --json ...` (falls back to the task table
                if gh is unavailable, e.g. offline)
  * Impacts  -> ../Quality/modules-features-matrix/pr-impact.json
                (PR -> functionality marks, written by the review flow)

The three sections are cross-linked: hovering/clicking anything carrying a PR
number highlights that PR everywhere (task row, PR card, impacted features).

Run:
    cd projects/recife-history-connections/dashboard
    python3 gen_dashboard.py            # regenerate dashboard.html (live gh)
    python3 gen_dashboard.py --no-gh    # skip gh, use the task table only
"""
import html, json, pathlib, re, subprocess, sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                  # projects/recife-history-connections
TASK_MD = ROOT / "docs" / "task-evolution.md"
PR_IMPACT = ROOT / "Quality" / "modules-features-matrix" / "pr-impact.json"
FONT_B64 = ROOT / "Quality" / "modules-features-matrix" / "roboto-b64.txt"
OUT = HERE / "dashboard.html"

USE_GH = "--no-gh" not in sys.argv

def esc(s): return html.escape(str(s if s is not None else ""))
def slug(s): return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")

# ---- Merge Status vocabulary (from task-evolution.md) -> (key, color, order) ----
STATUS = {
    "To do":                        ("todo",   "#8a94a0", 0),
    "Active (PR review ongoing)":   ("active", "#c07d16", 1),
    "Done (awaiting your approval)":("done",   "#2f6db0", 2),
    "Merged":                       ("merged", "#2f9e57", 3),
}
def status_meta(label):
    for k, v in STATUS.items():
        if label.strip().startswith(k.split(" (")[0]):
            return v
    return ("other", "#6b7885", 9)

# PR live-state -> (label, color)
PRSTATE = {
    "OPEN":   ("Open",   "#c07d16"),
    "DRAFT":  ("Draft",  "#8a94a0"),
    "MERGED": ("Merged", "#2f9e57"),
    "CLOSED": ("Closed", "#c0553f"),
}
REVIEW = {
    "APPROVED":          ("Approved",  "#2f9e57"),
    "CHANGES_REQUESTED": ("Changes requested", "#c0553f"),
    "REVIEW_REQUIRED":   ("Review required", "#c07d16"),
    "":                  ("—", "#8a94a0"),
    None:                ("—", "#8a94a0"),
}

# ---------------------------------------------------------------- parse tasks
def parse_tasks():
    """Parse the pipe table in task-evolution.md into task dicts."""
    if not TASK_MD.exists():
        return []
    rows = []
    for line in TASK_MD.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 11:
            continue
        if cells[0] in ("ID", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append(cells)
    tasks = []
    for c in rows:
        (tid, task, subsystem, why, what, expected, issue,
         impacts, has_pr, pr_link, merge) = c[:11]
        tasks.append({
            "id": tid,
            "task": task,
            "subsystem": subsystem.replace("`", ""),
            "issue_num": _first_int(issue),
            "issue_url": _first_url(issue),
            "impacts_text": impacts,
            "pr_num": _first_int(pr_link),
            "pr_url": _first_url(pr_link),
            "status": merge,
        })
    return tasks

def _first_int(s):
    m = re.search(r"#?(\d+)", s or "")
    return int(m.group(1)) if m else None
def _first_url(s):
    m = re.search(r"\((https?://[^)]+)\)", s or "")
    return m.group(1) if m else None

# ---------------------------------------------------------------- live PRs
def fetch_prs():
    if not USE_GH:
        return None
    fields = "number,title,state,isDraft,reviewDecision,mergedAt,createdAt,updatedAt,url,headRefName,comments"
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "all", "--limit", "200", "--json", fields],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            print("gh failed:", out.stderr.strip()[:200], file=sys.stderr)
            return None
        data = json.loads(out.stdout)
        for p in data:
            cs = p.get("comments") or []
            p["comment_count"] = len(cs)
            p["_comments"] = [{
                "body": c.get("body", ""),
                "createdAt": c.get("createdAt", ""),
                "author": (c.get("author") or {}).get("login", ""),
            } for c in cs]
            p.pop("comments", None)
        return data
    except Exception as e:
        print("gh unavailable:", e, file=sys.stderr)
        return None

def prs_from_tasks(tasks):
    """Fallback PR list when gh is offline: reconstruct from the task table."""
    prs = []
    seen = set()
    for t in tasks:
        n = t["pr_num"]
        if n is None or n in seen:
            continue
        seen.add(n)
        merged = t["status"].strip().startswith("Merged")
        prs.append({
            "number": n, "title": t["task"], "url": t["pr_url"] or "",
            "state": "MERGED" if merged else "OPEN", "isDraft": False,
            "reviewDecision": "", "mergedAt": None, "createdAt": None,
            "updatedAt": None, "headRefName": "", "comment_count": 0,
            "_comments": [],
        })
    return prs

# ---------------------------------------------------------------- impacts
def load_impacts():
    """Return {pr_number: [fid, ...]} and {fid: {subsystem, module, feature}}."""
    if not PR_IMPACT.exists():
        return {}, {}, {}
    data = json.loads(PR_IMPACT.read_text(encoding="utf-8"))
    pr_to_fids, fid_info, pr_titles = {}, {}, {}
    for sub, block in data.items():
        for pr in block.get("prs", []):
            n = _first_int(pr.get("label") or pr.get("id") or "")
            if n is not None:
                pr_titles[n] = pr.get("title", "")
        for fid, ids in block.get("marks", {}).items():
            parts = fid.split("/")
            fid_info[fid] = {
                "subsystem": parts[0] if parts else sub,
                "module": _pretty(parts[1]) if len(parts) > 1 else "",
                "feature": _pretty(parts[2]) if len(parts) > 2 else "",
            }
            for pid in ids:
                n = _first_int(pid)
                if n is None:
                    continue
                pr_to_fids.setdefault(n, [])
                if fid not in pr_to_fids[n]:
                    pr_to_fids[n].append(fid)
    return pr_to_fids, fid_info, pr_titles

def _pretty(s):
    return re.sub(r"\b(\w)", lambda m: m.group(1).upper(), (s or "").replace("-", " ")).strip()

# ---------------------------------------------------------------- time helpers
NOW = datetime.now(timezone.utc)
def ago(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return ""
    secs = (NOW - dt).total_seconds()
    for unit, s in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= s:
            return f"{int(secs // s)}{unit} ago"
    return "just now"

# ---------------------------------------------------------------- build model
def build():
    tasks = parse_tasks()
    prs = fetch_prs()
    live = prs is not None
    if not live:
        prs = prs_from_tasks(tasks)
    pr_to_fids, fid_info, pr_titles = load_impacts()

    # pr-impact.json keys impacts by the task's *issue* number (e.g. 15, 16),
    # but PRs are addressed by their real PR number (8, 9). Remap impact keys
    # through the task table's issue -> pr_num link so impacts land on the live
    # PR instead of rendering as orphan #issue cards. Keys with no known issue
    # mapping pass through unchanged.
    issue_to_pr = {t["issue_num"]: t["pr_num"] for t in tasks
                   if t.get("issue_num") and t.get("pr_num")}
    if issue_to_pr:
        remapped = {}
        for key, fids in pr_to_fids.items():
            bucket = remapped.setdefault(issue_to_pr.get(key, key), [])
            for f in fids:
                if f not in bucket:
                    bucket.append(f)
        pr_to_fids = remapped
        pr_titles = {issue_to_pr.get(n, n): v for n, v in pr_titles.items()}

    by_num = {p["number"]: p for p in prs}
    # normalise draft into a pseudo-state for display
    for p in prs:
        st = p["state"]
        if st == "OPEN" and p.get("isDraft"):
            st = "DRAFT"
        p["_state"] = st
        p["_impacts"] = pr_to_fids.get(p["number"], [])

    # link tasks -> live pr record
    for t in tasks:
        t["_pr"] = by_num.get(t["pr_num"])
        t["_impacts"] = pr_to_fids.get(t["pr_num"], []) if t["pr_num"] else []

    return {
        "tasks": tasks, "prs": prs, "by_num": by_num, "live": live,
        "pr_to_fids": pr_to_fids, "fid_info": fid_info, "pr_titles": pr_titles,
    }

# ---------------------------------------------------------------- review cycle
# The Codex bridge posts one consolidated comment with the hidden marker and
# the visible heading below. Older rounds used only the heading.
CODEX_MARKER = "<!-- codex-automated-review"
CODEX_MARK = "## Codex automated review"

# review-stage -> (label, color). Derived live from the PR's GitHub comments,
# which the review flow treats as the canonical discussion log.
RSTAGE = {
    "await-review": ("Awaiting Codex review", "#c07d16"),
    "await-claude": ("Codex reviewed · awaiting Claude", "#2f6db0"),
    "responded":    ("Response posted · awaiting your call", "#7a5bd0"),
    "merged":       ("Merged · cycle closed", "#2f9e57"),
    "closed":       ("Closed · no merge", "#c0553f"),
}

def _extract_guidance(body):
    m = re.search(r"###\s*Merge guidance\s*\n+(.+)", body)
    return m.group(1).strip() if m else ""

def _is_codex_comment(body):
    return CODEX_MARKER in body or CODEX_MARK in body

def _codex_rounds(comments):
    codex = [c for c in comments if _is_codex_comment(c["body"])]
    explicit = []
    for c in codex:
        m = re.search(r"\bround\s+(\d+)\b", c["body"], re.I)
        if m:
            explicit.append(int(m.group(1)))
    return max(explicit) if explicit else len(codex)

def review_stage(p):
    """Where a PR sits in the Claude <-> Codex(ChatGPT) review loop."""
    state = p["_state"]
    comments = p.get("_comments") or []
    codex = [c for c in comments if _is_codex_comment(c["body"])]
    rounds = _codex_rounds(comments)
    guidance = _extract_guidance(max(codex, key=lambda c: c["createdAt"])["body"]) if codex else ""
    if state == "MERGED":
        key = "merged"
    elif state == "CLOSED":
        key = "closed"
    elif rounds == 0:
        key = "await-review"
    else:
        last = max(comments, key=lambda c: c["createdAt"])
        key = "await-claude" if _is_codex_comment(last["body"]) else "responded"
    return {"key": key, "rounds": rounds, "guidance": guidance}

def _plain(s, limit=190):
    s = re.sub(r"<!--.*?-->", " ", s or "", flags=re.S)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[*_#>]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:limit - 1].rstrip() + "…") if len(s) > limit else s

def _codex_findings(body):
    findings = []
    for line in (body or "").splitlines():
        m = re.match(r"\s*-\s+\[(P[123])\]\s+(.+)", line)
        if not m:
            continue
        sev, title = m.groups()
        title = re.split(r"\s+[—-]\s+", title, maxsplit=1)[0]
        findings.append({"sev": sev, "title": _plain(title, 120)})
    return findings

def _comment_excerpt(body):
    for line in (body or "").splitlines():
        line = line.strip()
        if not line or line.startswith("<!--") or line.startswith("##"):
            continue
        if line.startswith("**Task:**") or line.startswith("### Task"):
            continue
        return _plain(line)
    return ""

def _is_claude_or_fix_reply(body):
    body_l = (body or "").lower()
    signals = (
        "fixed in", "corrig", "addressed", "claude-reply", "what was done",
        "review — what was done", "good catch", "thanks for the catch",
    )
    return any(s in body_l for s in signals)

def trace_events(p, task):
    comments = sorted(p.get("_comments") or [], key=lambda c: c.get("createdAt") or "")
    events = []
    if task:
        events.append({
            "actor": "Claude",
            "kind": "Implementation",
            "summary": f"{task['id']} · {task['task']}",
            "evidence": "task table",
        })
    else:
        events.append({
            "actor": "Claude",
            "kind": "Implementation",
            "summary": p["title"],
            "evidence": "PR title",
        })
    seen_codex = False
    for c in comments:
        body = c["body"]
        if _is_codex_comment(body):
            seen_codex = True
            findings = _codex_findings(body)
            if findings:
                sev = ", ".join(sorted({f["sev"] for f in findings}))
                titles = "; ".join(f["title"] for f in findings[:2])
                more = f" +{len(findings)-2} more" if len(findings) > 2 else ""
                summary = f"{sev}: {titles}{more}"
            else:
                summary = "No blocking finding captured in the automated review."
            events.append({
                "actor": "Codex",
                "kind": "Review",
                "summary": summary,
                "evidence": "Codex comment",
            })
        elif seen_codex and _is_claude_or_fix_reply(body):
            events.append({
                "actor": "Claude / operator",
                "kind": "Fix or reply",
                "summary": _comment_excerpt(body) or "Response posted after Codex review.",
                "evidence": "PR comment",
            })
    return [events[0], *events[-4:]] if len(events) > 5 else events

def impacted_area_chips(p, M):
    chips = ""
    for fid in p.get("_impacts") or []:
        info = M["fid_info"].get(fid, {})
        label = " / ".join(x for x in (
            _pretty(info.get("subsystem", "")),
            info.get("module", ""),
            info.get("feature", ""),
        ) if x)
        chips += f'<span class="achip">{esc(label or fid)}</span>'
    return chips or '<span class="muted">No mapped impact</span>'

# ---------------------------------------------------------------- HTML pieces
def pr_chip(num, extra=""):
    if num is None:
        return '<span class="pr-none">no PR</span>'
    return (f'<button class="prchip {extra}" data-pr="{num}" '
            f'title="highlight PR #{num} everywhere">#{num}</button>')

def summary(M):
    tasks, prs = M["tasks"], M["prs"]
    tcount = {}
    for t in tasks:
        k = status_meta(t["status"])[0]
        tcount[k] = tcount.get(k, 0) + 1
    pcount = {}
    for p in prs:
        pcount[p["_state"]] = pcount.get(p["_state"], 0) + 1
    impacted = len({fid for fids in M["pr_to_fids"].values() for fid in fids})
    open_pr = pcount.get("OPEN", 0) + pcount.get("DRAFT", 0)

    def card(big, lbl, sub, color):
        return (f'<div class="scard"><div class="snum" style="color:{color}">{big}</div>'
                f'<div class="slbl">{esc(lbl)}</div><div class="ssub">{esc(sub)}</div></div>')

    active = tcount.get("active", 0)
    todo = tcount.get("todo", 0)
    done = tcount.get("done", 0)
    merged = tcount.get("merged", 0)
    return ('<div class="summary">'
            + card(len(tasks), "Tasks", f"{todo} to do · {active} active · {done} done · {merged} merged", "#12202e")
            + card(open_pr, "Open PRs", f"{pcount.get('MERGED',0)} merged · {pcount.get('CLOSED',0)} closed", "#c07d16")
            + card(merged, "Shipped", "tasks merged to main", "#2f9e57")
            + card(impacted, "Impacted features", "functionalities touched by PRs", "#7a5bd0")
            + '</div>')

def tasks_section(M):
    rows = ""
    order = sorted(M["tasks"], key=lambda t: (status_meta(t["status"])[2], t["id"]))
    for t in order:
        skey, scol, _ = status_meta(t["status"])
        pr = t["_pr"]
        if pr:
            pst, pcol = PRSTATE[pr["_state"]]
            pr_state_badge = f'<span class="mini" style="background:{pcol}">{esc(pst)}</span>'
        else:
            pr_state_badge = ""
        nimp = len(t["_impacts"])
        issue = (f'<a href="{esc(t["issue_url"])}" target="_blank" rel="noopener">#{t["issue_num"]}</a>'
                 if t["issue_num"] else "—")
        rows += (
            f'<tr class="trow" data-sub="{esc(slug(t["subsystem"]))}" '
            f'data-status="{skey}"' + (f' data-pr="{t["pr_num"]}"' if t["pr_num"] else "") + '>'
            f'<td class="c-id">{esc(t["id"])}</td>'
            f'<td class="c-task"><b>{esc(t["task"])}</b>'
            f'<span class="c-sysline"><code>{esc(t["subsystem"])}</code></span></td>'
            f'<td class="c-status"><span class="sbadge" style="--sc:{scol}">{esc(_short_status(t["status"]))}</span></td>'
            f'<td class="c-issue">{issue}</td>'
            f'<td class="c-pr">{pr_chip(t["pr_num"])} {pr_state_badge}</td>'
            f'<td class="c-imp">' + (f'<span class="impn" data-pr="{t["pr_num"]}">{nimp}</span>' if nimp else '<span class="impz">0</span>') + '</td>'
            f'</tr>')
    return (
        '<section class="block" id="sec-tasks">'
        '<div class="bhead"><span class="btag" style="background:#12202e">1 · Tasks</span>'
        '<h2>Task state</h2><span class="bsub">from <code>docs/task-evolution.md</code> · one row per GitHub issue, ordered by merge status</span></div>'
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
        '<th>ID</th><th>Task</th><th>Status</th><th>Issue</th><th>PR</th><th>Impacts</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table></div></section>')

def _short_status(s):
    s = s.strip()
    if s.startswith("Active"): return "Active"
    if s.startswith("Done"): return "Done · review"
    if s.startswith("Merged"): return "Merged"
    if s.startswith("To do"): return "To do"
    return s

def prs_section(M):
    groups = [("OPEN", "Open"), ("DRAFT", "Draft"), ("MERGED", "Merged"), ("CLOSED", "Closed")]
    task_by_pr = {}
    for t in M["tasks"]:
        if t["pr_num"]:
            task_by_pr[t["pr_num"]] = t
    cols = ""
    for state, label in groups:
        items = [p for p in M["prs"] if p["_state"] == state]
        if not items:
            continue
        items.sort(key=lambda p: -(p["number"]))
        _, col = PRSTATE[state]
        cards = ""
        for p in items:
            t = task_by_pr.get(p["number"])
            rlabel, rcol = REVIEW.get(p.get("reviewDecision"), REVIEW[""])
            nimp = len(p["_impacts"])
            meta = []
            if p.get("headRefName"):
                meta.append(f'<code>{esc(p["headRefName"])}</code>')
            if p.get("comment_count"):
                meta.append(f'{p["comment_count"]}💬')
            if p.get("updatedAt"):
                meta.append(ago(p["updatedAt"]))
            title = p["title"]
            href = p.get("url") or "#"
            cards += (
                f'<article class="prcard" data-pr="{p["number"]}" '
                f'data-sub="{esc(slug(t["subsystem"])) if t else ""}">'
                f'<div class="prtop"><button class="prchip" data-pr="{p["number"]}">#{p["number"]}</button>'
                + (f'<span class="mini" style="background:{rcol}">{esc(rlabel)}</span>' if p.get("reviewDecision") else '')
                + (f'<span class="task-ref">{esc(t["id"])}</span>' if t else '')
                + '</div>'
                f'<a class="prtitle" href="{esc(href)}" target="_blank" rel="noopener">{esc(title)}</a>'
                f'<div class="prmeta">{" · ".join(meta)}</div>'
                + (f'<div class="prfoot"><span class="impn" data-pr="{p["number"]}">{nimp}</span> feature{"s" if nimp!=1 else ""} impacted</div>' if nimp else '<div class="prfoot muted">no mapped impact</div>')
                + '</article>')
        cols += (f'<div class="prband"><div class="prcol-h"><span class="dot" style="background:{col}"></span>'
                 f'{esc(label)}<span class="cnt">{len(items)}</span></div>'
                 f'<div class="prband-cards">{cards}</div></div>')
    src = "live from <code>gh pr list</code>" if M["live"] else "offline fallback — reconstructed from the task table"
    return (
        '<section class="block" id="sec-prs">'
        '<div class="bhead"><span class="btag" style="background:#c07d16">2 · Pull Requests</span>'
        f'<h2>PR state</h2><span class="bsub">{src} · grouped by state, newest first</span></div>'
        f'<div class="prboard">{cols}</div></section>')

def orchestration_section(M):
    # ---- the cycle diagram (Claude <-> Codex/ChatGPT) ----
    CLAUDE, GPT, YOU = "#d97757", "#10a37f", "#12202e"
    steps = [
        (CLAUDE, "Claude", "opens the PR", "1"),
        (GPT, "ChatGPT · Codex", "reviews the diff", "2"),
        (CLAUDE, "Claude", "addresses findings / replies", "3"),
        (GPT, "Both", "converge on the evidence", "⟳"),
        (YOU, "You", "decide the merge", "4"),
    ]
    nodes = ""
    for i, (col, actor, act, n) in enumerate(steps):
        if i:
            nodes += '<span class="flarrow">→</span>'
        nodes += (f'<span class="flnode" style="--ac:{col}"><span class="fln-n">{esc(n)}</span>'
                  f'<span class="fln-actor">{esc(actor)}</span><span class="fln-act">{esc(act)}</span></span>')
    diagram = (
        f'<div class="flow">{nodes}</div>'
        '<div class="flow-note">The loop repeats from <b>ChatGPT · Codex</b> whenever Claude pushes changes '
        'that need another review. Codex is a peer reviewer, not a subordinate — on disagreement they converge '
        'on the evidence, and if they can\'t, <b>you</b> decide. The GitHub PR conversation is the canonical log '
        '(see <code>docs/pr-review-flow.md</code>). Run a round with '
        '<code>python3 tools/review_pr_with_codex_cli.py &lt;PR&gt;</code>.</div>'
        '<div class="fllegend">'
        f'<span class="lgd"><i style="background:{CLAUDE}"></i>Claude — implementation</span>'
        f'<span class="lgd"><i style="background:{GPT}"></i>ChatGPT · Codex — review</span>'
        f'<span class="lgd"><i style="background:{YOU}"></i>You — merge decision</span></div>')

    # ---- per-PR live stage ----
    task_by_pr = {t["pr_num"]: t for t in M["tasks"] if t["pr_num"]}
    order = {"await-claude": 0, "responded": 1, "await-review": 2, "merged": 3, "closed": 4}
    prs = sorted(M["prs"], key=lambda p: (order.get(review_stage(p)["key"], 9), -p["number"]))
    cards = ""
    for p in prs:
        st = review_stage(p)
        label, color = RSTAGE[st["key"]]
        t = task_by_pr.get(p["number"])
        rounds = st["rounds"]
        rounds_txt = (f'{rounds} review round{"s" if rounds != 1 else ""}' if rounds else "no review yet")
        guid = f'<div class="og-guid">{esc(st["guidance"])}</div>' if st["guidance"] else ""
        cards += (
            f'<article class="ocard" data-pr="{p["number"]}" data-sub="{esc(slug(t["subsystem"])) if t else ""}">'
            f'<div class="otop"><button class="prchip" data-pr="{p["number"]}">#{p["number"]}</button>'
            + (f'<span class="task-ref">{esc(t["id"])}</span>' if t else '')
            + '</div>'
            f'<div class="ostage" style="--sc:{color}">{esc(label)}</div>'
            f'<a class="otitle" href="{esc(p.get("url") or "#")}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
            f'<div class="ometa">{esc(rounds_txt)}' + (f' · updated {ago(p["updatedAt"])}' if p.get("updatedAt") else '') + '</div>'
            + guid + '</article>')
    live = ("live from PR comments" if M["live"] else "offline — comment history unavailable")
    return (
        '<section class="block" id="sec-orch">'
        '<div class="bhead"><span class="btag" style="background:#10a37f">3 · Review orchestration</span>'
        f'<h2>Claude ↔ ChatGPT review flow</h2><span class="bsub">the review cycle, and where each PR sits in it · {live}</span></div>'
        f'{diagram}<div class="oboard">{cards}</div></section>')

def trace_section(M):
    task_by_pr = {t["pr_num"]: t for t in M["tasks"] if t["pr_num"]}
    cards = ""
    for p in sorted(M["prs"], key=lambda x: -x["number"]):
        t = task_by_pr.get(p["number"])
        events = trace_events(p, t)
        st = review_stage(p)
        slabel, scol = RSTAGE[st["key"]]
        nimp = len(p.get("_impacts") or [])
        if events:
            timeline = ""
            for i, ev in enumerate(events, 1):
                timeline += (
                    f'<li><span class="tnum">{i}</span><div><b>{esc(ev["actor"])}</b>'
                    f'<span class="tkind">{esc(ev["kind"])}</span>'
                    f'<p>{esc(ev["summary"])}</p>'
                    f'<em>{esc(ev["evidence"])}</em></div></li>')
        else:
            timeline = '<li><span class="tnum">1</span><div><b>No exchange captured</b><p>No Claude/Codex exchange was found in PR comments.</p></div></li>'
        cards += (
            f'<article class="tracecard" data-pr="{p["number"]}" data-sub="{esc(slug(t["subsystem"])) if t else ""}">'
            f'<div class="trtop"><button class="prchip" data-pr="{p["number"]}">#{p["number"]}</button>'
            + (f'<span class="task-ref">{esc(t["id"])}</span>' if t else '')
            + f'<span class="mini" style="background:{scol}">{esc(slabel)}</span></div>'
            f'<a class="trtitle" href="{esc(p.get("url") or "#")}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
            f'<ol class="timeline">{timeline}</ol>'
            f'<div class="areas"><div class="areas-h">Impacted areas <span>{nimp}</span></div>'
            f'<div class="areas-c">{impacted_area_chips(p, M)}</div></div>'
            '</article>')
    src = "validated from task table, PR comments, and impact matrix" if M["live"] else "offline snapshot from task table and impact matrix"
    return (
        '<section class="block" id="sec-trace">'
        '<div class="bhead"><span class="btag" style="background:#2f6db0">4 · Review & Impact Trace</span>'
        f'<h2>Exchange summary by PR</h2><span class="bsub">{src} · Claude actions, Codex reviews, replies, and impacted areas</span></div>'
        f'<div class="traceboard">{cards}</div></section>')

def impacts_section(M):
    # per-PR -> functionalities, grouped by subsystem
    fid_info = M["fid_info"]
    title_by_pr = {}
    for p in M["prs"]:
        title_by_pr[p["number"]] = p["title"]
    for n, t in M["pr_titles"].items():
        title_by_pr.setdefault(n, t)

    blocks = ""
    for num in sorted(M["pr_to_fids"], reverse=True):
        fids = M["pr_to_fids"][num]
        p = M["by_num"].get(num)
        state_badge = ""
        if p:
            pst, pcol = PRSTATE[p["_state"]]
            state_badge = f'<span class="mini" style="background:{pcol}">{esc(pst)}</span>'
        # group fids by subsystem
        bysub = {}
        for fid in fids:
            info = fid_info.get(fid, {"subsystem": fid.split("/")[0], "module": "", "feature": fid})
            bysub.setdefault(info["subsystem"], []).append(info)
        subhtml = ""
        for sub in sorted(bysub):
            chips = "".join(
                f'<span class="fchip"><span class="fmod">{esc(i["module"])}</span>{esc(i["feature"])}</span>'
                for i in sorted(bysub[sub], key=lambda x: (x["module"], x["feature"])))
            subhtml += f'<div class="fsub"><span class="fsub-name">{esc(sub)}</span>{chips}</div>'
        blocks += (
            f'<article class="impcard" data-pr="{num}">'
            f'<div class="imptop"><button class="prchip" data-pr="{num}">#{num}</button>{state_badge}'
            f'<span class="imptitle">{esc(title_by_pr.get(num, ""))}</span>'
            f'<span class="impcount">{len(fids)}</span></div>'
            f'<div class="fgrid">{subhtml}</div></article>')
    if not blocks:
        blocks = '<p class="muted">No impact marks yet — the review flow writes them into <code>pr-impact.json</code>.</p>'
    return (
        '<section class="block" id="sec-impacts">'
        '<div class="bhead"><span class="btag" style="background:#7a5bd0">5 · Impacts</span>'
        '<h2>App impact</h2><span class="bsub">from <code>Quality/modules-features-matrix/pr-impact.json</code> · each PR → the functionalities its diff touches</span></div>'
        f'<div class="impboard">{blocks}</div></section>')

# ---------------------------------------------------------------- assemble
def render(M):
    b64 = FONT_B64.read_text().strip() if FONT_B64.exists() else ""
    font = (f"@font-face{{font-family:'Roboto';font-style:normal;font-weight:100 900;"
            f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
            if b64 else "")
    stamp = NOW.strftime("%Y-%m-%d %H:%M UTC")
    live_tag = "live" if M["live"] else "offline snapshot"
    body = (summary(M) + tasks_section(M) + prs_section(M)
            + orchestration_section(M) + trace_section(M) + impacts_section(M))
    return TEMPLATE.format(font=font, style=STYLE, body=body, stamp=stamp,
                           live_tag=live_tag, js=JS)

STYLE = """
:root{--ground:#eef1f4;--surface:#fff;--surface-2:#f5f7fa;--ink:#12202e;--ink-2:#3a4653;
 --ink-3:#6b7885;--line:#d7dde4;--line-2:#e7ebf0;--amber:#c07d16;--hl:#fff3d6;--hl-line:#e6b23c;}
*{box-sizing:border-box;}
body{margin:0;background:var(--ground);color:var(--ink-2);
 font-family:'Roboto',system-ui,Arial,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1500px;margin:0 auto;padding:1.4rem clamp(.8rem,2.4vw,2rem) 4rem;}
.mast{margin-bottom:1rem;}
.eyebrow{font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:var(--amber);font-weight:700;margin:0 0 .35rem;}
.mast h1{color:var(--ink);font-size:clamp(1.4rem,3.4vw,2rem);font-weight:700;letter-spacing:-.015em;margin:0 0 .4rem;}
.mast p{margin:0;max-width:80ch;font-size:.9rem;color:var(--ink-3);}
.mast .live{display:inline-block;margin-top:.5rem;font-size:.72rem;color:var(--ink-3);
 background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:.15rem .7rem;}
.mast .live b{color:var(--ink-2);}
.filters{display:flex;gap:.4rem;flex-wrap:wrap;margin:1rem 0 .2rem;}
.fbtn{font-family:inherit;font-size:.76rem;font-weight:600;color:var(--ink-3);background:var(--surface);
 border:1px solid var(--line);border-radius:20px;padding:.28rem .7rem;cursor:pointer;}
.fbtn:hover{border-color:#c3ccd6;color:var(--ink);}
.fbtn.on{background:var(--ink);color:#fff;border-color:var(--ink);}

.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin:1rem 0 1.6rem;}
@media(max-width:720px){.summary{grid-template-columns:repeat(2,1fr);}}
.scard{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem;}
.snum{font-size:1.9rem;font-weight:800;line-height:1;font-variant-numeric:tabular-nums;}
.slbl{font-size:.82rem;font-weight:700;color:var(--ink);margin-top:.2rem;}
.ssub{font-size:.68rem;color:var(--ink-3);margin-top:.15rem;}

.block{margin:1.8rem 0;}
.bhead{display:flex;align-items:baseline;gap:.7rem;flex-wrap:wrap;margin-bottom:.8rem;}
.btag{font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:#fff;padding:.24rem .55rem;border-radius:6px;}
.bhead h2{color:var(--ink);font-size:1.2rem;font-weight:700;margin:0;}
.bsub{font-size:.78rem;color:var(--ink-3);}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em;background:#e9edf2;padding:.03rem .3rem;border-radius:4px;}

/* tasks table */
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface);}
table.tbl{border-collapse:separate;border-spacing:0;width:100%;font-size:.84rem;}
.tbl th,.tbl td{border-bottom:1px solid var(--line-2);padding:.55rem .7rem;text-align:left;vertical-align:top;}
.tbl thead th{position:sticky;top:0;background:var(--surface-2);font-size:.62rem;letter-spacing:.1em;
 text-transform:uppercase;color:var(--ink-3);font-weight:700;z-index:2;}
.tbl tbody tr:last-child td{border-bottom:0;}
.c-id{font-weight:700;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace;font-size:.76rem;white-space:nowrap;}
.c-task b{color:var(--ink);font-weight:600;display:block;}
.c-sysline{font-size:.7rem;color:var(--ink-3);}
.sbadge{font-size:.66rem;font-weight:700;color:#fff;background:var(--sc);border-radius:5px;padding:.16rem .5rem;white-space:nowrap;}
.c-issue a{color:var(--amber);text-decoration:none;font-weight:600;}
.c-issue a:hover{text-decoration:underline;}
.c-imp{text-align:center;}
.impn{display:inline-grid;place-items:center;min-width:1.5rem;height:1.5rem;border-radius:6px;
 background:#efeaf9;color:#5b3fb0;font-weight:800;font-size:.8rem;}
.impz{color:#b7c0ca;font-weight:600;}
.trow.dim{opacity:.28;}
.trow.hl{background:var(--hl);}
.trow:hover{background:var(--surface-2);}

/* pr chips + mini badges */
.prchip{font-family:inherit;font-weight:800;font-size:.76rem;color:var(--ink);background:#eef1f4;
 border:1px solid var(--line);border-radius:6px;padding:.1rem .4rem;cursor:pointer;}
.prchip:hover{border-color:var(--hl-line);background:var(--hl);}
.pr-none{font-size:.72rem;color:#b7c0ca;font-style:italic;}
.mini{font-size:.58rem;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:#fff;padding:.1rem .38rem;border-radius:5px;white-space:nowrap;}

/* pr board — stacked bands, cards wrap */
.prboard{display:flex;flex-direction:column;gap:.8rem;}
.prband{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:.6rem .7rem;}
.prcol-h{display:flex;align-items:center;gap:.4rem;font-size:.74rem;font-weight:700;color:var(--ink);
 text-transform:uppercase;letter-spacing:.06em;padding:.1rem .1rem .55rem;}
.prcol-h .dot{width:.55rem;height:.55rem;border-radius:50%;}
.prcol-h .cnt{color:var(--ink-3);background:var(--surface);border:1px solid var(--line);
 border-radius:20px;padding:0 .45rem;font-size:.7rem;}
.prband-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.5rem;}
.prcard{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.6rem .7rem;}
.prtop{display:flex;align-items:center;gap:.35rem;margin-bottom:.35rem;flex-wrap:wrap;}
.task-ref{margin-left:auto;font-size:.66rem;font-weight:700;color:var(--ink-3);font-family:ui-monospace,Menlo,monospace;}
.prtitle{display:block;color:var(--ink);font-size:.82rem;font-weight:600;text-decoration:none;line-height:1.3;}
.prtitle:hover{color:var(--amber);}
.prmeta{font-size:.68rem;color:var(--ink-3);margin-top:.3rem;display:flex;gap:.3rem;flex-wrap:wrap;align-items:center;}
.prfoot{font-size:.72rem;color:var(--ink-3);margin-top:.45rem;display:flex;align-items:center;gap:.35rem;}
.prfoot.muted{color:#b7c0ca;}
.prcard.dim{opacity:.28;} .prcard.hl{border-color:var(--hl-line);box-shadow:0 0 0 2px var(--hl-line);}

/* review orchestration */
.flow{display:flex;align-items:stretch;gap:.4rem;flex-wrap:wrap;padding:.9rem;background:var(--surface);
 border:1px solid var(--line);border-radius:12px;margin-bottom:.6rem;}
.flnode{flex:1 1 150px;min-width:130px;background:var(--surface-2);border:1px solid var(--line);
 border-top:3px solid var(--ac);border-radius:9px;padding:.5rem .6rem;display:flex;flex-direction:column;gap:.1rem;position:relative;}
.fln-n{position:absolute;top:.4rem;right:.5rem;font-size:.62rem;font-weight:800;color:var(--ac);opacity:.8;}
.fln-actor{font-size:.8rem;font-weight:700;color:var(--ink);}
.fln-act{font-size:.7rem;color:var(--ink-3);}
.flarrow{align-self:center;color:var(--ink-3);font-weight:700;font-size:1rem;}
@media(max-width:640px){.flarrow{transform:rotate(90deg);}.flnode{flex-basis:100%;}}
.flow-note{font-size:.78rem;color:var(--ink-3);max-width:90ch;margin:0 0 .5rem;}
.flow-note b{color:var(--ink-2);}
.fllegend{display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:.9rem;}
.lgd{font-size:.74rem;color:var(--ink-2);display:flex;align-items:center;gap:.35rem;}
.lgd i{width:.7rem;height:.7rem;border-radius:3px;display:inline-block;}
.oboard{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.6rem;}
.ocard{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:.65rem .75rem;
 border-left:4px solid var(--line);}
.ocard.dim{opacity:.28;} .ocard.hl{border-color:var(--hl-line);box-shadow:0 0 0 2px var(--hl-line);}
.otop{display:flex;align-items:center;gap:.4rem;margin-bottom:.4rem;}
.ostage{font-size:.72rem;font-weight:700;color:#fff;background:var(--sc);border-radius:6px;
 padding:.18rem .5rem;display:inline-block;margin-bottom:.35rem;}
.otitle{display:block;color:var(--ink);font-size:.82rem;font-weight:600;text-decoration:none;line-height:1.3;}
.otitle:hover{color:var(--amber);}
.ometa{font-size:.68rem;color:var(--ink-3);margin-top:.3rem;}
.og-guid{font-size:.72rem;color:var(--ink-2);margin-top:.4rem;padding-top:.4rem;border-top:1px solid var(--line-2);font-style:italic;}

/* review trace */
.traceboard{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:.8rem;align-items:start;}
.tracecard{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.75rem .85rem;}
.tracecard.dim{opacity:.28;} .tracecard.hl{border-color:var(--hl-line);box-shadow:0 0 0 2px var(--hl-line);}
.trtop{display:flex;align-items:center;gap:.4rem;margin-bottom:.45rem;flex-wrap:wrap;}
.trtop .mini{margin-left:auto;}
.trtitle{display:block;color:var(--ink);font-size:.86rem;font-weight:700;text-decoration:none;line-height:1.3;}
.trtitle:hover{color:var(--amber);}
.timeline{list-style:none;margin:.7rem 0 .65rem;padding:0;display:flex;flex-direction:column;gap:.55rem;}
.timeline li{display:grid;grid-template-columns:1.45rem 1fr;gap:.45rem;align-items:start;}
.tnum{display:grid;place-items:center;width:1.35rem;height:1.35rem;border-radius:50%;background:var(--surface-2);
 border:1px solid var(--line);color:var(--ink-3);font-size:.68rem;font-weight:800;}
.timeline b{font-size:.76rem;color:var(--ink);margin-right:.35rem;}
.tkind{font-size:.58rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);
 background:var(--surface-2);border:1px solid var(--line-2);border-radius:5px;padding:.06rem .3rem;}
.timeline p{margin:.12rem 0 0;color:var(--ink-2);font-size:.76rem;line-height:1.35;}
.timeline em{display:block;margin-top:.12rem;color:var(--ink-3);font-size:.64rem;font-style:normal;}
.areas{border-top:1px solid var(--line-2);padding-top:.55rem;}
.areas-h{display:flex;justify-content:space-between;align-items:center;color:var(--ink-3);
 font-size:.62rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.35rem;}
.areas-h span{letter-spacing:0;color:#5b3fb0;background:#efeaf9;border-radius:6px;padding:.02rem .4rem;font-size:.72rem;}
.areas-c{display:flex;gap:.3rem;flex-wrap:wrap;}
.achip{font-size:.7rem;color:var(--ink);background:var(--surface-2);border:1px solid var(--line-2);
 border-radius:6px;padding:.12rem .4rem;}

/* impacts */
.impboard{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:.8rem;align-items:start;}
.impcard{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:.75rem .85rem;}
.impcard.dim{opacity:.28;} .impcard.hl{border-color:var(--hl-line);box-shadow:0 0 0 2px var(--hl-line);}
.imptop{display:flex;align-items:center;gap:.4rem;margin-bottom:.5rem;}
.imptitle{font-size:.8rem;font-weight:600;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.impcount{margin-left:auto;font-weight:800;color:#5b3fb0;background:#efeaf9;border-radius:6px;padding:.05rem .45rem;font-size:.78rem;}
.fgrid{display:flex;flex-direction:column;gap:.45rem;}
.fsub{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center;}
.fsub-name{font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:var(--ink-3);
 background:var(--surface-2);border:1px solid var(--line-2);border-radius:5px;padding:.08rem .35rem;}
.fchip{font-size:.72rem;color:var(--ink);background:var(--surface-2);border:1px solid var(--line-2);
 border-radius:6px;padding:.12rem .42rem;}
.fmod{color:var(--ink-3);font-weight:700;margin-right:.3rem;}
.muted{color:var(--ink-3);font-size:.85rem;}
"""

JS = """
(function(){
 var sel=null;
 var all=document.querySelectorAll('[data-pr]');
 function apply(pr){
  document.querySelectorAll('.trow,.prcard,.ocard,.tracecard,.impcard').forEach(function(el){
   var m=el.getAttribute('data-pr');
   el.classList.toggle('hl', pr!=null && m===String(pr));
   el.classList.toggle('dim', pr!=null && m!==String(pr));
  });
 }
 function hover(pr){ if(sel==null) apply(pr); }
 document.querySelectorAll('.prchip,.impn').forEach(function(el){
  el.addEventListener('click',function(e){
   e.preventDefault();
   var pr=el.getAttribute('data-pr');
   if(sel===pr){sel=null;apply(null);}else{sel=pr;apply(pr);
    var t=document.querySelector('.impcard[data-pr="'+pr+'"]')||document.querySelector('.prcard[data-pr="'+pr+'"]');
   }
  });
 });
 document.querySelectorAll('.trow[data-pr],.prcard[data-pr],.ocard[data-pr],.tracecard[data-pr],.impcard[data-pr]').forEach(function(el){
  var pr=el.getAttribute('data-pr');
  el.addEventListener('mouseenter',function(){hover(pr);});
  el.addEventListener('mouseleave',function(){hover(null);});
 });
 // subsystem filters
 var subs={};
 document.querySelectorAll('.trow[data-sub]').forEach(function(r){var s=r.getAttribute('data-sub');if(s)subs[s]=1;});
 var bar=document.getElementById('filters');
 if(bar){
  var cur='';
  function mkbtn(val,label){
   var b=document.createElement('button');b.className='fbtn'+(val===cur?' on':'');b.textContent=label;
   b.addEventListener('click',function(){
    cur=val;bar.querySelectorAll('.fbtn').forEach(function(x){x.classList.remove('on');});b.classList.add('on');
    document.querySelectorAll('[data-sub]').forEach(function(el){
     var s=el.getAttribute('data-sub');
     el.style.display=(val===''||s===val||s==='')?'':'none';
    });
   });
   bar.appendChild(b);
  }
  mkbtn('','All subsystems');
  Object.keys(subs).sort().forEach(function(s){mkbtn(s,s);});
 }
})();
"""

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Dashboard · Conexões da História</title>
<style>{font}{style}</style></head>
<body><div class="wrap">
 <header class="mast">
  <p class="eyebrow">Operator dashboard</p>
  <h1>Tasks · Pull Requests · Impact</h1>
  <p>One view over the work: every task and its merge status, the live pull-request state, where each PR sits in the <b>Claude ↔ ChatGPT (Codex)</b> review loop, and which app functionalities each PR touches. Click any <b>#PR</b> chip to highlight it across every section.</p>
  <span class="live">Generated <b>{stamp}</b> · PR data: <b>{live_tag}</b></span>
 </header>
 <div class="filters" id="filters"></div>
 {body}
</div>
<script>{js}</script>
</body></html>
"""

if __name__ == "__main__":
    M = build()
    OUT.write_text(render(M), encoding="utf-8")
    print(f"wrote {OUT} · {len(M['tasks'])} tasks · {len(M['prs'])} PRs · "
          f"{'live gh' if M['live'] else 'offline fallback'}")
