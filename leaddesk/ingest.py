"""Ingest new items from a JSON (or CSV) file into the Excel workbook."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from leaddesk.dedupe import find_duplicate
from leaddesk.models import (
    STATUS_ACTIVE,
    clean_text,
    empty_lead,
    iso_ist,
    lead_id_for,
    now_ist,
    parse_captured_at,
)
from leaddesk.paths import ensure_data_home, raw_dir
from leaddesk.scoring import score_lead
from leaddesk.store_excel import SHEET_ACTIVE, all_leads, append_run, load, save

REQUIRED = ("source_url", "title")


def copy_to_raw(path: Path) -> Path:
    """Keep a dated copy of every ingested file under DATA_HOME/raw/YYYY-MM-DD/."""
    day = now_ist().strftime("%Y-%m-%d")
    dest_dir = raw_dir(day)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if path.resolve() != dest.resolve():
        shutil.copy2(path, dest)
    return dest


def load_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"new items file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "leads", "records"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError("JSON must be a list of items, or an object with an items/leads array")


def _found_at(item: dict[str, Any]) -> str:
    if clean_text(item.get("found_at")):
        return clean_text(item["found_at"])
    parsed = parse_captured_at(item.get("captured_at"))
    return iso_ist(parsed or now_ist())


def item_to_lead(item: dict[str, Any], as_of=None) -> dict[str, Any]:
    url = clean_text(item.get("source_url"))
    title = clean_text(item.get("title"))
    if not url or not title:
        missing = [name for name in REQUIRED if not clean_text(item.get(name))]
        raise ValueError(f"item is missing required fields: {', '.join(missing)}")

    lead = empty_lead()
    lead["source_url"] = url
    lead["title"] = title
    lead["lead_id"] = clean_text(item.get("lead_id")) or lead_id_for(url)
    lead["status"] = clean_text(item.get("status")) or STATUS_ACTIVE
    lead["track"] = clean_text(item.get("track"))
    lead["tier"] = clean_text(item.get("tier"))
    lead["source_date"] = clean_text(item.get("source_date"))
    lead["location"] = clean_text(item.get("location"))
    lead["exact_quote"] = clean_text(item.get("exact_quote"))
    lead["why_relevant"] = clean_text(item.get("why_relevant"))
    lead["next_step"] = clean_text(item.get("next_step"))
    lead["captured_at"] = clean_text(item.get("captured_at"))
    lead["found_at"] = _found_at(item)
    lead["last_seen_at"] = lead["found_at"]
    lead["archived_at"] = clean_text(item.get("archived_at"))
    score_lead(lead, as_of=as_of)
    return lead


def ingest(path: Path, as_of=None) -> dict[str, Any]:
    """Add new items to Active. Exact or near duplicates are skipped, never invented."""
    ensure_data_home()
    copy_to_raw(path)
    items = load_items(path)
    store = load()
    known = all_leads(store)
    added: list[dict[str, Any]] = []
    duplicates = 0
    near = 0
    errors: list[str] = []

    for index, item in enumerate(items, start=1):
        try:
            lead = item_to_lead(item, as_of=as_of)
        except (ValueError, TypeError) as exc:
            errors.append(f"item {index}: {exc}")
            continue
        kind, match = find_duplicate(lead, known)
        if kind == "url":
            duplicates += 1
            if match is not None:
                match["last_seen_at"] = lead["found_at"]
            continue
        if kind == "near":
            near += 1
            continue
        lead["status"] = STATUS_ACTIVE
        store[SHEET_ACTIVE].append(lead)
        known.append(lead)
        added.append(lead)

    result = {
        "run_at": iso_ist(),
        "command": "ingest",
        "source_file": str(path),
        "ingested": len(added),
        "duplicates": duplicates,
        "near_duplicates": near,
        "archived": 0,
        "config_applied": "",
        "published": "",
        "error_count": len(errors),
        "errors": "; ".join(errors),
        "notes": f"added {len(added)} of {len(items)} items",
        "added_ids": [row["lead_id"] for row in added],
    }
    append_run(store, result)
    save(store)
    return result
