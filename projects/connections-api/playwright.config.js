'use strict';

const { defineConfig } = require('@playwright/test');

const PORT = process.env.PORT || 3100;
const baseURL = `http://localhost:${PORT}`;

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
    env: { PORT: String(PORT) },
    url: `${baseURL}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
