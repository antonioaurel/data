'use strict';

const path = require('path');
const { loadCsvObjects } = require('./csv');

// Default to the real shared dataset; override with CONNECTIONS_CSV (e.g. a
// smaller fixture in tests).
const DEFAULT_CSV = path.resolve(
  __dirname,
  '../../recife-history-connections/data/nodes.csv'
);

const NUMERIC_FIELDS = ['lat', 'lon'];

// Coerce numeric-ish fields; keep everything else as-is.
function normalize(row) {
  const item = { ...row };
  for (const k of NUMERIC_FIELDS) {
    if (item[k] === '' || item[k] == null) {
      item[k] = null;
    } else {
      const n = Number(item[k]);
      item[k] = Number.isNaN(n) ? item[k] : n;
    }
  }
  return item;
}

// In-memory CRUD store seeded from the CSV. Writes never touch the source file,
// so tests can create/update/delete freely; reset() restores the seed.
class Store {
  constructor(csvPath = process.env.CONNECTIONS_CSV || DEFAULT_CSV) {
    this.csvPath = csvPath;
    this._seed = loadCsvObjects(csvPath).map(normalize);
    this.reset();
  }

  reset() {
    this.items = new Map();
    this._maxNum = 0;
    for (const row of this._seed) {
      this.items.set(row.id, { ...row });
      this._bumpCounter(row.id);
    }
  }

  // Keep the auto-id counter at/above the highest LC-#### id seen, so a later
  // auto-generated id never collides with an explicitly-created one.
  _bumpCounter(id) {
    const m = /^LC-(\d+)$/.exec(id || '');
    if (!m) return;
    const num = Number(m[1]);
    // Only advance for SAFE integers. A gigantic id (>= 2^53) must not poison
    // the counter: past MAX_SAFE_INTEGER, `_maxNum += 1` stops progressing and
    // nextId()'s dedup loop would spin forever, hanging the process.
    if (Number.isSafeInteger(num)) this._maxNum = Math.max(this._maxNum, num);
  }

  list({ type, neighborhood, city, q, limit, offset } = {}) {
    let arr = [...this.items.values()];
    const eq = (v, want) => String(v || '').toLowerCase() === String(want).toLowerCase();
    if (type) arr = arr.filter((i) => eq(i.type, type));
    if (neighborhood) arr = arr.filter((i) => eq(i.neighborhood, neighborhood));
    if (city) arr = arr.filter((i) => eq(i.city, city));
    if (q) {
      const needle = String(q).toLowerCase();
      arr = arr.filter(
        (i) =>
          String(i.name || '').toLowerCase().includes(needle) ||
          String(i.description || '').toLowerCase().includes(needle)
      );
    }
    const total = arr.length;
    const off = Number.isFinite(+offset) ? Math.max(0, Math.trunc(+offset)) : 0;
    const lim = Number.isFinite(+limit) && +limit >= 0 ? Math.trunc(+limit) : arr.length;
    const page = arr.slice(off, off + lim).map((i) => ({ ...i }));
    return { total, count: page.length, offset: off, limit: lim, items: page };
  }

  get(id) {
    const i = this.items.get(id);
    return i ? { ...i } : null;
  }

  nextId() {
    let id;
    do {
      this._maxNum += 1;
      id = 'LC-' + String(this._maxNum).padStart(4, '0');
    } while (this.items.has(id)); // defensive: never hand back an existing id
    return id;
  }

  create(data) {
    const id = data.id && String(data.id).trim() ? String(data.id).trim() : this.nextId();
    if (this.items.has(id)) {
      const e = new Error(`id ${id} already exists`);
      e.status = 409;
      throw e;
    }
    const item = normalize({ ...data, id });
    this.items.set(id, item);
    this._bumpCounter(id); // an explicit high LC id must advance the counter
    return { ...item };
  }

  replace(id, data) {
    if (!this.items.has(id)) return null;
    const item = normalize({ ...data, id });
    this.items.set(id, item);
    return { ...item };
  }

  update(id, patch) {
    const cur = this.items.get(id);
    if (!cur) return null;
    const item = normalize({ ...cur, ...patch, id });
    this.items.set(id, item);
    return { ...item };
  }

  remove(id) {
    return this.items.delete(id);
  }

  get size() {
    return this.items.size;
  }
}

module.exports = { Store, normalize };
