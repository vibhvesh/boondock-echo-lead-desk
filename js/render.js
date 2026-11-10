// render.js — DOM rendering only (uses textContent; no innerHTML of data).
import { countBy } from './filters.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const tierClass = t => 'tier-' + t.toLowerCase().split(/[\s(/]/)[0].replace(/[^a-z]/g, '');
const LOC_LABEL = { 'chicago-il': 'Chicago / IL', 'other-us': 'Other US', unknown: 'Unknown' };

export function fillSelect(select, values) {
  values.forEach(v => select.append(new Option(v, v)));
}

function block(title, counts) {
  const card = el('div', 'stat');
  card.append(el('h3', null, title));
  const ul = el('ul');
  Object.entries(counts).forEach(([k, n]) => { const li = el('li'); li.append(el('span', null, k), el('b', null, String(n))); ul.append(li); });
  card.append(ul); return card;
}

export function renderSummary(root, items) {
  root.replaceChildren();
  const total = el('div', 'stat total'); total.append(el('b', 'big', String(items.length)), el('span', null, 'items in sweep'));
  const locs = Object.fromEntries(Object.entries(countBy(items, 'locBucket')).map(([k, v]) => [LOC_LABEL[k], v]));
  root.append(total, block('By track', countBy(items, 'track')), block('By tier', countBy(items, 'tier')), block('By location', locs));
}

function field(label, value) {
  if (!value) return null;
  const d = el('div', 'field'); d.append(el('dt', null, label), el('dd', null, value)); return d;
}

export function renderLeads(root, items, countEl, total) {
  root.replaceChildren();
  countEl.textContent = `Showing ${items.length} of ${total}`;
  if (!items.length) { root.append(el('p', 'empty', 'No items match these filters.')); return; }
  for (const i of items) {
    const card = el('article', 'card');
    const top = el('div', 'tags');
    top.append(el('span', 'tag ' + tierClass(i.tier), i.tier), el('span', 'tag track', i.track), el('span', 'tag loc', LOC_LABEL[i.locBucket]));
    const h = el('h2'); const a = el('a', null, i.title);
    a.href = i.source_url; a.target = '_blank'; a.rel = 'noopener noreferrer'; h.append(a);
    const meta = el('p', 'meta', `${i.location} · ${i.source_date}`);
    const quote = el('blockquote', null, i.exact_quote);
    const dl = el('dl');
    [field('Why relevant', i.why_relevant), field('Next step (human)', i.next_step)].forEach(f => f && dl.append(f));
    const src = el('a', 'src', 'Open source ↗'); src.href = i.source_url; src.target = '_blank'; src.rel = 'noopener noreferrer';
    const foot = el('div', 'cfoot'); foot.append(src, el('span', 'cap', 'Captured ' + i.captured_at));
    card.append(top, h, meta, quote, dl, foot); root.append(card);
  }
}

export function renderError(root, err) {
  root.replaceChildren(el('p', 'empty', 'Could not load sweep data: ' + err.message));
}
