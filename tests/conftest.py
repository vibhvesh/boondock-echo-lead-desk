"""Shared fixtures: isolated DATA_HOME / REPO_ROOT for every test."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def desk(tmp_path, monkeypatch):
    home = tmp_path / "data-home"
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "config").mkdir(parents=True)
    (home / "raw").mkdir(parents=True)
    (home / "exports").mkdir(parents=True)
    (home / "config").mkdir(parents=True)
    (repo / ".git").mkdir()
    monkeypatch.setenv("LEADDESK_HOME", str(home))
    monkeypatch.setenv("LEADDESK_REPO", str(repo))
    # Reload path constants that were imported at module load time.
    import leaddesk.paths as paths

    monkeypatch.setattr(paths, "DATA_HOME", home)
    monkeypatch.setattr(paths, "REPO_ROOT", repo)
    import leaddesk.store_excel as store_excel
    import leaddesk.publish as publish
    import leaddesk.config as config
    import leaddesk.ingest as ingest
    import leaddesk.archive as archive

    monkeypatch.setattr(store_excel, "workbook_path", lambda: home / "leads.xlsx")
    monkeypatch.setattr(publish, "REPO_ROOT", repo)
    monkeypatch.setattr(config, "REPO_ROOT", repo)
    return {"home": home, "repo": repo}


@pytest.fixture
def sample_item():
    return {
        "tier": "Hot",
        "track": "Organisations and teams",
        "title": "Chicago 911 recorder replacement bid",
        "source_url": "https://example.com/bids/911-recorder",
        "source_date": "1 Nov 2026",
        "location": "Chicago, Illinois, USA",
        "exact_quote": "The city will replace the current communications recorder.",
        "why_relevant": "Public buying signal for a radio recorder.",
        "next_step": "A rep should check the official portal.",
        "captured_at": "2026-11-10 09:10 Asia/Calcutta",
        "found_at": "2026-11-10T09:10:00+05:30",
        "status": "active",
    }
