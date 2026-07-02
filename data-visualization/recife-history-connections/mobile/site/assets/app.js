/* Conexões da História — mobile progressive enhancement (Phase 2).
   Vanilla ES5-friendly for old Android WebView. Static HTML works without this file;
   this only enhances: alias-aware search, type filter, sort, inline connection expansion. */
(function () {
  "use strict";

  // Concentrated on the three original types in the base.
  var TYPES = {
    place:           { label: "Local",          ico: "📍" },
    person:          { label: "Personagem",     ico: "👤" },
    historical_fact: { label: "Fato Histórico", ico: "📜" }
  };
  var FALLBACK = { label: "Outro", ico: "●" };
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
        apply();
      });
    });
    if (searchInput) searchInput.addEventListener("input", debounce(runSearch, 180));
    if (sortSel) sortSel.addEventListener("change", function () { sortBy(sortSel.value); });

    // matrix drill-down: #pair=place-person -> filter to nodes in that type pair
    function loadPair(pairStr) {
      var ctx = el("list-context");
      var x = new XMLHttpRequest();
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
            e.preventDefault(); pairIds = null; ctx.hidden = true; ctx.innerHTML = "";
            if (history.replaceState) history.replaceState(null, "", location.pathname);
            apply();
          });
        }
        apply();
      };
      x.send();
    }

    // inline connection expansion (event delegation)
    listEl.addEventListener("click", function (e) {
      var btn = e.target;
      while (btn && btn !== listEl && !btn.classList.contains("card-main")) btn = btn.parentNode;
      if (!btn || btn === listEl) return;
      var card = btn.parentNode;
      toggleExpand(card);
    });

    // initial state from hash (#type=person&sort=connections&q=...)
    var h = hash();
    if (h.type && TYPES[h.type]) {
      activeTypes[h.type] = 1;
      chips.forEach(function (c) { if (c.getAttribute("data-type") === h.type) { c.setAttribute("aria-pressed", "true"); c.classList.add("is-active"); } });
    }
    if (h.sort && sortSel) { sortSel.value = h.sort; sortBy(h.sort); }
    if (h.q && searchInput) { searchInput.value = h.q; runSearch(); }
    if (h.pair) { loadPair(h.pair); }
    apply();
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

  /* ================================ FAVORITES ================================ */
  var FAV_KEY = "cdh_favs";
  function getFavs() {
    try { return JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch (e) { return []; }
  }
  function setFavs(a) { try { localStorage.setItem(FAV_KEY, JSON.stringify(a)); } catch (e) {} }
  function toggleFav(id) {
    var a = getFavs(), i = a.indexOf(id);
    if (i === -1) { a.push(id); } else { a.splice(i, 1); }
    setFavs(a);
    return i === -1;   // true if now favorited
  }

  function initNode() {
    var btn = el("fav-btn");
    if (!btn) return;
    var id = btn.getAttribute("data-id");
    function paint(on) {
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.className = "fav-btn js-only" + (on ? " is-fav" : "");
      btn.innerHTML = on ? "★ Favoritado" : "☆ Favoritar";
    }
    paint(getFavs().indexOf(id) !== -1);
    btn.addEventListener("click", function () { paint(toggleFav(id)); });
  }

  function initFavorites() {
    var listEl = el("fav-list"), emptyEl = el("fav-empty");
    if (!listEl) return;
    var favs = getFavs();
    if (!favs.length) { if (emptyEl) emptyEl.hidden = false; return; }
    var x = new XMLHttpRequest();
    x.open("GET", dataPath() + "/index.json", true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var idx = []; try { idx = JSON.parse(x.responseText); } catch (e) {}
      var byId = {};
      for (var i = 0; i < idx.length; i++) { byId[idx[i].id] = idx[i]; }
      var html = "", n = 0;
      for (var j = 0; j < favs.length; j++) {
        var o = byId[favs[j]];
        if (!o) continue;
        n++;
        var m = typeMeta(o.type);
        html += "<li class='card t-" + o.type + "'><a class='card-main' href='node/" + o.id + ".html'>" +
          "<span class='card-body'><span class='card-name'>" + escapeHtml(o.name) + "</span>" +
          "<span class='card-meta'><span class='badge t-" + o.type + "'><span class='ico'>" + m.ico +
          "</span>" + escapeHtml(m.label) + "</span><span class='conn'>" + o.conn_count +
          " conexões</span></span></span></a></li>";
      }
      if (!n) { if (emptyEl) emptyEl.hidden = false; return; }
      listEl.innerHTML = "<ul class='cards'>" + html + "</ul>";
    };
    x.send();
  }

  /* ================================ GRAPH (ego) ============================== */
  function initGraph() {
    var canvas = el("graph-canvas");
    if (!canvas) return;
    var titleEl = el("graph-title"), hintEl = el("graph-hint"), panel = el("graph-panel");

    function drawCenterAndNeighbors(d) {
      if (!d || !d.id) { canvas.innerHTML = "<p class='empty-state'>Nó não encontrado.</p>"; return; }
      if (titleEl) titleEl.textContent = "Conexões de " + d.name;
      var edges = d.edges || [];
      var MAX = 18, shown = edges.slice(0, MAX), more = edges.length - shown.length;
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

      if (hintEl) hintEl.innerHTML = (more > 0 ? ("+" + more + " conexões não exibidas. ") : "") +
        "<a href='node/" + d.id + ".html'>Ver como lista →</a>";

      var gnodes = canvas.querySelectorAll(".gnode"), k;
      function bind(gn) {
        gn.addEventListener("click", function () { selectNeighbor(gn.getAttribute("data-id")); });
        gn.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); selectNeighbor(gn.getAttribute("data-id")); }
        });
      }
      for (k = 0; k < gnodes.length; k++) { bind(gnodes[k]); }
    }

    function selectNeighbor(id) {
      xhrJSON(dataPath() + "/node/" + id + ".json", function (nd) {
        if (!panel || !nd) return;
        var m = typeMeta(nd.type), desc = nd.description ? trunc(nd.description, 160) : "";
        panel.innerHTML =
          "<button class='gp-close' type='button' aria-label='Fechar'>✕</button>" +
          "<div class='gp-head'><span class='badge t-" + nd.type + "'><span class='ico'>" + m.ico +
          "</span>" + escapeHtml(m.label) + "</span> <strong class='gp-name'>" + escapeHtml(nd.name) +
          "</strong></div>" + (desc ? "<p class='gp-desc'>" + escapeHtml(desc) + "</p>" : "") +
          "<div class='gp-actions'><a class='btn' href='node/" + nd.id + ".html'>Ver detalhes</a>" +
          "<a class='btn btn-primary' href='graph.html#node=" + encodeURIComponent(nd.id) +
          "'>Ver conexões</a></div>";
        panel.hidden = false;
        var cl = panel.querySelector(".gp-close");
        if (cl) cl.addEventListener("click", function () { panel.hidden = true; });
      });
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
      canvas.innerHTML = "<div class='skeleton' style='height:320px'></div>";
      xhrJSON(dataPath() + "/node/" + id + ".json", drawCenterAndNeighbors);
    }

    window.addEventListener("hashchange", load);   // "Ver conexões" recenters; back works
    load();
  }

  /* ---- boot ---- */
  function boot() {
    var page = document.body.getAttribute("data-page");
    if (page === "list") initList();
    else if (page === "home") initHome();
    else if (page === "node") initNode();
    else if (page === "favorites") initFavorites();
    else if (page === "graph") initGraph();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
