# #301 计划：多时间粒度 + 目标对比 + 预测 + Agent 差距分析

状态：Q1–Q6 已定（2026-10-07，均按建议；Q6 首期只到 指标×周期）。PR A 实现中。　分支：`feature/multi-period-targets-301`

## 0. 现状（读代码结论）

- issue 提到的 `metrics.py` `change_mom`（#65）是**旧路径**：`CATALOGUE` + `/aggregate-metric` 无 `business_review` 时的兜底。
  产品里真正上看板的指标是 **`business_review.metrics`**：每个 batch 由 `business.context()` 按声明的表达式树算出 `facts`（带 `SourceRef`，含 batch/file/sheet/source_row）。
- 已有跨期能力在 `conclusions/`：
  - `comparison.py`：`BASES = PriorMonth | SameMonthLastYear | DeclaredPlan`；`DeclaredPlan` 目前直接拒绝（"No plan source is declared"，D5）——**目标就是缺的这个 plan 源**。
  - `charts.py` + `api/conclusions.py::_metric_series`：trend 只按月取点，缺月是 gap 不插值。
  - `periods.py`：batch 索引，`latest_for(period, …)` + `same_series` 找某月的 batch。
  - `brief.py`：`BriefDeclaration.key_metrics`（1–5 个）。
- 月以上全靠"一月一 batch"；没有季/年概念，`shift()` 只做月偏移。
- 审计/人工写入已有模式：`monthly/dispositions.py`（追加日志）+ `write_authorization.OPERATIONS` + `consume_approval`。
- Agent 输出已有校验模式：`business.validate_role`——数字只能在校验字段里，文字不许带数字，动作必须来自声明集合。
- **新发现（影响"周"）**：`business.data_blockers` 要求 `business_review.inputs.<dept>.date_column` 每行以 `YYYY-MM-` 开头 → 声明了 review 合同的源报表**已经带日期列**，`clean_tables` 行里也保留着。周粒度前提可能已满足，见 §9。

结论：新功能建在 `conclusions/` + `business.expression` 上，不动 `metrics.py` 旧路径。

## 1. 周期模型（新 `conclusions/grain.py`）

```python
Grain = Literal["month", "quarter", "year"]
class Period(BaseModel):
    grain: Grain
    key: str            # "2026-07" | "2026-Q3" | "2026"（财年见 §1.1）
    def months(self) -> list[str]   # 展开为 YYYY-MM
    def prior(self) -> Period       # 环比：上一同粒度周期
    def last_year(self) -> Period   # 同比：去年同期
```

- 季/年**一律由月 batch 汇总**，不存季/年 batch。
- 每月取 `periods.latest_for(month, visible & same_series)`；缺月 → 记入 `missing_months`，不补零。
- 参与汇总的各月 `declaration_differences` 必须为空，否则 `declaration_changed`（与现有月对比同口径）。

### 1.1 财年
- 字典新增 `business_review.calendar.fiscal_year_start_month`（默认 1 = 自然年）。
- key 仍写 `FY2026` / `FY2026-Q1`，`months()` 按起始月展开。待定项 Q2。

## 2. 跨期汇总（核心：比率不求平均）

`business.expression` 扩展为可接收多个 batch：

- `sum` / `sum_product` 叶子：对周期内每个月 batch 各自求和再相加；`SourceRef` 照旧带 `batch`，追溯不丢。
- `add/subtract/multiply/divide`：在**汇总后的叶子**上运算。
  → 毛利率 = (Σ销售 + Σ成本) ÷ Σ销售，自动满足"比率按分子分母重算"。
- 实现：抽一个 `MultiBatch` 视图（`clean_tables` 按部门聚合、`period` = 周期 key），单月就是长度 1，现有调用不变。

**存量/余额类**（期末余额、累计数）求和是错的。原计划按指标声明，读 demo 字典后改为**按度量（叶子）声明**：
`receivable_months = closing_balance ÷ period_debit` 一个公式里同时有余额和流量，指标级声明表达不了。

```yaml
business_review.period_aggregation:
  measures:            # 部门 → 度量 → flow | period_end | rate
    finance: {revenue: flow, closing_balance: period_end, ...}
  month_only:          # 指标 → 原因：公式本身跨期变义
    receivable_months: 应收月数是期末余额与当月开票之比；季度、年度需另定口径 …
```

- `flow`：跨月相加。`period_end`：取最近一个有数月，结果带 `as_of`。`rate`：只能在 `sum_product` 里与一个 flow/period_end 相乘（Σ 方量×单方毛利）。
- 叶子里 flow+period_end 必须恰好 1 个，否则拒绝。
- 未声明 → 季/年 `aggregation_undeclared` 拒绝（Q4）。月粒度不需要声明，行为与现有完全一致。
- `month_only`：公式跨期后含义变了（余额 ÷ **当月**开票 → 余额 ÷ 季度开票，单位都不对），声明原因，季/年显示原因不出数。

### 2.1 不完整周期（Q1 已定）
建议：**实际值只显示已到月份**，附 `coverage: {months_present: 2, months_total: 3, missing: [...]}`，不外推；"能不能完成"交给 §5 预测。完成度同时给两个口径：
- 实际 ÷ 全期目标（进度）
- 预测期末 ÷ 全期目标（预计完成度）

## 3. 对比视图 API

- `comparison.BASES` 泛化为粒度感知：`prior`（环比）、`last_year`（同比）、`target`（替换 `DeclaredPlan`）。月粒度行为与现在一致（回归测试守住）。
- 新端点（只读）：
  - `GET /conclusions/series?metric=&grain=&periods=2026-Q1,2026-Q2,...`：多周期并排，每格 `value / coverage / sources / batch_ids`，相邻差值和变化率；比率型给百分点（沿用 `MetricChange.basis`）。
  - `GET /conclusions/periods/{grain}/{key}/comparison?base=prior|last_year|target`
- 指标范围沿用 `brief.key_metrics`；对比可额外选 `business_review.metrics` 里任意指标。
- Agent 读工具：新增 `compare-periods` plugin 工具（只读），不扩旧的 `aggregate-metric`。

## 4. 目标（人工设定 + 审计）

新模块 `conclusions/targets.py`，存储仿 `dispositions`：**追加日志**，改一次记一条，不覆盖。

```python
class TargetRecord(BaseModel):
    series: str          # 与 periods.same_series 同口径，demo 和真实数据不串
    metric: str
    grain: Grain
    period: str          # Period.key
    value: Decimal       # 单位必须等于指标声明单位
    unit: str
    reason: str          # 必填
    set_by: str          # 审批人（consume_approval 返回的 actor）
    set_at: str
    supersedes: str | None
```

- 写入端点 `POST /conclusions/targets`，新操作 `target_set` 加入 `write_authorization.OPERATIONS`，走 `consume_approval`。
- **Agent 不能写**：plugin 工具目录不注册 `target_set`；`TOOL_OPERATIONS` 不映射；后端加测试：agent 身份/工具调用路径打 `target_set` 必 403。
- `GET /conclusions/targets/history?metric=&grain=&period=` 返回完整审计链。
- 季/年目标独立设定，不从月目标自动加总（加总也是"Agent/系统改目标"的一种）。若只设了月目标，季目标显示"未设定"。（Q5 已定）
- **TODO（Q6）**：首期目标只到 `指标 × 周期`。`指标 × 部门 × 周期` 留待后续——届时 `TargetRecord` 加 `department`，差距来源可直接对部门目标；首期差距来源用对基期变化的分解（§7.1）。

## 5. 预测看板（仅人选关键指标）

- 声明：`business_review.forecast.metrics: [..]`（人配；与 `brief.key_metrics` 独立）、`forecast.method`、`forecast.window_months`（默认 12，最少 3）。
- 方法（可解释、无训练）：
  - `linear_trend`：最近 N 个月 OLS，预测剩余月，给 80% 预测区间（残差标准误）。
  - `last_year_growth`：去年同期剩余月 × 今年累计同比增长率；区间取窗口内月度同比的 min/max。
- 期末预测 = 已到月实际 + 剩余月预测（`flow`）；比率型对**分子、分母叶子分别预测**后再按表达式计算。
- 每个预测输出：`method`、`window`（期间 + batch_id 列表）、`n_points`、`interval`、`formula` 文字。点数不足 → `insufficient_history` 拒绝，不出数。
- 未配置的指标不出现在看板（验收项）。

## 6. 完成度分档

字典声明，缺省用 issue 默认值：

```yaml
business_review.attainment:
  direction: { <metric>: higher_better | lower_better }   # 默认 higher_better
  tiers:
    - { id: exceeded,  label: 超额完成, min: 1.10 }
    - { id: met,       label: 完成,     min: 1.00, max: 1.10 }
    - { id: mostly,    label: 基本完成, min: 0.90, max: 1.00 }
    - { id: gap,       label: 有差距,   min: 0.80, max: 0.90 }
    - { id: severe,    label: 严重落后,             max: 0.80 }
```

- 区间左闭右开 `[min, max)`；加载时校验：连续、无重叠、无缺口，否则 503 让字典负责人改。
- 完成度 = 实际 ÷ 目标（Decimal）；`lower_better`（成本、回款天数）用 目标 ÷ 实际，**计算式原样返回给前端显示**。待定 Q3。
- 目标 ≤ 0 或实际为 0（lower_better）→ `not_computable`，不分档。
- 改档位边界 = 改字典 → 新 batch 生效；同一 batch 的结果可复现。

## 7. 差距分析 + 改进建议（规则算，Agent 讲）

### 7.1 规则部分（`conclusions/gap.py`，无模型）
- 差距：`实际/预测 − 目标`（绝对值 + 百分比）。
- 来源分解：目标没有按部门/客户拆，所以"谁造成差距"用**对基期变化的分解**回答：
  - 按表达式叶子 → 部门/科目贡献；
  - 按字典声明的实体列（客户、物料）→ 复用 `compare_master` 的新增/流失/存续分解，取贡献前 N。
  - 比率型：分子效应 vs 分母效应。
  - 每个贡献项带 `SourceRef`（batch + 行），总和 = 总变化（测试断言）。

### 7.2 Agent 部分
- 输入 packet = 7.1 的事实 + 档位 + 声明的建议规则；输出结构仿 `RoleJudgement`：
  ```python
  class Suggestion(BaseModel):
      metric: str; period: str; tier: str
      contributor_ids: list[str]   # 只能引用 packet 里的贡献项
      rule_id: str                 # 只能来自声明的 suggestion_rules
      action: str                  # 只能来自该规则的 actions
      explanation: str             # 不许出现数字（沿用 validate_role 规则）
  ```
- `business_review.suggestion_rules`：按 `tier` × `metric` 声明可用动作。**没声明规则 → 不输出建议**（满足"没有依据的建议不输出"）。
- Host 校验失败整条丢弃并记录原因；展示时数字全部来自 7.1，不来自模型。
- 证据等级沿用 `grades.py`：建议 = G4 judgement。

## 8. 前端（`plugins/src/client/`）

- 新页 `targets.tsx`（"目标与趋势"），入口挂在 brief 旁：
  - 粒度切换 月/季/年；多周期选择 → 对比表（值、Δ、变化率、coverage 标记）。
  - 目标列 + 完成度 + 档位徽章 + 计算式（hover/展开）。
  - 预测卡片：期末预测、区间、方法、数据窗口。
  - 差距分析 + 建议：每条可点开到源数据行（复用 `Sources`/source preview）。
  - 目标表单（人工，走审批）+ 修改历史。
- `charts.tsx` trend 支持 grain 参数；目标画成参考线（复用 `threshold` 字段）。
- 文案进 `zh-messages.ts`；`user-guide.ts` 加章节并跑 `pnpm --dir plugins docs:guide`。对外文案写"多部门"。

## 9. 周粒度（不做，但更新事实）

`date_column` 已存在且行级日期保留在 `clean_tables` → "源报表是否带日期列"对声明了 review 合同的数据答案是**是**。剩余问题：周跨月（一个月 batch 拆不出完整跨月周，需要跨 batch 拼）、口径（自然周/ISO/财务周）。建议在 #301 下评论这一事实，周单独立项。

## 10. 拆 PR

| PR | 内容 | 依赖 |
|----|------|------|
| A | `grain.py`、`MultiBatch` 汇总、`period_aggregation`、series/comparison API、`compare-periods` 工具 | — |
| B | targets 存储 + `target_set` 审批 + 分档 + `target` 基期 | A |
| C | 预测 | A |
| D | 差距分解 + Agent 建议 + 校验 | B, C |
| E | 前端页面 + 指南 | A–D 逐步接 |

## 11. 测试（对应验收）

- 同一 `flow` 指标：季 = 三月之和，年 = 四季之和；比率型季值 == 汇总分子/分母重算，且 ≠ 月比率平均（构造反例）。
- `period_end` 取末月；`none`/未声明季年拒绝。
- 缺月 → coverage 正确，不补零；声明变更 → `declaration_changed`。
- 月粒度对比与现有 `comparison` 输出一致（回归）。
- 目标：无审批 403；agent 工具路径 403；每次修改一条历史，不覆盖；单位不符拒绝。
- 分档：边界值落档（1.10 → exceeded，0.80 → gap）；改边界后档位变化；非法边界 503；lower_better 计算式。
- 预测：仅配置指标出现；方法/窗口字段齐全；点数不足拒绝；比率型分子分母分别预测。
- 差距分解：贡献和 = 总变化；每项有 `SourceRef`。
- Agent：引用不存在的贡献项/规则/动作 → 丢弃；文字含数字 → 丢弃；无规则 → 无建议。

## 12. 决定（2026-10-07）

- **Q1 不完整周期**：实际只算已到月 + coverage，不外推；预测负责外推。
- **Q2 财年**：字典 `business_review.calendar.fiscal_year_start_month` 声明，默认 1（自然年）。非 1 时 key 写 `FY2024` / `FY2024-Q1`，按起始年份命名。
- **Q3 越低越好**：完成度 = 目标 ÷ 实际，计算式显示。
- **Q4 未声明聚合方式**：拒绝。
- **Q5 季/年目标**：独立设定。
- **Q6 目标粒度**：首期 指标 × 周期；部门维度 TODO（§4）。

## 13. PR A 落地记录

- `business.expression` 加 `leaf` 钩子：表叶子交给调用方求值，其余运算不变。
- `conclusions/grain.py`：`Calendar`、`Period`（`months/prior/last_year/shift`）、`containing`、`parse`。
- `conclusions/aggregate.py`：`Aggregation` 声明解析、`Months`（每月一次 `business.context`，不可审的月记为 `unusable` 并保留原因）、`period_facts`、`compare`（同位月对齐）、`series`（相邻列都完整才比）。
- API：`GET /conclusions/batches/{id}/period-comparison?grain=&base=prior|last_year&metrics=`、`GET /conclusions/batches/{id}/periods?grain=&periods=|count=&metrics=`、`POST /tools/compare-periods`。都以所选批次为锚：同一数据序列、该批次的声明、"截至该批次月份"。
- 插件只读工具 `compare_periods`。
- 字典：mock demo（中文）声明 `period_aggregation`；英文版经 `make_english_samples.py` 生成（glossary 加一条）；两个 manifest 哈希更新。`business_demo` 只有 2025-11 一个月，不声明。
- 已知限制：一年 = 最多 12 次批次加载 + `business.context`，每个请求内有缓存，跨请求无缓存。
