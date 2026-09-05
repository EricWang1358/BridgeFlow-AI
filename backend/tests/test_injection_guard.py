"""Tests for the input trust boundary, from the Python side.

The guard itself is TypeScript (`plugins/src/guards/untrusted-input.ts`) because it
has to run where tool dispatch happens. The cases live in JSON so both halves are
tested against the same list rather than drifting apart — and so the false-positive
cases are as visible as the attacks. A guard that denies "Ignore-Tech Pte Ltd" is a
broken product, not a safe one.
"""

from __future__ import annotations

import json
import re

import pytest

from bridgeflow.config import REPO_ROOT

GUARD = REPO_ROOT / "plugins" / "src" / "guards" / "untrusted-input.ts"
CASES = json.loads(
    (REPO_ROOT / "plugins" / "src" / "guards" / "untrusted-input.test-cases.json").read_text("utf-8")
)


def _patterns() -> list[re.Pattern[str]]:
    """The guard's patterns, read out of the TypeScript so there is one source."""
    source = GUARD.read_text(encoding="utf-8")
    block = source[source.index("INSTRUCTION_SHAPES"): source.index("/** Where an offending")]
    out: list[re.Pattern[str]] = []
    for raw, flags in re.findall(r"^\s*/(.+)/([a-z]*),\s*$", block, re.MULTILINE):
        out.append(re.compile(raw, re.IGNORECASE if "i" in flags else 0))
    return out


def test_the_patterns_can_be_read_from_the_guard():
    assert _patterns(), "if this breaks, the two halves have drifted apart"


@pytest.mark.parametrize("value", CASES["must_deny"])
def test_instruction_shaped_text_is_denied(value: str):
    assert any(p.search(value) for p in _patterns()), f"not caught: {value!r}"


@pytest.mark.parametrize("value", CASES["must_allow"])
def test_ordinary_business_text_is_not_denied(value: str):
    """False positives matter more than coverage here.

    Blocking a purchase order because a supplier is called Ignore-Tech is a broken
    product. Breadth belongs in the adversarial eval suite (#28), not in a longer
    list of English words.
    """
    hits = [p.pattern for p in _patterns() if p.search(value)]
    assert not hits, f"{value!r} wrongly matched {hits}"


def test_the_poisoned_datasets_are_all_caught():
    """Every planted cell must actually trip the guard, or the fixture is theatre."""
    patterns = _patterns()
    for poisoned in (REPO_ROOT / "data" / "poisoned").rglob("*.csv"):
        text = poisoned.read_text(encoding="utf-8")
        assert any(p.search(text) for p in patterns), f"{poisoned.name} is not actually poisoned"
