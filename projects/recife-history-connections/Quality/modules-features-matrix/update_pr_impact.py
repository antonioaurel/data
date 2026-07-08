#!/usr/bin/env python3
"""Update pr-impact.json from a real PR's changed files, regenerate the matrix
docs, and (by default) open a PR proposing the change for human review.

Part of the PR review flow (see ../../docs/pr-review-flow.md). Intended to run
after Codex reviews a PR: the review agent can pass the impacted features it
identified via --features; otherwise a file-path heuristic is used.

Usage:
  update_pr_impact.py <PR_NUMBER> [--features fid,fid,...] [--label "#16"]
                      [--dry-run] [--no-pr]

The PRECISE input is --features, supplied by the review agent that actually read
the diff. Without it, a deliberately CONSERVATIVE fallback runs: it only maps a
changed page file to that page's module (page-level, not diff-precise). Broad
signals (app.js, shared data files) are intentionally NOT auto-expanded — they
would mark almost everything and inflate the Total; the review agent decides
which specific features those touch.

  fallback:  pages/<x>.html or mobile/site/<x>.html -> that module's features
Explicit --features (comma-separated data-fid values) overrides the fallback.
"""
import json, subprocess, sys, os, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def fid(sub, module, feat):
    return f"{sub}/{slug(module)}/{slug(feat)}"


def load_modules():
    return json.load(open(os.path.join(HERE, 'modules.json')))


def pr_info(n):
    r = sh('gh', 'pr', 'view', str(n), '--json', 'number,title,headRefName,files')
    if r.returncode != 0:
        sys.exit('gh pr view failed: ' + r.stderr)
    return json.loads(r.stdout)


def sub_of_path(p):
    if 'mobile/' in p:
        return 'mobile'
    if '/pages/' in p or p.startswith('pages/'):
        return 'desktop'
    return None  # shared / data — not tied to one subsystem


def impacted_fids(files, mods):
    """Conservative page-level fallback: a changed page file -> that module's
    features, restricted to the file's subsystem. Deliberately does NOT expand
    shared files (app.js, data JSON) — that is the review agent's judgment call."""
    hits = set()
    for p in [f['path'] for f in files]:
        base = os.path.basename(p)
        psub = sub_of_path(p)
        for s in mods['subsystems']:
            if psub and s['id'] != psub:
                continue
            for m in s['modules']:
                mf = m.get('file', '')
                if not mf or mf in ('shared', 'both', 'mobile'):
                    continue
                matched = (mf == base) or ('*' in mf and mf.split('*')[0] and mf.split('*')[0] in p)
                if matched:
                    for f in m['features']:
                        hits.add(fid(s['id'], m['name'], f['name']))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pr', type=int)
    ap.add_argument('--features', default='', help='comma-separated data-fid values (overrides heuristic)')
    ap.add_argument('--label', default='', help='PR label to show (default "#<number>")')
    ap.add_argument('--dry-run', action='store_true', help='print the plan, write nothing')
    ap.add_argument('--no-pr', action='store_true', help='update files but do not open a PR')
    a = ap.parse_args()

    mods = load_modules()
    info = pr_info(a.pr)
    label = a.label or ('#' + str(info['number']))
    title = info['title']
    prid = 'pr-' + str(info['number'])

    if a.features.strip():
        fids = {x.strip() for x in a.features.split(',') if x.strip()}
    else:
        fids = impacted_fids(info.get('files', []), mods)

    bysub = {}
    for f in fids:
        bysub.setdefault(f.split('/', 1)[0], set()).add(f)

    print(f"PR {label}: {title}")
    print(f"changed files: {len(info.get('files', []))}")
    print(f"impacted features: {len(fids)} across {sorted(bysub) or '—'}")
    for f in sorted(fids):
        print('  +', f)

    if a.dry_run:
        print("(dry-run: nothing written)")
        return
    if not fids:
        print("no impacted features — nothing to do")
        return

    pj = os.path.join(HERE, 'pr-impact.json')
    data = json.load(open(pj))
    for sub, fs in bysub.items():
        d = data.setdefault(sub, {"prs": [], "marks": {}})
        if not any(p['id'] == prid for p in d['prs']):
            d['prs'].append({"id": prid, "label": label, "title": title})
        for f in fs:
            d['marks'].setdefault(f, [])
            if prid not in d['marks'][f]:
                d['marks'][f].append(prid)
    with open(pj, 'w') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    print("updated pr-impact.json")

    r = sh(sys.executable, 'gen.py', cwd=HERE)
    if r.returncode != 0:
        sys.exit('gen.py failed: ' + r.stderr)
    print("regenerated matrix.html + pr-impact.html")

    if a.no_pr:
        print("(--no-pr: changes left in the working tree)")
        return

    root = sh('git', 'rev-parse', '--show-toplevel').stdout.strip()
    branch = f'quality/pr-impact-{info["number"]}'
    rel = os.path.relpath(HERE, root)
    sh('git', 'checkout', '-b', branch, cwd=root)
    sh('git', 'add', rel, cwd=root)
    sh('git', 'commit', '-m', f'chore(recife/quality): PR impact for {label}', cwd=root)
    sh('git', 'push', '-u', 'origin', branch, cwd=root)
    body = (f"Automated PR-impact proposal for {label} ({title}).\n\n"
            f"Marks {len(fids)} feature(s) from a file-path heuristic — review them in "
            f"`pr-impact.html` and refine before merging.")
    sh('gh', 'pr', 'create', '--base', 'main', '--head', branch,
       '--title', f'chore(recife/quality): PR impact for {label}', '--body', body, cwd=root)
    print("opened proposal PR (review before merging)")


if __name__ == '__main__':
    main()
