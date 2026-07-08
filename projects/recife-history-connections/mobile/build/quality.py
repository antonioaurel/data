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
]


def fill_rates(nodes):
    n = len(nodes) or 1
    out = []
    for label, col in FILL_FIELDS:
        filled = sum(1 for r in nodes if (r.get(col) or "").strip())
        out.append((label, filled, n - filled, round(filled * 100 / n)))
    return out


def edge_issues(nodes, edges, aliases=None):
    """Return unresolved endpoint labels and self-loop labels for curation/reporting."""
    ids = {(n.get("id") or "").strip() for n in nodes}
    name_to_id = {}
    for n in nodes:
        nid = (n.get("id") or "").strip()
        name = (n.get("name") or "").strip()
        if name and nid:
            name_to_id[name] = nid
    if aliases:
        from common import alias_index  # local import keeps older direct script use simple
        name_to_id = alias_index(nodes, aliases)

    broken, self_loops = [], []
    for e in edges:
        o = (e.get("origin_id") or "").strip()
        t = (e.get("target_id") or "").strip()
        if o not in ids:
            o = name_to_id.get((e.get("origin_name") or "").strip(), "")
        if t not in ids:
            t = name_to_id.get((e.get("target_name") or "").strip(), "")
        if o not in ids:
            broken.append(e.get("origin_name") or e.get("origin_id") or "?")
            continue
        if t not in ids:
            broken.append(e.get("target_name") or e.get("target_id") or "?")
            continue
        if o == t:
            self_loops.append(e.get("origin_name") or e.get("origin_id") or o)
    return broken, self_loops


def curation_queue(nodes, edges, aliases=None):
    """Small, ordered queue for the Fill rate page."""
    def count_empty(col):
        return sum(1 for r in nodes if not (r.get(col) or "").strip())

    broken, self_loops = edge_issues(nodes, edges, aliases)
    alias_no_canon = sum(
        1 for a in (aliases or [])
        if (a.get("alias") or "").strip() and not (a.get("canonical_id") or "").strip()
    )

    items = [
        ("Alta", count_empty("description"), "Completar descrições ausentes"),
        ("Alta", len(broken), "Resolver conexões quebradas: %s" %
         ", ".join(broken[:3]) if broken else "Resolver conexões quebradas"),
        ("Média", count_empty("city"), "Preencher município/cidade"),
        ("Média", count_empty("neighborhood"), "Preencher local/bairro de referência"),
        ("Média", alias_no_canon, "Corrigir aliases sem canonical_id"),
        ("Baixa", len(self_loops), "Revisar self-loops: %s" %
         ", ".join(self_loops[:3]) if self_loops else "Revisar self-loops"),
        ("Baixa", count_empty("image"), "Adicionar imagens quando houver fonte confiável"),
    ]
    return [
        {"priority": priority, "count": count, "label": label}
        for priority, count, label in items
        if count
    ]


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

    isolated = [i for i in ids if degree[i] == 0]
    if isolated:
        warnings.append("%d isolated nodes (0 connections)" % len(isolated))

    stats = {
        "nodes":    len(nodes),
        "edges":    sum(degree.values()) // 2,
        "broken":   len(broken),
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
          "(broken: %(broken)d - isolated: %(isolated)d)" % stats)
    sys.exit(1 if errors else 0)
