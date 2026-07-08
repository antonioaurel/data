'use strict';

const express = require('express');

const REQUIRED = ['name', 'type'];

// Returns an array of error strings ([] means valid).
function validate(body, { partial = false } = {}) {
  if (body == null || typeof body !== 'object' || Array.isArray(body)) {
    return ['body must be a JSON object'];
  }
  const errors = [];
  if (!partial) {
    for (const f of REQUIRED) {
      if (body[f] == null || String(body[f]).trim() === '') errors.push(`${f} is required`);
    }
  }
  for (const f of REQUIRED) {
    if (f in body && (typeof body[f] !== 'string' || body[f].trim() === '')) {
      errors.push(`${f} must be a non-empty string`);
    }
  }
  for (const f of ['lat', 'lon']) {
    if (f in body && body[f] != null && body[f] !== '' && Number.isNaN(Number(body[f]))) {
      errors.push(`${f} must be numeric`);
    }
  }
  // An explicit id becomes a URL path segment (GET /api/items/:id); keep it to a
  // safe charset so items stay reachable and Location headers stay well-formed.
  if ('id' in body && body.id != null && String(body.id).trim() !== '' && !/^[A-Za-z0-9._-]+$/.test(String(body.id).trim())) {
    errors.push('id may only contain letters, digits, dot, underscore or hyphen');
  }
  return errors;
}

module.exports = function itemsRouter(store) {
  const router = express.Router();

  router.get('/', (req, res) => {
    const { type, neighborhood, city, q, limit, offset } = req.query;
    res.json(store.list({ type, neighborhood, city, q, limit, offset }));
  });

  router.get('/:id', (req, res) => {
    const item = store.get(req.params.id);
    if (!item) return res.status(404).json({ error: 'not found', id: req.params.id });
    res.json(item);
  });

  router.post('/', (req, res) => {
    const errors = validate(req.body);
    if (errors.length) return res.status(400).json({ error: 'validation failed', details: errors });
    try {
      const item = store.create(req.body);
      res.status(201).location(`/api/items/${encodeURIComponent(item.id)}`).json(item);
    } catch (e) {
      res.status(e.status || 500).json({ error: e.message });
    }
  });

  router.put('/:id', (req, res) => {
    const errors = validate(req.body);
    if (errors.length) return res.status(400).json({ error: 'validation failed', details: errors });
    const item = store.replace(req.params.id, req.body);
    if (!item) return res.status(404).json({ error: 'not found', id: req.params.id });
    res.json(item);
  });

  router.patch('/:id', (req, res) => {
    const errors = validate(req.body, { partial: true });
    if (errors.length) return res.status(400).json({ error: 'validation failed', details: errors });
    const item = store.update(req.params.id, req.body);
    if (!item) return res.status(404).json({ error: 'not found', id: req.params.id });
    res.json(item);
  });

  router.delete('/:id', (req, res) => {
    const ok = store.remove(req.params.id);
    if (!ok) return res.status(404).json({ error: 'not found', id: req.params.id });
    res.status(204).end();
  });

  return router;
};

module.exports.validate = validate;
