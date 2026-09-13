"""What an uploaded workbook is, before anyone decides what it means (#143).

The first question about a department's file is structural: which sheets, where the
header row is, whether a merged title sits above it, and whether there is any data at
all. Four files in the first round were headers only; treating them as business data
would have produced relationships and totals out of nothing.

Only structure is returned — sheet names, a title line, header labels and counts. No
data cell leaves this module, so the result is safe to show a model.
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd
from pydantic import BaseModel, Field

MAX_SHEETS = 20
MAX_LABELS = 200
MAX_EXPANDED_BYTES = 100 * 1024 * 1024


class SheetShape(BaseModel):
    name: str
    #: A single-cell row above the header, typically a merged title.
    title: str = ""
    header_row: int | None = None  # 1-based, as a person counts rows
    labels: list[str] = Field(default_factory=list)
    duplicate_labels: list[str] = Field(default_factory=list)
    data_rows: int = 0

    @property
    def header_only(self) -> bool:
        return self.header_row is not None and self.data_rows == 0


class MaterialShape(BaseModel):
    filename: str
    sheets: list[SheetShape]
    header_only: bool
    truncated: bool = False


class MaterialError(Exception):
    pass


def _cells(row: pd.Series) -> list[str]:
    return [str(v).strip() for v in row.tolist() if not pd.isna(v) and str(v).strip()]


def _shape(name: str, frame: pd.DataFrame) -> SheetShape:
    shape = SheetShape(name=name)
    rows = [(index, _cells(row)) for index, row in frame.iterrows()]
    rows = [(index, cells) for index, cells in rows if cells]
    for position, (index, cells) in enumerate(rows):
        if len(cells) == 1 and not shape.title and position + 1 < len(rows) and len(rows[position + 1][1]) > 1:
            shape.title = cells[0]
            continue
        if len(cells) > 1:
            shape.header_row = int(index) + 1
            shape.labels = cells[:MAX_LABELS]
            counts = {c: cells.count(c) for c in cells}
            shape.duplicate_labels = sorted(c for c, n in counts.items() if n > 1)
            shape.data_rows = len(rows) - position - 1
            break
    return shape


def inspect(filename: str, payload: bytes) -> MaterialShape:
    lowered = filename.lower()
    try:
        if lowered.endswith(".xlsx"):
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if sum(i.file_size for i in archive.infolist()) > MAX_EXPANDED_BYTES:
                    raise MaterialError("Expanded workbook exceeds 100 MiB")
            frames = pd.read_excel(io.BytesIO(payload), sheet_name=None, header=None)
        elif lowered.endswith(".csv"):
            frames = {"csv": pd.read_csv(io.BytesIO(payload), header=None, skip_blank_lines=False)}
        else:
            raise MaterialError("Use CSV or XLSX")
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        raise MaterialError(f"Cannot read {filename}") from exc
    names = list(frames)[:MAX_SHEETS]
    sheets = [_shape(str(name), frames[name]) for name in names]
    return MaterialShape(filename=filename, sheets=sheets,
                         header_only=any(s.header_row is not None for s in sheets)
                         and all(s.header_only or s.header_row is None for s in sheets),
                         truncated=len(frames) > MAX_SHEETS)
