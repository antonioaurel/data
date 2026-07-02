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

# type -> (Portuguese label, icon). Keys match the routes (#tipos=local,…).
# The .get() fallback keeps rendering safe if an unexpected type ever appears.
TYPE_META = {
    "local":      ("Local",                   "📍"),
    "personagem": ("Personagens Históricos",  "👤"),
    "evento":     ("Fatos Históricos",        "📅"),
}
FALLBACK_META = ("Outro", "●")
CATEGORY_ORDER = ["local", "personagem", "evento"]

# Links out to the existing desktop pages / external map (from mobile/site/ → ../../pages/).
DESKTOP_DIAGRAM = "../../pages/diagram.html"
DESKTOP_STATS = "../../pages/stats.html"
DESKTOP_MATRIX = "../../pages/matrix.html"
MARCO_ZERO = "LC-0215"   # symbolic entry point for the graph from Início
MAP_URL = ("https://www.google.com.br/maps/d/u/0/viewer?mid=1eOwVJYlWOV6PLI06K-h-ofmkJXyrgrnj"
           "&ll=-8.06055276702706%2C-34.882075024350215&z=15")

# Bottom/top nav sections.
NAV_ITEMS = [("index.html", "Início", "🏠", "inicio"),
             ("graph.html#node=" + MARCO_ZERO, "Diagram", "🕸", "diagrama"),
             ("matriz.html", "Matriz", "▦", "matriz"),
             ("fillrate.html", "Fill rate", "📊", "fillrate"),
             ("fontes.html", "Fontes", "📚", "fontes"),
             ("sobre.html", "Sobre", "ℹ", "sobre")]


def esc(s):
    return html.escape(s or "", quote=True)


def badge(t, with_label=True):
    label, ico = TYPE_META.get(t, FALLBACK_META)
    inner = "<span class='ico'>%s</span>" % ico
    if with_label:
        inner += "<span data-tlabel='%s'>%s</span>" % (t, esc(label))   # data-tlabel → i18n swap
    return "<span class='badge t-%s'>%s</span>" % (t, inner)


def bottom_nav(active, base=""):
    lis = []
    for href, label, _ico, key in NAV_ITEMS:
        cur = " aria-current='page'" if key == active else ""
        lis.append("<li><a href='%s%s'%s data-i18n='nav-%s'>%s</a></li>"
                   % (base, href, cur, key, esc(label)))
    return ("<nav class='bottom-nav' aria-label='Seções'><ul>%s</ul></nav>" % "".join(lis))


def view_switcher(active, base=""):
    """Segmented control over the three projections. JS enhances it (carries the current
    node / list filters via sessionStorage); the static default is plain navigation."""
    tabs = [("list", "Lista", base + "list.html"),
            ("graph", "Grafo", base + "graph.html"),
            ("matrix", "Matriz", base + "matriz.html")]
    items = []
    for key, label, href in tabs:
        on = key == active
        items.append(
            "<a role='tab' class='sw-tab%s' data-view='%s' href='%s' aria-selected='%s'%s "
            "data-i18n='sw-%s'>%s</a>"
            % (" is-active" if on else "", key, href, "true" if on else "false",
               " aria-current='page'" if on else "", key, esc(label)))
    return ("<nav class='switcher' role='tablist' aria-label='Modo de visualização'>%s</nav>"
            % "".join(items))


def top_nav(active, base=""):
    """Horizontal nav shown in the header on expanded screens (≥1024px); the bottom nav is
    hidden there."""
    links = "".join(
        "<a href='%s%s'%s data-i18n='nav-%s'>%s</a>"
        % (base, href, " aria-current='page'" if key == active else "", key, esc(label))
        for href, label, _ico, key in NAV_ITEMS)
    return "<nav class='top-nav' aria-label='Seções'>%s</nav>" % links


def shell(title, page, datapath, active_nav, body, base=""):
    return (
        "<!doctype html>\n"
        "<html lang='pt-BR' class='no-js'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>\n"
        "<title>%s</title>\n"
        "<meta name='description' content='Conexões da História — pessoas, lugares e fatos que formaram Recife e Pernambuco.'>\n"
        "<link rel='icon' href='data:,'>\n"
        "<link rel='stylesheet' href='%sassets/app.css'>\n"
        "<script>document.documentElement.className='has-js';"
        "try{var _t=localStorage.getItem('theme');if(_t)document.documentElement.setAttribute('data-theme',_t);}catch(e){}</script>\n"
        "</head>\n"
        "<body data-page='%s' data-datapath='%s'>\n"
        "<a class='skip-link' href='#main'>Pular para o conteúdo</a>\n"
        "<header class='app-header'><div class='wrap'>"
        "<div class='titlebar'>"
        "<h1 class='app-title'><a href='%sindex.html'>Conexões da História</a></h1>"
        "%s"
        "</div>"
        "<div class='header-toggles js-only'>"
        "<button id='lang-toggle' class='theme-toggle' type='button' "
        "aria-label='Português / English'>EN</button>"
        "<button id='theme-toggle' class='theme-toggle' type='button' "
        "aria-label='Alternar tema claro/escuro'>☀</button>"
        "</div>"
        "</div></header>\n"
        "<main id='main' class='wrap'>\n%s\n</main>\n"
        "%s\n"
        "<script src='%sassets/app.js' defer></script>\n"
        "</body>\n</html>\n"
        % (esc(title), base, page, esc(datapath), base, top_nav(active_nav, base),
           body, bottom_nav(active_nav, base), base)
    )


def present_types(index):
    counts = {}
    for o in index:
        counts[o["type"]] = counts.get(o["type"], 0) + 1
    return [(t, counts[t]) for t in CATEGORY_ORDER if counts.get(t)]


def viz_row(href, key, name, desc, external=False):
    ext = " target='_blank' rel='noopener'" if external else ""
    arrow = " ↗" if external else ""
    return ("<li class='viz-item'><a class='viz-link' href='%s'%s>"
            "<span class='viz-name'><span data-i18n='viz-%s-n'>%s</span>%s</span>"
            "<span class='viz-desc' data-i18n='viz-%s-d'>%s</span></a></li>"
            % (href, ext, key, esc(name), arrow, key, esc(desc)))


def render_home(index, stats):
    types = present_types(index)
    chips = "".join(
        "<a class='chip t-%s is-active' href='list.html#type=%s' data-tlabel='%s'>%s</a>"
        % (t, t, t, esc(TYPE_META[t][0]))
        for t, _c in types)

    viz = ("<ul class='viz-list'>"
           + viz_row("graph.html#node=" + MARCO_ZERO, "diagrama", "Diagrama", "Explore as conexões de nó.")
           + viz_row("matriz.html", "matriz", "Matriz", "Panorama das conexões por tipo.")
           + viz_row(MAP_URL, "mapa", "Mapa histórico", "Os pontos no mapa do Recife e região. (projeto original)", external=True)
           + viz_row("fillrate.html", "fillrate", "Fill rate", "Qualidade do preenchimento da base, campo a campo.")
           + viz_row("sobre.html", "sobre", "Sobre", "O projeto, o autor e as fontes.")
           + "</ul>")

    body = (
        "<img class='cover-start' src='assets/cover_start.png' alt='Conexões da História' "
        "onerror=\"this.style.display='none'\">\n"
        "<p class='home-intro' data-i18n='home-tagline'>Um mapeamento das conexões entre pessoas, "
        "locais e eventos da história de Pernambuco em pontos que influenciaram o Brasil.</p>\n"
        "<p class='home-stats'><strong>%d</strong> <span data-i18n='w-nos'>nós</span> · "
        "<strong>%d</strong> <span data-i18n='w-conexoes'>conexões</span></p>\n"
        "<form id='home-search' class='search js-only' role='search' action='list.html'>"
        "<input id='home-q' type='search' name='q' placeholder='Buscar pessoa, lugar, evento…' "
        "data-i18n-ph='ph-home' autocomplete='off' aria-label='Buscar'></form>\n"
        "<ul id='home-results' class='cards' hidden></ul>\n"
        "<div class='chips'>%s</div>\n"
        "<p class='no-js-only' style='margin-top:12px'><a href='list.html' data-i18n='home-verlista'>"
        "Ver a lista completa →</a></p>\n"
        "<h2 class='section-h' data-i18n='home-viz'>Visualizações</h2>\n"
        "%s\n"
        % (stats.get("n_nodes", 0), stats.get("n_edges", 0), chips, viz)
    )
    return shell("Conexões da História", "inicio", "../data", "inicio", body)


def render_list(index):
    types = present_types(index)
    chips = "".join(
        "<button type='button' class='chip t-%s' data-type='%s' aria-pressed='false' data-tlabel='%s'>%s</button>"
        % (t, t, t, esc(TYPE_META[t][0]))
        for t, _c in types)

    cards = []
    for o in sorted(index, key=lambda o: o["name"]):
        t = o["type"]
        cards.append(
            "<li class='card t-%s' data-id='%s' data-type='%s' data-conn='%d' data-name='%s'>"
            "<button class='card-main' type='button'>"
            "<span class='card-body'><span class='card-name'>%s</span>"
            "<span class='card-meta'>%s<span class='conn'>%d&nbsp;<span data-i18n='w-conexoes'>conexões</span></span>"
            "<span class='chevron' aria-hidden='true'>›</span></span></span>"
            "</button></li>"
            % (t, esc(o["id"]), t, o["conn_count"], esc(normalize(o["name"])),
               esc(o["name"]), badge(t), o["conn_count"])
        )

    body = (
        view_switcher("list") + "\n"
        "<div id='list-context' hidden></div>\n"
        "<div class='search js-only'><input id='q' type='search' placeholder='Buscar…' "
        "data-i18n-ph='ph-list' autocomplete='off' aria-label='Buscar na lista'></div>\n"
        "<div class='js-only'><h2 class='section-h' data-i18n='list-filtros'>Filtros</h2>"
        "<div class='chips'>%s</div></div>\n"
        "<div class='toolbar js-only'><span id='count' class='count'>%d nós</span></div>\n"
        "<p id='empty' class='empty-state' hidden>Nenhum resultado.</p>\n"
        "<div class='list-layout'>\n"
        "<ul id='list' class='cards'>%s</ul>\n"
        "<aside id='detail-pane' class='detail-pane' aria-live='polite'>"
        "<p class='empty-state'>Selecione um nó para ver os detalhes.</p></aside>\n"
        "</div>\n"
        % (chips, len(index), "".join(cards))
    )
    return shell("Lista — Conexões da História", "list", "../data", "inicio", body)


def render_node(d):
    """Full static detail page for one node (share/SEO/no-JS). Lives at site/node/{id}.html,
    so assets are ../ and data is ../../data; sibling node links are '{id}.html'."""
    t = d["type"]
    p = ["<p><a class='detail-back' href='../list.html' data-i18n='back-list'>← Lista</a></p>",
         "<article class='detail' data-node-id='%s' data-de='%s'>" % (esc(d["id"]), esc(d.get("de", ""))),
         "<div class='detail-head'>%s<h1 class='detail-name'>%s</h1></div>"
         % (badge(t), esc(d["name"])),
         "<p><a class='btn btn-primary' href='../graph.html#node=%s' data-i18n='btn-graph'>"
         "Ver conexões no grafo</a></p>" % esc(d["id"])]

    loc = " · ".join([x for x in [d.get("neighborhood"), d.get("municipality")] if x])
    if loc:
        p.append("<p class='detail-loc'>%s</p>" % esc(loc))
    if d.get("aliases"):
        p.append("<p class='detail-aliases'>Também conhecido como: %s</p>" % esc(", ".join(d["aliases"])))
    if d.get("image"):
        # hide the image element if the URL is broken (no broken-image icon, just the title/text)
        p.append("<img class='detail-img' src='%s' alt='%s' loading='lazy' "
                 "onerror=\"this.style.display='none'\">" % (esc(d["image"]), esc(d["name"])))
    if d.get("description"):
        p.append("<p class='detail-desc'>%s</p>" % esc(d["description"]))
    else:
        p.append("<p class='detail-desc muted'>Sem descrição ainda.</p>")

    edges = d.get("edges", [])
    p.append("<h2 class='section-h'><span data-i18n='h-conexoes'>Conexões</span> (%d)</h2>" % len(edges))
    if edges:
        groups = {}
        for e in edges:
            groups.setdefault(e["target_type"], []).append(e)
        for gt in CATEGORY_ORDER:
            if gt not in groups:
                continue
            p.append("<h3 class='conn-group'><span data-tlabel='%s'>%s</span> "
                     "<span class='conn'>(%d)</span></h3>"
                     % (gt, esc(TYPE_META.get(gt, FALLBACK_META)[0]), len(groups[gt])))
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

    # Source references live only on the Fontes page — not on the node detail.
    p.append("</article>")
    return shell(d["name"] + " — Conexões da História", "node", "../../data",
                 "inicio", "\n".join(p), base="../")


def render_matrix(matrix, stats):
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
                    "<td class='mx-cell'><a href='list.html#pair=%s-%s' style='--a:%s' "
                    "aria-label='%s ↔ %s: %d conexões'><span class='mx-n'>%d</span></a></td>"
                    % (ca, cb, alpha, esc(la), esc(lb), cnt, cnt))
            else:
                cells.append("<td class='mx-cell mx-empty' aria-label='%s ↔ %s: 0 conexões'>0</td>"
                             % (esc(la), esc(lb)))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table = ("<div class='mx-scroll'><table class='matrix'>"
             "<caption class='sr-only'>Conexões entre tipos de nó</caption>"
             "<thead>%s</thead><tbody>%s</tbody></table></div>" % (head, "".join(rows)))
    n = stats.get("n_nodes", 0)
    note = ("<p class='mx-note'>Este é um panorama por tipo. O acervo tem <strong>%d</strong> "
            "itens e <strong>%d</strong> conexões — a matriz completa, item a item, respira "
            "melhor numa tela grande.<br>"
            "<a href='%s' target='_blank' rel='noopener'>Abrir matriz completa (%d×%d) no "
            "computador ↗</a></p>" % (n, stats.get("n_edges", 0), DESKTOP_MATRIX, n, n))
    body = (view_switcher("matrix") + "\n"
            "<h1 class='section-h' style='font-size:18px' data-i18n='matriz-h'>Matriz de conexões</h1>\n"
            "<p class='mx-intro' data-i18n='matriz-intro'>Quantas conexões existem entre cada par de "
            "tipos. Toque numa célula para ver os nós envolvidos.</p>\n"
            + table + "\n" + note +
            "\n<p class='mx-foot'><a href='index.html' data-i18n='back-inicio'>← Início</a> · "
            "<a href='list.html' data-i18n='back-verlista'>Ver lista</a></p>")
    return shell("Matriz — Conexões da História", "matrix", "../data", "inicio", body)


PROJECTS = [
    "Troça Carnavalesca Segura o Tonho, Charlie Brown",
    "Data Quality review using IA to Conexões da História",
    "Hundred Days of Playwright", "Hundred Days of Python",
    "Mapa do Frevo", "Maracatu Quebra Baque",
    "Prediction of attendance in events organized through Facebook",
    "Quem Representa Você",
]


def render_about():
    # compact layout (fits without scrolling): inline projects, tight spacing.
    body = (
        "<h1 class='section-h' style='font-size:18px;margin:10px 0 8px' data-i18n='sobre-h'>Sobre</h1>\n"
        "<p class='about-p' data-i18n='home-tagline'>Um mapeamento das conexões entre pessoas, locais "
        "e eventos da história de Pernambuco em pontos que influenciaram o Brasil.</p>\n"
        "<hr class='divider'>\n"
        "<p class='author-name'>Antonio A. Oliveira</p>\n"
        "<p class='author-meta'><span data-i18n='sobre-authormeta'>Recife, Pernambuco — autor, "
        "curador e criador · </span>"
        "<a href='https://medium.com/@antonio-aureliano' target='_blank' rel='noopener'>Medium ↗</a></p>\n"
        "<p class='about-p' data-i18n='sobre-curation'>Curadoria para estudos de data science, "
        "data quality, história e software quality.</p>\n"
        "<hr class='divider'>\n"
        "<h2 class='section-h' style='margin:12px 0 6px' data-i18n='sobre-outros'>Outros projetos</h2>\n"
        "<ul class='projects'>%s</ul>\n"
        "<hr class='divider'>\n"
        "<p class='about-p disclaimer'><strong data-i18n='sobre-disclaimer-b'>Uso de IA:</strong>"
        "<span data-i18n='sobre-disclaimer'> pareamento no desenvolvimento; revisão da qualidade da "
        "base, do texto e validação das conexões; geração de mocks; e testes de usabilidade, "
        "compatibilidade, disponibilidade e desempenho.</span></p>\n"
        % "".join("<li>%s</li>" % esc(p) for p in PROJECTS)
    )
    return shell("Sobre — Conexões da História", "about", "../data", "sobre", body)


def render_fillrate(stats):
    rows = "".join(
        "<div class='fr-row%s'><span class='fr-label' data-i18n='fl-%s'>%s</span>"
        "<span class='fr-bar'><span class='fr-fill' style='width:%d%%'></span></span>"
        "<span class='fr-pct'>%d%%</span></div>"
        % (" fr-low" if pct < 60 else "", name, esc(name), pct, pct)
        for name, pct in stats.get("fields", []))
    body = (
        "<h1 class='section-h' style='font-size:18px' data-i18n='fill-h'>Fill rate</h1>\n"
        "<p class='home-stats'><strong>%d</strong> <span data-i18n='w-nos'>nós</span> · "
        "<strong>%d</strong> <span data-i18n='w-conexoes'>conexões</span></p>\n"
        "<div class='fr'>%s</div>\n"
        "<p class='mx-intro'><span data-i18n='fill-note-a'>Campos em âmbar precisam de curadoria.</span> "
        "<a href='%s' target='_blank' rel='noopener' data-i18n='fill-note-link'>Ver o relatório completo ↗</a></p>\n"
        % (stats.get("n_nodes", 0), stats.get("n_edges", 0), rows, DESKTOP_STATS)
    )
    return shell("Fill rate — Conexões da História", "fillrate", "../data", "fillrate", body)


BOOKS = [
    ("Trilhas do Recife", "guia turístico, histórico e cultural", "João B. M. Braga · 2007",
     "Amazon", "https://www.amazon.com.br/Trilhas-Recife-Braga-Batista-Meira/dp/8537302996"),
    ("O Recife e suas Ruas", "origem, história e nomenclatura", "IAHGP · 2010",
     "Touchê Livros", "https://www.touchelivros.com.br/o-recife-e-suas-ruas-se-essas-ruas-fossem-minhas/"),
    ("Pernambucanidade", "aspectos históricos", "Nilo Pereira · 1983 · 3 volumes",
     "Mercado Livre", "https://www.mercadolivre.com.br/livro-pernambucanidade-alguns-aspectos-historicos-"
     "nilo-pereira--secretaria-de-turismo-cultura-e-esportes-3-v-1983---g8/up/MLBU3415576957"),
]


def render_fontes():
    cards = "".join(
        "<li class='book'><div class='book-cover'>%s</div>"
        "<div class='book-body'><p class='book-title'>%s</p>"
        "<p class='book-sub'>%s</p><p class='book-meta'>%s</p>"
        "<p><a href='%s' target='_blank' rel='noopener'>%s ↗</a></p></div></li>"
        % (esc(title), esc(title), esc(sub), esc(meta), esc(url), esc(store))
        for title, sub, meta, store, url in BOOKS)
    body = (
        "<h1 class='section-h' style='font-size:18px' data-i18n='fontes-h'>Fontes</h1>\n"
        "<ul class='books'>%s</ul>\n" % cards
    )
    return shell("Fontes — Conexões da História", "fontes", "../data", "fontes", body)


def render_graph():
    body = (
        view_switcher("graph") + "\n"
        "<p><a class='detail-back' href='list.html' data-i18n='back-list'>← Lista</a></p>\n"
        "<h1 id='graph-title' class='section-h' style='font-size:18px'>Conexões</h1>\n"
        "<div id='graph-canvas' class='graph-canvas' role='img' aria-live='polite'></div>\n"
        "<p id='graph-hint' class='mx-intro'></p>\n"
        "<p class='mx-note'>Visualização condensada — no celular o grafo mostra até 5 conexões por "
        "vez. A rede completa, item a item, abre melhor no computador. "
        "<a href='" + DESKTOP_DIAGRAM + "' target='_blank' rel='noopener'>Abrir o diagrama completo "
        "no computador ↗</a></p>\n"
        "<div id='graph-panel' class='graph-panel' hidden></div>\n"
        "<noscript><p class='empty-state'>O grafo precisa de JavaScript. "
        "<a href='list.html'>Ver a lista</a>.</p></noscript>\n"
    )
    return shell("Grafo — Conexões da História", "graph", "../data", "inicio", body)


def build_site(index, details, matrix, stats, site_dir):
    node_dir = os.path.join(site_dir, "node")
    os.makedirs(node_dir, exist_ok=True)
    pages = {
        "index.html":    render_home(index, stats),
        "list.html":     render_list(index),
        "matriz.html":   render_matrix(matrix, stats),
        "graph.html":    render_graph(),
        "fillrate.html": render_fillrate(stats),
        "fontes.html":   render_fontes(),
        "sobre.html":    render_about(),
    }
    for name, content in pages.items():
        with open(os.path.join(site_dir, name), "w", encoding="utf-8") as f:
            f.write(content)
    for d in details:
        with open(os.path.join(node_dir, d["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(render_node(d))
    return len(details)
