"""The tuning sets and the holdout generator for the master table (#141).

The committed tuning sets (seeds 1 and 2) must grade clean and regenerate identically; a
fresh holdout set, from a seed nobody recorded, must grade clean too.
"""
import importlib.util
import json

import openpyxl

from bridgeflow.config import REPO_ROOT

_spec = importlib.util.spec_from_file_location("integration_cases", REPO_ROOT / "scripts" / "integration_cases.py")
cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cases)


def test_the_committed_tuning_sets_grade_clean():
    for seed in cases.TUNING_SEEDS:
        report = cases.grade(cases.TUNING / f"seed-{seed}")
        assert report["passed"], report
        assert report["clean_keys"] >= 5 and report["split_keys"] >= 1
        assert {k for k in report["faults"]} >= {"derived_mismatch", "missing_department", "disagreement",
                                                  "check_failed", "invalid_number", "needs_rollup", "missing_key"}


def test_the_tuning_sets_are_what_their_seeds_generate(tmp_path):
    for seed in cases.TUNING_SEEDS:
        answer = cases.write(seed, tmp_path / str(seed))
        committed = cases.TUNING / f"seed-{seed}"
        assert answer == json.loads((committed / "answer.json").read_text(encoding="utf-8"))
        for path in committed.glob("*.xlsx"):
            fresh = openpyxl.load_workbook(tmp_path / str(seed) / path.name).active
            original = openpyxl.load_workbook(path).active
            assert [[c.value for c in r] for r in fresh.iter_rows()] == [[c.value for c in r] for r in original.iter_rows()]


def test_a_fresh_holdout_set_grades_clean():
    totals = cases.holdout(2)
    assert totals["passed_sets"] == 2, totals
