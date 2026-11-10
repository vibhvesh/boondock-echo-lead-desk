// main.js — wiring: load data, populate filters, re-render on change.
import { loadLeads } from './data.js';
import { applyFilters, unique } from './filters.js';
import { fillSelect, renderSummary, renderLeads, renderError } from './render.js';

const $ = id => document.getElementById(id);
const ui = { track: $('f-track'), tier: $('f-tier'), loc: $('f-loc'), q: $('f-q') };

async function init() {
  let leads;
  try { leads = await loadLeads(); } catch (e) { renderError($('leads'), e); console.error(e); return; }
  fillSelect(ui.track, unique(leads, 'track'));
  fillSelect(ui.tier, unique(leads, 'tier'));
  renderSummary($('summary'), leads);
  const update = () => renderLeads($('leads'),
    applyFilters(leads, Object.fromEntries(Object.entries(ui).map(([k, e]) => [k, e.value]))),
    $('count'), leads.length);
  Object.values(ui).forEach(e => e.addEventListener('input', update));
  update();
}
init();
