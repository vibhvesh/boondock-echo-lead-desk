// admin.js — load config/search.json and open a prefilled search-config issue.
const CONFIG_PATH = 'config/search.json';
const ISSUE_REPO = 'https://github.com/vibhvesh/boondock-echo-lead-desk';
const TRACKS = ['organisations', 'dealers', 'hobbyists', 'news'];

const $ = id => document.getElementById(id);

function lines(text) {
  return String(text || '').split(/\n/).map(s => s.trim()).filter(Boolean);
}

function fillArea(id, values) {
  $(id).value = (values || []).join('\n');
}

function readForm() {
  return {
    instructions: $('instructions').value.trim(),
    queries: {
      organisations: lines($('q-organisations').value),
      dealers: lines($('q-dealers').value),
      hobbyists: lines($('q-hobbyists').value),
      news: lines($('q-news').value),
    },
    include_keywords: lines($('include_keywords').value),
    exclude_keywords: lines($('exclude_keywords').value),
    locations: lines($('locations').value),
    sources: {
      use: lines($('sources-use').value),
      skip: lines($('sources-skip').value),
    },
    minutes_per_run: Number($('minutes_per_run').value),
  };
}

function populate(config) {
  $('instructions').value = config.instructions || '';
  TRACKS.forEach(track => fillArea('q-' + track, (config.queries || {})[track]));
  fillArea('include_keywords', config.include_keywords);
  fillArea('exclude_keywords', config.exclude_keywords);
  fillArea('locations', config.locations);
  fillArea('sources-use', (config.sources || {}).use);
  fillArea('sources-skip', (config.sources || {}).skip);
  $('minutes_per_run').value = config.minutes_per_run ?? 8;
}

function issueUrl(config) {
  const json = JSON.stringify(config, null, 2);
  const body = [
    'Please apply this search config on the next daily run.',
    '',
    '```json',
    json,
    '```',
    '',
    'Opened from the Lead Desk admin page.',
  ].join('\n');
  const params = new URLSearchParams({
    title: 'search-config: update',
    labels: 'search-config',
    body,
  });
  return `${ISSUE_REPO}/issues/new?${params.toString()}`;
}

async function init() {
  const status = $('admin-status');
  const form = $('admin-form');
  const error = $('admin-error');
  try {
    const res = await fetch(CONFIG_PATH, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Could not load ${CONFIG_PATH} (${res.status})`);
    const config = await res.json();
    populate(config);
    const when = config.updated_at || '';
    status.textContent = when
      ? `Loaded current config (updated ${when}).`
      : 'Loaded current config.';
    form.hidden = false;
  } catch (err) {
    status.textContent = 'Could not load the search config.';
    error.hidden = false;
    error.textContent = err.message;
    return;
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    const config = readForm();
    if (!config.minutes_per_run || config.minutes_per_run < 5 || config.minutes_per_run > 10) {
      status.textContent = 'Minutes per run must be an integer from 5 to 10.';
      return;
    }
    const total = TRACKS.reduce((n, t) => n + config.queries[t].length, 0);
    if (!total) {
      status.textContent = 'Add at least one search query across the four tracks.';
      return;
    }
    window.open(issueUrl(config), '_blank', 'noopener,noreferrer');
    status.textContent = 'Opened a GitHub issue. Sign in as vibhvesh so the next daily run will apply it.';
  });
}
init();
