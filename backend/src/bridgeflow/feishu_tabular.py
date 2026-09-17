"""Materialize Feishu online sheets and bitables into CSV bytes (docs/33).

The import pipeline owns bytes, not frames: size and row limits, cleaning, quarantine and
dictionary matching all live downstream of the upload parser. These adapters paged-read
Feishu as the signed-in user and write CSV, so a sheet or a bitable arrives at
`_import_batch` as just another upload.

Two disciplines hold here as everywhere else: the row cap is enforced while paging — an
oversized table is refused with the counts and nothing is materialized (truncation would
be a silent error); and a bitable column with no representable value is dropped with a
reason recorded, never silently (FR-5).
"""

from __future__ import annotations

import csv
import io
import re
import tempfile
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from datetime import UTC, datetime
from typing import Self

from fastapi import HTTPException

from bridgeflow.config import settings
from bridgeflow.feishu import FeishuDrive, FeishuError

#: A cell whose type carries no representable value for a flat table.
_UNSET = object()

#: ui_types whose extractor always yields a flat representation, so the column is kept
#: even when every record leaves it empty. Anything else (Formula, unknown types) is
#: kept only if at least one record produced a representation — otherwise dropped (FR-5).
_DETERMINISTIC_UI_TYPES = {
    "Text", "Number", "Currency", "Progress", "Rating", "AutoNumber",
    "SingleSelect", "MultiSelect", "Phone", "Email", "Url",
    "DateTime", "CreatedTime", "ModifiedTime",
    "Checkbox", "User", "CreatedUser", "ModifiedUser",
    "Attachment", "Location", "Barcode",
}


def _epoch_ms(value: object) -> object:
    """A millisecond epoch as an ISO date; anything else falls through to the generic rule."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1000, UTC).date().isoformat()
    return _generic(value)


def _display_text(item: dict) -> object:
    """A structured cell's human label: a person's name, an attachment's file name, a link's text."""
    piece = item.get("text") or item.get("name") or item.get("title")
    return str(piece) if piece is not None else _UNSET


def _generic(value: object) -> object:
    """Best-effort flat text for one cell: scalars as-is, structured values by display text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _display_text(value)
    if isinstance(value, list):
        parts = [str(item) if isinstance(item, (str, int, float)) else _display_text(item)
                 if isinstance(item, dict) else _UNSET for item in value]
        return ", ".join(parts) if _UNSET not in parts else _UNSET
    return _UNSET


def _extractor(ui_type: str) -> Callable[[object], object]:
    if ui_type in {"DateTime", "CreatedTime", "ModifiedTime"}:
        return _epoch_ms
    return _generic


def _safe_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\r\n]', "-", text).strip() or "unnamed"


#: A spool stays in memory up to this many bytes, then rolls over to a temp file.
_SPOOL_MEMORY_BYTES = 8 * 1024 * 1024


class _Spool:
    """CSV bytes under a hard ceiling: memory up to a threshold, disk past it.

    Bytes are counted as each row is encoded, so an oversized table is refused while
    it is being written — the 413 lands before the payload is fully allocated.
    """

    def __init__(self, limit: int) -> None:
        # The spool's lifetime is owned by this class (close()/__exit__), which outlives
        # any single with-block at the call site.
        self._raw = tempfile.SpooledTemporaryFile(max_size=_SPOOL_MEMORY_BYTES, mode="w+b")  # noqa: SIM115
        self._line = io.StringIO()
        self._writer = csv.writer(self._line, lineterminator="\n")
        self._limit = limit
        self._written = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def writerow(self, row: Iterable[object]) -> None:
        self._line.seek(0)
        self._line.truncate(0)
        self._writer.writerow(row)
        data = self._line.getvalue().encode("utf-8")
        self._written += len(data)
        if self._written > self._limit:
            raise HTTPException(
                413, "Table exceeds the configured upload size limit; nothing was imported")
        self._raw.write(data)

    def rows(self) -> Iterator[list[str]]:
        """The spooled rows back, for the bitable's drop-columns second pass."""
        self._raw.seek(0)
        return iter(csv.reader(io.TextIOWrapper(self._raw, encoding="utf-8", newline="")))

    def payload(self) -> bytes:
        self._raw.seek(0)
        return self._raw.read()

    def close(self) -> None:
        self._raw.close()


async def _data_rows(pages: AsyncIterator[list[list[object]]],
                     skip_rows: int) -> AsyncIterator[list[object]]:
    """Rows below the selected header. The first row after skip_rows is the header the
    user picked: an empty one is a refusal, never a silent slide to the next row. Fully
    empty rows below it are dropped — a sheet's grid size counts formatting, not data."""
    skipped = skip_rows
    header_seen = False
    async for page in pages:
        for row in page:
            if skipped:
                skipped -= 1
                continue
            if not any(value not in (None, "") for value in row):
                if not header_seen:
                    raise FeishuError(f"The selected header row {skip_rows + 1} is empty")
                continue
            header_seen = True
            yield row
    if not header_seen:
        raise FeishuError("The selected range is empty below the header")


async def _csv(pages: AsyncIterator[list[list[object]]], skip_rows: int = 0) -> tuple[bytes, int]:
    """Stream rows into CSV bytes under the batch row and byte caps."""
    spool = _Spool(settings.bridgeflow_max_upload_bytes)
    try:
        rows_written = 0
        async for row in _data_rows(pages, skip_rows):
            if rows_written - 1 >= settings.bridgeflow_max_batch_rows:
                raise HTTPException(
                    413, f"Table exceeds the {settings.bridgeflow_max_batch_rows}-row import limit "
                         f"after reading {rows_written - 1} data rows; nothing was imported")
            spool.writerow(["" if value is None else value for value in row])
            rows_written += 1
        return spool.payload(), rows_written
    finally:
        spool.close()


async def materialize_sheet(drive: FeishuDrive, spreadsheet_token: str, sheet_id: str,
                            header_row: int) -> tuple[str, bytes, list[dict]]:
    """One worksheet as CSV bytes: the header row the user picked becomes row 1.

    Returns (filename, payload, dropped) — a sheet never drops columns, so the third
    element is always empty; the shape matches materialize_bitable.
    """
    sheets = await drive.sheet_meta(spreadsheet_token)
    meta = next((s for s in sheets if s["sheet_id"] == sheet_id), None)
    if meta is None:
        raise FeishuError(
            f"sheet {sheet_id!r} not found; the spreadsheet has: {[s['title'] for s in sheets]}")
    if header_row > max(meta["rows"], 1):
        raise FeishuError(
            f"header row {header_row} is beyond the sheet's {meta['rows']} rows")
    pages = drive.sheet_values(spreadsheet_token, sheet_id, meta["rows"], meta["cols"])
    payload, _ = await _csv(pages, skip_rows=header_row - 1)
    filename = f"feishu-sheet-{spreadsheet_token[:8]}-{_safe_name(meta['title'])}.csv"
    return filename, payload, []


async def _spool_records(drive: FeishuDrive, app_token: str, table_id: str, fields: list[dict],
                         extractors: list[Callable[[object], object]], representable: list[bool],
                         spool: _Spool) -> None:
    """Every record's normalized cells (all columns) into the spool, marking which columns
    produced a representation. The row cap is enforced while paging — an oversized table is
    refused with the counts and nothing is materialized (truncation would be a silent error)."""
    count = 0
    async for page in drive.bitable_records(app_token, table_id):
        for record in page:
            count += 1
            if count > settings.bridgeflow_max_batch_rows:
                raise HTTPException(
                    413, f"Table exceeds the {settings.bridgeflow_max_batch_rows}-row import limit "
                         f"after reading {count - 1} records; nothing was imported")
            cells: list[str] = []
            record_fields = record["fields"]
            for index, field in enumerate(fields):
                text = extractors[index](record_fields.get(field["name"]))
                if text is _UNSET:
                    text = ""
                elif text:
                    representable[index] = True
                cells.append(str(text))
            spool.writerow(cells)


async def materialize_bitable(drive: FeishuDrive, app_token: str,
                              table_id: str) -> tuple[str, bytes, list[dict]]:
    """One bitable table as CSV bytes, field names as the header (docs/33, FR-3/FR-5).

    Scalars import as-is; people, attachments, links and formulas import as their display
    text; a column with no representable value in any record is dropped and reported.
    """
    tables = await drive.bitable_tables(app_token)
    name = next((t["name"] for t in tables if t["table_id"] == table_id), None)
    if name is None:
        raise FeishuError(
            f"table {table_id!r} not found; the bitable has: {[t['name'] for t in tables]}")
    fields = await drive.bitable_fields(app_token, table_id)
    if not fields:
        raise FeishuError(f"table {name!r} declares no fields")
    extractors = [_extractor(f["ui_type"]) for f in fields]
    representable = [f["ui_type"] in _DETERMINISTIC_UI_TYPES for f in fields]

    # Which columns survive is known only after every record is read, so the normalized
    # cells spool to disk first, then a second pass writes the kept columns.
    spool = _Spool(settings.bridgeflow_max_upload_bytes)
    try:
        await _spool_records(drive, app_token, table_id, fields, extractors, representable, spool)
        keep = [i for i in range(len(fields)) if representable[i]]
        dropped = [{"column": fields[i]["name"], "field_type": fields[i]["ui_type"],
                    "reason": "no representable value; column dropped"}
                   for i in range(len(fields)) if i not in keep]
        if not keep:
            raise FeishuError(f"table {name!r} has no importable columns")
        final = _Spool(settings.bridgeflow_max_upload_bytes)
        try:
            final.writerow([fields[i]["name"] for i in keep])
            for row in spool.rows():
                final.writerow([row[i] for i in keep])
            filename = f"feishu-bitable-{app_token[:8]}-{_safe_name(name)}.csv"
            return filename, final.payload(), dropped
        finally:
            final.close()
    finally:
        spool.close()
