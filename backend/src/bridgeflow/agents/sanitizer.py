from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from bridgeflow.agents.base import Agent
from bridgeflow.schemas import CleanTable, ColumnSpec, Correction, Department

_HEADER_NOISE = re.compile(r"[^0-9a-z]+")


class SanitizerInput:
    def __init__(self, department: Department, period: str, frame: pd.DataFrame) -> None:
        self.department = department
        self.period = period
        self.frame = frame


class DataSanitizerAgent(Agent[SanitizerInput, CleanTable]):
    """Stage 1 — make a messy sheet machine-readable without losing anything.

    Rules run first and are logged individually; the LLM is only consulted for the
    residue (currently: nothing, see `_needs_llm`). Rows we cannot repair are moved to
    `quarantine` rather than dropped or guessed at.
    """

    slug = "sanitizer"
    system_prompt = (
        "You repair messy spreadsheet data exported by SME staff. "
        "Never invent values. If a cell cannot be repaired with confidence, say so."
    )

    async def run(self, payload: SanitizerInput) -> CleanTable:
        frame = payload.frame.copy()
        corrections: list[Correction] = []

        frame, header_fixes = self._normalise_headers(frame)
        corrections.extend(header_fixes)

        frame = frame.dropna(how="all").reset_index(drop=True)

        columns: list[ColumnSpec] = []
        for column in frame.columns:
            series, dtype, fixes = self._coerce(frame[column], column)
            frame[column] = series
            corrections.extend(fixes)
            columns.append(ColumnSpec(name=column, dtype=dtype))

        rows, quarantine = self._split_quarantine(frame)

        return CleanTable(
            department=payload.department,
            period=payload.period,
            columns=columns,
            rows=rows,
            corrections=corrections,
            quarantine=quarantine,
        )

    # -- rules ---------------------------------------------------------------

    def _normalise_headers(
        self, frame: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[Correction]]:
        fixes: list[Correction] = []
        renames: dict[Any, str] = {}
        for column in frame.columns:
            clean = _HEADER_NOISE.sub("_", str(column).strip().lower()).strip("_")
            if clean and clean != column:
                renames[column] = clean
                fixes.append(
                    Correction(
                        row=-1,
                        column=str(column),
                        before=column,
                        after=clean,
                        rule="header_normalise",
                        confidence=1.0,
                        reason="header snake-cased for stable downstream keys",
                    )
                )
        return frame.rename(columns=renames), fixes

    def _coerce(
        self, series: pd.Series, column: str
    ) -> tuple[pd.Series, str, list[Correction]]:
        """Infer a column's type and log every value that changed shape."""
        fixes: list[Correction] = []

        as_date = pd.to_datetime(series, errors="coerce", format="mixed")
        if as_date.notna().mean() > 0.8:
            for idx, (before, after) in enumerate(zip(series, as_date, strict=False)):
                if pd.notna(after) and str(before) != after.strftime("%Y-%m-%d"):
                    fixes.append(
                        Correction(
                            row=idx,
                            column=column,
                            before=str(before),
                            after=after.strftime("%Y-%m-%d"),
                            rule="date_parse",
                            confidence=0.95,
                            reason="mixed date formats normalised to ISO",
                        )
                    )
            return as_date.dt.strftime("%Y-%m-%d"), "date", fixes

        stripped = series.astype(str).str.replace(r"[,\s$]", "", regex=True)
        as_number = pd.to_numeric(stripped, errors="coerce")
        if as_number.notna().mean() > 0.8:
            for idx, (before, after) in enumerate(zip(series, as_number, strict=False)):
                if pd.notna(after) and str(before) != str(after):
                    fixes.append(
                        Correction(
                            row=idx,
                            column=column,
                            before=str(before),
                            after=float(after),
                            rule="number_normalise",
                            confidence=0.95,
                            reason="stripped currency symbols and thousands separators",
                        )
                    )
            return as_number, "number", fixes

        return series.astype(str).str.strip(), "string", fixes

    def _split_quarantine(
        self, frame: pd.DataFrame
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """A row missing more than half its cells is not worth guessing at."""
        rows: list[dict[str, Any]] = []
        quarantine: list[dict[str, Any]] = []
        threshold = max(1, len(frame.columns) // 2)

        for record in frame.to_dict(orient="records"):
            filled = sum(1 for v in record.values() if not _is_blank(v))
            (rows if filled >= threshold else quarantine).append(_jsonable(record))
        return rows, quarantine

    def _needs_llm(self, value: Any) -> bool:
        """Hook for the LLM fallback — not yet used (see docs/05-roadmap.md, M1)."""
        return False


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() in {"", "nan", "NaT", "None"}


def _jsonable(record: dict[str, Any]) -> dict[str, Any]:
    """numpy scalars survive `to_dict` but not JSON serialisation — unwrap them."""
    out: dict[str, Any] = {}
    for key, value in record.items():
        if _is_blank(value):
            out[key] = None
        elif hasattr(value, "item"):
            out[key] = value.item()
        else:
            out[key] = value
    return out
