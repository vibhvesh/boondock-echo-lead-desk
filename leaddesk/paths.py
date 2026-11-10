"""Filesystem locations for the lead desk.

DATA_HOME (/workspace/boondock-leads by default) is the single home for
every crawl, the Excel workbook, exports and the mirrored search config.
REPO_ROOT is the GitHub Pages / mirror checkout.
Both can be overridden in tests with LEADDESK_HOME and LEADDESK_REPO.
"""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

def _ist() -> ZoneInfo:
    """Prefer Asia/Calcutta (the label this desk uses); fall back to Kolkata or a fixed offset."""
    for key in ("Asia/Calcutta", "Asia/Kolkata"):
        try:
            return ZoneInfo(key)
        except Exception:
            continue
    from datetime import timedelta, timezone
    return timezone(timedelta(hours=5, minutes=30))


IST = _ist()
IST_LABEL = "Asia/Calcutta"

DATA_HOME = Path(os.environ.get("LEADDESK_HOME", "/workspace/boondock-leads"))
REPO_ROOT = Path(
    os.environ.get(
        "LEADDESK_REPO",
        Path(__file__).resolve().parents[1],
    )
)

GITHUB_REPO = os.environ.get("LEADDESK_GITHUB_REPO", "vibhvesh/boondock-echo-lead-desk")
GITHUB_OWNER = "vibhvesh"


def workbook_path() -> Path:
    return DATA_HOME / "leads.xlsx"


def raw_dir(day: str) -> Path:
    return DATA_HOME / "raw" / day


def exports_dir() -> Path:
    return DATA_HOME / "exports"


def config_path_home() -> Path:
    return DATA_HOME / "config" / "search.json"


def config_path_repo() -> Path:
    return REPO_ROOT / "config" / "search.json"


def repo_data_dir() -> Path:
    return REPO_ROOT / "data"


def ensure_data_home() -> None:
    """Create the standard folders under DATA_HOME if they are missing."""
    for path in (
        DATA_HOME,
        DATA_HOME / "raw",
        DATA_HOME / "exports",
        DATA_HOME / "config",
    ):
        path.mkdir(parents=True, exist_ok=True)
