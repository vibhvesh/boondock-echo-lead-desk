from datetime import date

from leaddesk.scoring import (
    STALE_AFTER_DAYS,
    freshness_factor,
    latest_source_date,
    parse_tier,
    score_lead,
)


def test_parse_tier_hints():
    assert parse_tier("Hot (stale)") == ("Hot", False, True)
    assert parse_tier("Hot (closed)") == ("Hot", True, False)
    assert parse_tier("Warm (stale)") == ("Warm", False, True)
    assert parse_tier("News/Signal") == ("News/Signal", False, False)
    assert parse_tier("Partner") == ("Partner", False, False)


def test_latest_source_date_prefers_due_date():
    text = "Posted 29 Mar 2026; due 14 Apr 2026 (expired before this sweep)"
    assert latest_source_date(text) == date(2026, 4, 14)


def test_about_month_uses_first_of_month():
    assert latest_source_date("About Oct 2026 (page said “1mo ago”)") == date(2026, 10, 1)


def test_stale_after_90_days():
    as_of = date(2026, 11, 10)
    stale = score_lead({"tier": "Hot", "source_date": "5 Aug 2026"}, as_of=as_of)
    assert stale["stale"] == "yes"
    assert stale["tier"] == "Hot"
    assert stale["tier_label"] == "Hot (stale)"
    assert (as_of - date(2026, 8, 5)).days > STALE_AFTER_DAYS

    fresh = score_lead({"tier": "Hot", "source_date": "8 Nov 2026"}, as_of=as_of)
    assert fresh["stale"] == "no"
    assert fresh["tier_label"] == "Hot"
    assert fresh["score"] == 90


def test_closed_label_wins_over_stale():
    lead = score_lead({"tier": "Hot (closed)", "source_date": "8 Sep 2025"}, as_of=date(2026, 11, 10))
    assert lead["closed"] == "yes"
    assert lead["stale"] == "yes"
    assert lead["tier_label"] == "Hot (closed)"


def test_freshness_decay_between_week_and_90_days():
    assert freshness_factor(0) == 1.0
    assert freshness_factor(7) == 1.0
    mid = freshness_factor(48)
    assert 0.3 < mid < 1.0
    assert freshness_factor(90) == 0.2
    hot = score_lead({"tier": "Hot", "source_date": "22 Sep 2026"}, as_of=date(2026, 11, 10))
    assert hot["stale"] == "no"
    assert hot["score"] < 90
    assert hot["score"] > 30


def test_undated_page_is_not_auto_stale():
    lead = score_lead({"tier": "Partner", "source_date": "Undated page; captured 10 Nov 2026"}, as_of=date(2026, 11, 10))
    assert lead["stale"] == "no"
    assert lead["source_date_iso"] == "" or lead["source_date_iso"] == "2026-11-10"
    # "10 Nov 2026" is parseable from that string — captured date may be picked up.
    # An explicitly empty / non-date string must not be stale:
    empty = score_lead({"tier": "Partner", "source_date": "Undated page"}, as_of=date(2026, 11, 10))
    assert empty["stale"] == "no"
    assert empty["score"] == 50
