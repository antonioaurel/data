"""
common.py — shared helpers for the mobile-site build (Phase 1 data layer).

The source of truth stays the existing project CSVs
(recife-history-connections/data/{nodes,edges,aliases}.csv); this package only
reads them and derives static JSON. Standard library only.
"""
import csv
import os
import unicodedata

# nodes.csv carries Portuguese type labels; the mobile app uses three keys
# (local / personagem / evento) that also appear in routes (#tipos=local,evento).
# "Fato Histórico" is surfaced as "Evento" in the mobile UI.
TYPE_MAP = {
    "Local":          "local",
    "Personagem":     "personagem",
    "Fato Histórico": "evento",
}
DEFAULT_TYPE = "other"


def map_type(pt_type):
    return TYPE_MAP.get((pt_type or "").strip(), DEFAULT_TYPE)


def normalize(s):
    """Lowercase + strip diacritics — for diacritic-insensitive, case-insensitive search."""
    s = (s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def source_data_dir(build_dir):
    """The shared source CSVs live two levels up from mobile/build/ (…/data)."""
    return os.path.normpath(os.path.join(build_dir, "..", "..", "data"))


def load_csvs(data_dir):
    def rd(name):
        with open(os.path.join(data_dir, name), encoding="utf-8") as f:
            return list(csv.DictReader(f))
    return rd("nodes.csv"), rd("edges.csv"), rd("aliases.csv")


def alias_index(nodes, aliases):
    """{name -> id} resolver: canonical names first, then aliases (alias -> canonical_id)."""
    name_to_id = {(n.get("name") or "").strip(): (n.get("id") or "").strip() for n in nodes}
    ids = set(name_to_id.values())
    for a in (aliases or []):
        al = (a.get("alias") or "").strip()
        cid = (a.get("canonical_id") or "").strip()
        if al and cid in ids and al not in name_to_id:
            name_to_id[al] = cid
    return name_to_id


def resolve_endpoint(eid, ename, ids, name_to_id):
    eid = (eid or "").strip()
    if eid in ids:
        return eid
    return name_to_id.get((ename or "").strip(), "")


def build_adjacency(nodes, edges, aliases=None):
    """Resolve edges by id (falling back to name, then alias) into an undirected adjacency.

    Returns (ids, degree{id:int}, neighbors{id:set}, name_to_id, broken_list).
    Parallel edges and self-loops are collapsed; unresolved endpoints are listed."""
    ids = {(n.get("id") or "").strip() for n in nodes}
    name_to_id = alias_index(nodes, aliases)
    neighbors = {i: set() for i in ids}
    broken = []
    for e in edges:
        o = resolve_endpoint(e.get("origin_id"), e.get("origin_name"), ids, name_to_id)
        t = resolve_endpoint(e.get("target_id"), e.get("target_name"), ids, name_to_id)
        if o not in ids:
            broken.append(e.get("origin_name") or e.get("origin_id") or "?")
            continue
        if t not in ids:
            broken.append(e.get("target_name") or e.get("target_id") or "?")
            continue
        if o == t:
            continue
        neighbors[o].add(t)
        neighbors[t].add(o)
    degree = {i: len(neighbors[i]) for i in ids}
    return ids, degree, neighbors, name_to_id, broken
