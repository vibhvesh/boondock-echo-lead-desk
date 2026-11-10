"""Search-config schema, validation, and process-config (trusted issues only)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Callable

from leaddesk.authors import is_allowed_author
from leaddesk.gh_issues import (
    close_issue,
    comment_on_issue,
    issue_author,
    list_collaborators,
    list_open_issues,
)
from leaddesk.models import iso_ist, now_ist
from leaddesk.paths import (
    GITHUB_REPO,
    REPO_ROOT,
    config_path_home,
    config_path_repo,
    ensure_data_home,
)
from leaddesk.store_excel import append_run, load, save

CONFIG_LABEL = "search-config"
TITLE_PREFIX = "search-config:"
QUERY_TRACKS = ("organisations", "dealers", "hobbyists", "news")
MIN_MINUTES = 5
MAX_MINUTES = 10

DEFAULT_LOCATIONS = ["Chicago, Illinois, USA", "Illinois, USA", "United States"]

REQUIRED_TOP = ("instructions", "queries", "include_keywords", "exclude_keywords", "locations", "sources", "minutes_per_run")


def default_config() -> dict[str, Any]:
    return {
        "instructions": "",
        "queries": {track: [] for track in QUERY_TRACKS},
        "include_keywords": [],
        "exclude_keywords": [],
        "locations": list(DEFAULT_LOCATIONS),
        "sources": {"use": [], "skip": []},
        "minutes_per_run": 8,
        "updated_at": "",
    }


def _as_str_list(value: Any, field: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [line.strip() for line in re.split(r"[\n,]+", value) if line.strip()]
        return items
    if not isinstance(value, list):
        errors.append(f"{field} must be a list of strings")
        return []
    items: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"{field}[{i}] must be a string")
            continue
        text = item.strip()
        if text:
            items.append(text)
    return items


def validate_search_config(data: Any) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Return (ok, errors, normalised config). Does not invent queries or keywords."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ["config must be a JSON object"], None

    unknown = sorted(set(data) - set(REQUIRED_TOP) - {"updated_at", "version", "notes"})
    # Unknown keys are allowed as notes-like extras? Safer to reject so we don't apply unexpected fields.
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))

    normalised = default_config()
    normalised["instructions"] = data.get("instructions") if isinstance(data.get("instructions"), str) else ""
    if "instructions" in data and not isinstance(data.get("instructions"), str):
        errors.append("instructions must be a string")
    normalised["instructions"] = normalised["instructions"].strip()

    queries = data.get("queries")
    if not isinstance(queries, dict):
        errors.append("queries must be an object with organisations, dealers, hobbyists and news")
        queries = {}
    else:
        extra = sorted(set(queries) - set(QUERY_TRACKS))
        if extra:
            errors.append("queries has unknown tracks: " + ", ".join(extra))
    for track in QUERY_TRACKS:
        normalised["queries"][track] = _as_str_list(queries.get(track), f"queries.{track}", errors)

    normalised["include_keywords"] = _as_str_list(data.get("include_keywords"), "include_keywords", errors)
    normalised["exclude_keywords"] = _as_str_list(data.get("exclude_keywords"), "exclude_keywords", errors)

    locations = data.get("locations")
    if locations in (None, [], ""):
        normalised["locations"] = list(DEFAULT_LOCATIONS)
    else:
        normalised["locations"] = _as_str_list(locations, "locations", errors)
        if not normalised["locations"]:
            normalised["locations"] = list(DEFAULT_LOCATIONS)

    sources = data.get("sources")
    if sources is None:
        sources = {}
    if not isinstance(sources, dict):
        errors.append("sources must be an object with use and skip lists")
        sources = {}
    else:
        extra = sorted(set(sources) - {"use", "skip"})
        if extra:
            errors.append("sources has unknown fields: " + ", ".join(extra))
    normalised["sources"]["use"] = _as_str_list(sources.get("use"), "sources.use", errors)
    normalised["sources"]["skip"] = _as_str_list(sources.get("skip"), "sources.skip", errors)

    minutes = data.get("minutes_per_run")
    if minutes is None:
        errors.append("minutes_per_run is required and must be an integer from 5 to 10")
    elif isinstance(minutes, bool) or not isinstance(minutes, int):
        errors.append("minutes_per_run must be an integer from 5 to 10")
    elif minutes < MIN_MINUTES or minutes > MAX_MINUTES:
        errors.append("minutes_per_run must be between 5 and 10")
    else:
        normalised["minutes_per_run"] = minutes

    if isinstance(data.get("updated_at"), str):
        normalised["updated_at"] = data["updated_at"]

    total_queries = sum(len(normalised["queries"][t]) for t in QUERY_TRACKS)
    if total_queries == 0:
        errors.append("at least one search query is required across the four tracks")

    if errors:
        return False, errors, None
    return True, [], normalised


def extract_json_block(body: str | None) -> dict[str, Any] | None:
    """Pull the first JSON object out of a fenced code block, or the whole body."""
    text = body or ""
    fences = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    candidates = fences + [text]
    for chunk in candidates:
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError:
            # Try to find a top-level object in mixed text
            start, end = chunk.find("{"), chunk.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(chunk[start : end + 1])
                except json.JSONDecodeError:
                    continue
            else:
                continue
        if isinstance(data, dict):
            return data
    return None


def write_config(config: dict[str, Any], updated_at: str | None = None) -> tuple[Path, Path]:
    """Write config to the repo and mirror it under DATA_HOME."""
    payload = dict(config)
    payload["updated_at"] = updated_at or iso_ist()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    repo_path = config_path_repo()
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.write_text(text, encoding="utf-8")
    ensure_data_home()
    home_path = config_path_home()
    home_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo_path, home_path)
    return repo_path, home_path


def read_config(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path_repo()
    if not target.exists():
        home = config_path_home()
        if home.exists():
            target = home
        else:
            raise FileNotFoundError(f"search config not found at {target}")
    data = json.loads(target.read_text(encoding="utf-8"))
    ok, errors, normalised = validate_search_config(data)
    if not ok or normalised is None:
        raise ValueError("invalid search config: " + "; ".join(errors))
    if data.get("updated_at"):
        normalised["updated_at"] = data["updated_at"]
    return normalised


def _commit_config(message: str) -> str:
    """Commit config/search.json in the repo. Returns the commit sha or a note."""
    import subprocess

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=REPO_ROOT, check=False, capture_output=True, text=True)

    run(["git", "add", "config/search.json"])
    status = run(["git", "status", "--porcelain", "--", "config/search.json"])
    if not (status.stdout or "").strip():
        return "no-change"
    committed = run(["git", "commit", "-m", message])
    if committed.returncode != 0:
        raise RuntimeError((committed.stderr or committed.stdout or "git commit failed").strip())
    sha = run(["git", "rev-parse", "--short", "HEAD"])
    return (sha.stdout or "").strip() or "committed"


def process_config(
    *,
    issues: list[dict[str, Any]] | None = None,
    collaborators: list[str] | None = None,
    comment: Callable[[int, str], None] | None = None,
    close: Callable[[int], None] | None = None,
    commit: Callable[[str], str] | None = None,
    repo: str = GITHUB_REPO,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply the newest open search-config issue from a trusted author."""
    errors: list[str] = []
    applied = ""

    if issues is None:
        try:
            issues = list_open_issues(CONFIG_LABEL, repo=repo)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"could not list search-config issues: {exc}")
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
    do_commit = commit or (_commit_config if not dry_run else (lambda msg: "dry-run"))

    # Newest first: prefer createdAt descending, then number.
    def sort_key(issue: dict[str, Any]) -> tuple:
        return (issue.get("createdAt") or "", issue.get("number") or 0)

    trusted = []
    for issue in issues:
        number = issue.get("number")
        title = (issue.get("title") or "").strip()
        author = issue_author(issue)
        if not is_allowed_author(author, collaborators):
            errors.append(f"issue #{number} ignored: author {author or '(unknown)'} is not the owner or a collaborator")
            continue
        if not title.lower().startswith(TITLE_PREFIX):
            errors.append(f"issue #{number} ignored: title must start with 'search-config:'")
            continue
        trusted.append(issue)

    trusted.sort(key=sort_key, reverse=True)
    chosen = trusted[0] if trusted else None
    # Leave older trusted issues open; only the newest is applied. Mention this in the comment if we close only one.

    if chosen is not None:
        number = chosen.get("number")
        payload = extract_json_block(chosen.get("body") or "")
        if payload is None:
            errors.append(f"issue #{number}: no JSON object found in the body")
            try:
                do_comment(number, "No JSON object was found in this issue body. Left open. Please put the config in a ```json code block.")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"issue #{number}: comment failed: {exc}")
        else:
            ok, validation_errors, normalised = validate_search_config(payload)
            if not ok or normalised is None:
                msg = "Config failed validation:\n- " + "\n- ".join(validation_errors)
                errors.append(f"issue #{number}: " + "; ".join(validation_errors))
                try:
                    do_comment(number, msg + "\n\nLeft open so it can be corrected.")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"issue #{number}: comment failed: {exc}")
            else:
                when = iso_ist()
                write_config(normalised, updated_at=when)
                try:
                    sha = do_commit(f"Lead desk: apply search-config from issue #{number}")
                except Exception as exc:  # noqa: BLE001
                    sha = ""
                    errors.append(f"issue #{number}: config written but commit failed: {exc}")
                applied = f"issue #{number}" + (f" ({sha})" if sha else "")
                try:
                    do_comment(
                        number,
                        f"Applied this search config at {when} Asia/Calcutta. "
                        f"Saved to `config/search.json` and mirrored under the server data folder. "
                        f"Commit: {sha or 'pending'}.",
                    )
                    do_close(number)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"issue #{number}: applied but GitHub update failed: {exc}")

    result = {
        "run_at": iso_ist(),
        "command": "process-config",
        "source_file": str(config_path_repo()),
        "ingested": 0,
        "duplicates": 0,
        "near_duplicates": 0,
        "archived": 0,
        "config_applied": applied,
        "published": "",
        "error_count": len(errors),
        "errors": "; ".join(errors),
        "notes": applied or "no trusted search-config issue to apply",
    }
    try:
        store = load()
        append_run(store, result)
        save(store)
    except Exception as exc:  # noqa: BLE001
        result["error_count"] += 1
        result["errors"] = (result["errors"] + "; " if result["errors"] else "") + f"workbook log failed: {exc}"
    return result
