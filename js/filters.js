// filters.js — pure filtering helpers.
export const unique = (items, key) => [...new Set(items.map(i => i[key]).filter(Boolean))];

export function applyFilters(items, { track = '', tier = '', loc = '', q = '' }) {
  const needle = q.trim().toLowerCase();
  return items.filter(i =>
    (!track || i.track === track) &&
    (!tier || i.tier === tier) &&
    (!loc || i.locBucket === loc) &&
    (!needle || Object.values(i).join(' ').toLowerCase().includes(needle)));
}

export function countBy(items, key) {
  return items.reduce((m, i) => (m[i[key]] = (m[i[key]] || 0) + 1, m), {});
}
