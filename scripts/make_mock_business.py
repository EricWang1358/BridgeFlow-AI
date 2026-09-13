"""模拟「真实月度导出」：一家虚构商砼公司三个月的四部门报表与人工总表（#141）。

业务方还没有给出真实导出。这里按行业常识编一套**账能对上**的月度数据，代替真实样板演示调优与留出流程：

- 两个搅拌站、四个项目（C30/C35/C40），每个项目按日填报生产部的发货记录；
- 物资部按配合比与当月材料价测算单方成本，材料含量 kg/方、单价 元/吨，水泥、矿粉、粉煤灰、外加剂按 13% 进项、砂石按 3%；
- 市场部结算滞后一个月、次月回款约为上月结算额的 80%，不同客户回款习惯不同；
- 财务部应收账款的期末余额与市场部总欠款一致，资金占用利息按垫资额 × 4.35% ÷ 12；
- 比率保留 4 位小数、金额 2 位、方量 1 位，就像人手工填的那样。

`expected.xlsx` 是「人工核对后的总表」：每个单元格都按业务口径直接算出，不调用 `bridgeflow.integration`。
部门表里故意留了几处真实填报常见的错误（见 README），总表里写的是**正确值**，评分时这些位置应被系统拦下。

所有单位、项目与人名均为虚构，不对应任何真实企业或个人。

    python scripts/make_mock_business.py                # 写到 data/mock_business/monthly/
    python scripts/integration_cases.py real data/mock_business/monthly/2024-05-调优A
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from bridgeflow.integration import load_spec

TEMPLATES = ROOT / "data" / "company_templates"
OUT = ROOT / "data" / "mock_business" / "monthly"
D = Decimal


def q(value, places: int) -> Decimal:
    return D(value).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def plain(value: Decimal):
    return int(value) if value == value.to_integral_value() else float(value)


# --- 业务设定 -----------------------------------------------------------------------------

VAT = D("0.13")
MONTHS = [("2024-05", "调优A"), ("2024-06", "调优B"), ("2024-07", "模拟留出")]
PROCESSING = D("50")        # 运输、泵送与制造费用，元/方（财务结转口径）
INTEREST = D("0.0435")      # 一年期贷款市场报价利率口径，年化
PREPAY_DISCOUNT = D("0.985")

MATERIALS = ["水泥 P·O42.5", "矿粉 S95", "粉煤灰 F类Ⅱ级", "机制砂", "碎石 5-25mm", "聚羧酸减水剂"]
INPUT_VAT = [D("0.13"), D("0.13"), D("0.13"), D("0.03"), D("0.03"), D("0.13")]
#: 含税到厂价，元/吨，按月
MATERIAL_PRICE = {
    "2024-05": [400, 260, 150, 85, 75, 2400],
    "2024-06": [415, 260, 150, 88, 75, 2400],
    "2024-07": [405, 255, 150, 88, 78, 2350],
}
#: 配合比，kg/方
MIX = {"C30": [280, 70, 80, 800, 1030, D("6.0")], "C35": [320, 70, 70, 770, 1040, D("6.8")], "C40": [360, 80, 60, 730, 1050, D("7.6")]}
DENSITY = {"C30": 2390, "C35": 2400, "C40": 2410}


@dataclass
class Project:
    code: str
    name: str
    customer_code: str
    customer: str
    grade: str
    plant: str
    price: Decimal           # 合同含税单价，元/方
    manager: str
    april_actual: Decimal    # 2024-04 实际量，方
    base_output: Decimal     # 截至 2024-04 累计产值
    base_received: Decimal   # 截至 2024-04 累计收款
    ytd_debit: Decimal       # 2024-01~04 应收借方累计
    ytd_credit: Decimal      # 2024-01~04 应收贷方累计
    monthly_actual: dict     # 月份 → 目标实际量
    sign_rate: dict          # 月份 → 现场签收率
    pay_habit: Decimal       # 实际回款 / 应回款（80% × 上月结算）
    status: dict
    finish: str
    terms: str
    supplier_terms: str


PROJECTS = [
    Project("PRJ2024011", "滨江安置房二期", "CUST0103", "示例建工第一分公司", "C30", "东区拌站", D(390), "王磊",
            D("5200"), D("6240000"), D("4680000"), D("6240000"), D("4680000"),
            {"2024-05": 5500, "2024-06": 5650, "2024-07": 5600}, {"2024-05": "0.994", "2024-06": "0.992", "2024-07": "0.993"},
            D("1.00"), {m: "在供" for m, _ in MONTHS}, "2024-12-31",
            "按月结算，次月25日前支付当月结算额的80%，主体封顶后付至90%，竣工结算后付至97%，余3%质保金满一年付清",
            "水泥月结，次月15日前付清；砂石款到发货"),
    Project("PRJ2024017", "高新区产业园三号厂房", "CUST0211", "示例城建集团有限公司", "C35", "西区拌站", D(405), "李娜",
            D("3600"), D("2916000"), D("2040000"), D("2916000"), D("2040000"),
            {"2024-05": 3950, "2024-06": 4400, "2024-07": 4900}, {"2024-05": "0.991", "2024-06": "0.989", "2024-07": "0.990"},
            D("0.90"), {m: "在供" for m, _ in MONTHS}, "2025-03-31",
            "按月结算，次月底前支付当月结算额的80%，竣工验收后付至95%，余5%质保金两年内付清",
            "水泥预付30%，到货后月结"),
    Project("PRJ2024023", "市政道路改造一标段", "CUST0156", "示例市政工程有限公司", "C40", "东区拌站", D(430), "王磊",
            D("2100"), D("3612000"), D("1806000"), D("3612000"), D("1806000"),
            {"2024-05": 2200, "2024-06": 2150, "2024-07": 2050}, {"2024-05": "0.975", "2024-06": "0.962", "2024-07": "0.931"},
            D("0.60"), {m: "在供" for m, _ in MONTHS}, "2024-10-31",
            "按月结算，结算后60日内支付70%，工程决算审计完成后付至95%",
            "水泥月结，次月15日前付清；外加剂季度结算"),
    Project("PRJ2023098", "第二实验学校扩建", "CUST0089", "示例教育建设有限公司", "C30", "西区拌站", D(385), "赵敏",
            D("2600"), D("7700000"), D("6930000"), D("7700000"), D("6930000"),
            {"2024-05": 2450, "2024-06": 2250, "2024-07": 1350}, {"2024-05": "0.990", "2024-06": "0.988", "2024-07": "0.985"},
            D("0.80"), {"2024-05": "在供", "2024-06": "在供", "2024-07": "收尾"}, "2024-08-15",
            "按月结算，次月支付当月结算额的80%，竣工后三个月内付至97%",
            "水泥月结，次月15日前付清"),
]


def diagnosis(rate: Decimal, growth: Decimal) -> str:
    """与 integration.yaml 的规则表同一口径，但在这里独立写一遍。"""
    if rate < D("0.95"):
        return "签收异常"
    if growth <= D("-0.2"):
        return "合作萎缩"
    if growth < D("-0.05"):
        return "需求下滑"
    if growth >= D("0.05"):
        return "稳定增长"
    return "平稳合作"


# --- 按月推演 -------------------------------------------------------------------------------


def simulate() -> dict:
    """{月份: {项目编号: {"master": 总表字段→值, "days": [生产部日记录]}}}"""
    rng = random.Random(20240501)
    state = {p.code: {"output": p.base_output, "received": p.base_received, "last_actual": p.april_actual,
                      "last_billed": q(p.april_actual * p.price, 2), "debit": p.ytd_debit, "credit": p.ytd_credit}
             for p in PROJECTS}
    months: dict = {}
    for month, _ in MONTHS:
        months[month] = {}
        prices = [D(x) for x in MATERIAL_PRICE[month]]
        for p in PROJECTS:
            s = state[p.code]
            # 生产部：按日发货。每天的生产量、余料与现场签收各自取整到 0.5 方。
            target = D(p.monthly_actual[month])
            rate = D(p.sign_rate[month])
            n_days = rng.randint(4, 6)
            weights = [rng.uniform(0.7, 1.3) for _ in range(n_days)]
            days = []
            for i, w in enumerate(weights):
                shipped = q(target / rate * D(str(w / sum(weights))) * 2, 0) / 2
                produced = shipped + q(D(str(rng.uniform(2, 8))) * 2, 0) / 2
                actual = q(shipped * rate * 2, 0) / 2
                day = 3 + i * (26 // n_days)
                days.append({"date": f"{month}-{day:02d}", "produced": produced, "shipped": shipped, "actual": actual})
            produced = sum((d["produced"] for d in days), D(0))
            shipped = sum((d["shipped"] for d in days), D(0))
            actual = sum((d["actual"] for d in days), D(0))
            sign = actual / shipped
            growth = (actual - s["last_actual"]) / s["last_actual"]

            # 物资部：配合比 × 当月价
            mix = MIX[p.grade]
            taxed = q(sum((prices[i] * D(mix[i]) / 1000 for i in range(6)), D(0)), 2)
            untaxed = q(sum((prices[i] / (1 + INPUT_VAT[i]) * D(mix[i]) / 1000 for i in range(6)), D(0)), 2)
            material_total = q(produced * untaxed, 2)
            margin = q(p.price / (1 + VAT) - untaxed, 2)

            # 市场部：结算滞后一月；回款 = 上月结算 × 80% × 客户回款习惯
            billed = q(actual * p.price, 2)
            receipt = q(s["last_billed"] * D("0.8") * p.pay_habit, -3)
            output = s["output"] + billed
            settled = output - billed
            received = s["received"] + receipt
            contract_debt = settled - received
            total_debt = output - received
            confirmed, likely, possible = (q(contract_debt * D(x), -3) for x in ("0.40", "0.25", "0.15"))
            plan_total = received + confirmed + likely + possible

            # 财务部：应收账款明细账与项目损益
            opening = s["output"] - s["received"]
            revenue = q(actual * p.price / (1 + VAT), 2)
            cost = q(material_total + produced * PROCESSING, 2)
            interest = q(total_debt * INTEREST / 12, 2)

            master = {
                "项目名称": p.name, "客户名称": p.customer, "项目编号": p.code, "客户代码": p.customer_code, "报表年月": month,
                "产品名称": p.grade, "产品代码": f"PRD-{p.grade}",
                "财务_期初金额": opening, "财务_期初方向": "借", "财务_本期借方金额": billed, "财务_本期贷方金额": receipt,
                "财务_本年累计借方金额": s["debit"] + billed, "财务_本年累计贷方金额": s["credit"] + receipt,
                "财务_期末余额": opening + billed - receipt, "财务_期末方向": "借",
                "财务_本期实现收入": revenue, "财务_本期实际成本": cost, "财务_资金占用利息成本": interest,
                "财务_项目财务净利润": revenue - cost - interest,
                "市场_负责人": p.manager, "市场_付款比例": "80%" if "80%" in p.terms else "70%",
                "市场_在供完工状态": p.status[month], "市场_完工时间": p.finish, "市场_合同条款": p.terms,
                "市场_累计产值": output, "市场_累计结算": settled, "市场_累计收款": received,
                "市场_合同欠款": contract_debt, "市场_总欠款": total_debt,
                "市场_已到账": received, "市场_已落实": confirmed, "市场_有把握": likely, "市场_可争取": possible,
                "市场_收款计划合计": plan_total, "市场_缺口": settled - plan_total,
                "市场_产值收款率": q(received / output, 4), "市场_结算收款率": q(received / settled, 4),
                "市场_合同销售单价": p.price, "市场_当前垫资额": total_debt, "市场_垫资比例": q(total_debt / output, 4),
                "生产_厂站": p.plant, "生产_生产量": produced, "生产_出厂量": shipped, "生产_实际量": actual,
                "生产_备注": "供应正常" if sign >= D("0.95") else "现场签收偏低，部分车次退料待核",
                "生产_上月实际量": s["last_actual"], "生产_实际签收率": q(sign, 4), "生产_产量环比增长率": q(growth, 4),
                "生产_客户合作状态诊断": diagnosis(sign, growth),
                "物资_付款比例": p.supplier_terms,
                **{f"物资_材料{chr(65 + i)}": MATERIALS[i] for i in range(6)},
                **{f"物资_材料{chr(65 + i)}单价": prices[i] for i in range(6)},
                **{f"物资_材料{chr(65 + i)}含量": D(mix[i]) for i in range(6)},
                "物资_容重": D(DENSITY[p.grade]), "物资_不含税成本": untaxed, "物资_含税成本": taxed,
                "物资_预付款含税成本": q(taxed * PREPAY_DISCOUNT, 2),
                "物资_备注": "水泥价格较上月上涨" if month == "2024-06" else "原材料价格基本平稳",
                "物资_当月生产量": produced, "物资_当月物资总成本": material_total, "物资_单方不含税毛利": margin,
            }
            months[month][p.code] = {"master": master, "days": days}
            s.update(output=output, received=received, last_actual=actual, last_billed=billed,
                     debit=s["debit"] + billed, credit=s["credit"] + receipt)
    return months


# --- 部门表里的真实填报错误（总表写正确值） -----------------------------------------------------------

PLANTED = {
    "2024-06": [("marketing", "PRJ2023098", "row", None, "市场部本月漏填该项目（项目收尾，负责人休假）")],
    "2024-07": [
        ("production", "PRJ2024017", "客户名称", "示例城建集团", "生产部客户单位写了简称"),
        ("procurement", "PRJ2024023", "物资_当月生产量", "plan", "物资部按排产计划量而非实际生产量测算"),
        ("marketing", "PRJ2024011", "市场_可争取", "待定", "市场部可争取金额填了文字"),
    ],
}


def _write_department(spec, department: str, month: str, projects: dict, headers: list[str], path: Path) -> None:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    sheet.append(headers)
    planted = [p for p in PLANTED.get(month, []) if p[0] == department]
    for code, record in projects.items():
        if any(p[1] == code and p[2] == "row" for p in planted):
            continue
        values = dict(record["master"])
        for _, target, name, wrong, _ in planted:
            if target == code and name != "row":
                values[name] = values[name] * D("1.08") if wrong == "plan" else wrong
        if department == "production":
            rows = []
            for day in record["days"]:
                row_values = dict(values, 生产_生产量=day["produced"], 生产_出厂量=day["shipped"], 生产_实际量=day["actual"], 生产_实际签收率=q(day["actual"] / day["shipped"], 4))
                rows.append((row_values, day["date"]))
        else:
            rows = [(values, None)]
        for row_values, date in rows:
            row: list = [None] * len(headers)
            for name, decl in spec.fields.items():
                ref = decl.sources.get(department)
                if ref is None or row_values.get(name) is None:
                    continue
                if ref.period_from:
                    year, mon = row_values[name].split("-")
                    row[headers.index(ref.period_from[0])], row[headers.index(ref.period_from[1])] = int(year), int(mon)
                    continue
                index = [i for i, h in enumerate(headers) if h == ref.column][ref.occurrence - 1]
                value = row_values[name]
                row[index] = plain(value) if isinstance(value, Decimal) else value
            if date and "日期" in headers:
                row[headers.index("日期")] = date
            sheet.append(row)
    for column_cells in sheet.iter_cols(min_row=2):
        header = headers[column_cells[0].column - 1]
        if header.endswith("率") or header == "垫资比例":
            for cell in column_cells:
                cell.number_format = "0.00%"
    book.save(path)


def main() -> None:
    spec = load_spec(TEMPLATES / "integration.yaml")
    master_headers = [c.value for c in openpyxl.load_workbook(TEMPLATES / spec.master_template).active[1]]
    months = simulate()
    for month, label in MONTHS:
        folder = OUT / f"{month}-{label}"
        folder.mkdir(parents=True, exist_ok=True)
        for department, decl in spec.departments.items():
            template = openpyxl.load_workbook(TEMPLATES / decl.template).active
            headers = [str(c.value or "").strip() for c in template[1]]
            _write_department(spec, department, month, months[month], headers, folder / f"{decl.label}.xlsx")
        book = openpyxl.Workbook()
        book.active.title = "总表"
        book.active.append(master_headers)
        for record in months[month].values():
            book.active.append([plain(v) if isinstance(v, Decimal) else v for v in (record["master"][h] for h in master_headers)])
        book.save(folder / "expected.xlsx")
        print(f"wrote {folder.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
