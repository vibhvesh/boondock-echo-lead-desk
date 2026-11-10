// main.js — wiring: load data, tabs, filters, mark-done hide.
import { loadDesk, isNewToday } from './data.js';
import { applyFilters, unique, sortLeads } from './filters.js';
import { hiddenIds } from './done.js';
import { fillSelect, renderSummary, renderLeads, renderError, renderLastUpdated, setTab } from './render.js';

const $ = id => document.getElementById(id);
const ui = { track: $('f-track'), tier: $('f-tier'), loc: $('f-loc'), q: $('f-q') };

let desk = { active: [], archive: [], updated_at_ist: '' };
let mode = 'active';

function visibleActive() {
  const hidden = hiddenIds();
  return desk.active.filter(i => !hidden.has(String(i.lead_id)));
}

function visibleArchive() {
  const hidden = hiddenIds();
  const pending = desk.active.filter(i => hidden.has(String(i.lead_id)));
  const seen = new Set(desk.archive.map(i => i.lead_id));
  return desk.archive.concat(pending.filter(i => !seen.has(i.lead_id)));
}

function currentPool() {
  return mode === 'archive' ? visibleArchive() : visibleActive();
}

function paint() {
  const pool = currentPool();
  const shown = sortLeads(applyFilters(pool, Object.fromEntries(Object.entries(ui).map(([k, e]) => [k, e.value]))));
  renderLeads($('leads'), shown, $('count'), pool.length, {
    archived: mode === 'archive',
    onDone: () => paint(),
  });
  $('tab-active').textContent = `Active (${visibleActive().length})`;
  $('tab-archive').textContent = `Archive (${visibleArchive().length})`;
}

async function init() {
  try {
    desk = await loadDesk();
  } catch (e) {
    renderError($('leads'), e);
    console.error(e);
    return;
  }
  const active = visibleActive();
  const tierValues = unique(desk.active.concat(desk.archive).map(i => ({ t: i.tier_label || i.tier })), 't');
  const trackValues = unique(desk.active.concat(desk.archive), 'track');
  fillSelect(ui.track, trackValues);
  fillSelect(ui.tier, tierValues);
  renderSummary($('summary'), active, { newToday: active.filter(isNewToday).length });
  renderLastUpdated($('last-updated'), desk.updated_at_ist);
  Object.values(ui).forEach(e => e.addEventListener('input', paint));
  $('tab-active').addEventListener('click', () => { mode = 'active'; setTab($('tab-active'), $('tab-archive'), mode); paint(); });
  $('tab-archive').addEventListener('click', () => { mode = 'archive'; setTab($('tab-active'), $('tab-archive'), mode); paint(); });
  setTab($('tab-active'), $('tab-archive'), mode);
  paint();
}
init();
