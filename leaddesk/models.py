"""Lead schema, URL normalisation, and lead_id hashing."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from leaddesk.paths import IST, IST_LABEL

# Canonical tiers stored in the workbook. Display labels may add (stale)/(closed).
TIERS = ("Hot", "Warm", "Partner", "News/Signal")

STATUS_ACTIVE = "active"
STATUS_ARCHIVE = "archive"

# CSV columns from the 10 Nov 2026 sweep, plus the three added fields.
CSV_COLUMNS = [
    "tier",
    "track",
    "title",
    "source_url",
    "source_date",
    "location",
    "exact_quote",
    "why_relevant",
    "next_step",
    "captured_at",
]

LEAD_FIELDS = [
    "lead_id",
    "status",
    "tier",
    "tier_label",
    "stale",
    "closed",
    "score",
    "track",
    "title",
    "source_url",
    "source_date",
    "source_date_iso",
    "location",
    "exact_quote",
    "why_relevant",
    "next_step",
    "captured_at",
    "found_at",
    "last_seen_at",
    "archived_at",
]

RUN_FIELDS = [
    "run_at",
    "command",
    "source_file",
    "ingested",
    "duplicates",
    "near_duplicates",
    "archived",
    "config_applied",
    "published",
    "error_count",
    "errors",
    "notes",
]

DROP_QUERY_KEYS = {"fbclid", "gclid", "ref", "ref_src", "ref_url"}

YES, NO = "yes", "no"


def now_ist() -> datetime:
    return datetime.now(IST)


def format_ist(dt: datetime | None) -> str:
    """Human timestamp in the user's zone, e.g. '10 Nov 2026, 09:40 Asia/Calcutta'."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    local = dt.astimezone(IST)
    return local.strftime("%d %b %Y, %H:%M ") + IST_LABEL


def iso_ist(dt: datetime | None = None) -> str:
    if dt is None:
        dt = now_ist()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt


def parse_captured_at(value: str | None) -> datetime | None:
    """Parse sweep timestamps like '2026-11-10 09:10 Asia/Calcutta'."""
    if not value:
        return None
    text = value.strip()
    dt = parse_iso(text)
    if dt:
        return dt
    m = re.match(
        r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?(?:\s+Asia/Calcutta)?$",
        text,
    )
    if m:
        sec = m.group(3) or "00"
        return datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}:{sec}").replace(tzinfo=IST)
    return None


def normalize_url(url: str) -> str:
    """Stable URL form used for lead_id and exact-URL dedupe."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    if netloc in {"twitter.com", "www.twitter.com"}:
        netloc = "x.com"
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in DROP_QUERY_KEYS and not k.lower().startswith("utm_")
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", urlencode(query_pairs), ""))


def lead_id_for(url: str) -> str:
    """16-char SHA-256 prefix of the normalised source URL."""
    normalised = normalize_url(url)
    if not normalised:
        raise ValueError("source_url is required to build a lead_id")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


def as_yes_no(value: Any) -> str:
    if value is True or str(value).strip().lower() in {"yes", "true", "1", "y"}:
        return YES
    return NO


def is_yes(value: Any) -> bool:
    return as_yes_no(value) == YES


def empty_lead() -> dict[str, Any]:
    return {key: "" for key in LEAD_FIELDS}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
