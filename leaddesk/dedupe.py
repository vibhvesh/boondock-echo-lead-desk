"""Exact-URL and near-duplicate (title / quote) matching."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable

from leaddesk.models import clean_text, lead_id_for, normalize_url

DEFAULT_THRESHOLD = 0.85


def normalize_text(value: str | None) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similar(a: str | None, b: str | None, threshold: float = DEFAULT_THRESHOLD) -> bool:
    left, right = normalize_text(a), normalize_text(b)
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


def same_url(a: str | None, b: str | None) -> bool:
    left, right = normalize_url(a or ""), normalize_url(b or "")
    return bool(left) and left == right


def is_near_duplicate(new: dict[str, Any], existing: dict[str, Any], threshold: float = DEFAULT_THRESHOLD) -> bool:
    """True when titles or exact quotes are near-duplicates."""
    if similar(new.get("title"), existing.get("title"), threshold):
        return True
    new_quote = clean_text(new.get("exact_quote"))
    old_quote = clean_text(existing.get("exact_quote"))
    if new_quote and old_quote and similar(new_quote, old_quote, threshold):
        return True
    return False


def find_duplicate(
    item: dict[str, Any],
    existing: Iterable[dict[str, Any]],
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[str | None, dict[str, Any] | None]:
    """Return ('url'|'near', match) or (None, None). URL matches win."""
    try:
        new_id = item.get("lead_id") or lead_id_for(item.get("source_url") or "")
    except ValueError:
        new_id = ""
    new_url = normalize_url(item.get("source_url") or "")

    for row in existing:
        if new_id and row.get("lead_id") == new_id:
            return "url", row
        if new_url and normalize_url(row.get("source_url") or "") == new_url:
            return "url", row

    for row in existing:
        if is_near_duplicate(item, row, threshold):
            return "near", row
    return None, None
