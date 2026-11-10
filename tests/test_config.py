from leaddesk.authors import is_allowed_author
from leaddesk.config import (
    DEFAULT_LOCATIONS,
    extract_json_block,
    process_config,
    validate_search_config,
    write_config,
)


VALID = {
    "instructions": "Focus on 911 recorder RFPs in Illinois.",
    "queries": {
        "organisations": ["Chicago 911 recorder RFP"],
        "dealers": ["Motorola dealer Chicago"],
        "hobbyists": ["transcribe ham radio Whisper"],
        "news": ["Chicago OEMC 911"],
    },
    "include_keywords": ["audio logger", "communications recorder"],
    "exclude_keywords": ["FM broadcast"],
    "locations": ["Chicago, Illinois, USA", "United States"],
    "sources": {"use": ["government bid boards"], "skip": ["direct messages"]},
    "minutes_per_run": 8,
}


def test_valid_config_normalises():
    ok, errors, normalised = validate_search_config(VALID)
    assert ok, errors
    assert normalised["minutes_per_run"] == 8
    assert normalised["queries"]["organisations"] == ["Chicago 911 recorder RFP"]
    assert "audio logger" in normalised["include_keywords"]


def test_minutes_must_be_5_to_10():
    for value in (4, 11, 8.5, "8", True):
        payload = dict(VALID, minutes_per_run=value)
        ok, errors, normalised = validate_search_config(payload)
        assert not ok and normalised is None
        assert any("minutes_per_run" in e for e in errors)

    for value in (5, 10):
        ok, errors, _ = validate_search_config(dict(VALID, minutes_per_run=value))
        assert ok, errors


def test_empty_locations_default_to_chicago_then_us():
    payload = dict(VALID, locations=[])
    ok, errors, normalised = validate_search_config(payload)
    assert ok, errors
    assert normalised["locations"] == DEFAULT_LOCATIONS


def test_missing_queries_fail():
    payload = dict(VALID, queries={"organisations": [], "dealers": [], "hobbyists": [], "news": []})
    ok, errors, _ = validate_search_config(payload)
    assert not ok
    assert any("at least one search query" in e for e in errors)


def test_unknown_fields_rejected():
    ok, errors, _ = validate_search_config(dict(VALID, shell="rm -rf /"))
    assert not ok
    assert any("unknown fields" in e for e in errors)


def test_extract_json_from_fenced_block():
    body = "Please apply this.\n\n```json\n" + __import__("json").dumps(VALID) + "\n```\n"
    assert extract_json_block(body)["minutes_per_run"] == 8
    assert extract_json_block("not json at all") is None


def test_allowed_author():
    assert is_allowed_author("vibhvesh", [])
    assert is_allowed_author("Vibhvesh", ["alice"])
    assert is_allowed_author("alice", ["alice", "bob"])
    assert is_allowed_author("@alice", ["Alice"])
    assert not is_allowed_author("random-spammer", ["alice"])
    assert not is_allowed_author("", ["vibhvesh"])
    assert not is_allowed_author(None, ["vibhvesh"])
    assert not is_allowed_author("dependabot", [])


def test_process_config_applies_newest_trusted_issue(desk):
    comments, closed, commits = [], [], []

    older = {
        "number": 1,
        "title": "search-config: update",
        "createdAt": "2026-11-09T10:00:00Z",
        "author": {"login": "vibhvesh"},
        "body": "```json\n" + __import__("json").dumps(dict(VALID, minutes_per_run=5)) + "\n```",
    }
    newer = {
        "number": 2,
        "title": "search-config: update",
        "createdAt": "2026-11-10T10:00:00Z",
        "author": {"login": "vibhvesh"},
        "body": "```json\n" + __import__("json").dumps(dict(VALID, minutes_per_run=9)) + "\n```",
    }
    result = process_config(
        issues=[older, newer],
        collaborators=["vibhvesh"],
        comment=lambda n, b: comments.append((n, b)),
        close=lambda n: closed.append(n),
        commit=lambda msg: commits.append(msg) or "abc123",
        dry_run=True,
    )
    assert result["config_applied"].startswith("issue #2")
    assert closed == [2]
    assert commits
    from leaddesk.config import read_config

    assert read_config()["minutes_per_run"] == 9


def test_process_config_ignores_untrusted_author(desk):
    comments, closed = [], []
    result = process_config(
        issues=[
            {
                "number": 4,
                "title": "search-config: update",
                "createdAt": "2026-11-10T12:00:00Z",
                "author": {"login": "not-vibhvesh"},
                "body": "```json\n" + __import__("json").dumps(VALID) + "\n```",
            }
        ],
        collaborators=["alice"],
        comment=lambda n, b: comments.append((n, b)),
        close=lambda n: closed.append(n),
        commit=lambda msg: "nope",
        dry_run=True,
    )
    assert result["config_applied"] == ""
    assert closed == []
    assert comments == []
    assert "ignored" in result["errors"]
