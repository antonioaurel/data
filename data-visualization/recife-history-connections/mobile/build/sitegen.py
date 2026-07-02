"""
sitegen.py — static HTML generation (SSG) for the mobile site, Phase 2.

Pre-renders Home (index.html) and List (list.html) from the index so the site is
navigable with no JavaScript; assets/app.js then enhances (search/filter/sort/expand).
Called by build.py after the JSON artifacts are written. Standard library only.
"""
import html
import math
import os

from common import normalize

# type -> (Portuguese label, icon). Concentrated on the three original types in the base.
# The .get() fallback keeps rendering safe if an unexpected type ever appears.
TYPE_META = {
    "place":           ("Local",           "📍"),
    "person":          ("Personagem",      "👤"),
    "historical_fact": ("Fato Histórico",  "📜"),
}
FALLBACK_META = ("Outro", "●")
CATEGORY_ORDER = ["place", "person", "historical_fact"]


def esc(s):
    return html.escape(s or "", quote=True)


def badge(t, with_label=True):
    label, ico = TYPE_META.get(t, FALLBACK_META)
    inner = "<span class='ico'>%s</span>%s" % (ico, esc(label) if with_label else "")
    return "<span class='badge t-%s'>%s</span>" % (t, inner)


def bottom_nav(active, base=""):
    items = [(base + "index.html",     "Explorar",  "🧭", "explorar"),
             (base + "favoritos.html", "Favoritos", "★",  "favoritos"),
             (base + "sobre.html",     "Sobre",     "ℹ",  "sobre")]
    lis = []
    for href, label, ico, key in items:
        cur = " aria-current='page'" if key == active else ""
        lis.append("<li><a href='%s'%s><span class='ico' aria-hidden='true'>%s</span>%s</a></li>"
                   % (href, cur, ico, esc(label)))
    return ("<nav class='bottom-nav' aria-label='Seções'><ul>%s</ul></nav>" % "".join(lis))


def shell(title, page, datapath, active_nav, body, base=""):
    return (
        "<!doctype html>\n"
        "<html lang='pt-BR' class='no-js'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>\n"
        "<title>%s</title>\n"
        "<meta name='description' content='Conexões da História — pessoas, lugares e fatos que formaram Recife e Pernambuco.'>\n"
        "<link rel='stylesheet' href='%sassets/app.css'>\n"
        "<script>document.documentElement.className='has-js';</script>\n"
        "</head>\n"
        "<body data-page='%s' data-datapath='%s'>\n"
        "<a class='skip-link' href='#main'>Pular para o conteúdo</a>\n"
        "<header class='app-header'><div class='wrap'>"
        "<h1 class='app-title'><a href='%sindex.html'>Conexões da História</a></h1>"
        "</div></header>\n"
        "<main id='main' class='wrap'>\n%s\n</main>\n"
        "%s\n"
        "<script src='%sassets/app.js' defer></script>\n"
        "</body>\n</html>\n"
        % (esc(title), base, page, esc(datapath), base, body, bottom_nav(active_nav, base), base)
    )


def present_types(index):
    counts = {}
    for o in index:
        counts[o["type"]] = counts.get(o["type"], 0) + 1
    return [(t, counts[t]) for t in CATEGORY_ORDER if counts.get(t)]


def render_home(index):
    types = present_types(index)
    chips = "".join(
        "<a class='chip t-%s is-active' href='list.html#type=%s'>"
        "<span class='ico' aria-hidden='true'>%s</span>%s "
        "<span class='conn'>(%d)</span></a>"
        % (t, t, TYPE_META[t][1], esc(TYPE_META[t][0]), c)
        for t, c in types)

    top = sorted(index, key=lambda o: (-o["conn_count"], o["name"]))[:8]
    starts = "".join(
        "<li class='start-item t-%s'><span class='rank'>%d</span>%s"
        "<span class='card-body'><span class='card-name'>%s</span>"
        "<span class='card-meta'><span class='conn'>%d conexões</span></span></span></li>"
        % (o["type"], i + 1, badge(o["type"], with_label=False), esc(o["name"]), o["conn_count"])
        for i, o in enumerate(top))

    body = (
        "<form id='home-search' class='search js-only' role='search' action='list.html'>"
        "<input id='home-q' type='search' name='q' placeholder='Buscar pessoa, lugar, fato…' "
        "autocomplete='off' aria-label='Buscar'>"
        "</form>\n"
        "<ul id='home-results' class='cards' hidden></ul>\n"
        "<h2 class='section-h'>Explorar por tipo</h2>\n"
        "<div class='chips'>%s</div>\n"
        "<h2 class='section-h'>Comece por aqui</h2>\n"
        "<p class='no-js-only'><a href='list.html'>Ver todos os nós →</a></p>\n"
        "<ul class='starts'>%s</ul>\n"
        "<h2 class='section-h'>Panorama</h2>\n"
        "<p class='view-links'><a href='matriz.html'>▦ Matriz de conexões por tipo</a></p>\n"
        "<p style='margin-top:16px'><a href='list.html'>Ver a lista completa →</a></p>\n"
        % (chips, starts)
    )
    return shell("Conexões da História", "home", "../data", "explorar", body)


def render_list(index):
    types = present_types(index)
    chips = "".join(
        "<button type='button' class='chip t-%s' data-type='%s' aria-pressed='false'>"
        "<span class='ico' aria-hidden='true'>%s</span>%s</button>"
        % (t, t, TYPE_META[t][1], esc(TYPE_META[t][0]))
        for t, _c in types)

    cards = []
    for o in sorted(index, key=lambda o: o["name"]):
        t = o["type"]
        label = TYPE_META.get(t, FALLBACK_META)[0]
        cards.append(
            "<li class='card t-%s' data-id='%s' data-type='%s' data-conn='%d' data-name='%s' aria-expanded='false'>"
            "<button class='card-main' type='button' aria-label='%s — %s, %d conexões. Toque para ver conexões.'>"
            "<span class='card-body'><span class='card-name'>%s</span>"
            "<span class='card-meta'>%s<span class='conn'>%d conexões</span>"
            "<span class='chevron' aria-hidden='true'>›</span></span></span>"
            "</button></li>"
            % (t, esc(o["id"]), t, o["conn_count"], esc(normalize(o["name"])),
               esc(o["name"]), esc(label), o["conn_count"],
               esc(o["name"]), badge(t), o["conn_count"])
        )

    body = (
        "<p class='view-links'><a href='matriz.html'>▦ Ver matriz de conexões</a></p>\n"
        "<div id='list-context' hidden></div>\n"
        "<div class='search js-only'><input id='q' type='search' placeholder='Buscar…' "
        "autocomplete='off' aria-label='Buscar na lista'></div>\n"
        "<div class='js-only'><h2 class='section-h'>Filtros</h2>"
        "<div class='chips'>%s</div></div>\n"
        "<div class='toolbar js-only'>"
        "<span><label for='sort'>Ordenar:</label> "
        "<select id='sort'><option value='name'>Nome</option>"
        "<option value='connections'>Conexões</option>"
        "<option value='type'>Tipo</option></select></span>"
        "<span id='count' class='count'>%d nós</span>"
        "</div>\n"
        "<p id='empty' class='empty-state' hidden>Nenhum resultado.</p>\n"
        "<ul id='list' class='cards'>%s</ul>\n"
        % (chips, len(index), "".join(cards))
    )
    return shell("Lista — Conexões da História", "list", "../data", "explorar", body)


def render_node(d):
    """Full static detail page for one node (share/SEO/no-JS). Lives at site/node/{id}.html,
    so assets are ../ and data is ../../data; sibling node links are '{id}.html'."""
    t = d["type"]
    p = ["<p><a class='detail-back' href='../list.html'>← Lista</a></p>",
         "<article class='detail'>",
         "<div class='detail-head'>%s<h1 class='detail-name'>%s</h1></div>"
         % (badge(t), esc(d["name"])),
         "<button id='fav-btn' class='fav-btn js-only' type='button' data-id='%s' "
         "aria-pressed='false'>☆ Favoritar</button>" % esc(d["id"])]

    loc = " · ".join([x for x in [d.get("neighborhood"), d.get("municipality")] if x])
    if loc:
        p.append("<p class='detail-loc'>%s</p>" % esc(loc))
    if d.get("aliases"):
        p.append("<p class='detail-aliases'>Também conhecido como: %s</p>" % esc(", ".join(d["aliases"])))
    if d.get("image"):
        p.append("<img class='detail-img' src='%s' alt='%s' loading='lazy'>"
                 % (esc(d["image"]), esc(d["name"])))
    if d.get("description"):
        p.append("<p class='detail-desc'>%s</p>" % esc(d["description"]))
    else:
        p.append("<p class='detail-desc muted'>Sem descrição ainda.</p>")

    edges = d.get("edges", [])
    p.append("<h2 class='section-h'>Conexões (%d)</h2>" % len(edges))
    if edges:
        groups = {}
        for e in edges:
            groups.setdefault(e["target_type"], []).append(e)
        for gt in CATEGORY_ORDER:
            if gt not in groups:
                continue
            p.append("<h3 class='conn-group'>%s <span class='conn'>(%d)</span></h3>"
                     % (esc(TYPE_META.get(gt, FALLBACK_META)[0]), len(groups[gt])))
            p.append("<ul class='cards'>")
            for e in sorted(groups[gt], key=lambda x: x["target_name"]):
                p.append("<li class='card t-%s'><a class='card-main' href='%s.html'>"
                         "<span class='card-body'><span class='card-name'>%s</span>"
                         "<span class='card-meta'>%s</span></span></a></li>"
                         % (e["target_type"], esc(e["target_id"]),
                            esc(e["target_name"]), badge(e["target_type"])))
            p.append("</ul>")
    else:
        p.append("<p class='empty-state'>Sem conexões.</p>")

    if d.get("sources"):
        p.append("<h2 class='section-h'>Fontes</h2><ul class='sources'>")
        for s in d["sources"]:
            if s.get("url"):
                p.append("<li><a href='%s' rel='noopener' target='_blank'>%s</a></li>"
                         % (esc(s["url"]), esc(s["title"])))
            else:
                p.append("<li>%s</li>" % esc(s["title"]))
        p.append("</ul>")

    p.append("</article>")
    return shell(d["name"] + " — Conexões da História", "node", "../../data",
                 "explorar", "\n".join(p), base="../")


def render_matrix(matrix):
    """3×3 type×type adjacency as a semantic table. Each non-empty cell is a link to
    the List filtered to that type pair. The number is always shown; background
    intensity (neutral slate, sqrt-scaled) is a secondary cue only."""
    by, mx = {}, 1
    for m in matrix:
        by[(m["type_a"], m["type_b"])] = m["count"]
        by[(m["type_b"], m["type_a"])] = m["count"]
        mx = max(mx, m["count"])
    types = CATEGORY_ORDER
    rank = {t: i for i, t in enumerate(types)}

    head = ("<tr><td class='mx-corner' aria-hidden='true'></td>"
            + "".join("<th scope='col'>%s</th>" % badge(t) for t in types) + "</tr>")
    rows = []
    for ta in types:
        cells = ["<th scope='row'>%s</th>" % badge(ta)]
        for tb in types:
            cnt = by.get((ta, tb), 0)
            la = TYPE_META.get(ta, FALLBACK_META)[0]
            lb = TYPE_META.get(tb, FALLBACK_META)[0]
            if cnt:
                alpha = round(0.10 + 0.42 * math.sqrt(cnt / mx), 3)
                ca, cb = (ta, tb) if rank[ta] <= rank[tb] else (tb, ta)
                cells.append(
                    "<td class='mx-cell'><a href='list.html#pair=%s-%s' "
                    "style='background:rgba(30,41,59,%s)' "
                    "aria-label='%s ↔ %s: %d conexões'><span class='mx-n'>%d</span></a></td>"
                    % (ca, cb, alpha, esc(la), esc(lb), cnt, cnt))
            else:
                cells.append("<td class='mx-cell mx-empty' aria-label='%s ↔ %s: 0 conexões'>0</td>"
                             % (esc(la), esc(lb)))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table = ("<div class='mx-scroll'><table class='matrix'>"
             "<caption class='sr-only'>Conexões entre tipos de nó</caption>"
             "<thead>%s</thead><tbody>%s</tbody></table></div>" % (head, "".join(rows)))
    body = ("<h1 class='section-h' style='font-size:18px'>Matriz de conexões</h1>\n"
            "<p class='mx-intro'>Quantas conexões existem entre cada par de tipos. "
            "Toque numa célula para ver os nós envolvidos.</p>\n"
            + table +
            "\n<p class='mx-foot'><a href='index.html'>← Explorar</a> · "
            "<a href='list.html'>Ver lista</a></p>")
    return shell("Matriz — Conexões da História", "matrix", "../data", "explorar", body)


def render_about(sources):
    if sources:
        src = "".join(
            ("<li><a href='%s' rel='noopener' target='_blank'>%s</a></li>"
             % (esc(s["url"], ), esc(s["title"])) if s.get("url")
             else "<li>%s</li>" % esc(s["title"]))
            for s in sources)
    else:
        src = "<li class='empty-state'>Registro de fontes em construção.</li>"
    body = (
        "<h1 class='section-h' style='font-size:18px'>Sobre o projeto</h1>\n"
        "<p class='about-p'>Conexões da História mapeia as relações entre as pessoas, os lugares "
        "e os fatos que formaram Recife e Pernambuco. A ideia é explorar como personagens, locais "
        "e acontecimentos aparentemente distantes estão ligados ao longo do tempo.</p>\n"
        "<h2 class='section-h'>Como usar</h2>\n"
        "<p class='about-p'>Comece pela busca ou pelos tipos na tela Explorar, abra um nó para ver "
        "sua descrição, fontes e conexões, e use a Matriz para ver como os tipos se conectam no "
        "conjunto. Salve nós em Favoritos para voltar depois.</p>\n"
        "<h2 class='section-h'>Metodologia</h2>\n"
        "<p class='about-p'>Cada nó é uma pessoa (Personagem), um lugar (Local) ou um fato "
        "histórico, curado a partir de fontes públicas; as conexões são relações documentadas "
        "entre eles. A base é revisada continuamente — nós ainda sem descrição ou imagem são "
        "exibidos com a devida marcação.</p>\n"
        "<h2 class='section-h'>Fontes</h2>\n"
        "<ul class='sources'>%s</ul>\n" % src
    )
    return shell("Sobre — Conexões da História", "about", "../data", "sobre", body)


def render_favorites():
    body = (
        "<h1 class='section-h' style='font-size:18px'>Favoritos</h1>\n"
        "<div id='fav-list'></div>\n"
        "<p id='fav-empty' class='empty-state' hidden>Você ainda não salvou nenhum nó. "
        "Abra um nó e toque em <strong>☆ Favoritar</strong> para guardá-lo aqui.</p>\n"
        "<noscript><p class='empty-state'>Os favoritos precisam de JavaScript.</p></noscript>\n"
        "<p class='view-links'><a href='list.html'>Explorar a lista →</a></p>\n"
    )
    return shell("Favoritos — Conexões da História", "favorites", "../data", "favoritos", body)


def build_site(index, details, matrix, sources, site_dir):
    node_dir = os.path.join(site_dir, "node")
    os.makedirs(node_dir, exist_ok=True)
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_home(index))
    with open(os.path.join(site_dir, "list.html"), "w", encoding="utf-8") as f:
        f.write(render_list(index))
    with open(os.path.join(site_dir, "matriz.html"), "w", encoding="utf-8") as f:
        f.write(render_matrix(matrix))
    with open(os.path.join(site_dir, "sobre.html"), "w", encoding="utf-8") as f:
        f.write(render_about(sources))
    with open(os.path.join(site_dir, "favoritos.html"), "w", encoding="utf-8") as f:
        f.write(render_favorites())
    for d in details:
        with open(os.path.join(node_dir, d["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(render_node(d))
    return len(details)
