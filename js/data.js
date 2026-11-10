// data.js — CSV loading and parsing (RFC 4180-style, handles quotes/newlines).
export const CSV_PATH = 'data/sweep-2026-11-10.csv'; // relative: works under /<repo>/

export function parseCSV(text) {
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
      else f += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(f); f = ''; if (row.some(v => v !== '')) rows.push(row); row = [];
    } else f += c;
  }
  if (f !== '' || row.length) { row.push(f); if (row.some(v => v !== '')) rows.push(row); }
  const [head, ...body] = rows;
  return body.map(r => Object.fromEntries(head.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

export function locationBucket(loc) {
  const l = (loc || '').toLowerCase();
  if (!l || l === 'unknown') return 'unknown';
  if (l.includes('chicago') || l.includes('illinois')) return 'chicago-il';
  return 'other-us';
}

export async function loadLeads(path = CSV_PATH) {
  const res = await fetch(path, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`CSV fetch failed: ${res.status} ${path}`);
  return parseCSV(await res.text()).map(r => ({ ...r, locBucket: locationBucket(r.location) }));
}
