"""Command-line entry: ingest, process-archive, process-config, publish, run-all."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from leaddesk.archive import process_archive
from leaddesk.config import process_config
from leaddesk.ingest import ingest
from leaddesk.paths import DATA_HOME, REPO_ROOT, ensure_data_home
from leaddesk.publish import publish


def _print(result: dict) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def cmd_ingest(args: argparse.Namespace) -> int:
    ensure_data_home()
    result = ingest(Path(args.new_items).expanduser().resolve())
    _print(result)
    return 1 if result.get("error_count") and result.get("ingested", 0) == 0 else 0


def cmd_process_archive(_args: argparse.Namespace) -> int:
    result = process_archive()
    _print(result)
    return 0


def cmd_process_config(_args: argparse.Namespace) -> int:
    result = process_config()
    _print(result)
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    result = publish(push=not args.no_push)
    _print(result)
    return 1 if result.get("error_count") else 0


def cmd_run_all(args: argparse.Namespace) -> int:
    """process-config, process-archive, optional ingest, then publish."""
    summary = {
        "command": "run-all",
        "config": process_config(),
        "archive": process_archive(),
        "ingest": None,
        "publish": None,
    }
    if args.new_items:
        summary["ingest"] = ingest(Path(args.new_items).expanduser().resolve())
    summary["publish"] = publish(push=not args.no_push)
    _print(summary)
    publish_errors = (summary["publish"] or {}).get("error_count") or 0
    return 1 if publish_errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leaddesk",
        description="Boondock Echo Lead Desk — Excel store, archive, search config and publish.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Add new items from a JSON or CSV file into leads.xlsx")
    p_ingest.add_argument("new_items", help="Path to new_items.json (or a CSV with the sweep columns)")
    p_ingest.set_defaults(func=cmd_ingest)

    p_arch = sub.add_parser("process-archive", help="Apply trusted archive: <lead_id> GitHub issues")
    p_arch.set_defaults(func=cmd_process_archive)

    p_cfg = sub.add_parser("process-config", help="Apply the newest trusted search-config GitHub issue")
    p_cfg.set_defaults(func=cmd_process_config)

    p_pub = sub.add_parser("publish", help="Export data/ JSON + xlsx and commit/push")
    p_pub.add_argument("--no-push", action="store_true", help="Export and commit locally, do not push")
    p_pub.set_defaults(func=cmd_publish)

    p_all = sub.add_parser("run-all", help="process-config, process-archive, ingest (optional), publish")
    p_all.add_argument(
        "--new",
        dest="new_items",
        default=None,
        metavar="FILE",
        help="Optional path to new items JSON or CSV (usually /workspace/boondock-leads/raw/<date>/new_items.json)",
    )
    p_all.add_argument("--no-push", action="store_true", help="Do not push after exporting")
    p_all.set_defaults(func=cmd_run_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Make sure `python3 -m leaddesk.cli` works from any cwd; imports use absolute paths.
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
