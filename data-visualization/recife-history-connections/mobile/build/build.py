#!/usr/bin/env python3
"""
build.py — Phase 1 data layer for the mobile progressive-exploration site.

Reads the shared source CSVs (recife-history-connections/data/{nodes,edges,aliases}.csv)
and emits the static JSON the mobile site consumes, plus a build/quality report.

Outputs (into mobile/data/):
    index.json          [{id,name,type,conn_count}]                         list + fast filter
    search.json         [{id,name,type,norm,aliases:[normalized]}]          alias-aware search
    sources.json        [{id,title,source_type,author,year,url,notes}]      FT registry
    matrix.json         [{type_a,type_b,count,strength_sum}]                 type×type adjacency (3×3, symmetric)
    node/{id}.json      per-node detail incl. resolved edges + sources + aliases

Static HTML (SSG) is Phase 2+; this phase produces data only.
Standard library only. Run from anywhere: python3 build.py
"""
import json
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_csvs, source_data_dir, normalize, map_type,  # noqa: E402
                    alias_index, resolve_endpoint)
import quality  # noqa: E402
import sitegen  # noqa: E402

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR   = source_data_dir(BUILD_DIR)
OUT_DIR   = os.path.normpath(os.path.join(BUILD_DIR, "..", "data"))
NODE_DIR  = os.path.join(OUT_DIR, "node")
SITE_DIR  = os.path.normpath(os.path.join(BUILD_DIR, "..", "site"))

# Node-type order for the type×type matrix. Concentrated on the three original types
# that actually exist in the base (Local / Personagem / Fato Histórico). The matrix is 3×3.
CANON_TYPES = ["place", "person", "historical_fact"]

# Soft/hard ceilings for the initial-route DATA (index + search), gzip. The
# shell HTML/CSS/JS budget is measured in Phase 2 when those files exist.
BUDGET_SOFT_KB = 150
BUDGET_HARD_KB = 200


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def build_sources(nodes):
    """Split the ';'-delimited `source` column into a deduped FT registry.
    Returns (records, url_to_id)."""
    records, url_to_id = [], {}
    for r in nodes:
        for raw in (r.get("source") or "").split(";"):
            u = raw.strip()
            if not u or u in url_to_id:
                continue
            fid = "FT-%04d" % (len(records) + 1)
            url_to_id[u] = fid
            is_url = u.startswith("http")
            records.append({
                "id": fid, "title": u,
                "source_type": "url" if is_url else "text",
                "author": "", "year": "",
                "url": u if is_url else "", "notes": "",
            })
    return records, url_to_id


def node_source_ids(row, url_to_id):
    ids = []
    for raw in (row.get("source") or "").split(";"):
        u = raw.strip()
        if u and url_to_id.get(u) and url_to_id[u] not in ids:
            ids.append(url_to_id[u])
    return ids


def build_edge_index(nodes, edges, aliases):
    """node_id -> {target_id: {type, strength}} (undirected, first-seen wins).
    Endpoints resolve by id, then name, then alias. `strength` defaults to 1 —
    the data has no weight column yet."""
    ids = {(n.get("id") or "").strip() for n in nodes}
    name_to_id = alias_index(nodes, aliases)
    idx = {i: {} for i in ids}
    for e in edges:
        o = resolve_endpoint(e.get("origin_id"), e.get("origin_name"), ids, name_to_id)
        t = resolve_endpoint(e.get("target_id"), e.get("target_name"), ids, name_to_id)
        if o not in ids or t not in ids or o == t:
            continue
        rtype = (e.get("relationship_type") or "").strip()
        if t not in idx[o]:
            idx[o][t] = {"type": rtype, "strength": 1}
        if o not in idx[t]:
            idx[t][o] = {"type": rtype, "strength": 1}
    return idx


def build_matrix(nodes, edge_idx):
    """Aggregated type×type adjacency over the deduped undirected edge set.
    Returns (matrix_rows, edges_counted, pair_nodes). Symmetric → one row per
    unordered canonical type pair (incl. the diagonal). pair_nodes maps each pair
    to the set of node ids that participate in ≥1 edge of that pair (drill-down)."""
    type_of = {(n.get("id") or "").strip(): map_type(n.get("type")) for n in nodes}
    rank = {t: i for i, t in enumerate(CANON_TYPES)}

    count, strength, pair_nodes = {}, {}, {}
    seen = set()
    for a, nbrs in edge_idx.items():
        for b, meta in nbrs.items():
            key = (a, b) if a < b else (b, a)
            if key in seen:
                continue
            seen.add(key)
            ta, tb = type_of[a], type_of[b]
            if ta not in rank or tb not in rank:
                continue  # outside the three concentrated types (shouldn't happen)
            pk = (ta, tb) if rank[ta] <= rank[tb] else (tb, ta)
            count[pk] = count.get(pk, 0) + 1
            strength[pk] = strength.get(pk, 0) + meta["strength"]
            pair_nodes.setdefault(pk, set()).update((a, b))

    rows = []
    for i, ta in enumerate(CANON_TYPES):
        for tb in CANON_TYPES[i:]:
            rows.append({"type_a": ta, "type_b": tb,
                         "count": count.get((ta, tb), 0),
                         "strength_sum": strength.get((ta, tb), 0)})
    return rows, len(seen), pair_nodes


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def kb(text):
    return len(text.encode("utf-8")) / 1024.0


def gz_kb(text):
    return len(gzip.compress(text.encode("utf-8"))) / 1024.0


def main():
    nodes, edges, aliases = load_csvs(SRC_DIR)

    id_to_node = {(n.get("id") or "").strip(): n for n in nodes}
    alias_map = {}
    for a in aliases:
        cid = (a.get("canonical_id") or "").strip()
        al = (a.get("alias") or "").strip()
        if cid and al:
            alias_map.setdefault(cid, []).append(al)

    source_records, url_to_id = build_sources(nodes)
    src_by_id = {s["id"]: s for s in source_records}
    edge_idx = build_edge_index(nodes, edges, aliases)

    index, search, details = [], [], []
    os.makedirs(NODE_DIR, exist_ok=True)

    for r in nodes:
        nid = (r.get("id") or "").strip()
        name = (r.get("name") or "").strip()
        typ = map_type(r.get("type"))
        nbhd = (r.get("neighborhood") or "").strip()

        index.append({"id": nid, "name": name, "type": typ,
                      "conn_count": len(edge_idx.get(nid, {}))})

        search.append({"id": nid, "name": name, "type": typ,
                       "norm": normalize(name),
                       "aliases": [normalize(a) for a in alias_map.get(nid, [])]})

        edges_out = []
        for tid, meta in sorted(edge_idx.get(nid, {}).items(),
                                key=lambda kv: (id_to_node[kv[0]].get("name") or "")):
            tgt = id_to_node[tid]
            edges_out.append({
                "target_id": tid,
                "target_name": (tgt.get("name") or "").strip(),
                "target_type": map_type(tgt.get("type")),
                "type": meta["type"], "strength": meta["strength"],
            })

        detail = {
            "id": nid, "name": name, "type": typ,
            "subtype": (r.get("sub_type") or "").strip(),
            "description": (r.get("description") or "").strip(),
            "period": "",                       # not in the data yet
            "reference_location": nbhd,
            "municipality": (r.get("city") or "").strip(),
            "neighborhood": nbhd,
            "image": (r.get("image") or "").strip(),
            "aliases": alias_map.get(nid, []),
            "sources": [src_by_id[i] for i in node_source_ids(r, url_to_id)],
            "edges": edges_out,
        }
        details.append(detail)
        write(os.path.join(NODE_DIR, nid + ".json"), dumps(detail))

    index.sort(key=lambda o: o["name"])
    search.sort(key=lambda o: o["name"])

    index_txt = dumps(index)
    search_txt = dumps(search)
    write(os.path.join(OUT_DIR, "index.json"), index_txt)
    write(os.path.join(OUT_DIR, "search.json"), search_txt)
    write(os.path.join(OUT_DIR, "sources.json"), dumps(source_records))

    matrix, edges_counted, pair_nodes = build_matrix(nodes, edge_idx)
    write(os.path.join(OUT_DIR, "matrix.json"), dumps(matrix))

    # per-pair node sets for the matrix drill-down (lazy-loaded on cell tap)
    pairs_dir = os.path.join(OUT_DIR, "pairs")
    os.makedirs(pairs_dir, exist_ok=True)
    for (ta, tb), ids in pair_nodes.items():
        write(os.path.join(pairs_dir, "%s-%s.json" % (ta, tb)),
              dumps({"a": ta, "b": tb, "nodes": sorted(ids)}))

    # ---- static HTML (SSG): home + list + matrix + about + favorites + node pages ----
    n_pages = sitegen.build_site(index, details, matrix, source_records, SITE_DIR)

    # ---- report ----
    print("=== mobile build — Phase 1 (data layer) ===")
    errors, _warnings, stats = quality.report(nodes, edges, aliases)
    print("  sources registry: %d distinct entries" % len(source_records))
    print("  per-node detail:  %d files in mobile/data/node/" % len(nodes))

    # initial route = the Home landing: index.html + app.css + app.js (no eager JSON;
    # search.json/node files load lazily on interaction).
    def read(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""
    home_html = read(os.path.join(SITE_DIR, "index.html"))
    list_html = read(os.path.join(SITE_DIR, "list.html"))
    css = read(os.path.join(SITE_DIR, "assets", "app.css"))
    js = read(os.path.join(SITE_DIR, "assets", "app.js"))

    route_gz = gz_kb(home_html) + gz_kb(css) + gz_kb(js)
    ceiling = "OK" if route_gz <= BUDGET_SOFT_KB else ("OVER SOFT" if route_gz <= BUDGET_HARD_KB else "OVER HARD")
    print("  INITIAL ROUTE (index.html + app.css + app.js), gzip: %.1f KB  [budget %d/%d -> %s]"
          % (route_gz, BUDGET_SOFT_KB, BUDGET_HARD_KB, ceiling))
    print("    index.html %.1f/%.1f  list.html %.1f/%.1f  app.css %.1f/%.1f  app.js %.1f/%.1f  (raw/gzip KB)"
          % (kb(home_html), gz_kb(home_html), kb(list_html), gz_kb(list_html),
             kb(css), gz_kb(css), kb(js), gz_kb(js)))
    print("    lazy on interaction: search.json %.1f KB gzip (first search); node/{id}.json on expand"
          % gz_kb(search_txt))
    nonzero = sum(1 for m in matrix if m["count"])
    print("  matrix.json: %d type-pair rows (%d non-empty), %d undirected edges aggregated; %d pairs/*.json"
          % (len(matrix), nonzero, edges_counted, len(pair_nodes)))
    print("  index.json %.1f KB  search.json %.1f KB"
          % (kb(index_txt), kb(search_txt)))
    print("base: %(nodes)d nodes - %(edges)d edges "
          "(broken: %(broken)d - isolated: %(isolated)d)" % stats)

    if errors:
        print("FAILED: fix the errors above.")
        return 1
    print("generated: mobile/data/{index,search,sources,matrix}.json + node/*.json")
    print("           site/{index,list}.html + site/node/*.html (%d detail pages)" % n_pages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
