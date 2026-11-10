from leaddesk.archive import move_to_archive, parse_archive_title, process_archive
from leaddesk.ingest import ingest
from leaddesk.store_excel import SHEET_ACTIVE, SHEET_ARCHIVE, find_lead, load


def _write_items(desk, items, name="new_items.json"):
    import json

    path = desk["home"] / name
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def test_parse_archive_title():
    assert parse_archive_title("archive: abcdef0123456789") == "abcdef0123456789"
    assert parse_archive_title("archive: ABCDEF0123456789") == "abcdef0123456789"
    assert parse_archive_title("Please archive this") is None
    assert parse_archive_title("search-config: update") is None


def test_move_to_archive_moves_and_is_idempotent(desk, sample_item):
    ingest(_write_items(desk, [sample_item]))
    store = load()
    assert len(store[SHEET_ACTIVE]) == 1
    lead_id = store[SHEET_ACTIVE][0]["lead_id"]
    status, lead = move_to_archive(store, lead_id, archived_at="2026-11-10T10:00:00+05:30")
    assert status == "archived"
    assert lead["status"] == "archive"
    assert lead["archived_at"] == "2026-11-10T10:00:00+05:30"
    assert store[SHEET_ACTIVE] == []
    assert len(store[SHEET_ARCHIVE]) == 1

    again, same = move_to_archive(store, lead_id, archived_at="2026-11-11T10:00:00+05:30")
    assert again == "already"
    assert same["archived_at"] == "2026-11-10T10:00:00+05:30"
    assert find_lead(store, lead_id)[0] == SHEET_ARCHIVE


def test_process_archive_trusted_issue(desk, sample_item):
    ingest(_write_items(desk, [sample_item]))
    store = load()
    lead_id = store[SHEET_ACTIVE][0]["lead_id"]
    comments = []
    closed = []

    def comment(number, body):
        comments.append((number, body))

    def close(number):
        closed.append(number)

    result = process_archive(
        issues=[
            {
                "number": 7,
                "title": f"archive: {lead_id}",
                "body": "please archive",
                "author": {"login": "vibhvesh"},
            }
        ],
        collaborators=["vibhvesh"],
        comment=comment,
        close=close,
        dry_run=True,
    )
    assert result["archived"] == 1
    assert closed == [7]
    assert comments and lead_id in comments[0][1]
    store = load()
    assert store[SHEET_ACTIVE] == []
    assert store[SHEET_ARCHIVE][0]["lead_id"] == lead_id
    assert store[SHEET_ARCHIVE][0]["archived_at"]


def test_process_archive_ignores_strangers(desk, sample_item):
    ingest(_write_items(desk, [sample_item]))
    store = load()
    lead_id = store[SHEET_ACTIVE][0]["lead_id"]
    comments, closed = [], []
    result = process_archive(
        issues=[
            {
                "number": 9,
                "title": f"archive: {lead_id}",
                "author": {"login": "random-spammer"},
            }
        ],
        collaborators=["alice"],
        comment=lambda n, b: comments.append((n, b)),
        close=lambda n: closed.append(n),
        dry_run=True,
    )
    assert result["archived"] == 0
    assert closed == []
    assert comments == []
    assert "ignored" in result["errors"]
    store = load()
    assert len(store[SHEET_ACTIVE]) == 1
