#!/usr/bin/env python3
"""
build.py — generate the derived files the site consumes, from the normalized model.

Source of truth (Google Sheets export, 3 tabs):
    data/nodes.csv    id, name, type, sub_type, neighborhood, image, description, ...
    data/edges.csv    origin_id, target_id, relationship_type, ...
    data/aliases.csv  alias, canonical_id, ...

Generated outputs (same shape the site already consumes — no visual change):
    data/graph.json   {"nodes":[{"n":name,"t":type}], "edges":[[i,j], ...]}  (index pairs, undirected)
    data/content.json {name: {"st":sub_type,"l":neighborhood,"img":url,"d":description}}

Usage:
    python3 build.py            # validate and (re)generate the JSON
    python3 build.py --check    # validate and verify committed JSON are in sync
                                # (writes nothing; exits non-zero if they diverge) — used in CI

Edge resolution (migration note, item 7):
    1) target_id found in nodes.id        -> use it
    2) target_name matches nodes.name     -> use it
    3) target_name matches aliases.alias  -> resolve to canonical_id
    4) otherwise                          -> broken edge (dropped from graph, warned)

Severities (item 13):
    ERROR (fails build/CI): duplicate id, duplicate name, unresolved origin.
    WARN  (report only):    unresolved target (broken edge), alias without canonical_id,
                            self-loop, missing description, missing city.

Standard library only. Run whenever the base changes; commit the JSON alongside the CSVs.
"""
import csv, json, os, sys, argparse

ROOT        = os.path.dirname(os.path.abspath(__file__))
NODES_SRC   = os.path.join(ROOT, "data", "nodes.csv")
EDGES_SRC   = os.path.join(ROOT, "data", "edges.csv")
ALIASES_SRC = os.path.join(ROOT, "data", "aliases.csv")
GRAPH_OUT   = os.path.join(ROOT, "data", "graph.json")
CONTENT_OUT = os.path.join(ROOT, "data", "content.json")
# Legacy wide CSV, now a GENERATED artifact (not a source). diagram.html and stats.html
# still read it directly; regenerating it from the model keeps every page on the same data.
WIDE_OUT    = os.path.join(ROOT, "data", "lista-geral-do-mapeamento.csv")
WIDE_HEADER = (["Nome", "Tipo", "Sub-Tipo", "Local", "Imagem", "Descrição"]
               + ["Interconexão %d" % i for i in range(1, 16)])


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    return read_csv(NODES_SRC), read_csv(EDGES_SRC), read_csv(ALIASES_SRC)


def build(nodes, edges, aliases):
    """Build (graph, content, stats, errors, warnings) deterministically."""
    errors, warnings = [], []

    # --- node indexes (file order) ---
    id_to_index, name_to_id = {}, {}
    seen_id, seen_name = set(), set()
    nodes_out, content = [], {}

    for i, r in enumerate(nodes, start=2):  # line 2 = first data row
        nid  = (r.get("id") or "").strip()
        name = (r.get("name") or "").strip()
        typ  = (r.get("type") or "").strip()
        if not nid:
            errors.append(f"nodes line {i}: empty id ({name!r})")
            continue
        if not name:
            errors.append(f"nodes line {i}: empty name ({nid})")
            continue
        if nid in seen_id:
            errors.append(f"nodes line {i}: duplicate id: {nid}")
            continue
        if name in seen_name:
            errors.append(f"nodes line {i}: duplicate name: {name!r}")
            continue
        seen_id.add(nid); seen_name.add(name)
        id_to_index[nid] = len(nodes_out)
        name_to_id[name] = nid
        nodes_out.append({"n": name, "t": typ})
        content[name] = {
            "st":  (r.get("sub_type") or "").strip(),
            "l":   (r.get("neighborhood") or "").strip(),
            "img": (r.get("image") or "").strip(),
            "d":   (r.get("description") or "").strip(),
        }

    # quality counts (reported as totals, not one line each)
    n_no_desc = sum(1 for r in nodes if not (r.get("description") or "").strip())
    n_no_city = sum(1 for r in nodes if not (r.get("city") or "").strip())
    if n_no_desc:
        warnings.append(f"{n_no_desc} nodes without description")
    if n_no_city:
        warnings.append(f"{n_no_city} nodes without city")

    # --- alias map (alias -> canonical_id) ---
    alias_to_id = {}
    alias_no_canon = 0
    for r in aliases:
        alias = (r.get("alias") or "").strip()
        canon = (r.get("canonical_id") or "").strip()
        if not alias:
            continue
        if not canon:
            alias_no_canon += 1
            continue
        alias_to_id[alias] = canon
    if alias_no_canon:
        warnings.append(f"{alias_no_canon} aliases without canonical_id")

    def resolve(eid, ename):
        eid, ename = (eid or "").strip(), (ename or "").strip()
        if eid in id_to_index:
            return eid
        if ename in name_to_id:
            return name_to_id[ename]
        if ename in alias_to_id and alias_to_id[ename] in id_to_index:
            return alias_to_id[ename]
        return None

    # --- edges (undirected, deduplicated) ---
    edge_set = set()
    broken = self_loops = 0
    for r in edges:
        o = resolve(r.get("origin_id"), r.get("origin_name"))
        t = resolve(r.get("target_id"), r.get("target_name"))
        if o is None:
            errors.append("edges: unresolved origin: %r" % (r.get("origin_name") or r.get("origin_id")))
            continue
        if t is None:
            broken += 1
            continue
        ia, ib = id_to_index[o], id_to_index[t]
        if ia == ib:
            self_loops += 1
            continue
        edge_set.add((min(ia, ib), max(ia, ib)))
    if broken:
        warnings.append(f"{broken} broken edges (target not found in nodes/aliases) - dropped")
    if self_loops:
        warnings.append(f"{self_loops} self-loops dropped")

    graph = {"nodes": nodes_out, "edges": sorted(edge_set)}
    stats = {"nodes": len(nodes_out), "edges": len(edge_set), "broken": broken, "self_loops": self_loops}
    return graph, content, stats, errors, warnings


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def wide_csv_text(graph, content):
    """Regenerate the legacy wide CSV (used by diagram.html / stats.html) from the model.
    Each node lists up to 15 neighbor names (undirected, sorted), matching the old schema."""
    import io
    names = [n["n"] for n in graph["nodes"]]
    adj = [set() for _ in names]
    for a, b in graph["edges"]:
        adj[a].add(b); adj[b].add(a)
    buf = io.StringIO()
    w = csv.writer(buf)  # default lineterminator is CRLF, matching the original file
    w.writerow(WIDE_HEADER)
    for i, nd in enumerate(graph["nodes"]):
        c = content[nd["n"]]
        neigh = sorted(names[j] for j in adj[i])[:15]
        neigh += [""] * (15 - len(neigh))
        w.writerow([nd["n"], nd["t"], c["st"], c["l"], c["img"], c["d"]] + neigh)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="write nothing; fail if committed JSON are out of sync")
    args = ap.parse_args()

    nodes, edges, aliases = load()
    graph, content, stats, errors, warnings = build(nodes, edges, aliases)
    graph_txt, content_txt = dumps(graph), dumps(content)
    wide_txt = wide_csv_text(graph, content)

    for w in warnings:
        print("  warning:", w)
    for e in errors[:20]:
        print("  ERROR:", e)
    if len(errors) > 20:
        print("  ... +%d more errors" % (len(errors) - 20))

    print("base: %d nodes - %d edges (broken: %d - self-loops: %d)"
          % (stats["nodes"], stats["edges"], stats["broken"], stats["self_loops"]))

    if errors:
        print("FAILED: fix the errors above.")
        return 1

    if args.check:
        ok = True
        for path, txt in [(GRAPH_OUT, graph_txt), (CONTENT_OUT, content_txt), (WIDE_OUT, wide_txt)]:
            cur = open(path, encoding="utf-8", newline="").read() if os.path.exists(path) else None
            if cur != txt:
                print("OUT OF SYNC:", os.path.relpath(path, ROOT), "- run `python3 build.py` and commit.")
                ok = False
        if ok:
            print("OK: derived files in sync with the base.")
        return 0 if ok else 1

    with open(GRAPH_OUT, "w", encoding="utf-8") as f:
        f.write(graph_txt)
    with open(CONTENT_OUT, "w", encoding="utf-8") as f:
        f.write(content_txt)
    with open(WIDE_OUT, "w", encoding="utf-8", newline="") as f:
        f.write(wide_txt)
    print("generated:", ", ".join(os.path.relpath(p, ROOT)
          for p in (GRAPH_OUT, CONTENT_OUT, WIDE_OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
