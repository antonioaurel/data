/* Conexões da História — mobile progressive enhancement (Phase 2).
   Vanilla ES5-friendly for old Android WebView. Static HTML works without this file;
   this only enhances: alias-aware search, type filter, sort, inline connection expansion. */
(function () {
  "use strict";

  // Type keys match the routes (#tipos=local,…). "Fato Histórico" shows as "Evento".
  var TYPES = {
    local:      { label: "Local",                  ico: "📍" },
    personagem: { label: "Personagens Históricos", ico: "👤" },
    evento:     { label: "Fatos Históricos",       ico: "📅" }
  };
  var FALLBACK = { label: "Outro", ico: "●" };

  /* ================================ i18n ================================== */
  // Default PT (never auto-follow the browser); the toggle persists the choice.
  var LANG_KEY = "lang";
  function getLang() {
    try { return localStorage.getItem(LANG_KEY) === "en" ? "en" : "pt"; } catch (e) { return "pt"; }
  }
  function setLang(l) { try { localStorage.setItem(LANG_KEY, l); } catch (e) {} }
  function L(pt, en) { return getLang() === "en" ? en : pt; }   // inline dual-language for JS strings
  function typeLabel(t) {                                        // type label per language
    var en = { local: "Places", personagem: "Historical Figures", evento: "Historical Facts" };
    return getLang() === "en" ? (en[t] || "Other") : typeMeta(t).label;
  }
  // EN strings for static [data-i18n] elements (PT stays in the HTML as the default/fallback).
  var EN = {
    "nav-inicio": "Home", "nav-diagrama": "Diagram", "nav-matriz": "Matrix",
    "nav-fillrate": "Fill rate", "nav-fontes": "Sources", "nav-sobre": "About",
    "sw-list": "List", "sw-graph": "Graph", "sw-matrix": "Matrix",
    "home-tagline": "A mapping of the connections between people, places and events in the history of Pernambuco at points that influenced Brazil.",
    "home-viz": "Visualizations", "home-verlista": "See the full list →",
    "viz-matriz-n": "Matrix", "viz-matriz-d": "Overview of connections by type.",
    "viz-mapa-n": "Historical map", "viz-mapa-d": "The points on the map of Recife and region. (original project)",
    "viz-diagrama-n": "Diagram", "viz-diagrama-d": "Explore a node's connections.",
    "viz-fillrate-n": "Fill rate", "viz-fillrate-d": "How well the base is filled in, field by field.",
    "viz-sobre-n": "About", "viz-sobre-d": "The project, the author and the sources.",
    "list-filtros": "Filters", "matriz-h": "Connection matrix",
    "matriz-intro": "How many connections exist between each pair of types. Tap a cell to see the nodes involved.",
    "fill-h": "Fill rate", "fill-note-a": "Fields in amber need curation.", "fill-note-link": "See the full report ↗",
    "fontes-h": "Sources", "sobre-h": "About",
    "sobre-authormeta": "Recife, Pernambuco — author, curator and creator · ",
    "sobre-curation": "Curation for studies in data science, data quality, history and software quality.",
    "sobre-outros": "Other projects",
    "sobre-disclaimer-b": "AI use:", "sobre-disclaimer": " pairing in development; review of the database quality, the text and validation of the connections; mock generation; and usability, compatibility, availability and performance testing.",
    "fl-Nome": "Name", "fl-Descrição": "Description", "fl-Interconexões": "Interconnections",
    "fl-Imagem": "Image", "fl-Tipo": "Type", "fl-Local": "Location",
    "back-list": "← List", "back-inicio": "← Home", "back-verlista": "See list",
    "w-nos": "nodes", "w-conexoes": "connections",
    "ph-home": "Search person, place, event…", "ph-list": "Search…",
    "btn-graph": "View connections in the graph", "h-conexoes": "Connections",
    "fill-method-h": "Working method",
    "fill-method-1": "Reading of sources, identification of the associated places on a map, and creation of a cross-reference matrix — considering direct interaction, area, period and consequence.",
    "fill-method-2": "Data cleaning, quality validation and publishing with constant correction."
  };
  function applyI18n() {
    var lang = getLang();
    document.documentElement.setAttribute("lang", lang === "en" ? "en" : "pt-BR");
    var nodes = document.querySelectorAll("[data-i18n]"), i;
    for (i = 0; i < nodes.length; i++) {
      var el2 = nodes[i], k = el2.getAttribute("data-i18n");
      if (el2.__pt == null) el2.__pt = el2.textContent;
      el2.textContent = (lang === "en" && EN[k] != null) ? EN[k] : el2.__pt;
    }
    var phs = document.querySelectorAll("[data-i18n-ph]");
    for (i = 0; i < phs.length; i++) {
      var el3 = phs[i], k3 = el3.getAttribute("data-i18n-ph");
      if (el3.__ptph == null) el3.__ptph = el3.getAttribute("placeholder") || "";
      el3.setAttribute("placeholder", (lang === "en" && EN[k3] != null) ? EN[k3] : el3.__ptph);
    }
    // node detail: swap the description + type badge/chips to the chosen language
    swapNodeLang(lang);
  }
  function swapNodeLang(lang) {
    var art = document.querySelector(".detail[data-node-id]");
    if (art) {
      var desc = art.querySelector(".detail-desc:not(.muted)");
      var de = art.getAttribute("data-de");
      if (desc) { if (desc.__pt == null) desc.__pt = desc.textContent; desc.textContent = (lang === "en" && de) ? de : desc.__pt; }
    }
    // type chips/badges labels (static)
    var tl = document.querySelectorAll("[data-tlabel]"), i;
    for (i = 0; i < tl.length; i++) {
      var e = tl[i], ty = e.getAttribute("data-tlabel");
      e.textContent = typeLabel(ty);
    }
  }
  function initLang() {
    var btn = el("lang-toggle");
    function paint() { if (btn) btn.textContent = getLang() === "en" ? "PT" : "EN"; }
    applyI18n(); paint();
    if (!btn) return;
    btn.addEventListener("click", function () {
      setLang(getLang() === "en" ? "pt" : "en");
      applyI18n(); paint();
    });
  }

  function typeMeta(t) { return TYPES[t] || FALLBACK; }

  function stripAccents(s) {
    s = (s || "").toLowerCase();
    if (s.normalize) { return s.normalize("NFD").replace(/[̀-ͯ]/g, ""); }
    return s.replace(/[àáâãä]/g, "a").replace(/[èéêë]/g, "e").replace(/[ìíîï]/g, "i")
            .replace(/[òóôõö]/g, "o").replace(/[ùúûü]/g, "u").replace(/ç/g, "c").replace(/ñ/g, "n");
  }
  function debounce(fn, ms) {
    var t; return function () { var a = arguments, c = this;
      clearTimeout(t); t = setTimeout(function () { fn.apply(c, a); }, ms); };
  }
  function el(id) { return document.getElementById(id); }
  function dataPath() { return document.body.getAttribute("data-datapath") || "../data"; }
  function trunc(s, n) { s = s || ""; return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function parseHash() {
    var h = {};
    (location.hash.replace(/^#/, "").split("&")).forEach(function (kv) {
      var p = kv.split("="); if (p[0]) h[p[0]] = decodeURIComponent(p[1] || "");
    });
    return h;
  }
  function typeColor(t) {
    var root = document.documentElement, cs = getComputedStyle(root);
    return (cs.getPropertyValue("--type-" + t).trim()) || cs.getPropertyValue("--type-other").trim();
  }
  // Breakpoints are defined once in CSS; JS reads the active mode from body::after.
  function getMode() {
    try {
      var c = (getComputedStyle(document.body, "::after").content || "").replace(/["']/g, "");
      if (c === "compact" || c === "medium" || c === "expanded") return c;
    } catch (e) {}
    var w = window.innerWidth || 360;
    return w >= 1024 ? "expanded" : (w >= 640 ? "medium" : "compact");
  }
  function initResponsive() {
    var raf = null;
    function apply() { document.documentElement.setAttribute("data-mode", getMode()); }
    function onChange() {
      if (window.cancelAnimationFrame && raf) cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame ? requestAnimationFrame(apply) : (apply(), null);
    }
    if (window.matchMedia) {
      ["(min-width:640px)", "(min-width:1024px)"].forEach(function (q) {
        var mq = window.matchMedia(q);
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        else if (mq.addListener) mq.addListener(onChange);   // old WebView
      });
    }
    window.addEventListener("resize", onChange);
    apply();
  }

  function ssGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function ssSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }
  function xhrJSON(url, cb) {
    var x = new XMLHttpRequest();
    x.open("GET", url, true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var o = null; try { o = JSON.parse(x.responseText); } catch (e) {}
      cb(o);
    };
    x.send();
  }

  /* ---- search.json (lazy, once): id -> "normname alias1 alias2" ---- */
  var searchTerms = null, searchLoading = null;
  function loadSearch(cb) {
    if (searchTerms) { cb(searchTerms); return; }
    if (searchLoading) { searchLoading.push(cb); return; }
    searchLoading = [cb];
    var x = new XMLHttpRequest();
    x.open("GET", dataPath() + "/search.json", true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      searchTerms = {};
      try {
        var arr = JSON.parse(x.responseText);
        for (var i = 0; i < arr.length; i++) {
          var o = arr[i];
          searchTerms[o.id] = o.norm + " " + (o.aliases ? o.aliases.join(" ") : "");
        }
      } catch (e) {}
      var q = searchLoading; searchLoading = null;
      for (var j = 0; j < q.length; j++) { q[j](searchTerms); }
    };
    x.send();
  }

  /* ================================ LIST PAGE ================================ */
  function initList() {
    var listEl = el("list");
    if (!listEl) return;
    var cards = [].slice.call(listEl.querySelectorAll(".card"));
    var countEl = el("count");
    var searchInput = el("q");
    var sortSel = el("sort");
    var chips = [].slice.call(document.querySelectorAll(".chip[data-type]"));

    var activeTypes = {};   // set of selected types (empty = all)
    var query = "";
    var matchIds = null;    // null = no active text query
    var pairIds = null;     // null = no matrix type-pair drill-down active
    var pairActive = null;  // the "a-b" pair string when a drill-down is active

    function stateHash() {
      var parts = [];
      var ts = []; for (var t in activeTypes) { ts.push(t); }
      if (ts.length) parts.push("type=" + ts.join(","));
      if (sortSel && sortSel.value && sortSel.value !== "name") parts.push("sort=" + sortSel.value);
      var q = searchInput ? searchInput.value.trim() : "";
      if (q) parts.push("q=" + encodeURIComponent(q));
      if (pairActive) parts.push("pair=" + pairActive);
      return parts.length ? "#" + parts.join("&") : "";
    }
    function syncHash() {
      var h = stateHash();
      if (history.replaceState) history.replaceState(null, "", location.pathname + h);
      ssSet("ctxList", h);
    }

    function hash() {
      var h = {};
      (location.hash.replace(/^#/, "").split("&")).forEach(function (kv) {
        var p = kv.split("="); if (p[0]) h[p[0]] = decodeURIComponent(p[1] || "");
      });
      return h;
    }
    function apply() {
      var shown = 0;
      for (var i = 0; i < cards.length; i++) {
        var c = cards[i];
        var okType = true, okText = true, okPair = true;
        for (var t in activeTypes) { okType = false; break; }
        if (!okType) { okType = !!activeTypes[c.getAttribute("data-type")]; }
        if (matchIds) { okText = !!matchIds[c.getAttribute("data-id")]; }
        if (pairIds) { okPair = !!pairIds[c.getAttribute("data-id")]; }
        var visible = okType && okText && okPair;
        c.hidden = !visible;
        if (visible) shown++;
      }
      if (countEl) countEl.textContent = shown + (shown === 1 ? " resultado" : " resultados");
      toggleEmpty(shown === 0);
    }
    function toggleEmpty(on) {
      var e = el("empty");
      if (e) e.hidden = !on;
    }
    function runSearch() {
      query = stripAccents(searchInput.value.trim());
      if (!query) { matchIds = null; apply(); return; }
      loadSearch(function (terms) {
        matchIds = {};
        for (var id in terms) { if (terms[id].indexOf(query) !== -1) matchIds[id] = 1; }
        apply();
      });
    }
    function sortBy(mode) {
      var arr = cards.slice();
      arr.sort(function (a, b) {
        if (mode === "connections") {
          return (+b.getAttribute("data-conn")) - (+a.getAttribute("data-conn"));
        }
        if (mode === "type") {
          var ta = a.getAttribute("data-type"), tb = b.getAttribute("data-type");
          if (ta !== tb) return ta < tb ? -1 : 1;
        }
        return a.getAttribute("data-name") < b.getAttribute("data-name") ? -1 : 1;
      });
      for (var i = 0; i < arr.length; i++) listEl.appendChild(arr[i]);
    }

    // chips
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var t = chip.getAttribute("data-type");
        if (activeTypes[t]) { delete activeTypes[t]; chip.setAttribute("aria-pressed", "false"); chip.classList.remove("is-active"); }
        else { activeTypes[t] = 1; chip.setAttribute("aria-pressed", "true"); chip.classList.add("is-active"); }
        apply(); syncHash();
      });
    });
    if (searchInput) searchInput.addEventListener("input", debounce(function () { runSearch(); syncHash(); }, 180));
    if (sortSel) sortSel.addEventListener("change", function () { sortBy(sortSel.value); syncHash(); });

    // matrix drill-down: #pair=place-person -> filter to nodes in that type pair
    function loadPair(pairStr) {
      var ctx = el("list-context");
      var x = new XMLHttpRequest();
      pairActive = pairStr;
      x.open("GET", dataPath() + "/pairs/" + pairStr + ".json", true);
      x.onreadystatechange = function () {
        if (x.readyState !== 4) return;
        var d = {}; try { d = JSON.parse(x.responseText); } catch (e) {}
        pairIds = {};
        (d.nodes || []).forEach(function (id) { pairIds[id] = 1; });
        if (ctx) {
          var la = typeMeta(d.a).label, lb = typeMeta(d.b).label, n = (d.nodes || []).length;
          ctx.innerHTML = "<div class='ctx'>Conexões <strong>" + escapeHtml(la) +
            " ↔ " + escapeHtml(lb) + "</strong> · " + n + " nós " +
            "<a href='#' id='ctx-clear'>limpar</a></div>";
          ctx.hidden = false;
          var cl = el("ctx-clear");
          if (cl) cl.addEventListener("click", function (e) {
            e.preventDefault(); pairIds = null; pairActive = null; ctx.hidden = true; ctx.innerHTML = "";
            apply(); syncHash();
          });
        }
        apply();
      };
      x.send();
    }

    // card tap: expanded → load the detail pane; compact/medium → inline connection expansion
    var pane = el("detail-pane");
    function loadPaneDetail(id) {
      if (!pane) return;
      ssSet("ctxNode", id);
      pane.innerHTML = "<div class='skeleton'></div>";
      xhrJSON(dataPath() + "/node/" + id + ".json", function (nd) { if (nd) pane.innerHTML = paneHTML(nd); });
    }
    listEl.addEventListener("click", function (e) {
      var btn = e.target;
      while (btn && btn !== listEl && !btn.classList.contains("card-main")) btn = btn.parentNode;
      if (!btn || btn === listEl) return;
      var card = btn.parentNode;
      if (getMode() === "expanded") {
        for (var i = 0; i < cards.length; i++) cards[i].classList.remove("is-selected");
        card.classList.add("is-selected");
        loadPaneDetail(card.getAttribute("data-id"));
      } else {
        openSheet(card.getAttribute("data-id"));   // compact/medium: detail bottom sheet
      }
    });
    // drilling inside the pane loads the neighbour into the same pane (expanded)
    if (pane) pane.addEventListener("click", function (e) {
      var a = e.target;
      while (a && a !== pane && !a.getAttribute("data-pane-id")) a = a.parentNode;
      if (a && a !== pane && getMode() === "expanded") { e.preventDefault(); loadPaneDetail(a.getAttribute("data-pane-id")); }
    });

    // initial state from hash (#type=person,place&sort=connections&q=…&pair=…)
    var h = hash();
    if (h.type) {
      h.type.split(",").forEach(function (tp) {
        if (!TYPES[tp]) return;
        activeTypes[tp] = 1;
        chips.forEach(function (c) {
          if (c.getAttribute("data-type") === tp) { c.setAttribute("aria-pressed", "true"); c.classList.add("is-active"); }
        });
      });
    }
    if (h.sort && sortSel) { sortSel.value = h.sort; sortBy(h.sort); }
    if (h.q && searchInput) { searchInput.value = h.q; runSearch(); }
    if (h.pair) { loadPair(h.pair); }
    apply();
    ssSet("ctxList", stateHash());   // remember this list state for the switcher
  }

  function toggleExpand(card) {
    var open = card.getAttribute("aria-expanded") === "true";
    if (open) { card.setAttribute("aria-expanded", "false"); var s = card.querySelector(".subconns"); if (s) s.hidden = true; return; }
    card.setAttribute("aria-expanded", "true");
    var existing = card.querySelector(".subconns");
    if (existing) { existing.hidden = false; return; }
    var holder = document.createElement("ul");
    holder.className = "subconns"; holder.innerHTML = "<li class='empty'>carregando…</li>";
    card.appendChild(holder);
    var id = card.getAttribute("data-id");
    var x = new XMLHttpRequest();
    x.open("GET", dataPath() + "/node/" + id + ".json", true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var edges = [];
      try { edges = JSON.parse(x.responseText).edges || []; } catch (e) {}
      if (!edges.length) { holder.innerHTML = "<li class='empty'>sem conexões</li>"; return; }
      var html = "";
      for (var i = 0; i < edges.length; i++) {
        var ed = edges[i], m = typeMeta(ed.target_type);
        html += "<li><a href='node/" + ed.target_id + ".html'>" +
                "<span class='badge t-" + ed.target_type + "'><span class='ico'>" + m.ico + "</span></span>" +
                escapeHtml(ed.target_name) + "</a></li>";
      }
      holder.innerHTML = html;
    };
    x.send();
  }

  function escapeHtml(s) {
    // escapes quotes too: values are injected into single-quoted HTML/SVG attributes
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* ---- detail bottom sheet (compact): a dialog reusing paneHTML ---- */
  var _sheetPrevFocus = null;
  function ensureSheet() {
    if (el("sheet")) return;
    var bd = document.createElement("div");
    bd.id = "sheet-backdrop"; bd.className = "sheet-backdrop"; bd.hidden = true;
    var sh = document.createElement("div");
    sh.id = "sheet"; sh.className = "sheet"; sh.hidden = true;
    sh.setAttribute("role", "dialog"); sh.setAttribute("aria-modal", "true");
    sh.setAttribute("aria-label", "Detalhe do nó");
    sh.innerHTML = "<button class='sheet-close' type='button' aria-label='Fechar'>✕</button>" +
      "<div id='sheet-body'></div>";
    document.body.appendChild(bd); document.body.appendChild(sh);
    bd.addEventListener("click", closeSheet);
    sh.querySelector(".sheet-close").addEventListener("click", closeSheet);
    document.addEventListener("keydown", function (e) { if (!sh.hidden && e.key === "Escape") closeSheet(); });
    sh.addEventListener("keydown", function (e) {          // focus trap
      if (e.key !== "Tab") return;
      var f = sh.querySelectorAll("button, a[href]");
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    el("sheet-body").addEventListener("click", function (e) {   // drill within the sheet
      var a = e.target;
      while (a && a !== this && !(a.getAttribute && a.getAttribute("data-pane-id"))) a = a.parentNode;
      if (a && a.getAttribute && a.getAttribute("data-pane-id")) { e.preventDefault(); openSheet(a.getAttribute("data-pane-id")); }
    });
  }
  function openSheet(id) {
    ensureSheet();
    _sheetPrevFocus = document.activeElement;
    ssSet("ctxNode", id);
    var body = el("sheet-body"); body.innerHTML = "<div class='skeleton'></div>";
    el("sheet-backdrop").hidden = false; el("sheet").hidden = false;
    document.body.style.overflow = "hidden";
    el("sheet").querySelector(".sheet-close").focus();
    xhrJSON(dataPath() + "/node/" + id + ".json", function (nd) { if (nd) body.innerHTML = paneHTML(nd); });
  }
  function closeSheet() {
    var sh = el("sheet"); if (!sh || sh.hidden) return;
    sh.hidden = true; el("sheet-backdrop").hidden = true; document.body.style.overflow = "";
    if (_sheetPrevFocus && _sheetPrevFocus.focus) _sheetPrevFocus.focus();
  }

  // detail pane (expanded multi-panel) — renders a node's detail from its JSON
  function paneHTML(nd) {
    var m = typeMeta(nd.type), edges = nd.edges || [];
    var dsc = (getLang() === "en" && nd.de) ? nd.de : nd.description;
    var loc = [nd.neighborhood, nd.municipality].filter(function (x) { return x; }).join(" · ");
    var conns = "";
    for (var i = 0; i < edges.length && i < 60; i++) {
      var e = edges[i], em = typeMeta(e.target_type);
      conns += "<li class='card t-" + e.target_type + "'><a class='card-main' href='node/" +
        e.target_id + ".html' data-pane-id='" + escapeHtml(e.target_id) + "'>" +
        "<span class='card-body'><span class='card-name'>" + escapeHtml(e.target_name) + "</span>" +
        "<span class='card-meta'><span class='badge t-" + e.target_type + "'><span class='ico'>" +
        em.ico + "</span>" + escapeHtml(em.label) + "</span></span></span></a></li>";
    }
    return "<div class='detail-head'><span class='badge t-" + nd.type + "'><span class='ico'>" +
      m.ico + "</span>" + escapeHtml(m.label) + "</span><h2 class='detail-name'>" +
      escapeHtml(nd.name) + "</h2></div>" +
      (loc ? "<p class='detail-loc'>" + escapeHtml(loc) + "</p>" : "") +
      (nd.image ? "<img class='detail-img' src='" + escapeHtml(nd.image) +
        "' alt='' loading='lazy' onerror=\"this.style.display='none'\">" : "") +
      (dsc ? "<p class='detail-desc'>" + escapeHtml(dsc) + "</p>"
           : "<p class='detail-desc muted'>" + L("Sem descrição ainda.", "No description yet.") + "</p>") +
      "<div class='gp-actions'><a class='btn' href='node/" + nd.id + ".html'>" +
      L("Abrir página", "Open page") + "</a>" +
      "<a class='btn btn-primary' href='graph.html#node=" + encodeURIComponent(nd.id) +
      "'>" + L("Ver conexões", "View connections") + "</a></div>" +
      "<h3 class='section-h'>" + L("Conexões", "Connections") + " (" + edges.length +
      ")</h3><ul class='cards'>" + conns + "</ul>";
  }

  /* ================================ HOME PAGE ================================ */
  function initHome() {
    var input = el("home-q");
    if (!input) return;
    var results = el("home-results");
    var form = el("home-search");

    if (form) form.addEventListener("submit", function (e) {
      e.preventDefault();
      var v = input.value.trim();
      location.href = "list.html" + (v ? "#q=" + encodeURIComponent(v) : "");
    });

    input.addEventListener("input", debounce(function () {
      var q = stripAccents(input.value.trim());
      if (q.length < 2) { results.innerHTML = ""; results.hidden = true; return; }
      loadSearch(function (terms) {
        // need names for display -> pull from search.json array (re-fetch cached)
        var x = new XMLHttpRequest();
        x.open("GET", dataPath() + "/search.json", true);
        x.onreadystatechange = function () {
          if (x.readyState !== 4) return;
          var arr = []; try { arr = JSON.parse(x.responseText); } catch (e) {}
          var out = [], n = 0;
          for (var i = 0; i < arr.length && n < 8; i++) {
            var o = arr[i];
            var hay = o.norm + " " + (o.aliases ? o.aliases.join(" ") : "");
            if (hay.indexOf(q) !== -1) {
              var m = typeMeta(o.type);
              out.push("<li class='card t-" + o.type + "'><a class='card-main' href='node/" + o.id + ".html'>" +
                "<span class='badge t-" + o.type + "'><span class='ico'>" + m.ico + "</span>" + m.label + "</span>" +
                "<span class='card-body'><span class='card-name'>" + escapeHtml(o.name) + "</span></span></a></li>");
              n++;
            }
          }
          results.innerHTML = out.length ? out.join("") :
            "<li class='empty-state'>Nenhum resultado para “" + escapeHtml(input.value.trim()) + "”.</li>";
          results.hidden = false;
        };
        x.send();
      });
    }, 200));
  }

  /* ---- node detail page: remember it as the switcher's graph context ---- */
  function initNode() {
    var art = document.querySelector(".detail[data-node-id]");
    if (art) ssSet("ctxNode", art.getAttribute("data-node-id"));
  }

  /* ================================ GRAPH (ego) ============================== */
  function initGraph() {
    var canvas = el("graph-canvas");
    if (!canvas) return;
    var titleEl = el("graph-title"), hintEl = el("graph-hint"), panel = el("graph-panel");
    var _wantPanel = false;   // set when a neighbour tap should open the panel after recentering

    function drawCenterAndNeighbors(d) {
      if (!d || !d.id) { canvas.innerHTML = "<p class='empty-state'>Nó não encontrado.</p>"; return; }
      if (titleEl) titleEl.textContent = "Conexões de " + d.name;
      var edges = d.edges || [];
      var MAX = getMode() === "expanded" ? 18 : 5;   // mobile: cap at 5 neighbours
      var shown = edges.slice(0, MAX), more = edges.length - shown.length;
      var W = 320, H = 320, cx = 160, cy = 160, R = 116, n = shown.length, i, ang, nx, ny;

      var svg = "<svg viewBox='0 0 " + W + " " + H + "' width='100%' " +
        "aria-label='Grafo de conexões de " + escapeHtml(d.name) + "'>";
      var pts = [];
      for (i = 0; i < n; i++) {
        ang = (-90 + i * 360 / n) * Math.PI / 180;
        nx = cx + R * Math.cos(ang); ny = cy + R * Math.sin(ang);
        pts.push({ x: nx, y: ny, e: shown[i] });
        var sw = 1 + Math.min(4, (shown[i].strength || 1));
        svg += "<line x1='" + cx + "' y1='" + cy + "' x2='" + nx.toFixed(1) + "' y2='" + ny.toFixed(1) +
               "' stroke='#c9c9d0' stroke-width='" + sw + "'/>";
      }
      for (i = 0; i < n; i++) {
        var p = pts[i], col = typeColor(p.e.target_type);
        svg += "<g class='gnode' data-id='" + escapeHtml(p.e.target_id) + "' tabindex='0' role='button' " +
          "aria-label='" + escapeHtml(p.e.target_name) + "'>" +
          "<circle cx='" + p.x.toFixed(1) + "' cy='" + p.y.toFixed(1) + "' r='13' fill='" + col + "'/>" +
          "<text x='" + p.x.toFixed(1) + "' y='" + (p.y + 24).toFixed(1) + "' text-anchor='middle' " +
          "class='glabel'>" + escapeHtml(trunc(p.e.target_name, 13)) + "</text></g>";
      }
      svg += "<circle cx='" + cx + "' cy='" + cy + "' r='20' fill='" + typeColor(d.type) +
        "' stroke='#fff' stroke-width='2'/>";
      svg += "<text x='" + cx + "' y='" + (cy + 38) + "' text-anchor='middle' class='glabel gcenter'>" +
        escapeHtml(trunc(d.name, 16)) + "</text></svg>";
      canvas.innerHTML = svg;

      if (hintEl) hintEl.innerHTML =
        "<strong>" + L("Toque num nó para ver os detalhes.", "Tap a node to see its details.") + "</strong> " +
        (more > 0 ? (L("+" + more + " conexões não exibidas. ", "+" + more + " connections not shown. ")) : "") +
        "<a href='node/" + d.id + ".html'>" + L("Ver como lista →", "View as list →") + "</a>";

      var gnodes = canvas.querySelectorAll(".gnode"), k;
      function bind(gn) {
        gn.addEventListener("click", function () { selectNeighbor(gn.getAttribute("data-id")); });
        gn.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); selectNeighbor(gn.getAttribute("data-id")); }
        });
      }
      for (k = 0; k < gnodes.length; k++) { bind(gnodes[k]); }
    }

    function showPanel(nd) {
      if (!panel || !nd) return;
      var src = (getLang() === "en" && nd.de) ? nd.de : nd.description;
      var m = typeMeta(nd.type), desc = src ? trunc(src, 160) : "";
      panel.innerHTML =
        "<button class='gp-close' type='button' aria-label='Fechar'>✕</button>" +
        "<div class='gp-head'><span class='badge t-" + nd.type + "'><span class='ico'>" + m.ico +
        "</span>" + escapeHtml(typeLabel(nd.type)) + "</span> <strong class='gp-name'>" + escapeHtml(nd.name) +
        "</strong></div>" +
        (nd.image ? "<img class='gp-img' src='" + escapeHtml(nd.image) +
          "' alt='' loading='lazy' onerror=\"this.style.display='none'\">" : "") +
        (desc ? "<p class='gp-desc'>" + escapeHtml(desc) + "</p>" : "") +
        "<div class='gp-actions'><a class='btn' href='node/" + nd.id + ".html'>" +
        L("Ver detalhes", "View details") + "</a>" +
        "<a class='btn btn-primary' href='node/" + nd.id + ".html'>" +
        L("Abrir página", "Open page") + "</a></div>";
      panel.hidden = false;
      var cl = panel.querySelector(".gp-close");
      if (cl) cl.addEventListener("click", function () { panel.hidden = true; });
    }

    // selecting an adjacent node recenters the graph on it (and opens its panel)
    function selectNeighbor(id) {
      _wantPanel = true;
      location.hash = "node=" + encodeURIComponent(id);
    }

    function load() {
      var id = parseHash().node;
      if (panel) panel.hidden = true;
      if (!id) {
        canvas.innerHTML = "";
        if (hintEl) hintEl.innerHTML = "Abra um nó e toque em “Ver conexões”. " +
          "<a href='list.html'>Ver a lista →</a>";
        return;
      }
      ssSet("ctxNode", id);   // current graph center is the switcher's node context
      canvas.innerHTML = "<div class='skeleton' style='height:320px'></div>";
      xhrJSON(dataPath() + "/node/" + id + ".json", function (d) {
        drawCenterAndNeighbors(d);
        if (_wantPanel) { showPanel(d); _wantPanel = false; }   // opened via neighbour tap
      });
    }

    window.addEventListener("hashchange", load);   // "Ver conexões" recenters; back works
    load();
  }

  /* ============================== VIEW SWITCHER ============================== */
  // Preserves context across the three projections: the current node (ctxNode) and
  // the list's filter/search hash (ctxList), carried via sessionStorage.
  function initSwitcher() {
    var sw = document.querySelector(".switcher");
    if (!sw) return;
    var ctxNode = ssGet("ctxNode"), ctxList = ssGet("ctxList");
    var gTab = sw.querySelector("[data-view='graph']");
    var lTab = sw.querySelector("[data-view='list']");

    if (gTab && gTab.getAttribute("aria-selected") !== "true") {
      if (ctxNode) {
        gTab.setAttribute("href", "graph.html#node=" + encodeURIComponent(ctxNode));
      } else {
        gTab.classList.add("is-disabled");
        gTab.setAttribute("aria-disabled", "true");
        gTab.setAttribute("title", "Abra um nó para ver o grafo");
        gTab.addEventListener("click", function (e) { e.preventDefault(); });
      }
    }
    if (lTab && lTab.getAttribute("aria-selected") !== "true" && ctxList) {
      lTab.setAttribute("href", "list.html" + ctxList);
    }
  }

  /* ========================= OFFLINE + SERVICE WORKER ======================= */
  function initOffline() {
    function update() {
      var bar = el("offline-bar");
      if (!navigator.onLine) {
        if (!bar) {
          bar = document.createElement("div");
          bar.id = "offline-bar"; bar.className = "offline-bar";
          bar.setAttribute("role", "status");
          bar.textContent = "Sem conexão — mostrando o conteúdo já salvo.";
          document.body.insertBefore(bar, document.body.firstChild);
        }
      } else if (bar && bar.parentNode) {
        bar.parentNode.removeChild(bar);
      }
    }
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    update();
  }

  function registerSW() {
    if (!("serviceWorker" in navigator) || location.protocol === "file:") return;
    // data lives at <root>/data; the SW sits one level up at <root>/sw.js so its
    // scope covers both site/ and data/. Compute <root> from the page's data path.
    var root = dataPath().replace(/data\/?$/, "");
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(root + "sw.js", { scope: root })["catch"](function () {});
    });
  }

  /* ================================ THEME ================================== */
  // Dark is the default (set in CSS); a manual toggle persists the choice.
  function initTheme() {
    var btn = el("theme-toggle");
    function current() { return document.documentElement.getAttribute("data-theme") || "dark"; }
    function paint() { if (btn) btn.textContent = current() === "dark" ? "☀" : "🌙"; }
    paint();
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      paint();
    });
  }

  /* ---- boot ---- */
  function boot() {
    var page = document.body.getAttribute("data-page");
    initTheme();
    initLang();
    initResponsive();
    initOffline();
    registerSW();
    initSwitcher();
    if (page === "list") initList();
    else if (page === "inicio") initHome();
    else if (page === "node") initNode();
    else if (page === "graph") initGraph();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
