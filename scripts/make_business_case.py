"""Generate a transparent business-demo test group, not the held-out acceptance set."""
from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def constant(value):
    return {"op": "constant", "value": value}


def measure(department, *measures):
    return {"op": "sum" if len(measures) == 1 else "sum_product", "department": department, "measures": list(measures)}


def arithmetic(op, a, b):
    return {"op": op, "args": [a, b]}


def ratio(a, b):
    return arithmetic("multiply", arithmetic("divide", a, b), constant(100))


def generate(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    used, capacity = measure("production", "used_hours"), measure("production", "available_hours")
    price = measure("procurement", "unit_price", "purchase_quantity")
    budget = measure("procurement", "budget_price", "purchase_quantity")
    sales, cost = measure("finance", "sales_amount"), measure("finance", "cost_amount")
    orders, output = measure("marketing", "order_quantity"), measure("production", "output_quantity")
    definitions = {
        "total_output": ("units", "sum(output quantity)", output),
        "capacity_utilisation": ("%", "sum(used hours) / sum(available hours) * 100", ratio(used, capacity)),
        "capacity_headroom": ("hours", "sum(available hours) - sum(used hours)", arithmetic("subtract", capacity, used)),
        "material_spend": ("SGD", "sum(unit price * purchase quantity)", price),
        "purchase_budget": ("SGD", "sum(budget unit price * purchase quantity)", budget),
        "purchase_price_drift": ("%", "(actual spend - budget spend) / budget spend * 100", ratio(arithmetic("subtract", price, budget), budget)),
        "sales": ("SGD", "sum(sales amount); cost is a separate measurement", sales),
        "cost_of_sales": ("SGD", "sum(cost amount), positive cost convention", cost),
        "gross_margin": ("%", "(sales - positive costs) / sales * 100", ratio(arithmetic("subtract", sales, cost), sales)),
        "ar_weighted_days": ("days", "sum(AR balance * AR days) / sum(AR balance)", arithmetic("divide", measure("finance", "ar_balance", "ar_days"), measure("finance", "ar_balance"))),
        "order_gap": ("units", "sum(order quantity) - sum(output quantity)", arithmetic("subtract", orders, output)),
        "requested_terms_days": ("days", "sum(order quantity * requested days) / sum(order quantity)", arithmetic("divide", measure("marketing", "order_quantity", "requested_days"), orders)),
    }
    columns = {"production": {"sku": "sku", "line": "capacity_unit"},
               "procurement": {"material": "raw_material"},
               "finance": {"project": "sku"}, "marketing": {"product": "sku", "customer": "customer"}}
    measures = {"production": {"output": "output_quantity", "used_hrs": "used_hours", "available_hrs": "available_hours"},
                "procurement": {"price": "unit_price", "budget_price": "budget_price", "qty": "purchase_quantity"},
                "finance": {"sales": "sales_amount", "cost": "cost_amount", "ar_balance": "ar_balance", "ar_days": "ar_days"},
                "marketing": {"qty": "order_quantity", "terms": "requested_days"}}
    role_specs = {
        "production": ("核对可交付产量、实际工时与可用工时，提出排产处置；不得批准加班预算或承诺客户交期。", "operations_director", ["可用工时按每条班次记录一次", "负余量表示排产超出已声明可用工时"]),
        "procurement": ("核对采购实际支出与预算价格偏差，提出询价或预算复核；不得自行改销售报价。", "procurement_manager", ["仅比较同批采购数量下的预算与实际价格", "缺价、缺数量、币种不符必须拒绝总额"]),
        "finance": ("核对项目收入、正数成本与余额加权账期，提出利润或信用复核；不得认定客户已构成坏账。", "finance_controller", ["成本独立于收入，不净额冒充收入", "账期指标不是逾期账龄，也不等于坏账概率"]),
        "marketing": ("核对订单数量与本期产出差额、客户请求账期，提出交期和信用协商；不得自行分层客户或批准授信。", "sales_director", ["订单差额只是同期间总量比较，不是物料齐套或客户级交付保证", "客户请求账期未获批准"]),
    }
    raw_checks = [
        ("capacity", "production", "capacity_utilisation", "above", 100, "排产负荷", "提交排产与加班预算复核", "维持已批准排产"),
        ("headroom", "production", "capacity_headroom", "below", 0, "剩余工时", "暂停额外产能承诺并核实班次", "按已核实余量评估新增需求"),
        ("spend", "procurement", "material_spend", "above", "purchase_budget", "采购预算", "提交采购超预算说明", "记录预算内采购结果"),
        ("price", "procurement", "purchase_price_drift", "above", 5, "采购价格偏差", "发起供应商复议并通知财务", "继续监测已声明采购价格"),
        ("margin", "finance", "gross_margin", "below", 0, "项目毛利", "发起成本与售价联合复核", "记录正毛利并持续核对成本"),
        ("receivables", "finance", "ar_weighted_days", "above", 45, "应收账期", "核实合同账期并复核信用敞口", "按现行信用政策跟踪回款"),
        ("fulfilment", "marketing", "order_gap", "above", 0, "订单与产出差额", "与生产核对未覆盖需求后协商交期", "核实品项匹配后维持交付沟通"),
        ("terms", "marketing", "requested_terms_days", "above", 45, "客户请求账期", "提交财务审批且暂不承诺延长账期", "按已批准账期规则沟通客户"),
    ]
    checks = []
    for key, role, metric, comparison, threshold, title, attention, normal in raw_checks:
        checks.append({"id": key, "owner": role, "metric": metric, "attention_when": comparison,
            "threshold_metric" if isinstance(threshold, str) else "threshold": threshold,
            "title": title, "actions": {"attention": [attention], "ok": [normal]}})
    dictionary = {"columns": columns, "measures": measures,
        "rollups": {meaning: "average" if meaning in ("unit_price", "budget_price", "ar_days", "requested_days") else "sum"
                    for department in measures.values() for meaning in department.values()},
        "relations": [{"source": "sku:sku-a1", "target": "raw_material:rm-a", "relation": "consumes", "note": "Synthetic declared BOM"}],
        "business_review": {"case": "合成制造企业月度交付与利润复核；非客户数据",
            "inputs": {role: {"date_column": "date", "nonnegative_columns": list(measures[role]), **({"currency": {"column": "currency", "value": "SGD"}} if role in ("procurement", "finance", "marketing") else {})} for role in role_specs},
            "metrics": {key: {"unit": unit, "formula": formula, "expression": expr} for key, (unit, formula, expr) in definitions.items()},
            "roles": {role: {"responsibility": brief, "decision_owner": owner, "constraints": constraints,
                "unsupported_topics": ["计提", "减值", "坏账概率", "健康水平", "信用敞口扩大", "信用敞口缩小"] if role == "finance" else []}
                for role, (brief, owner, constraints) in role_specs.items()},
            "checks": checks, "manager_decision": "由运营负责人协调排产，采购负责人解释预算差异，财务负责人复核利润及信用，销售负责人据批准结果沟通客户；本报告不自动执行订单、报价或授信。",
            "limitations": ["合成数据用于业务用例设计，不代表真实 OA 验收", "采购偏差相对同数量预算，不是月环比", "缺少存货、BOM 用量及历史回款，不能判断物料齐套或坏账", "不生成价格带、客户 Tier 或自动调整账期"]}}
    (destination / "dictionary.yaml").write_text(yaml.safe_dump(dictionary, allow_unicode=True, sort_keys=False), encoding="utf-8")
    expected = {}
    for name, stressed in (("risk", True), ("balanced", False)):
        folder = destination / name
        folder.mkdir(exist_ok=True)
        data = {
            "production": (["sku", "line", "date", "output", "used_hrs", "available_hrs"], [
                ["SKU-A1", "LINE-A", "2025-11-03", 60, 48 if stressed else 30, 40],
                ["sku-a1", "LINE-A", "2025-11-04", 40, 32 if stressed else 25, 30],
                ["SKU-B2", "LINE-B", "2025-11-03", 30, 18 if stressed else 15, 20],
                ["SKU-B2", "LINE-B", "2025-11-04", 20, 12 if stressed else 10, 10]]),
            "procurement": (["material", "date", "qty", "price", "budget_price", "currency"], [
                ["RM-A", "2025-11-02", 10, 12 if stressed else 10, 10, "SGD"],
                ["RM-A", "2025-11-09", 20, 12 if stressed else 10, 10, "SGD"],
                ["RM-B", "2025-11-02", 10, 20, 20, "SGD"], ["RM-B", "2025-11-09", 10, 20, 20, "SGD"]]),
            "finance": (["project", "date", "sales", "cost", "ar_balance", "ar_days", "currency"], [
                ["SKU-A1", "2025-11-30", 1800, 2000 if stressed else 1200, 800, 60 if stressed else 30, "SGD"],
                ["SKU-B2", "2025-11-30", 1200, 1300 if stressed else 800, 600, 30, "SGD"]]),
            "marketing": (["product", "customer", "date", "qty", "terms", "currency"], [
                ["SKU-A1", "ACME", "2025-11-05", 120 if stressed else 90, 60 if stressed else 30, "SGD"],
                ["SKU-B2", "BETA", "2025-11-05", 60 if stressed else 40, 30, "SGD"]]),
        }
        for role, (headers, rows) in data.items():
            with (folder / f"{role}.csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file, lineterminator="\n"); writer.writerow(headers); writer.writerows(rows)
        # Independent oracle: explicit arithmetic, never the application's evaluator.
        D = Decimal
        expected[name] = {"period": "2025-11", "metric_values": {
            "total_output": 150, "capacity_utilisation": 110 if stressed else 80,
            "capacity_headroom": -10 if stressed else 20, "material_spend": 760 if stressed else 700,
            "purchase_budget": 700, "purchase_price_drift": float(round(D(60) / D(700) * 100, 4)) if stressed else 0,
            "sales": 3000, "cost_of_sales": 3300 if stressed else 2000,
            "gross_margin": -10 if stressed else float(round(D(1000) / D(3000) * 100, 4)),
            "ar_weighted_days": float(round(D(800 * 60 + 600 * 30) / D(1400), 4)) if stressed else 30,
            "order_gap": 30 if stressed else -20, "requested_terms_days": 50 if stressed else 30},
            "check_status": "attention" if stressed else "ok", "roles": list(role_specs),
            "must_not_claim": ["客户 Tier", "坏账认定", "已执行订单或价格变更", "审批即重写旧批次"]}
    (destination / "expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "README.md").write_text("# 业务演示测试组\n\n由 `scripts/make_business_case.py` 生成，属于可见开发/演示数据，不是留出验收集。\n\n"
        "分别导入 risk 或 balanced 下四份 CSV，月份选 2025-11，字典使用本目录 dictionary.yaml。\n\n"
        "**字典不是可选项。** 只有本目录这份声明了 finance 的可连接列（project）与 business_review 契约；\n"
        "默认字典两样都没有，用它导入会得到 needs_configuration，研判起不来（第 1 步过、第 2 步不可能）。\n"
        "用 `python3 scripts/start_web.py --demo` 启动，或导出 FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml\n"
        "（路径相对仓库根解析，不是相对你所在的目录）。\n\n"
        "expected.json 是人工复核答案，不得作为模型输入。修改数据后应重新生成并核对。\n"
        "该组覆盖同批四部门责任；不宣称真实客户科目、库存齐套、授信或报价验收。\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/business_demo")
    generate(parser.parse_args().output)
