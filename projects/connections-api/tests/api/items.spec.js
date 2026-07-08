'use strict';

const { test, expect } = require('@playwright/test');

// Restore the seeded dataset before each test (shared in-memory store).
test.beforeEach(async ({ request }) => {
  const res = await request.post('/api/_reset');
  expect(res.ok()).toBeTruthy();
});

test.describe('health', () => {
  test('reports ok and the seeded item count', async ({ request }) => {
    const res = await request.get('/health');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.items).toBeGreaterThan(500);
  });
});

test.describe('GET /api/items', () => {
  test('lists items with pagination metadata', async ({ request }) => {
    const res = await request.get('/api/items?limit=10');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.total).toBeGreaterThan(500);
    expect(body.items).toHaveLength(10);
    expect(body.items[0]).toHaveProperty('id');
    expect(body.items[0]).toHaveProperty('name');
  });

  test('paginates with offset', async ({ request }) => {
    const first = await (await request.get('/api/items?limit=1&offset=0')).json();
    const second = await (await request.get('/api/items?limit=1&offset=1')).json();
    expect(first.items[0].id).not.toBe(second.items[0].id);
  });

  test('filters by type', async ({ request }) => {
    const res = await request.get('/api/items?type=Local&limit=5');
    const body = await res.json();
    expect(body.items.length).toBeGreaterThan(0);
    for (const it of body.items) expect(it.type).toBe('Local');
  });

  test('search q matches name or description', async ({ request }) => {
    const res = await request.get('/api/items?q=jardim&limit=5');
    const body = await res.json();
    expect(body.total).toBeGreaterThan(0);
  });
});

test.describe('GET /api/items/:id', () => {
  test('returns a known item', async ({ request }) => {
    const res = await request.get('/api/items/LC-0002');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.id).toBe('LC-0002');
    expect(body).toHaveProperty('name');
  });

  test('returns 404 for an unknown id', async ({ request }) => {
    const res = await request.get('/api/items/NOPE-9999');
    expect(res.status()).toBe(404);
    expect((await res.json()).error).toBe('not found');
  });
});

test.describe('POST /api/items', () => {
  test('creates an item, returns 201 + Location, and is retrievable', async ({ request }) => {
    const res = await request.post('/api/items', {
      data: { name: 'Teste API', type: 'Local', city: 'Recife' },
    });
    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body.id).toMatch(/^LC-\d+$/);
    expect(body.name).toBe('Teste API');
    expect(res.headers()['location']).toContain(body.id);

    const got = await request.get(`/api/items/${body.id}`);
    expect(got.status()).toBe(200);
    expect((await got.json()).city).toBe('Recife');
  });

  test('rejects missing required fields with 400', async ({ request }) => {
    const res = await request.post('/api/items', { data: { city: 'Recife' } });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.details).toEqual(
      expect.arrayContaining([expect.stringContaining('name')])
    );
  });

  test('rejects invalid JSON with 400', async ({ request }) => {
    const res = await request.post('/api/items', {
      headers: { 'Content-Type': 'application/json' },
      data: '{ not valid json',
    });
    expect(res.status()).toBe(400);
  });

  test('rejects a duplicate id with 409', async ({ request }) => {
    const res = await request.post('/api/items', {
      data: { id: 'LC-0002', name: 'Dup', type: 'Local' },
    });
    expect(res.status()).toBe(409);
  });

  test('auto-id after an explicit high id does not collide (regression)', async ({ request }) => {
    const explicit = await request.post('/api/items', {
      data: { id: 'LC-9003', name: 'Explicit high id', type: 'Local' },
    });
    expect(explicit.status()).toBe(201);
    // a following auto-id create must not be handed the same id → no false 409
    const auto = await request.post('/api/items', {
      data: { name: 'Auto after explicit', type: 'Local' },
    });
    expect(auto.status()).toBe(201);
    expect((await auto.json()).id).not.toBe('LC-9003');
  });
});

test.describe('PUT /api/items/:id', () => {
  test('replaces an existing item', async ({ request }) => {
    const res = await request.put('/api/items/LC-0002', {
      data: { name: 'Substituído', type: 'Local' },
    });
    expect(res.status()).toBe(200);
    expect((await res.json()).name).toBe('Substituído');
  });

  test('returns 404 on unknown id', async ({ request }) => {
    const res = await request.put('/api/items/NOPE-1', {
      data: { name: 'x', type: 'Local' },
    });
    expect(res.status()).toBe(404);
  });
});

test.describe('PATCH /api/items/:id', () => {
  test('updates part of an item, keeping id', async ({ request }) => {
    const res = await request.patch('/api/items/LC-0002', {
      data: { neighborhood: 'Novo Bairro' },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.neighborhood).toBe('Novo Bairro');
    expect(body.id).toBe('LC-0002');
  });
});

test.describe('DELETE /api/items/:id', () => {
  test('removes an item (204) and then 404s', async ({ request }) => {
    const del = await request.delete('/api/items/LC-0002');
    expect(del.status()).toBe(204);
    const got = await request.get('/api/items/LC-0002');
    expect(got.status()).toBe(404);
  });

  test('returns 404 deleting an unknown id', async ({ request }) => {
    const res = await request.delete('/api/items/NOPE-2');
    expect(res.status()).toBe(404);
  });
});

test.describe('_reset', () => {
  test('restores a deleted item', async ({ request }) => {
    await request.delete('/api/items/LC-0003');
    await request.post('/api/_reset');
    const got = await request.get('/api/items/LC-0003');
    expect(got.status()).toBe(200);
  });
});
