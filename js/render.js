// render.js — DOM rendering only (uses textContent; no innerHTML of data).
import { countBy } from './filters.js';
import { isNewToday } from './data.js';
import { archiveIssueUrl, markDoneLocal } from './done.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const tierClass = t => 'tier-' + String(t || '').toLowerCase().split(/[\s(/]/)[0].replace(/[^a-z]/g, '');
const LOC_LABEL = { 'chicago-il': 'Chicago / IL', 'other-us': 'Other US', unknown: 'Unknown' };

export function fillSelect(select, values) {
  const current = select.value;
  while (select.options.length > 1) select.remove(1);
  values.forEach(v => select.append(new Option(v, v)));
  if ([...select.options].some(o => o.value === current)) select.value = current;
}

function block(title, counts) {
  const card = el('div', 'stat');
  card.append(el('h3', null, title));
  const ul = el('ul');
  Object.entries(counts).forEach(([k, n]) => { const li = el('li'); li.append(el('span', null, k), el('b', null, String(n))); ul.append(li); });
  card.append(ul); return card;
}

export function renderSummary(root, active, extra) {
  root.replaceChildren();
  const total = el('div', 'stat total');
  total.append(el('b', 'big', String(active.length)), el('span', null, 'active leads'));
  if (extra && extra.newToday) {
    total.append(el('span', 'new-pill', extra.newToday + ' new today'));
  }
  const tiers = countBy(active.map(i => ({ ...i, tierView: i.tier_label || i.tier })), 'tierView');
  const locs = Object.fromEntries(Object.entries(countBy(active, 'locBucket')).map(([k, v]) => [LOC_LABEL[k] || k, v]));
  root.append(total, block('By track', countBy(active, 'track')), block('By tier', tiers), block('By location', locs));
}

export function renderLastUpdated(node, label) {
  node.textContent = label ? ('Last updated ' + label) : 'Last updated: unknown';
}

function makeCard(item, { archived = false, onDone } = {}) {
  const card = el('article', 'card');
  const left = el('div', 'card-left');
  const tags = el('div', 'tags');
  tags.append(el('span', 'tag ' + tierClass(item.tier_label || item.tier), item.tier_label || item.tier));
  if (item.track) tags.append(el('span', 'tag track', item.track));
  if (isNewToday(item) && !archived) tags.append(el('span', 'tag new-pill', 'New today'));
  left.append(tags, el('p', 'meta-date', item.source_date || item.source_date_iso || ''));

  const mid = el('div', 'card-mid');
  const h = el('h2');
  const a = el('a', null, item.title);
  a.href = item.source_url; a.target = '_blank'; a.rel = 'noopener noreferrer';
  h.append(a);
  mid.append(h);
  if (item.exact_quote) mid.append(el('p', 'quote-line', item.exact_quote));
  if (item.why_relevant) mid.append(el('p', 'why', item.why_relevant));
  if (item.next_step) mid.append(el('p', 'next', 'Next: ' + item.next_step));

  const right = el('div', 'card-right');
  right.append(el('div', 'loc', item.location || 'Unknown location'));
  const actions = el('div', 'card-actions');
  const src = el('a', 'btn ghost', 'Source');
  src.href = item.source_url; src.target = '_blank'; src.rel = 'noopener noreferrer';
  actions.append(src);
  if (archived) {
    if (item.archived_at) right.append(el('p', 'meta-date', 'Archived ' + item.archived_at));
  } else {
    const done = el('button', 'btn done', 'Mark done');
    done.type = 'button';
    done.addEventListener('click', () => {
      markDoneLocal(item.lead_id);
      card.classList.add('leaving');
      window.open(archiveIssueUrl(item), '_blank', 'noopener,noreferrer');
      if (onDone) onDone(item.lead_id);
    });
    actions.append(done);
  }
  right.append(actions);
  card.append(left, mid, right);
  return card;
}

export function renderLeads(root, items, countEl, total, { archived = false, onDone } = {}) {
  root.replaceChildren();
  const label = archived ? 'archived' : 'active';
  countEl.textContent = `Showing ${items.length} of ${total} ${label}`;
  if (!items.length) {
    root.append(el('p', 'empty', archived ? 'No archived leads match these filters.' : 'No items match these filters.'));
    return;
  }
  for (const item of items) root.append(makeCard(item, { archived, onDone }));
}

export function renderError(root, err) {
  root.replaceChildren(el('p', 'empty', 'Could not load lead data: ' + err.message));
}

export function setTab(activeBtn, archiveBtn, mode) {
  const onActive = mode === 'active';
  activeBtn.classList.toggle('on', onActive);
  archiveBtn.classList.toggle('on', !onActive);
  activeBtn.setAttribute('aria-pressed', onActive ? 'true' : 'false');
  archiveBtn.setAttribute('aria-pressed', onActive ? 'false' : 'true');
}
