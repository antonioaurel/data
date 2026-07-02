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
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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

  /* ---- boot ---- */
  function boot() {
    var page = document.body.getAttribute("data-page");
    if (page === "list") initList();
    else if (page === "home") initHome();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
