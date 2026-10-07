"""Quarters and years read back from their months (#301).

The fictional supplier has three months: 2024-05 and 2024-06 (sample history) and 2024-07
(the sample case). Nothing calls a model; every figure is recomputed from the frozen batches.
"""
from copy import deepcopy
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from bridgeflow import business
from bridgeflow.api.main import app
from bridgeflow.conclusions import aggregate
from bridgeflow.conclusions.grain import Calendar, containing, parse
from bridgeflow.config import REPO_ROOT, settings

FISCAL_APRIL = Calendar(4)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mock_business/demo/dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def months(client):
    """Batch ids of the three sample months, July being the one a person opens."""
    history = client.post("/batches/demo/history").json()
    ids = {item["period"]: item["batch_id"] for item in history["imported"]}
    ids["2024-07"] = client.post("/batches/demo").json()["batch_id"]
    return ids


def facts(column: dict) -> dict:
    return {fact["metric"]: fact for fact in column["facts"]}


# --- the calendar --------------------------------------------------------------------------


def test_a_month_falls_in_its_quarter_and_year():
    quarter = containing("2024-08", "quarter")
    assert quarter.key == "2024-Q3" and quarter.months() == ["2024-07", "2024-08", "2024-09"]
    assert containing("2024-08", "year").months()[0] == "2024-01"
    assert quarter.prior().key == "2024-Q2" and quarter.last_year().key == "2023-Q3"
    assert containing("2024-01", "quarter").prior().key == "2023-Q4"


def test_a_fiscal_year_is_named_after_the_year_it_starts_in():
    assert containing("2024-03", "year", FISCAL_APRIL).key == "FY2023"
    assert containing("2024-03", "quarter", FISCAL_APRIL).key == "FY2023-Q4"
    assert parse("FY2023", FISCAL_APRIL).months() == [f"2023-{m:02d}" for m in range(4, 13)] + ["2024-01", "2024-02", "2024-03"]
    assert parse("FY2024-Q1", FISCAL_APRIL).months() == ["2024-04", "2024-05", "2024-06"]


def test_a_key_from_the_other_calendar_is_refused_rather_than_reinterpreted():
    with pytest.raises(HTTPException):
        parse("FY2024", Calendar())
    with pytest.raises(HTTPException):
        parse("2024-Q1", FISCAL_APRIL)
    with pytest.raises(HTTPException):
        Calendar.declared({"business_review": {"calendar": {"fiscal_year_start_month": 13}}})


# --- adding months up -----------------------------------------------------------------------


def test_a_ratio_over_a_year_is_recomputed_from_its_parts_not_averaged(client, months):
    from bridgeflow.api.batches import load_batch

    result = client.get(f"/conclusions/batches/{months['2024-07']}/periods?grain=year&count=2").json()
    year = facts(result["columns"][-1])["net_margin"]
    batches = [load_batch(months[m]) for m in ("2024-05", "2024-06", "2024-07")]
    profit = sum((business.expression({"op": "sum", "department": "finance", "measures": ["net_profit"]}, b).number
                  for b in batches), Decimal(0))
    revenue = sum((business.expression({"op": "sum", "department": "finance", "measures": ["revenue"]}, b).number
                   for b in batches), Decimal(0))
    assert year["state"] == "computed"
    assert year["value"] == float(round(profit / revenue * 100, 4))
    monthly = [business.context(months[m], b)["facts"]["net_margin"]["value"]
               for m, b in zip(("2024-05", "2024-06", "2024-07"), batches, strict=True)]
    assert year["value"] != pytest.approx(sum(monthly) / 3)
    # The evidence sample reaches into more than one month, and the count is every cell.
    assert len({ref["period"] for ref in year["sources"]}) > 1
    assert year["source_count"] > len(year["sources"])


def test_a_balance_is_read_at_the_latest_month_not_summed(client, months):
    query = f"/conclusions/batches/{months['2024-07']}/periods?count=2&metrics=advance_ratio&grain="
    july, year = client.get(query + "month").json(), client.get(query + "year").json()
    advance = facts(year["columns"][-1])["advance_ratio"]
    assert advance["as_of"] == "2024-07"
    assert advance["value"] == facts(july["columns"][-1])["advance_ratio"]["value"]


def test_a_metric_declared_month_only_says_why_instead_of_a_figure(client, months):
    result = client.get(f"/conclusions/batches/{months['2024-07']}/periods?grain=quarter&count=2").json()
    receivable = facts(result["columns"][-1])["receivable_months"]
    assert receivable["state"] == "month_only" and receivable["value"] is None and receivable["reason"]


def test_a_partial_year_shows_which_months_it_has_and_which_it_lacks(client, months):
    result = client.get(f"/conclusions/batches/{months['2024-07']}/periods?grain=year&count=2").json()
    coverage = result["columns"][-1]["coverage"]
    assert coverage["present"] == ["2024-05", "2024-06", "2024-07"]
    assert coverage["missing"] == [f"2024-{m:02d}" for m in range(1, 5)]
    assert coverage["considered"][-1] == "2024-07" and len(coverage["months"]) == 12
    assert coverage["complete"] is False
    assert coverage["batch_ids"]["2024-06"] == months["2024-06"]


# --- comparing -------------------------------------------------------------------------------


def test_month_grain_agrees_with_the_existing_month_comparison(client, months):
    batch = months["2024-07"]
    old = {m["metric"]: m for m in client.get(f"/conclusions/batches/{batch}/comparison").json()["metrics"]}
    new = client.get(f"/conclusions/batches/{batch}/period-comparison?grain=month&base=prior").json()
    assert new["status"] == "compared" and new["base_period"] == "2024-06"
    for change in new["changes"]:
        expected = old[change["metric"]]
        assert (change["current"], change["base"], change["absolute"], change["basis"]) == \
               (expected["current"], expected["base"], expected["absolute"], expected["basis"])


def test_a_base_without_the_same_months_is_not_compared(client, months):
    batch = months["2024-07"]
    prior = client.get(f"/conclusions/batches/{batch}/period-comparison?grain=quarter&base=prior").json()
    # Q3 has July only, so the base is April alone — which was never imported.
    assert prior["status"] == "no_base" and prior["changes"] == [] and "2024-04" in prior["reason"]
    assert prior["base"]["coverage"]["considered"] == ["2024-04"]
    last_year = client.get(f"/conclusions/batches/{batch}/period-comparison?grain=year&base=last_year").json()
    assert last_year["status"] == "no_base" and last_year["base_period"] == "2023"


def test_neighbouring_months_compare_and_incomplete_quarters_do_not(client, months):
    batch = months["2024-07"]
    by_month = client.get(f"/conclusions/batches/{batch}/periods?grain=month&count=3").json()
    assert [c["period"] for c in by_month["columns"]] == ["2024-05", "2024-06", "2024-07"]
    assert {c["state"] for c in by_month["changes"] if c["metric"] == "net_margin"} == {"compared"}
    by_quarter = client.get(f"/conclusions/batches/{batch}/periods?grain=quarter&periods=2024-Q2,2024-Q3").json()
    assert {c["state"] for c in by_quarter["changes"]} == {"incomplete"}


def test_the_agent_tool_reads_the_same_comparison_the_page_shows(client, months):
    batch = months["2024-07"]
    page = client.get(f"/conclusions/batches/{batch}/period-comparison?grain=month&base=prior&metrics=net_margin").json()
    tool = client.post("/tools/compare-periods", json={"batch_id": batch, "grain": "month", "base": "prior",
                                                       "metrics": ["net_margin"]}).json()
    assert tool == page and [c["metric"] for c in tool["changes"]] == ["net_margin"]


def test_requests_outside_what_is_declared_or_known_are_refused(client, months):
    batch = months["2024-07"]
    unknown = client.get(f"/conclusions/batches/{batch}/periods?grain=quarter&metrics=profit")
    assert unknown.status_code == 422 and "net_margin" in unknown.json()["detail"]
    assert client.get(f"/conclusions/batches/{batch}/periods?grain=year&periods=FY2023,FY2024").status_code == 422
    assert client.get(f"/conclusions/batches/{batch}/periods?grain=quarter&periods=2024-Q3,2024-Q4").status_code == 422
    assert client.get(f"/conclusions/batches/{batch}/periods?grain=quarter&periods=2024-Q3,2024").status_code == 422


# --- the rules themselves, on borrowed months ------------------------------------------------
# A batch is only checked against its own month, so one month's batch can stand in for
# another here; that is what makes a complete like-for-like comparison possible in a test.


def _stand_ins(client, months, mapping: dict[str, str]):
    from bridgeflow.api.batches import load_batch
    loaded = {period: load_batch(batch_id) for period, batch_id in months.items()}
    return aggregate.Months(lambda month: (months[mapping[month]], loaded[mapping[month]]) if month in mapping else None)


def test_the_same_months_a_year_apart_compare_like_for_like(client, months):
    from bridgeflow.api.batches import load_batch
    declaration = load_batch(months["2024-07"]).dictionary_snapshot
    lookup = _stand_ins(client, months, {"2024-05": "2024-05", "2024-06": "2024-06",
                                         "2023-05": "2024-05", "2023-06": "2024-06"})
    result = aggregate.compare(parse("2024-Q2"), as_of="2024-06", base_kind="last_year",
                               metrics=["net_margin", "weighted_unit_margin"], declaration=declaration, months=lookup)
    assert result.status == "compared" and result.base.coverage.considered == ["2023-05", "2023-06"]
    assert {(c.metric, c.state, c.absolute) for c in result.changes} == {("net_margin", "compared", 0.0),
                                                                          ("weighted_unit_margin", "compared", 0.0)}


def test_an_undeclared_measure_gets_no_quarterly_figure(client, months):
    from bridgeflow.api.batches import load_batch
    declaration = deepcopy(load_batch(months["2024-07"]).dictionary_snapshot)
    del declaration["business_review"]["period_aggregation"]["measures"]["finance"]["revenue"]
    lookup = _stand_ins(client, months, {"2024-05": "2024-05", "2024-06": "2024-06"})
    result = aggregate.period_facts(parse("2024-Q2"), ["2024-05", "2024-06"], metrics=["net_margin", "sign_rate"],
                                    declaration=declaration, months=lookup)
    by_metric = {f.metric: f for f in result.facts}
    assert by_metric["net_margin"].state == "aggregation_undeclared" and "revenue" in by_metric["net_margin"].reason
    assert by_metric["sign_rate"].state == "computed"


def test_months_declaring_a_metric_differently_are_not_added_up(client, months):
    from bridgeflow.api.batches import load_batch
    june = load_batch(months["2024-06"])
    changed = june.model_copy(deep=True)
    changed.dictionary_snapshot["business_review"]["metrics"]["net_margin"]["formula"] = "a different formula"
    lookup = aggregate.Months(lambda month: {"2024-05": (months["2024-05"], load_batch(months["2024-05"])),
                                             "2024-06": (months["2024-06"], changed)}.get(month))
    result = aggregate.period_facts(parse("2024-Q2"), ["2024-05", "2024-06"], metrics=["net_margin"],
                                    declaration=june.dictionary_snapshot, months=lookup)
    assert result.facts[0].state == "declaration_changed" and "2024-06" in result.facts[0].reason
