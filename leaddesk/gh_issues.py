"""Thin wrappers around `gh` for issue list / comment / close, plus collaborator lookup."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from leaddesk.paths import GITHUB_REPO


class GitHubError(RuntimeError):
    pass


def _run(args: list[str], timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitHubError(f"failed to run {' '.join(args)}: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise GitHubError(message or f"command failed: {' '.join(args)}")
    return result.stdout


def list_open_issues(label: str, repo: str = GITHUB_REPO) -> list[dict[str, Any]]:
    raw = _run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--label",
            label,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,body,author,url,createdAt",
        ]
    )
    return json.loads(raw or "[]")


def list_collaborators(repo: str = GITHUB_REPO) -> list[str]:
    raw = _run(["gh", "api", f"repos/{repo}/collaborators", "--paginate"])
    people = json.loads(raw or "[]")
    return [p.get("login", "") for p in people if p.get("login")]


def comment_on_issue(number: int, body: str, repo: str = GITHUB_REPO) -> None:
    _run(["gh", "issue", "comment", str(number), "--repo", repo, "--body", body])


def close_issue(number: int, repo: str = GITHUB_REPO) -> None:
    _run(["gh", "issue", "close", str(number), "--repo", repo])


def issue_author(issue: dict[str, Any]) -> str:
    author = issue.get("author") or {}
    if isinstance(author, dict):
        return (author.get("login") or "").strip()
    return str(author).strip()
