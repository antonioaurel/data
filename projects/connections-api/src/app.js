'use strict';

const express = require('express');
const { Store } = require('./store');
const itemsRouter = require('./routes/items');

// App factory so tests can inject a store (e.g. a fixture-backed one).
function createApp({ store } = {}) {
  const app = express();
  app.use(express.json());

  const s = store || new Store();
  app.locals.store = s;

  app.get('/health', (req, res) => res.json({ status: 'ok', items: s.size }));

  app.use('/api/items', itemsRouter(s));

  // Test helper: restore the seeded dataset between tests.
  app.post('/api/_reset', (req, res) => {
    s.reset();
    res.json({ status: 'reset', items: s.size });
  });

  app.use((req, res) => res.status(404).json({ error: 'route not found', path: req.path }));

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    if (err && (err.type === 'entity.parse.failed' || err instanceof SyntaxError)) {
      return res.status(400).json({ error: 'invalid JSON body' });
    }
    // body-parser (and other) client errors carry a 4xx status — preserve it
    // instead of masking as 500 (e.g. 413 payload too large, 415 unsupported type).
    const status = err && (err.status || err.statusCode);
    if (Number.isInteger(status) && status >= 400 && status < 500) {
      return res.status(status).json({ error: err.message || 'bad request' });
    }
    res.status(500).json({ error: 'internal error' });
  });

  return app;
}

module.exports = { createApp };
