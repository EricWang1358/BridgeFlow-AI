"""Department sheets with data and a known answer, for the 跨部门业务整合总表 (#141).

The business side supplied one worked example row. Generalisation needs more: several
projects and months, daily production rows, and sheets with the mistakes real people make.
This script makes them from `integration.yaml` alone — no business name is written here —
and grades `bridgeflow.integration` against an answer it computes itself:

- **Inputs** are the business example's own magnitudes, perturbed per key, so ratios stay
  in a realistic range while every class of the declared rule table can occur.
- **The answer is independent of the code under test**: formulas are evaluated here with
  exact fractions over the declaration, rule tables walked here, roll-ups summed here.
  Nothing calls `integration` or `business.expression` to produce the answer.
- **Faults are injected on purpose** (a wrong derived figure, a missing department, names
  that disagree, a failed cross-department check, text in a number column, duplicated rows
  without a roll-up, daily rows that differ where they must not, a row with no key, a title
  row above the header) and each must be reported for exactly the key it was put on, while
  clean keys must come out complete and exact.

Two uses:

    python scripts/integration_cases.py tuning            # regenerate the committed tuning sets (seeds 1, 2)
    python scripts/integration_cases.py grade DIR         # grade one generated set
    python scripts/integration_cases.py holdout --sets 5  # fresh sets from unrecorded random seeds

The holdout draws its seeds from the operating system and never prints or stores them or
the generated sheets; only the aggregate score is shown. That keeps tuning from fitting the
instances it will be judged on. It does not replace a holdout made from real exports.
"""
from __future__ import annotations

import argparse
import io
import json
import random
import secrets
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from bridgeflow import integration

BASE = ROOT / "data" / "company_templates"
TUNING = BASE / "tuning"
TUNING_SEEDS = (1, 2)
FAULTS = ("derived_mismatch", "missing_department", "disagreement", "check_failed",
          "invalid_number", "needs_rollup", "rollup_conflict")


# --- the answer, computed without the code under test -------------------------------------


def evaluate(tree: dict, values: dict, constants: dict) -> Fraction:
    op = tree["op"]
    if op == "input":
        return Fraction(str(values[tree["key"]]))
    if op == "constant":
        return Fraction(str(tree["value"]))
    if op == "declared":
        return Fraction(str(constants[tree["key"]]))
    a, b = (evaluate(child, values, constants) for child in tree["args"])
    return {"add": a + b, "subtract": a - b, "multiply": a * b, "divide": a / b}[op]


def classify(table, values: dict) -> str:
    compare = {"lt": lambda x, y: x < y, "lte": lambda x, y: x <= y, "gt": lambda x, y: x > y, "gte": lambda x, y: x >= y}
    for rule in table.rules:
        if all(compare[op](Fraction(str(values[f])), Fraction(str(bound))) for f, op, bound in rule.when):
            return rule.label
    return table.otherwise


def complete_values(spec, values: dict) -> dict:
    """Fill derived fields in dependency order, then classifications."""
    pending = dict(spec.derived)
    while pending:
        ready = [n for n, t in pending.items() if all(k not in pending for k in integration._inputs(t))]
        if not ready:
            raise ValueError("derived fields depend on each other in a cycle")
        for name in ready:
            result = evaluate(pending.pop(name), values, spec.constants)
            values[name] = int(result) if result.denominator == 1 else float(result)
    for name, table in spec.classifications.items():
        values[name] = classify(table, values)
    return values


# --- generating a set ---------------------------------------------------------------------


def _example() -> dict:
    spec = integration.load_spec(BASE / "integration.yaml")
    master = openpyxl.load_workbook(BASE / spec.master_template, read_only=True).active
    rows = list(master.iter_rows(values_only=True))
    return dict(zip(rows[0], rows[1], strict=True))


def _headers(spec, department: str) -> list[str]:
    decl = spec.departments[department]
    return integration.read_sheet(department, Path(decl.template).name, (BASE / decl.template).read_bytes()).headers


def _period_field(spec) -> str:
    [name] = [g for g in spec.grain if any(s.period_from for s in spec.fields[g].sources.values())]
    return name


def _noise(rng: random.Random) -> float:
    # Mostly ordinary month-to-month wobble, sometimes a real swing.
    return rng.uniform(-0.02, 0.02) if rng.random() < 0.7 else rng.uniform(-0.3, 0.3)


def _key_values(spec, example: dict, rng: random.Random, seed: int, project: int, period: str) -> dict:
    """One key's values. Draws are redrawn until the first rule table lands on a chosen label,
    so every label is exercised rather than whichever the example's magnitudes favour."""
    tables = list(spec.classifications.values())
    target = rng.choice([r.label for r in tables[0].rules] + [tables[0].otherwise]) if tables else None
    for _ in range(500):
        values = _draw(spec, example, rng, seed, project, period)
        if target is None or values[next(iter(spec.classifications))] == target:
            break
    return values


def _draw(spec, example: dict, rng: random.Random, seed: int, project: int, period: str) -> dict:
    computed = set(spec.derived) | set(spec.classifications)
    values: dict = {}
    for name, decl in spec.fields.items():
        if name in computed:
            continue
        sample = example.get(name)
        if name == _period_field(spec):
            values[name] = period
        elif decl.type == "number":
            base = sample if isinstance(sample, int | float) and sample else 100
            values[name] = round(base * (1 + _noise(rng)), 2)
        else:
            values[name] = f"{sample or name}-S{seed}P{project}" if name in spec.grain or name in spec.agree else (sample or "")
    for check in spec.checks:
        values[check.right] = values[check.left]
    return complete_values(spec, values)


def _row(spec, department: str, headers: list[str], values: dict, supply_computed: bool) -> list:
    row: list = [None] * len(headers)
    computed = set(spec.derived) | set(spec.classifications)
    for name, decl in spec.fields.items():
        ref = decl.sources.get(department)
        if ref is None or values.get(name) in (None, "") or (name in computed and not supply_computed):
            continue
        if ref.period_from:
            year, month = str(values[name]).split("-")
            row[headers.index(ref.period_from[0])], row[headers.index(ref.period_from[1])] = int(year), int(month)
            continue
        row[[i for i, h in enumerate(headers) if h == ref.column][ref.occurrence - 1]] = values[name]
    return row


def _split(spec, department: str, values: dict, rng: random.Random, parts: int, vary_concat: bool) -> list[dict]:
    """Daily rows that add up to the month: sum fields split exactly, ratios per day."""
    policy = spec.rollup[department]
    days = [dict(values) for _ in range(parts)]
    for name in policy.sum:
        total = Fraction(str(values[name]))
        weights = [rng.uniform(0.5, 1.5) for _ in range(parts)]
        cents = [Fraction(round(float(total) * w / sum(weights) * 100), 100) for w in weights[:-1]]
        last = total - sum(cents)
        for day, share in zip(days, [*cents, last], strict=True):
            day[name] = int(share) if share.denominator == 1 else float(share)
    for i, day in enumerate(days):
        for name in policy.concat:
            if vary_concat and day.get(name):
                day[name] = f"{values[name]}#{i + 1}"
        for name in policy.recompute:
            day.pop(name, None)
        complete_values_partial(spec, day, policy.recompute)
    return days


def complete_values_partial(spec, day: dict, names: list[str]) -> None:
    """A day's own ratio and diagnosis, as a person filling a daily sheet would write them."""
    for name in names:
        if name in spec.derived:
            try:
                day[name] = float(evaluate(spec.derived[name], day, spec.constants))
            except (KeyError, ZeroDivisionError):
                day.pop(name, None)
    for name in names:
        if name in spec.classifications:
            day[name] = classify(spec.classifications[name], day)


def generate(seed: int) -> tuple[dict[str, list[list]], dict]:
    """Rows per department (header first) and the answer."""
    spec = integration.load_spec(BASE / "integration.yaml")
    rng, example = random.Random(seed), _example()
    headers = {d: _headers(spec, d) for d in spec.departments}
    sheets: dict[str, list[list]] = {d: [list(h)] for d, h in headers.items()}
    period = str(example[_period_field(spec)])
    year, month = (int(p) for p in period.split("-"))
    periods = [period, f"{year + (month == 12)}-{month % 12 + 1:02d}"]
    keys = [(p, m) for p in range(1, rng.randint(7, 9) + 1) for m in periods]
    faulted = dict(zip(rng.sample(range(len(keys)), len(FAULTS)), rng.sample(FAULTS, len(FAULTS)), strict=True))
    rollup_departments = [d for d in spec.departments if d in spec.rollup]
    plain_departments = [d for d in spec.departments if d not in spec.rollup]
    answer: dict = {"seed": seed, "keys": [], "global": []}

    for index, (project, period) in enumerate(keys):
        values = _key_values(spec, example, rng, seed, project, period)
        key = [str(values[g]) for g in spec.grain]
        fault = faulted.get(index)
        entry: dict = {"key": key, "faults": [], "split": []}
        rows = {d: [values] for d in spec.departments}
        supplied = rng.random() < 0.5

        if fault is None:
            for department in rollup_departments:
                if rng.random() < 0.6:
                    rows[department] = _split(spec, department, values, rng, rng.randint(2, 4), vary_concat=rng.random() < 0.5)
                    entry["split"].append(department)
                    for name in spec.rollup[department].concat:
                        if values.get(name):
                            values[name] = "；".join(dict.fromkeys(str(d[name]) for d in rows[department]))
            entry["values"] = values
        elif fault == "derived_mismatch":
            choices = [(n, d) for n in spec.derived for d in spec.fields[n].sources]
            name, department = rng.choice(choices)
            wrong = dict(values, **{name: float(Fraction(str(values[name])) * Fraction(3, 2) + 1)})
            rows[department] = [wrong]
            supplied = True
            entry["faults"].append({"kind": fault, "field": name})
        elif fault == "missing_department":
            department = rng.choice(list(spec.departments))
            rows[department] = []
            entry["faults"].append({"kind": fault, "departments": [department]})
        elif fault == "disagreement":
            name = rng.choice([a for a in spec.agree if len(spec.fields[a].sources) > 1])
            department = rng.choice(list(spec.fields[name].sources))
            rows[department] = [dict(values, **{name: f"{values[name]}-other"})]
            entry["faults"].append({"kind": fault, "field": name})
        elif fault == "check_failed":
            check = rng.choice(spec.checks)
            [department] = list(spec.fields[check.left].sources)
            rows[department] = [dict(values, **{check.left: values[check.left] + 7})]
            entry["faults"].append({"kind": fault, "field": check.left})
        elif fault == "invalid_number":
            used = {f for c in spec.checks for f in (c.left, c.right)} | set(spec.grain)
            name = rng.choice([n for n, d in spec.fields.items() if d.type == "number" and n not in spec.derived and n not in used])
            department = rng.choice(list(spec.fields[name].sources))
            rows[department] = [dict(values, **{name: "n/a"})]
            entry["faults"].append({"kind": fault, "field": name})
        elif fault == "needs_rollup":
            department = rng.choice(plain_departments)
            rows[department] = [values, values]
            entry["faults"].append({"kind": fault, "departments": [department]})
        elif fault == "rollup_conflict":
            department = rng.choice(rollup_departments)
            policy = spec.rollup[department]
            covered = set(policy.sum) | set(policy.concat) | set(policy.recompute) | set(spec.grain)
            name = rng.choice([n for n, d in spec.fields.items() if department in d.sources and d.type == "number"
                               and n not in covered and n not in spec.derived and n not in {c.left for c in spec.checks} | {c.right for c in spec.checks}])
            days = _split(spec, department, values, rng, 2, vary_concat=False)
            days[1][name] = values[name] + 1
            rows[department] = days
            entry["faults"].append({"kind": "needs_rollup", "field": name, "departments": [department]})

        for department, department_rows in rows.items():
            for row_values in department_rows:
                sheets[department].append(_row(spec, department, headers[department], row_values, supplied))
        answer["keys"].append(entry)

    # A row nobody can place: its key cells are empty.
    department = rng.choice(list(spec.departments))
    orphan = _row(spec, department, headers[department], _key_values(spec, example, rng, seed, 99, periods[0]), False)
    for name in spec.grain:
        ref = spec.fields[name].sources[department]
        for label in ref.period_from or [ref.column]:
            orphan[headers[department].index(label)] = None
    sheets[department].insert(rng.randint(1, len(sheets[department])), orphan)
    answer["global"].append({"kind": "missing_key", "departments": [department]})

    # One department exports with a title row above its header.
    titled = rng.choice(list(spec.departments))
    sheets[titled].insert(0, [f"{spec.departments[titled].label} {periods[0]}"])
    answer["title_row"] = titled
    return sheets, answer


def write(seed: int, out: Path) -> dict:
    sheets, answer = generate(seed)
    out.mkdir(parents=True, exist_ok=True)
    for department, rows in sheets.items():
        book = openpyxl.Workbook()
        for row in rows:
            book.active.append(row)
        book.save(out / f"{department}.xlsx")
    (out / "answer.json").write_text(json.dumps(answer, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return answer


# --- grading ------------------------------------------------------------------------------


def _same(a, b) -> bool:
    if isinstance(a, int | float) and isinstance(b, int | float) and not isinstance(a, bool):
        return abs(a - b) <= 1e-9 * max(1, abs(b))
    return a == b


def grade(directory: Path, answer: dict | None = None) -> dict:
    spec = integration.load_spec(BASE / "integration.yaml")
    answer = answer or json.loads((directory / "answer.json").read_text(encoding="utf-8"))
    sheets = [integration.read_sheet(d, f"{d}.xlsx", (directory / f"{d}.xlsx").read_bytes()) for d in spec.departments]
    result = integration.integrate(spec, sheets)
    rows = {tuple(r.key): r for r in result.rows}
    issues_by_key: dict[tuple, list] = {}
    for issue in result.issues:
        issues_by_key.setdefault(tuple(issue.key), []).append(issue)

    report = {"clean_keys": 0, "clean_exact": 0, "split_keys": 0, "faults": {}, "false_alarms": [], "missed": [], "classes": {}}
    for entry in answer["keys"]:
        key = tuple(entry["key"])
        row, found = rows.get(key), issues_by_key.pop(key, [])
        if not entry["faults"]:
            report["clean_keys"] += 1
            report["split_keys"] += bool(entry["split"])
            wrong = [c for c in result.columns if row is None or not _same(row.values.get(c), entry["values"].get(c))]
            if row is not None and row.complete and not wrong and not found:
                report["clean_exact"] += 1
            else:
                report["false_alarms"].append({"key": list(key), "columns": wrong[:5], "issues": sorted({i.kind for i in found})})
            for name in spec.classifications:
                label = entry["values"][name]
                report["classes"][label] = report["classes"].get(label, 0) + 1
            continue
        for fault in entry["faults"]:
            tally = report["faults"].setdefault(fault["kind"], [0, 0])
            tally[1] += 1
            hit = any(i.kind == fault["kind"] and (not fault.get("field") or i.field == fault["field"])
                      and (not fault.get("departments") or i.departments == fault["departments"]) for i in found)
            if hit and (row is None or not row.complete):
                tally[0] += 1
            else:
                report["missed"].append({"key": list(key), **fault})
    for expected in answer["global"]:
        tally = report["faults"].setdefault(expected["kind"], [0, 0])
        tally[1] += 1
        stray = issues_by_key.get((), [])
        match = next((i for i in stray if i.kind == expected["kind"] and i.departments == expected["departments"]), None)
        if match:
            tally[0] += 1
            stray.remove(match)
        else:
            report["missed"].append(expected)
    leftovers = [i for group in issues_by_key.values() for i in group]
    report["false_alarms"] += [{"key": i.key, "issues": [i.kind], "field": i.field} for i in leftovers]
    titled = answer.get("title_row")
    if titled and result.departments_read[titled]["header_row"] != 2:
        report["missed"].append({"kind": "title_row", "departments": [titled]})
    report["passed"] = not report["missed"] and not report["false_alarms"] and report["clean_exact"] == report["clean_keys"]
    return report


def holdout(sets: int) -> dict:
    totals = {"sets": sets, "passed_sets": 0, "clean_exact": [0, 0], "faults": {}, "classes": {}}
    for _ in range(sets):
        seed = secrets.randbits(63)  # never printed or stored
        with tempfile.TemporaryDirectory() as tmp:
            sheets, answer = generate(seed)
            for department, rows in sheets.items():
                book = openpyxl.Workbook()
                for row in rows:
                    book.active.append(row)
                buffer = io.BytesIO()
                book.save(buffer)
                (Path(tmp) / f"{department}.xlsx").write_bytes(buffer.getvalue())
            report = grade(Path(tmp), answer)
        totals["passed_sets"] += report["passed"]
        totals["clean_exact"][0] += report["clean_exact"]
        totals["clean_exact"][1] += report["clean_keys"]
        for label, count in report["classes"].items():
            totals["classes"][label] = totals["classes"].get(label, 0) + count
        for kind, (hit, total) in report["faults"].items():
            tally = totals["faults"].setdefault(kind, [0, 0])
            tally[0] += hit
            tally[1] += total
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tuning")
    grade_cmd = sub.add_parser("grade")
    grade_cmd.add_argument("directory", type=Path)
    holdout_cmd = sub.add_parser("holdout")
    holdout_cmd.add_argument("--sets", type=int, default=5)
    args = parser.parse_args()
    if args.command == "tuning":
        for seed in TUNING_SEEDS:
            write(seed, TUNING / f"seed-{seed}")
            print(f"seed {seed}: {json.dumps(grade(TUNING / f'seed-{seed}'), ensure_ascii=False)}")
    elif args.command == "grade":
        report = grade(args.directory)
        print(json.dumps(report, ensure_ascii=False, indent=1))
        sys.exit(0 if report["passed"] else 1)
    else:
        totals = holdout(args.sets)
        print(json.dumps(totals, ensure_ascii=False))
        sys.exit(0 if totals["passed_sets"] == totals["sets"] else 1)


if __name__ == "__main__":
    main()
