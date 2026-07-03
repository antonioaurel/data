#!/usr/bin/env python3
"""
build_map.py — generate data/map.json for the map visualization (pages/mapa.html).

Joins three inputs:
    data/coords.csv   id, name, lat, lon   (place coordinates; survives the sheet sync)
    data/nodes.csv    sub_type, neighborhood per node
    data/graph.json   adjacency (which nodes each place connects to)

Output:
    data/map.json  {"places":[{id,n,st,cat,l,lat,lon,deg,conns:[{n,t}]}], "cats":[[cat,count]]}

Only "Local" nodes that have coordinates in coords.csv become map points. Each place carries
its raw sub_type (st), a coarse category (cat, for map color/legend — there are ~48 raw
sub_types, too many to color directly), neighborhood, degree, and its connections.

coords.csv is seeded from the project's Google My Maps export; see pull_coords.py.
Standard library only.
"""
import csv, json, os, re, unicodedata
from collections import Counter

ROOT      = os.path.dirname(os.path.abspath(__file__))
COORDS    = os.path.join(ROOT, "data", "coords.csv")
PERIODS   = os.path.join(ROOT, "data", "periods.csv")
NODES     = os.path.join(ROOT, "data", "nodes.csv")
GRAPH     = os.path.join(ROOT, "data", "graph.json")
MAP_OUT   = os.path.join(ROOT, "data", "map.json")

# Fallback year domain for the time slider until periods.csv is filled in (Recife's
# foundation is ~1537; leave headroom on both ends).
DEFAULT_YEARS = [1500, 2025]

# Coarse categories for map color/legend. Each raw sub_type maps to one bucket; anything
# unmapped falls into "Outros". Tune freely — the raw sub_type is still shown in the panel.
CATEGORIES = [
    ("Igreja",              ["Igreja"]),
    ("Templo Religioso",    ["Templo Religioso"]),
    ("Museu",               ["Museu", "Museu/Centro Cultural"]),
    ("Teatro",              ["Teatro"]),
    ("Sítio Histórico",     ["Sítio Histórico", "Prédios e Sítios Históricos"]),
    ("Cultura & Memória",   ["Biblioteca", "Cinema", "Monumento", "Observatório Astronômico"]),
    ("Logradouro",          ["Logradouro", "Travessa", "Viaduto"]),
    ("Praças e Parques",    ["Praça", "Parque", "Praças e Parques"]),
    ("Educação",            ["Colégio", "Universidade", "Faculdade", "Escola"]),
    ("Instituições & Governo", ["Instituição", "Militar"]),
    ("Água & Transporte",   ["Rio", "Cais", "Ponte", "Porto", "Lagoa", "Rio/Corpo d’água",
                             "Aeroporto", "Estação de Transporte Público",
                             "Transporte viário e aéreo", "Transporte"]),
    ("Saúde",               ["Hospital", "Cemitério"]),
    ("Carnaval & Clubes",   ["Agremiação Carnavalesca", "Clube de Carnaval", "Clube",
                             "Estilo Musical"]),
    ("Comércio & Mídia",    ["Mercado Público", "Bar/Restaurante", "Bar", "Comércio",
                             "Hotel", "Edifício", "Jornais e Sistemas de Comunicação",
                             "Jornal", "Forte"]),
]
SUBTYPE_TO_CAT = {st: cat for cat, sts in CATEGORIES for st in sts}


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def to_year(v):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def main():
    coords = {}  # name -> (lat, lon)
    with open(COORDS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                coords[r["name"]] = (float(r["lat"]), float(r["lon"]))
            except (ValueError, KeyError):
                continue

    periods = {}  # id -> (year_start, year_end)  either may be None
    if os.path.exists(PERIODS):
        with open(PERIODS, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                periods[r.get("id", "")] = (to_year(r.get("year_start")),
                                            to_year(r.get("year_end")))

    meta = {}  # name -> node row
    with open(NODES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            meta[r["name"]] = r

    g = json.load(open(GRAPH, encoding="utf-8"))
    gn = g["nodes"]
    adj = {}
    for a, b in g["edges"]:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    places = []
    for idx, nd in enumerate(gn):
        nm = nd["n"]
        if nm not in coords:
            continue
        m = meta.get(nm, {})
        st = norm(m.get("sub_type"))
        lat, lon = coords[nm]
        conns = [{"n": gn[j]["n"], "t": gn[j]["t"]} for j in adj.get(idx, [])]
        y0, y1 = periods.get(m.get("id", ""), (None, None))
        p = {
            "id": m.get("id", ""), "n": nm, "t": norm(m.get("type")) or "Local",
            "st": st, "cat": SUBTYPE_TO_CAT.get(st, "Outros"),
            "l": norm(m.get("neighborhood")),
            "lat": lat, "lon": lon, "deg": len(conns),
            "conns": conns,
        }
        if y0 is not None:
            p["y0"] = y0
        if y1 is not None:
            p["y1"] = y1
        places.append(p)

    cats = Counter(p["cat"] for p in places)
    # alphabetical order (accent-insensitive), with "Outros" always last
    def _akey(c):
        return unicodedata.normalize("NFD", c).encode("ascii", "ignore").decode().lower()
    cats_sorted = sorted([[c, n] for c, n in cats.items() if c != "Outros"],
                         key=lambda x: _akey(x[0]))
    if cats.get("Outros"):
        cats_sorted.append(["Outros", cats["Outros"]])

    # neighborhoods, sorted by frequency then name (for the "Bairro" filter)
    bairros = Counter(p["l"] for p in places if p["l"])
    bairros_sorted = [b for b, _ in sorted(bairros.items(), key=lambda x: (-x[1], x[0]))]

    # year domain for the time slider: always span the broad historical range, extended
    # to include any filled periods that fall outside it (never shrink to the few dated).
    ys = [p[k] for p in places for k in ("y0", "y1") if k in p]
    years = [min([DEFAULT_YEARS[0]] + ys), max([DEFAULT_YEARS[1]] + ys)]
    dated = sum(1 for p in places if "y0" in p or "y1" in p)

    # type layer (filter above categories). Map points are Local-only for now (only
    # Locais have coordinates), but the 3 model types are exposed so the type→category
    # enable/disable behavior works and is ready when other types gain coordinates.
    TYPE_ORDER = ["Local", "Personagem", "Fato Histórico"]
    tcount = Counter(p["t"] for p in places)
    types_sorted = [[t, tcount.get(t, 0)] for t in TYPE_ORDER]
    # category -> type (categories are Local buckets today; derived from the data)
    cat_type = {}
    for p in places:
        cat_type.setdefault(p["cat"], p["t"])

    out = {"places": places, "cats": cats_sorted, "catType": cat_type,
           "types": types_sorted, "bairros": bairros_sorted,
           "years": years, "dated": dated}
    with open(MAP_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("map.json: %d places, %d categories, %d bairros" %
          (len(places), len(cats_sorted), len(bairros_sorted)))
    print("  years: %d–%d  (%d/%d places with a period filled in)" %
          (years[0], years[1], dated, len(places)))
    for c, n in cats_sorted:
        print("  %4d  %s" % (n, c))


if __name__ == "__main__":
    main()
