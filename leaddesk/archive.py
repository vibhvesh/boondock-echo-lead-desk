"""Move Active leads to Archive, driven by trusted `archive: <lead_id>` issues."""

from __future__ import annotations

import re
from typing import Any, Callable

from leaddesk.authors import is_allowed_author
from leaddesk.gh_issues import (
    close_issue,
    comment_on_issue,
    issue_author,
    list_collaborators,
    list_open_issues,
)
from leaddesk.models import STATUS_ARCHIVE, iso_ist
from leaddesk.paths import GITHUB_REPO
from leaddesk.store_excel import (
    SHEET_ACTIVE,
    SHEET_ARCHIVE,
    append_run,
    find_lead,
    load,
    save,
)

ARCHIVE_LABEL = "archive"
TITLE_RE = re.compile(r"^archive:\s*([0-9a-fA-F]{8,64})\s*$", re.I)


def parse_archive_title(title: str | None) -> str | None:
    if not title:
        return None
    match = TITLE_RE.match(title.strip())
    return match.group(1).lower() if match else None


def move_to_archive(
    store: dict[str, list[dict[str, Any]]],
    lead_id: str,
    archived_at: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Move a lead from Active to Archive. Idempotent if already archived.

    Returns ('archived', lead), ('already', lead), or ('missing', None).
    """
    when = archived_at or iso_ist()
    sheet, lead = find_lead(store, lead_id)
    if lead is None:
        return "missing", None
    if sheet == SHEET_ARCHIVE:
        if not lead.get("archived_at"):
            lead["archived_at"] = when
            lead["status"] = STATUS_ARCHIVE
        return "already", lead
    store[SHEET_ACTIVE] = [row for row in store[SHEET_ACTIVE] if row.get("lead_id") != lead_id]
    lead["status"] = STATUS_ARCHIVE
    lead["archived_at"] = when
    store.setdefault(SHEET_ARCHIVE, []).append(lead)
    return "archived", lead


def process_archive(
    *,
    issues: list[dict[str, Any]] | None = None,
    collaborators: list[str] | None = None,
    comment: Callable[[int, str], None] | None = None,
    close: Callable[[int], None] | None = None,
    repo: str = GITHUB_REPO,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply open `archive:` issues from the owner or a collaborator only."""
    store = load()
    errors: list[str] = []
    archived = 0
    skipped = 0
    already = 0

    if issues is None:
        try:
            issues = list_open_issues(ARCHIVE_LABEL, repo=repo)
        except Exception as exc:  # noqa: BLE001 — surface API errors in the run log
            errors.append(f"could not list archive issues: {exc}")
            issues = []
    if collaborators is None and not dry_run:
        try:
            collaborators = list_collaborators(repo=repo)
        except Exception as exc:  # noqa: BLE001
            collaborators = []
            errors.append(f"could not list collaborators (owner still allowed): {exc}")
    collaborators = collaborators or []

    do_comment = comment or (comment_on_issue if not dry_run else (lambda *a, **k: None))
    do_close = close or (close_issue if not dry_run else (lambda *a, **k: None))

    for issue in issues:
        number = issue.get("number")
        author = issue_author(issue)
        lead_id = parse_archive_title(issue.get("title") or "")
        if not is_allowed_author(author, collaborators):
            skipped += 1
            errors.append(f"issue #{number} ignored: author {author or '(unknown)'} is not the owner or a collaborator")
            continue
        if not lead_id:
            skipped += 1
            errors.append(f"issue #{number} ignored: title is not 'archive: <lead_id>'")
            continue
        when = iso_ist()
        status, lead = move_to_archive(store, lead_id, archived_at=when)
        if status == "missing":
            skipped += 1
            try:
                do_comment(number, f"Lead `{lead_id}` was not found in Active or Archive. Left open.")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"issue #{number}: found no lead, and comment failed: {exc}")
            continue
        verb = "Already archived" if status == "already" else "Archived"
        title = (lead or {}).get("title") or ""
        try:
            do_comment(number, f"{verb} `{lead_id}` ({title}) at {when} Asia/Calcutta.")
            do_close(number)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"issue #{number}: archived in the workbook but GitHub update failed: {exc}")
        if status == "archived":
            archived += 1
        else:
            already += 1

    result = {
        "run_at": iso_ist(),
        "command": "process-archive",
        "source_file": "",
        "ingested": 0,
        "duplicates": 0,
        "near_duplicates": 0,
        "archived": archived,
        "config_applied": "",
        "published": "",
        "error_count": len(errors),
        "errors": "; ".join(errors),
        "notes": f"archived={archived} already={already} skipped={skipped}",
    }
    append_run(store, result)
    save(store)
    return result
