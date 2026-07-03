#!/usr/bin/env python3
"""
i18n_report.py — coverage report for English descriptions (no database needed).

This is the "no-SQL" equivalent of a view that lists the nodes still missing a
translation (see ADR 0003). It compares the canonical node list (data/nodes.csv)
against the English source (mobile/data-source/descriptions_en.json, keyed by id)
and reports:

    - how many nodes have a non-empty EN description,
    - which nodes are missing one (id + name + type),
    - any EN keys that don't match a known node (orphans).

Usage:
    python3 tools/i18n_report.py            # print the report (exit 0)
    python3 tools/i18n_report.py --strict   # exit 1 if any node is missing EN (for CI)

Standard library only.
"""
import os, csv, json, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES = os.path.join(ROOT, "data", "nodes.csv")
EN = os.path.join(ROOT, "mobile", "data-source", "descriptions_en.json")


def load_nodes():
    with open(NODES, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        nid = (r.get("id") or "").strip()
        if not nid:
            continue
        out.append((nid, (r.get("name") or "").strip(), (r.get("type") or "").strip()))
    return out


def load_en():
    with open(EN, encoding="utf-8") as f:
        data = json.load(f)
    en = {}
    for k, v in data.items():
        text = v if isinstance(v, str) else (v.get("d") or v.get("de") or "")
        en[k.strip()] = (text or "").strip()
    return en


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any node is missing an EN description")
    args = ap.parse_args()

    nodes = load_nodes()
    en = load_en()
    ids = {nid for nid, _, _ in nodes}

    missing = [(nid, name, typ) for nid, name, typ in nodes if not en.get(nid)]
    orphans = sorted(k for k in en if k not in ids)
    have = len(nodes) - len(missing)
    pct = (have / len(nodes) * 100) if nodes else 0.0

    print("EN description coverage")
    print("-" * 32)
    print(f"nodes            : {len(nodes)}")
    print(f"with EN          : {have} ({pct:.1f}%)")
    print(f"missing EN       : {len(missing)}")
    print(f"orphan EN keys   : {len(orphans)}")

    if missing:
        print("\nMissing EN (id — name [type]):")
        for nid, name, typ in missing:
            print(f"  {nid}  {name}  [{typ}]")
    if orphans:
        print("\nOrphan EN keys (no matching node):")
        for k in orphans:
            print(f"  {k}")

    if args.strict and missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
