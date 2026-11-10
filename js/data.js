// data.js — load published JSON snapshots (relative paths work on Pages and the mirror).
export const LEADS_JSON = 'data/leads.json';
export const ARCHIVE_JSON = 'data/archive.json';

export function locationBucket(loc) {
  const l = (loc || '').toLowerCase();
  if (!l || l === 'unknown') return 'unknown';
  if (l.includes('chicago') || l.includes('illinois')) return 'chicago-il';
  return 'other-us';
}

function decorate(row) {
  return { ...row, locBucket: locationBucket(row.location) };
}

export function todayIST() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Calcutta' });
}

export function isNewToday(lead) {
  const raw = String(lead.found_at || lead.captured_at || lead.source_date_iso || '');
  const day = raw.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) && day === todayIST();
}

async function fetchJson(path) {
  const res = await fetch(path, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export async function loadDesk() {
  const leadsData = await fetchJson(LEADS_JSON);
  let archiveData = { leads: [], updated_at: '', updated_at_ist: '', count: 0 };
  try {
    archiveData = await fetchJson(ARCHIVE_JSON);
  } catch (err) {
    console.warn('archive.json missing', err);
  }
  return {
    updated_at: leadsData.updated_at || '',
    updated_at_ist: leadsData.updated_at_ist || '',
    active: (leadsData.leads || []).map(decorate),
    archive: (archiveData.leads || []).map(decorate),
  };
}
