"""Turning what somebody wrote into a declared type, or saying why it cannot be.

One strategy per declared type, chosen from a registry. A strategy either returns a
canonical value with a note of what it did, or an issue; it never returns a value it
had to guess. A bare number where a unit matters, a date that parses two ways, a
negative quantity where the declaration says none — each becomes a question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from bridgeflow.workflow.catalogue import FieldSpec


@dataclass(frozen=True)
class Normalised:
    value: str | None
    #: What was changed and on what authority, for the provenance trail.
    note: str = ""
    #: `invalid` or `ambiguous`, with a sentence a person can act on.
    problem: tuple[str, str] | None = None

    @classmethod
    def ok(cls, value: str, note: str = "") -> Normalised:
        return cls(value=value, note=note)

    @classmethod
    def refuse(cls, kind: str, message: str) -> Normalised:
        return cls(value=None, problem=(kind, message))


class Normaliser(Protocol):
    def __call__(self, raw: str, spec: FieldSpec) -> Normalised: ...


def _text(raw: str, spec: FieldSpec) -> Normalised:
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return Normalised.ok(cleaned, "whitespace collapsed" if cleaned != raw else "")


_NUMBER = re.compile(r"^\s*([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(\S*)\s*$")


def _number(raw: str, spec: FieldSpec) -> Normalised:
    match = _NUMBER.match(raw)
    if not match:
        return Normalised.refuse("invalid", f"{spec.label} must be a number")
    digits, suffix = match.groups()
    try:
        number = Decimal(digits.replace(",", ""))
    except InvalidOperation:
        return Normalised.refuse("invalid", f"{spec.label} must be a number")
    note = ""
    if spec.unit:
        if suffix:
            canonical = spec.units.get(suffix)
            if canonical != spec.unit:
                return Normalised.refuse(
                    "invalid", f"{spec.label}: unit {suffix!r} is not declared for this field")
            note = f"unit {suffix!r} read as {spec.unit} per template"
        elif spec.bare_number_in_unit:
            note = f"no unit written; template declares {spec.unit}"
        else:
            return Normalised.refuse(
                "ambiguous", f"{spec.label}: which unit is {digits} in? The template expects {spec.unit}")
    elif suffix:
        return Normalised.refuse("invalid", f"{spec.label} takes no unit, got {suffix!r}")
    if spec.minimum is not None and number < Decimal(str(spec.minimum)):
        return Normalised.refuse("invalid", f"{spec.label} cannot be below {spec.minimum}")
    return Normalised.ok(format(number.normalize(), "f"), note)


def _parse_dates(raw: str, formats: tuple[str, ...]) -> set[date]:
    found: set[date] = set()
    candidates = raw.strip()
    try:
        found.add(date.fromisoformat(candidates))
    except ValueError:
        pass
    for fmt in formats:
        try:
            found.add(datetime.strptime(candidates, fmt).date())  # noqa: DTZ007 — a calendar date, no instant
        except ValueError:
            continue
    return found


def _date(raw: str, spec: FieldSpec) -> Normalised:
    found = _parse_dates(raw, spec.formats)
    if not found:
        return Normalised.refuse("invalid", f"{spec.label}: {raw!r} is not a declared date format")
    if len(found) > 1:
        options = ", ".join(sorted(d.isoformat() for d in found))
        return Normalised.refuse("ambiguous", f"{spec.label}: {raw!r} could be {options}")
    value = found.pop().isoformat()
    return Normalised.ok(value, "" if value == raw.strip() else "date written in ISO form")


_PERIOD = re.compile(r"^\s*(\d{4})\s*[-/.年]\s*(\d{1,2})\s*月?\s*$")


def _period(raw: str, spec: FieldSpec) -> Normalised:
    match = _PERIOD.match(raw)
    if not match or not 1 <= int(match.group(2)) <= 12:
        return Normalised.refuse("invalid", f"{spec.label}: {raw!r} is not a year and month")
    value = f"{match.group(1)}-{int(match.group(2)):02d}"
    return Normalised.ok(value, "" if value == raw.strip() else "period written as YYYY-MM")


def _enum(raw: str, spec: FieldSpec) -> Normalised:
    cleaned = raw.strip()
    if cleaned in spec.allowed:
        return Normalised.ok(cleaned)
    return Normalised.refuse("invalid", f"{spec.label}: {cleaned!r} is not one of {', '.join(spec.allowed)}")


REGISTRY: dict[str, Normaliser] = {
    "string": _text,
    "number": _number,
    "date": _date,
    "period": _period,
    "enum": _enum,
}


def normalise(raw: object, spec: FieldSpec) -> Normalised:
    text = "" if raw is None else str(raw)
    if not text.strip():
        return Normalised(value=None)
    return REGISTRY[spec.dtype](text, spec)
