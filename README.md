# Boondock Echo Lead Desk

Static, read-only viewer for Boondock Echo lead and news sweeps.
Default search location is Chicago, Illinois, USA. The site never reads a phone or device location.

The public page is hosted on GitHub Pages and mirrored at the server copy. Every path is relative so both hosts work. Search engines are asked not to index the site (`noindex` and `robots.txt`).

Nothing here is posted, sent, liked or replied to. People do all outreach after they check the source.

## Live URLs

- GitHub Pages: https://vibhvesh.github.io/boondock-echo-lead-desk/
- Server mirror: https://radioleads.bowlinger.net

## Module map

### Site (static ES modules)

| File | Responsibility |
|---|---|
| `index.html` | Lead list shell, filters, Active/Archive tabs, CSV and Excel downloads |
| `admin.html` | Form for crawler instructions and search queries |
| `js/data.js` | Fetch `data/leads.json` and `data/archive.json`, location buckets, “new today” |
| `js/filters.js` | Filtering, counts, Chicago-first sort |
| `js/done.js` | Hide a lead in `localStorage` and open an `archive: <lead_id>` GitHub issue |
| `js/render.js` | Landscape cards, summary, errors |
| `js/main.js` | Wiring for filters, tabs and mark-done |
| `js/admin.js` | Load `config/search.json` and open a `search-config: update` issue |
| `css/style.css` | Landscape cards and admin layout |
| `config/search.json` | What the daily crawl should search for |
| `data/leads.json` | Active leads published from the Excel store |
| `data/archive.json` | Archived leads |
| `data/runs.json` | Crawl / publish log |
| `data/leads.xlsx` | Excel copy with `Active`, `Archive` and `Runs` sheets |
| `data/leads.csv` | Active-lead download |
| `robots.txt` + `noindex` | Ask search engines to skip the site |

### Python package (`leaddesk/`)

| Module | Responsibility |
|---|---|
| `models` | Lead fields, URL normalisation, `lead_id` (SHA-256 prefix of the normalised URL) |
| `store_excel` | Read and write `/workspace/boondock-leads/leads.xlsx` |
| `dedupe` | Exact-URL matches plus near-duplicate titles or quotes |
| `scoring` | Tiers Hot / Warm / Partner / News/Signal, freshness decay, stale after 90 days |
| `archive` | Move a lead to the Archive sheet from a trusted `archive:` issue |
| `config` | Load and validate `config/search.json`; apply a trusted `search-config` issue |
| `gh_issues` | Thin `gh` wrappers for issues, comments, close and collaborators |
| `authors` | Allow only `vibhvesh` or a repo collaborator |
| `ingest` | Add new JSON/CSV items into the workbook and copy the file to `raw/YYYY-MM-DD/` |
| `publish` | Export JSON/XLSX into `data/` and `exports/`, then commit and push |
| `cli` | `ingest`, `process-archive`, `process-config`, `publish`, `run-all` |

Master data lives in one folder, `/workspace/boondock-leads/`:

```
/workspace/boondock-leads/
  leads.xlsx
  config/search.json
  raw/YYYY-MM-DD/
  exports/
```

`publish` mirrors `leads.json`, `archive.json`, `runs.json` and `leads.xlsx` into this repo’s `data/` folder, and mirrors the search config into `config/search.json`.

## New-items JSON format

Save findings as `/workspace/boondock-leads/raw/YYYY-MM-DD/new_items.json`. A list of objects, or an object with an `items` / `leads` array. Never invent a quote, URL or contact.

Required fields: `source_url`, `title`.

```json
[
  {
    "tier": "Hot",
    "track": "Organisations and teams",
    "title": "Example 911 recorder replacement bid",
    "source_url": "https://example.gov/bids/recorder",
    "source_date": "10 Nov 2026",
    "location": "Chicago, Illinois, USA",
    "exact_quote": "The city will replace the current communications recorder.",
    "why_relevant": "Public buying signal for a radio recorder.",
    "next_step": "A rep should check the official portal.",
    "captured_at": "2026-11-10 09:10 Asia/Calcutta"
  }
]
```

Useful tracks: `Organisations and teams`, `Radio dealers and integrators`, `Individual hobbyists`, `News/Signals`.  
Useful tiers: `Hot`, `Warm`, `Partner`, `News/Signal` (add `(closed)` or `(stale)` when that is already known).

CSV with the same column names is also accepted.

Each stored lead gets a stable `lead_id` (a hash of the normalised URL), plus `found_at` and `status`.

## How a daily run reads the config

1. `process-config` looks at open GitHub issues labelled `search-config`.
2. It keeps only issues created by `vibhvesh` or a repository collaborator. Everyone else is ignored.
3. The newest valid issue is written to `config/search.json` (and copied under `/workspace/boondock-leads/config/search.json`), then commented on and closed.
4. The sweep agent reads that file: `instructions`, `queries` (organisations, dealers, hobbyists, news), `include_keywords`, `exclude_keywords`, `locations` (Chicago first), `sources.use` / `sources.skip`, and `minutes_per_run` (5–10).
5. It searches only those public sources for that many minutes, writes `raw/YYYY-MM-DD/new_items.json`, and does not contact anyone.
6. `run-all --new …` then ingests the file (skipping URL and near-duplicate titles), applies trusted `archive:` issues, exports the Excel store, and publishes the site.

## Daily command

After the day’s findings are saved (or with no `--new` file if the crawl found nothing):

```bash
cd /workspace/boondock-echo-lead-desk
.venv/bin/python -m leaddesk run-all --new /workspace/boondock-leads/raw/YYYY-MM-DD/new_items.json
```

Without new items:

```bash
.venv/bin/python -m leaddesk run-all
```

That command runs `process-config`, `process-archive`, optional `ingest`, then `publish`.

Other commands:

```bash
.venv/bin/python -m leaddesk ingest path/to/new_items.json
.venv/bin/python -m leaddesk process-archive
.venv/bin/python -m leaddesk process-config
.venv/bin/python -m leaddesk publish
```

## Mark done and admin

- **Mark done** hides the card immediately (browser `localStorage`) and opens a GitHub issue titled `archive: <lead_id>` with the `archive` label. `process-archive` moves that lead to the Archive sheet, sets `archived_at`, comments and closes the issue.
- **Admin** (`admin.html`) loads the current `config/search.json`. Save opens a GitHub issue titled `search-config: update` with the JSON in a code block. There is also an “Edit directly on GitHub” link. Sign in as `vibhvesh`. Changes from other accounts are ignored.

## Local preview

```bash
python3 -m http.server
```

Then open http://localhost:8000 (modules need `http`, not `file://`).

## Tests

```bash
.venv/bin/pytest -q
```
