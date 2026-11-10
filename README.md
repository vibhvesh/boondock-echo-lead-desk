# Boondock Echo Lead Desk

Static, read-only viewer for Boondock Echo lead & news sweeps (default location Chicago, IL).
No build step: plain HTML, CSS and vanilla ES modules, hosted on GitHub Pages.
Everything is read-only research; all outreach is human-reviewed only.

## Module layout
| File | Responsibility |
|---|---|
| `index.html` | Page shell, filter controls, loads `js/main.js` as a module |
| `js/data.js` | Fetch + parse the CSV (relative path, works under `/<repo>/`), location bucketing |
| `js/filters.js` | Pure helpers: unique values, filtering, counts |
| `js/render.js` | DOM rendering for summary, cards, errors (uses `textContent`) |
| `js/main.js` | Wiring: load data, populate filters, re-render on input |
| `css/style.css` | Responsive styles |
| `data/sweep-2026-11-10.csv` | Sweep data (14 items), also offered as a download |
| `robots.txt` + `noindex` meta | Ask search engines to skip the site |

## Adding a new sweep
Drop the new CSV in `data/`, then update `CSV_PATH` in `js/data.js` and the download link in `index.html`.

## Local preview
`python3 -m http.server` then open http://localhost:8000 (modules need http, not file://).
