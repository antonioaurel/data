# connections-api

A small CRUD REST API over the **Conexões da História** nodes dataset
(`projects/recife-history-connections/data/nodes.csv`), built to practice and
demonstrate **API testing** with Playwright.

- **Stack:** Node + Express, tests with `@playwright/test` (request context).
- **Data:** seeded **in memory** from the CSV on startup — writes never touch the
  source file. `POST /api/_reset` restores the seed (used between tests).

## Run

```sh
cd projects/connections-api
npm install
npm start          # http://localhost:3000
```

Point at a different dataset with `CONNECTIONS_CSV=/path/to/file.csv`.

## Test

```sh
npm test           # boots the server on PORT 3100 and runs the API suite
```

(No browsers needed — Playwright's `request` fixture hits the HTTP API directly.)

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{ status, items }` |
| GET | `/api/items` | query: `type`, `neighborhood`, `city`, `q`, `limit`, `offset` → `{ total, count, offset, limit, items }` |
| GET | `/api/items/:id` | `404` if missing |
| POST | `/api/items` | `name` + `type` required → `201` + `Location`; `400` invalid; `409` duplicate id |
| PUT | `/api/items/:id` | full replace; `404` if missing |
| PATCH | `/api/items/:id` | partial update; `404` if missing |
| DELETE | `/api/items/:id` | `204`; `404` if missing |
| POST | `/api/_reset` | restore the seeded dataset (test helper) |

## Item shape

Mirrors the CSV columns: `id`, `legacy_id`, `name`, `type`, `sub_type`,
`neighborhood`, `city`, `state`, `country`, `lat`, `lon`, `image`, `description`,
`source`, `curation_status`, `notes` (`lat`/`lon` coerced to numbers or `null`).
