"""Export the workbook to data/ JSON + xlsx, then commit and optionally push."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from leaddesk.models import LEAD_FIELDS, format_ist, iso_ist, parse_iso
from leaddesk.paths import REPO_ROOT, ensure_data_home, exports_dir, repo_data_dir, workbook_path
from leaddesk.store_excel import SHEET_ACTIVE, SHEET_ARCHIVE, SHEET_RUNS, append_run, load, save


def _dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEAD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in LEAD_FIELDS})


def export_snapshots(store: dict[str, list[dict[str, Any]]] | None = None, updated_at: str | None = None) -> dict[str, Path]:
    """Write leads.json, archive.json, runs.json, leads.xlsx (and CSV) to data/ and exports/."""
    ensure_data_home()
    store = store if store is not None else load()
    when = updated_at or iso_ist()
    active = store.get(SHEET_ACTIVE, [])
    archive = store.get(SHEET_ARCHIVE, [])
    runs = store.get(SHEET_RUNS, [])

    data_dir = repo_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    out_exports = exports_dir()
    out_exports.mkdir(parents=True, exist_ok=True)

    leads_json = {
        "updated_at": when,
        "updated_at_ist": format_ist(parse_iso(when)),
        "count": len(active),
        "leads": active,
    }
    archive_json = {
        "updated_at": when,
        "updated_at_ist": format_ist(parse_iso(when)),
        "count": len(archive),
        "leads": archive,
    }
    runs_json = {
        "updated_at": when,
        "updated_at_ist": format_ist(parse_iso(when)),
        "count": len(runs),
        "runs": runs,
    }

    paths = {
        "leads_json": data_dir / "leads.json",
        "archive_json": data_dir / "archive.json",
        "runs_json": data_dir / "runs.json",
        "leads_xlsx": data_dir / "leads.xlsx",
        "leads_csv": data_dir / "leads.csv",
    }
    _dump(paths["leads_json"], leads_json)
    _dump(paths["archive_json"], archive_json)
    _dump(paths["runs_json"], runs_json)
    _write_csv(paths["leads_csv"], active)

    # Master workbook lives in DATA_HOME; copy the published snapshot next to the JSON.
    master = workbook_path()
    if master.exists():
        shutil.copyfile(master, paths["leads_xlsx"])
        shutil.copyfile(master, out_exports / "leads.xlsx")
    else:
        # If the master is somehow missing, write from the in-memory store first.
        save(store, master)
        shutil.copyfile(master, paths["leads_xlsx"])
        shutil.copyfile(master, out_exports / "leads.xlsx")

    _write_csv(out_exports / "leads.csv", active)
    _dump(out_exports / "leads.json", leads_json)
    _dump(out_exports / "archive.json", archive_json)
    return paths


def _git(args: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def _ensure_git_identity() -> None:
    name = _git(["git", "config", "--get", "user.name"])
    email = _git(["git", "config", "--get", "user.email"])
    if not (name.stdout or "").strip():
        _git(["git", "config", "user.name", "vibhvesh"])
    if not (email.stdout or "").strip():
        _git(["git", "config", "user.email", "310699826+vibhvesh@users.noreply.github.com"])


PUBLISH_PATHS = [
    "data/leads.json",
    "data/archive.json",
    "data/runs.json",
    "data/leads.xlsx",
    "data/leads.csv",
    "config/search.json",
]


def commit_and_push(message: str, push: bool = True) -> dict[str, str]:
    _ensure_git_identity()
    _git(["git", "add", "--"] + PUBLISH_PATHS)
    status = _git(["git", "status", "--porcelain", "--"] + PUBLISH_PATHS)
    porcelain = (status.stdout or "").strip()
    if not porcelain:
        if push:
            pushed = _git(["git", "push", "origin", "HEAD"])
            return {
                "commit": "no-change",
                "push": "ok" if pushed.returncode == 0 else (pushed.stderr or pushed.stdout or "push failed").strip(),
            }
        return {"commit": "no-change", "push": "skipped"}

    committed = _git(["git", "commit", "-m", message])
    if committed.returncode != 0:
        raise RuntimeError((committed.stderr or committed.stdout or "git commit failed").strip())
    sha = (_git(["git", "rev-parse", "--short", "HEAD"]).stdout or "").strip()
    if not push:
        return {"commit": sha, "push": "skipped"}
    pushed = _git(["git", "push", "origin", "HEAD"])
    if pushed.returncode != 0:
        raise RuntimeError((pushed.stderr or pushed.stdout or "git push failed").strip())
    return {"commit": sha, "push": "ok"}


def publish(push: bool = True) -> dict[str, Any]:
    when = iso_ist()
    store = load()
    export_snapshots(store, updated_at=when)
    git_info = {"commit": "", "push": "skipped"}
    errors: list[str] = []
    try:
        git_info = commit_and_push(
            f"Lead desk: publish Active/Archive snapshot ({format_ist(parse_iso(when))})",
            push=push,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    result = {
        "run_at": when,
        "command": "publish",
        "source_file": str(workbook_path()),
        "ingested": 0,
        "duplicates": 0,
        "near_duplicates": 0,
        "archived": 0,
        "config_applied": "",
        "published": git_info.get("commit") or "",
        "error_count": len(errors),
        "errors": "; ".join(errors),
        "notes": f"push={git_info.get('push')}",
    }
    append_run(store, result)
    save(store)
    # Re-export so the publish run itself is in runs.json / the copied xlsx.
    export_snapshots(store, updated_at=when)
    if push and not errors:
        # The second export changed files after the first commit; include them.
        try:
            commit_and_push(
                f"Lead desk: record publish run ({format_ist(parse_iso(when))})",
                push=True,
            )
        except Exception as exc:  # noqa: BLE001
            # If only the run log changed and the second commit is empty, that's fine.
            if "no-change" not in str(exc) and "nothing to commit" not in str(exc).lower():
                errors.append(str(exc))
                result["error_count"] = len(errors)
                result["errors"] = "; ".join(errors)
    elif not push:
        # Keep local export current; caller may commit later.
        pass
    return result
