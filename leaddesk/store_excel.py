"""Read and write the master Excel workbook (Active, Archive, Runs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from leaddesk.models import LEAD_FIELDS, RUN_FIELDS, STATUS_ACTIVE, STATUS_ARCHIVE, clean_text
from leaddesk.paths import ensure_data_home, workbook_path

SHEET_ACTIVE = "Active"
SHEET_ARCHIVE = "Archive"
SHEET_RUNS = "Runs"


def _blank_book() -> Workbook:
    book = Workbook()
    # First sheet is created by default; rename and add the others.
    active = book.active
    active.title = SHEET_ACTIVE
    active.append(LEAD_FIELDS)
    archive = book.create_sheet(SHEET_ARCHIVE)
    archive.append(LEAD_FIELDS)
    runs = book.create_sheet(SHEET_RUNS)
    runs.append(RUN_FIELDS)
    return book


def _header_map(sheet: Worksheet) -> dict[str, int]:
    header = [clean_text(c.value) for c in next(sheet.iter_rows(min_row=1, max_row=1))]
    return {name: idx for idx, name in enumerate(header) if name}


def _row_to_dict(values: tuple[Any, ...], headers: dict[str, int], fields: list[str]) -> dict[str, Any]:
    row = {key: "" for key in fields}
    for key, idx in headers.items():
        if key in row and idx < len(values):
            value = values[idx]
            row[key] = "" if value is None else value
    return row


def _dicts_from_sheet(sheet: Worksheet, fields: list[str]) -> list[dict[str, Any]]:
    if sheet.max_row < 2:
        return []
    headers = _header_map(sheet)
    rows: list[dict[str, Any]] = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if not values or all(v is None or str(v).strip() == "" for v in values):
            continue
        rows.append(_row_to_dict(values, headers, fields))
    return rows


def _write_sheet(sheet: Worksheet, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    if sheet.max_row > 1:
        sheet.delete_rows(2, sheet.max_row - 1)
    # Ensure header is correct even if the sheet was new or drifted.
    if sheet.max_row < 1 or [c.value for c in sheet[1]] != fields:
        if sheet.max_row >= 1:
            sheet.delete_rows(1, sheet.max_row)
        sheet.append(fields)
    for row in rows:
        sheet.append([row.get(key, "") for key in fields])


def load(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Return {'Active': [...], 'Archive': [...], 'Runs': [...]}."""
    target = path or workbook_path()
    if not target.exists():
        return {SHEET_ACTIVE: [], SHEET_ARCHIVE: [], SHEET_RUNS: []}
    book = load_workbook(target)
    data = {
        SHEET_ACTIVE: _dicts_from_sheet(book[SHEET_ACTIVE], LEAD_FIELDS)
        if SHEET_ACTIVE in book.sheetnames
        else [],
        SHEET_ARCHIVE: _dicts_from_sheet(book[SHEET_ARCHIVE], LEAD_FIELDS)
        if SHEET_ARCHIVE in book.sheetnames
        else [],
        SHEET_RUNS: _dicts_from_sheet(book[SHEET_RUNS], RUN_FIELDS)
        if SHEET_RUNS in book.sheetnames
        else [],
    }
    book.close()
    return data


def save(
    store: dict[str, list[dict[str, Any]]],
    path: Path | None = None,
) -> Path:
    target = path or workbook_path()
    ensure_data_home()
    target.parent.mkdir(parents=True, exist_ok=True)
    book = _blank_book()
    _write_sheet(book[SHEET_ACTIVE], LEAD_FIELDS, store.get(SHEET_ACTIVE, []))
    _write_sheet(book[SHEET_ARCHIVE], LEAD_FIELDS, store.get(SHEET_ARCHIVE, []))
    _write_sheet(book[SHEET_RUNS], RUN_FIELDS, store.get(SHEET_RUNS, []))
    book.save(target)
    book.close()
    return target


def all_leads(store: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return list(store.get(SHEET_ACTIVE, [])) + list(store.get(SHEET_ARCHIVE, []))


def find_lead(store: dict[str, list[dict[str, Any]]], lead_id: str) -> tuple[str | None, dict[str, Any] | None]:
    for sheet in (SHEET_ACTIVE, SHEET_ARCHIVE):
        for row in store.get(sheet, []):
            if row.get("lead_id") == lead_id:
                return sheet, row
    return None, None


def append_run(store: dict[str, list[dict[str, Any]]], run: dict[str, Any]) -> None:
    row = {key: run.get(key, "") for key in RUN_FIELDS}
    store.setdefault(SHEET_RUNS, []).append(row)
