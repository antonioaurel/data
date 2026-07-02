#!/usr/bin/env python3
"""
quality.py — data-quality & reference-integrity report for the mobile build.

Importable (build.py calls report()) and runnable on its own:
    python3 quality.py

Checks: duplicate ids/names, edges pointing at non-existent nodes, isolated nodes,
and the coordinate gap that keeps the Map projection empty. Also reports fill rates
for the fields the mobile detail relies on. Standard library only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_csvs, source_data_dir, build_adjacency  # noqa: E402

# Fields the mobile detail/list actually surface, with the CSV column behind each.
FILL_FIELDS = [
    ("name",         "name"),
    ("type",         "type"),
    ("description",  "description"),
    ("neighborhood", "neighborhood"),
    ("image",        "image"),
    ("source",       "source"),
    ("coordinates",  "lat"),  # lat presence stands in for geo readiness
]


def fill_rates(nodes):
    n = len(nodes) or 1
    out = []
    for label, col in FILL_FIELDS:
        filled = sum(1 for r in nodes if (r.get(col) or "").strip())
        out.append((label, filled, n - filled, round(filled * 100 / n)))
    return out


def integrity(nodes, edges, aliases=None):
    ids, degree, _neighbors, _n2i, broken = build_adjacency(nodes, edges, aliases)
    errors, warnings = [], []

    seen_id, seen_name = set(), set()
    for r in nodes:
        i = (r.get("id") or "").strip()
        nm = (r.get("name") or "").strip()
        if not i:
            errors.append("node with empty id (%r)" % nm)
        elif i in seen_id:
            errors.append("duplicate id: %s" % i)
        seen_id.add(i)
        if nm in seen_name:
            errors.append("duplicate name: %r" % nm)
        seen_name.add(nm)

    if broken:
        sample = ", ".join(repr(b) for b in broken[:5])
        warnings.append("%d edges reference a non-existent node (dropped): %s%s"
                        % (len(broken), sample, " …" if len(broken) > 5 else ""))

    with_geo = sum(1 for r in nodes
                   if (r.get("lat") or "").strip() and (r.get("lon") or "").strip())
    if with_geo == 0:
        warnings.append("0 nodes have coordinates -> Map projection has no data yet (Phase 5 blocked)")

    isolated = [i for i in ids if degree[i] == 0]
    if isolated:
        warnings.append("%d isolated nodes (0 connections)" % len(isolated))

    stats = {
        "nodes":    len(nodes),
        "edges":    sum(degree.values()) // 2,
        "broken":   len(broken),
        "with_geo": with_geo,
        "isolated": len(isolated),
    }
    return errors, warnings, stats


def report(nodes, edges, aliases=None):
    """Print the report; return (errors, warnings, stats)."""
    errors, warnings, stats = integrity(nodes, edges, aliases)

    print("  fill rates (fields the mobile detail uses):")
    for label, filled, empty, pct in fill_rates(nodes):
        bar = "#" * (pct // 5) + "." * (20 - pct // 5)
        print("    %-13s [%s] %3d%%  (%d filled / %d empty)" % (label, bar, pct, filled, empty))

    for w in warnings:
        print("  warning:", w)
    for e in errors:
        print("  ERROR:", e)
    return errors, warnings, stats


if __name__ == "__main__":
    src = source_data_dir(os.path.dirname(os.path.abspath(__file__)))
    nodes, edges, aliases = load_csvs(src)
    errors, _w, stats = report(nodes, edges, aliases)
    print("base: %(nodes)d nodes - %(edges)d edges "
          "(broken: %(broken)d - with_geo: %(with_geo)d - isolated: %(isolated)d)" % stats)
    sys.exit(1 if errors else 0)
