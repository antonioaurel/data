'use strict';

const fs = require('fs');

// Minimal RFC-4180-ish CSV parser: handles quoted fields, embedded commas,
// escaped quotes ("") and newlines inside quoted fields. Enough for the
// Conexões da História nodes.csv (quoted descriptions with commas).
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } // escaped quote
        else inQuotes = false;
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n') {
      row.push(field); rows.push(row); row = []; field = '';
    } else if (c === '\r') {
      // ignore CR (handles CRLF)
    } else {
      field += c;
    }
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

// Parse a CSV file into an array of plain objects keyed by the header row.
function loadCsvObjects(filePath) {
  const text = fs.readFileSync(filePath, 'utf8');
  const rows = parseCsv(text).filter((r) => !(r.length === 1 && r[0] === ''));
  const header = rows.shift();
  if (!header) return [];
  return rows.map((r) => {
    const obj = {};
    header.forEach((h, i) => { obj[h] = r[i] !== undefined ? r[i] : ''; });
    return obj;
  });
}

module.exports = { parseCsv, loadCsvObjects };
