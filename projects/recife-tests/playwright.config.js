'use strict';

const path = require('path');
const { defineConfig } = require('@playwright/test');

const PORT = process.env.PORT || 3100;
const baseURL = `http://localhost:${PORT}`;

// The API suite hits the connections-api server, which lives in a sibling
// project. We boot it here from its own directory so it resolves its own
// node_modules (express). Keep `db/` and `ui/` suites in their own projects
// below as they come online (pytest / browser Playwright).
const connectionsApiDir = path.resolve(__dirname, '../connections-api');

module.exports = defineConfig({
  testDir: './tests/api',
  // Shared in-memory store → run serially so tests don't step on each other.
  workers: 1,
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL,
    extraHTTPHeaders: { 'Content-Type': 'application/json' },
  },
  webServer: {
    command: 'node src/server.js',
    cwd: connectionsApiDir,
    env: { PORT: String(PORT) },
    url: `${baseURL}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
