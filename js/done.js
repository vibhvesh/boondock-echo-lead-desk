// done.js — local hide + GitHub issue used to archive a lead.
const STORAGE_KEY = 'leaddesk:done';
export const ISSUE_REPO = 'https://github.com/vibhvesh/boondock-echo-lead-desk';

export function hiddenIds() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return new Set(Array.isArray(raw) ? raw.map(String) : []);
  } catch {
    return new Set();
  }
}

export function markDoneLocal(leadId) {
  const ids = hiddenIds();
  ids.add(String(leadId));
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
  return ids;
}

export function archiveIssueUrl(lead) {
  const id = lead.lead_id || '';
  const title = `archive: ${id}`;
  const body = [
    'Please archive this lead on the next daily run.',
    '',
    `- **lead_id:** \`${id}\``,
    `- **Title:** ${lead.title || ''}`,
    `- **URL:** ${lead.source_url || ''}`,
    '',
    'Opened from the Lead Desk “Mark done” button.',
  ].join('\n');
  const params = new URLSearchParams({ title, labels: 'archive', body });
  return `${ISSUE_REPO}/issues/new?${params.toString()}`;
}
