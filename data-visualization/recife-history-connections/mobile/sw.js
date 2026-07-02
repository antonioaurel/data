/* Conexões da História — service worker.
   Lives at mobile/sw.js so its scope (mobile/) covers both site/ (pages) and data/ (JSON).
   Strategy: precache the shell + core indexes; stale-while-revalidate for everything else
   (return cache immediately, refresh in the background) so a data-depleted user keeps
   browsing what they've already seen. Bump CACHE when the shell changes. */
var CACHE = "cdh-v4";
var OFFLINE_FALLBACK = "site/index.html";
var PRECACHE = [
  "site/index.html", "site/list.html", "site/matriz.html", "site/graph.html",
  "site/fillrate.html", "site/fontes.html", "site/sobre.html",
  "site/assets/app.css", "site/assets/app.js", "site/assets/fonts/inter-latin.woff2",
  "data/index.json", "data/search.json", "data/matrix.json"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE); })
                      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { if (k !== CACHE) return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    caches.open(CACHE).then(function (cache) {
      return cache.match(req).then(function (cached) {
        var net = fetch(req).then(function (res) {
          if (res && res.status === 200) cache.put(req, res.clone());
          return res;
        }).catch(function () {
          return cached || (req.mode === "navigate" ? cache.match(OFFLINE_FALLBACK) : undefined);
        });
        return cached || net;
      });
    })
  );
});
