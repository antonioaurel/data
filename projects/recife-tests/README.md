# recife-tests

Central, standalone test project for the **Conexões da História / Recife** work.
Tests are grouped by nature under `tests/`:

```
tests/
├── api/   → REST API tests (Playwright request context, no browser)
├── db/    → dataset / "database" tests over the CSVs (pytest — planned)
└── ui/    → screen tests using the data-testid hooks (Playwright browser — planned)
```

## api/ — ready

Covers the CRUD REST API exposed by the **`connections-api`** project over the
`nodes.csv` dataset. The suite boots that server automatically (see
`playwright.config.js` → `webServer`, which runs `node src/server.js` from
`../connections-api`). No browser is used — Playwright's `request` fixture hits
the HTTP API directly.

```sh
cd projects/recife-tests
npm install        # installs @playwright/test here
# express must be installed in ../connections-api (its own `npm install`)
npm test           # boots the server on PORT 3100 and runs the API suite
npm run test:api   # api only
```

> The server dependency lives in `../connections-api/node_modules`, so run
> `npm install` there once as well.

## db/ — planned

Validation over the source CSVs in
`../recife-history-connections/data/` (`nodes.csv`, `edges.csv`, `coords.csv`,
`periods.csv`, `aliases.csv`): unique ids, finite coordinates, edges referencing
existing nodes, etc. The project is Python-based, so these will most likely be
`pytest`.

## ui/ — planned

Screen tests (Diagrama/Grafo, Mapa, Lista, Matriz) driving the published site via
the `pc-<screen>-<region>-<component>` `data-testid` hooks added in PR #27.
Playwright with a real browser.
