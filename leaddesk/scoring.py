"""Tier normalisation, 90-day stale flag, and freshness-decayed scores."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from leaddesk.models import TIERS, as_yes_no, clean_text, is_yes
from leaddesk.paths import IST

BASE_SCORES = {
    "Hot": 90,
    "Warm": 60,
    "Partner": 50,
    "News/Signal": 30,
}

STALE_AFTER_DAYS = 90
FRESH_DAYS = 7
FRESH_MIN = 0.3  # score multiplier at the 90-day mark
STALE_FACTOR = 0.2

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_tier(raw: str | None) -> tuple[str, bool, bool]:
    """Return (canonical tier, closed_hint, stale_hint) from a free-text tier."""
    text = clean_text(raw)
    lower = text.lower()
    closed = "closed" in lower
    stale_hint = "stale" in lower
    if lower.startswith("news") or "signal" in lower:
        tier = "News/Signal"
    elif lower.startswith("partner"):
        tier = "Partner"
    elif lower.startswith("warm"):
        tier = "Warm"
    elif lower.startswith("hot"):
        tier = "Hot"
    elif text in TIERS:
        tier = text
    else:
        tier = "News/Signal"
    return tier, closed, stale_hint


def _month_date(month: str, year: int, day: int = 1) -> date | None:
    num = MONTHS.get(month.lower())
    if not num:
        return None
    try:
        return date(year, num, day)
    except ValueError:
        return None


def parse_source_dates(source_date: str | None) -> list[date]:
    """Extract calendar dates from messy source_date strings. Never invents a date."""
    text = clean_text(source_date)
    if not text:
        return []
    found: list[date] = []

    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})(?:[T\s]\d{2}:\d{2})?", text):
        try:
            found.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue

    # 5 Aug 2026 / 29 Mar 2026 / 22 Sep 2026
    for m in re.finditer(
        r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b",
        text,
        re.I,
    ):
        parsed = _month_date(m.group(2), int(m.group(3)), int(m.group(1)))
        if parsed:
            found.append(parsed)

    # About Oct 2026 / About Nov 2025 — first of the named month (conservative).
    for m in re.finditer(
        r"\b(?:about|circa|around)?\s*"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b",
        text,
        re.I,
    ):
        parsed = _month_date(m.group(1), int(m.group(2)), 1)
        if parsed:
            found.append(parsed)

    # de-dupe, keep order
    seen: set[date] = set()
    unique: list[date] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def latest_source_date(source_date: str | None) -> date | None:
    dates = parse_source_dates(source_date)
    return max(dates) if dates else None


def freshness_factor(days_old: int | None) -> float:
    if days_old is None:
        return 1.0
    if days_old <= FRESH_DAYS:
        return 1.0
    if days_old >= STALE_AFTER_DAYS:
        return STALE_FACTOR
    span = STALE_AFTER_DAYS - FRESH_DAYS
    progress = (days_old - FRESH_DAYS) / span
    return 1.0 - progress * (1.0 - FRESH_MIN)


def days_between(when: date, as_of: date) -> int:
    return (as_of - when).days


def as_of_date(as_of: date | datetime | None = None) -> date:
    if as_of is None:
        return datetime.now(IST).date()
    if isinstance(as_of, datetime):
        return as_of.astimezone(IST).date() if as_of.tzinfo else as_of.date()
    return as_of


def tier_label(tier: str, stale: bool, closed: bool) -> str:
    if closed:
        return f"{tier} (closed)"
    if stale and tier in {"Hot", "Warm"}:
        return f"{tier} (stale)"
    return tier


def score_lead(lead: dict[str, Any], as_of: date | datetime | None = None) -> dict[str, Any]:
    """Fill tier, stale, score and tier_label on a lead dict. Returns the same dict."""
    today = as_of_date(as_of)
    incoming = clean_text(lead.get("tier") or lead.get("tier_label"))
    tier, closed_hint, stale_hint = parse_tier(incoming)
    closed = is_yes(lead.get("closed")) or closed_hint

    iso = clean_text(lead.get("source_date_iso"))
    source_day: date | None = None
    if iso:
        try:
            source_day = date.fromisoformat(iso[:10])
        except ValueError:
            source_day = None
    if source_day is None:
        source_day = latest_source_date(lead.get("source_date"))
    lead["source_date_iso"] = source_day.isoformat() if source_day else clean_text(lead.get("source_date_iso"))

    days_old = days_between(source_day, today) if source_day else None
    stale = bool(source_day and days_old is not None and days_old > STALE_AFTER_DAYS)
    if stale_hint and source_day is None:
        # Keep an explicit incoming stale flag only when we have no date to judge.
        stale = True

    factor = freshness_factor(days_old)
    score = round(BASE_SCORES[tier] * factor, 1)

    lead["tier"] = tier
    lead["closed"] = as_yes_no(closed)
    lead["stale"] = as_yes_no(stale)
    lead["score"] = score
    lead["tier_label"] = tier_label(tier, stale, closed)
    return lead


def is_stale_as_of(source_date: str | None, as_of: date | datetime | None = None) -> bool:
    day = latest_source_date(source_date)
    if day is None:
        return False
    return days_between(day, as_of_date(as_of)) > STALE_AFTER_DAYS
