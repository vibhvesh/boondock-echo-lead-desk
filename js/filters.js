// filters.js — pure filtering and sorting helpers.
export const unique = (items, key) => [...new Set(items.map(i => i[key]).filter(Boolean))];

export function applyFilters(items, { track = '', tier = '', loc = '', q = '' }) {
  const needle = q.trim().toLowerCase();
  return items.filter(i =>
    (!track || i.track === track) &&
    (!tier || (i.tier_label || i.tier) === tier || i.tier === tier) &&
    (!loc || i.locBucket === loc) &&
    (!needle || Object.values(i).join(' ').toLowerCase().includes(needle)));
}

export function countBy(items, key) {
  return items.reduce((m, i) => (m[i[key]] = (m[i[key]] || 0) + 1, m), {});
}

const LOC_RANK = { 'chicago-il': 0, 'other-us': 1, unknown: 2 };

export function sortLeads(items) {
  return [...items].sort((a, b) => {
    const loc = (LOC_RANK[a.locBucket] ?? 9) - (LOC_RANK[b.locBucket] ?? 9);
    if (loc) return loc;
    const score = (Number(b.score) || 0) - (Number(a.score) || 0);
    if (score) return score;
    return String(b.source_date_iso || '').localeCompare(String(a.source_date_iso || ''));
  });
}
