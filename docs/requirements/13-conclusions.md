# E13 — 月度结论呈现与口径治理

# E13 — Monthly conclusions, presentation and convention governance

需求来源 / Sources: [2026-09-17 需求盘点 / requirements review](00-foundations.md#1-进展盘点三个视角--progress-review-from-three-perspectives)；[#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127) 管理层决策旅程；[#23](https://github.com/EricWang1358/BridgeFlow-AI/issues/23) 口径确认。

基线 / Baseline: `692d3d5`, reviewed 2026-09-17. [状态规则 / Status rules](README.md)；[角色、非功能需求与呈现规范 / Actors, quality attributes and presentation standards](00-foundations.md)；[类设计 / Class design](class-design.md)。

## 目标与角色 / Goal and actors

把已经算对的月度结果变成管理层能直接读懂、能放心引用的结论：一页看清本月、和过去比、用图说话、导出成正式报告、口径由业务方确认、每条结论标明依据有多可靠。
主要角色：管理层决策者（A04）、月度汇总负责人（A03）、部门负责人（A02）、字典与标准维护人（A05）。

Turn correctly computed monthly results into conclusions management can read directly and cite with confidence: a one-page brief, period comparison, charts, a formal report, business-confirmed conventions and an evidence grade on every conclusion. Actors: Management decision-maker (A04), Monthly consolidation lead (A03), Department owner (A02), Dictionary and standards steward (A05).

本 epic 不新增计算口径：所有数字仍来自 E06 总表与 E07 声明指标。它只决定**怎么比、怎么排、怎么说、怎么交付**。

This epic adds no computation of its own. Every number still comes from the E06 master and E07 declared metrics; E13 governs comparison, ordering, wording and delivery.

## UC 索引 / UC index

| UC | 中文 / English | Status | 优先级 / Priority |
| --- | --- | --- | --- |
| E13-UC01 | 一页月度结论 / One-page monthly brief | PARTIAL | Must |
| E13-UC02 | 跨期对比与差异解释 / Period comparison and variance explanation | IMPLEMENTED_OFFLINE | Must |
| E13-UC03 | 指标可视化与下钻 / Metric charts with drill-down | IMPLEMENTED_OFFLINE | Should |
| E13-UC04 | 月度报告文档导出 / Export the monthly report document | IMPLEMENTED_OFFLINE | Should |
| E13-UC05 | 口径假设确认与替换 / Confirm or replace declared conventions | IMPLEMENTED_OFFLINE | Must |
| E13-UC06 | 结论依据等级标注 / Label conclusions with evidence grades | PARTIAL | Should |

## E13-UC01 — 一页月度结论 / One-page monthly brief

**Status: PARTIAL**

看板 / Issue: [#190](https://github.com/EricWang1358/BridgeFlow-AI/issues/190)

### 中文需求与验收

- 参与者：管理层决策者（A04）、月度汇总负责人（A03）。
- 触发：月度研判完成，管理层需要一页看懂本月结论与要做的决定。
- 前置：批次状态为就绪；四部门研判报告已保存（validated 或 partial）；跨部门总表已生成。
- 主流程：
  1. 汇总负责人在工作室打开「本月结论」（界面名称以实现为准）。
  2. 系统从已保存报告与总表生成一页结论：本月一句话结论；声明为关键指标的 3–5 个指标（本期值、较上期变化、状态）；需关注事项按严重度排序，每项含负责人与建议动作；待确认事项计数；完整性说明（完整行数、partial 部门、口径假设条数）。
  3. 每个数字可点开，跳到 E07 指标来源或 E06 单元格出处。
  4. 汇总负责人可把结论保存为笔记本产物，供管理层打开。
- 异常：报告为 partial 时，页首显示缺失部门，缺失部门的指标不参与排序，也不显示为「正常」；没有已保存报告时拒绝生成，并提示先发起研判。
- 验收：
  - AC-1 Given 示例批次 2024-07 的已保存报告有 3 项需关注 When 打开本月结论 Then 页面列出这 3 项，按声明严重度排序，每项显示负责人角色与出处链接。
  - AC-2 Given 财务部研判失败的 partial 报告 When 打开本月结论 Then 页首标「部分完成：财务部缺失」，财务指标不出现在关键指标区。
  - AC-3 Given 批次尚无报告 When 请求本月结论 Then 返回拒绝原因「请先完成研判」，不生成空白页。
  - AC-4 Given 本月结论页 When 统计其生成过程 Then 模型调用次数为 0。
- 后置：结论页作为派生产物保存，绑定批次、报告与声明版本；报告更新后旧结论页标为过期，不被覆盖。
- 依赖：E07-UC06、E06-UC02、E13-UC02（上期对比）、E13-UC06（依据等级）。
- 当前证据与缺口（2026-09-17 第一轮）：[conclusions/brief.py](../../backend/src/bridgeflow/conclusions/brief.py) 的 `BriefBuilder` 与 `GET /conclusions/batches/{id}`，工作室「本月结论」视图（[brief.tsx](../../plugins/src/client/brief.tsx)）；关键指标、严重度与口径依赖由字典 `business_review.brief` 声明，缺声明拒绝。[行为测试](../../backend/tests/test_conclusions.py) 覆盖 AC-1–4 与过期标记；[浏览器旅程](../../plugins/tests/round1-journey.mjs)。剩余：保存为笔记本产物、关注项直接跳到单个指标出处。（较上期变化已由 E13-UC02 在第二轮补上。）

### English requirements and acceptance

- Actors: Management decision-maker (A04), Monthly consolidation lead (A03).
- Trigger: the monthly review is done and management needs one page with the conclusions and decisions.
- Preconditions: batch ready; four-department report saved (validated or partial); master table built.
- Main flow: (1) open “This month” in Studio; (2) build one page from the saved report and master: a one-sentence conclusion, the 3–5 metrics declared as key with value, change and status, attention items ordered by declared severity with owner and action, open-item count and a completeness note; (3) every number drills to E07 metric sources or E06 cell provenance; (4) save as a notebook artifact.
- Exceptions: a partial report names missing departments and excludes their metrics from ranking and from “OK”; no saved report refuses with “complete the review first”.
- Acceptance: AC-1 three attention items are listed, ordered and linked; AC-2 a partial report is labelled and finance metrics are excluded; AC-3 no report refuses without a blank page; AC-4 zero model calls.
- Postcondition: the brief is a derived artifact bound to batch, report and declaration versions; a newer report marks it stale without overwriting.
- Evidence and gap (round 1, 2026-09-17): `BriefBuilder`, `GET /conclusions/batches/{id}` and the Studio “This month” view; key metrics, severity and convention dependencies are declared under `business_review.brief` and refused when absent. Tests cover AC-1–4 and staleness; a browser journey passes. Remaining: saving as a notebook artifact and drilling from an attention item to its metric sources. (Change versus prior period landed with UC02 in round 2.)

## E13-UC02 — 跨期对比与差异解释 / Period comparison and variance explanation

**Status: IMPLEMENTED_OFFLINE**

看板 / Issue: [#191](https://github.com/EricWang1358/BridgeFlow-AI/issues/191)

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、管理层决策者（A04）。
- 触发：本月结论需要与上月、去年同期或计划对比才有意义。
- 前置：对比两期都有已冻结批次，且使用同一字典版本或声明了版本间映射；计划值需有声明来源。
- 主流程：
  1. 用户选择比较基准：上月、去年同期或计划。
  2. 系统按实体键（项目、客户）对齐两期总表或指标，给出每个指标的本期值、基期值、绝对变化与相对变化。
  3. 对总量指标给出差异分解：新增实体、消失实体与持续实体的变化，三部分之和等于总变化。
  4. 超过声明阈值的变化进入 E13-UC01 的关注区，附两期出处。
- 异常：基期缺失时显示「无基期」，不以 0 代替；两期字典版本不同且没有声明映射时拒绝对比并列出不一致字段；基期为 0 时相对变化显示「无法计算」。
- 验收：
  - AC-1 Given 模拟商砼公司 2024-06 与 2024-07 两个批次 When 选择「较上月」 Then 每个项目的实际量给出两期值与变化，且变化之和等于公司合计变化。
  - AC-2 Given 声明的环比关注阈值为 −20%，第二实验学校扩建 7 月实际量较 6 月下降约 40% When 生成对比 Then 该项进入关注区，并附 6 月与 7 月两个出处。
  - AC-3 Given 只有 2024-07 一个批次 When 选择「较上月」 Then 显示「无基期」，不显示 0 或 −100%。
  - AC-4 Given 两期字典版本不同且未声明映射 When 请求对比 Then 拒绝并列出不一致的字段名。
- 后置：对比结果是派生视图，不改动任一批次。
- 依赖：E04-UC01（冻结批次）、E06-UC02、E05-UC01；计划值依赖业务方提供计划来源。
- 当前证据与缺口（2026-09-19 第二轮）：[conclusions/comparison.py](../../backend/src/bridgeflow/conclusions/comparison.py)（基准策略、实体对齐、差异分解、四类拒绝）与 [periods.py](../../backend/src/bridgeflow/conclusions/periods.py)（按期间检索批次的索引）；`GET /conclusions/batches/{id}/comparison`；可比字段与阈值在 `integration.yaml` 的 `comparison` 中声明；结论页每个关键指标显示较上期变化，越阈项单列。[行为测试](../../backend/tests/test_comparison.py) 覆盖 AC-1–4 与分解恒等式，[浏览器旅程](../../plugins/tests/round1-journey.mjs) 覆盖界面。缺口：去年同期只测了期间推算、未用真实两期数据跑过；计划对比按 D5 拒绝，等业务方给计划来源；总表级完整对比视图（非结论页摘要）未做。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Management decision-maker (A04).
- Trigger: this month's figures only mean something against last month, last year or plan.
- Preconditions: frozen batches for both periods with the same dictionary version or a declared mapping; plan values have a declared source.
- Main flow: choose a base (prior month, same month last year, plan); align masters or metrics by entity keys; show current, base, absolute and relative change; decompose totals into new, discontinued and continuing entities whose parts sum to the total change; changes beyond declared thresholds feed the E13-UC01 attention list with both sources.
- Exceptions: a missing base shows “no base period”, never 0; different dictionary versions without a declared mapping are refused with the mismatched fields; a zero base shows “not computable”.
- Acceptance: AC-1 June vs July per-project changes sum to the company change; AC-2 with a declared −20% threshold, a ~40% decline enters attention with both sources; AC-3 a single batch shows “no base period”; AC-4 unmapped version mismatch is refused.
- Postcondition: comparison is a derived view and modifies no batch.
- Evidence and gap (round 2, 2026-09-19): `comparison.py` (base strategies, entity alignment, decomposition, four refusal kinds) and `periods.py` (per-period batch index); `GET /conclusions/batches/{id}/comparison`; comparable fields and thresholds declared under `comparison` in `integration.yaml`; the brief shows each key metric's change and lists threshold breaches. Tests cover AC-1–4 and the decomposition identity; a browser journey covers the UI. Gaps: the last-year base is only tested through period arithmetic, not two real periods; plan comparison refuses by D5 until a plan source exists; a full master-level comparison view (beyond the brief summary) is not built.

## E13-UC03 — 指标可视化与下钻 / Metric charts with drill-down

**Status: IMPLEMENTED_OFFLINE**

### 中文需求与验收

- 参与者：管理层决策者（A04）、月度汇总负责人（A03）。
- 触发：表格里的数字难以一眼看出趋势、差异和异常。
- 前置：图表所用数据来自 E07 声明指标或 E13-UC02 对比结果；图表类型由声明选择，不由模型临时决定。
- 主流程：
  1. 结论页与指标详情提供声明过的图：多期趋势折线、差异瀑布、部门或项目对比条。
  2. 图标题写成结论句，坐标轴标单位与期间，阈值线来自同一声明版本。
  3. 点击数据点，下钻到该指标的来源单元格或公式输入。
  4. 每张图提供同等信息的表格视图，供读屏与复制。
- 异常：数据点少于 2 期时不画趋势线，改为说明；缺失期间显示断点，不插值；声明中没有图表定义的指标只显示表格。
- 验收：
  - AC-1 Given 三期模拟数据 When 打开「签收率趋势」 Then 折线有 3 个点，阈值线位于声明值 95%，点击 7 月数据点打开 7 月出处。
  - AC-2 Given 只有一期数据 When 打开趋势图 Then 显示「至少需要两期」，不画单点线。
  - AC-3 Given 深色主题与读屏工具 When 访问同一图 Then 表格视图给出与图相同的数值，状态不只靠颜色区分。
- 后置：图表不保存独立数值副本；数值变化时从来源重新生成。
- 依赖：E07-UC01、E13-UC02、E10-UC05、00-foundations §5.5。
- 当前证据与缺口（2026-09-19 第七轮）：图表由字典 `business_review.charts` 声明（种类、指标或字段、期数、阈值取自哪条判定），[conclusions/charts.py](../../backend/src/bridgeflow/conclusions/charts.py) 只把声明变成数据点，不保存任何数值副本；`GET /conclusions/batches/{id}/charts` 每次从各期自己的批次重算。三种图：多期趋势（阈值线取自同一声明里的判定阈值）、差异瀑布（复用 E13-UC02 的新增/消失/持续分解，四段之和等于总变化）、按实体条形（超出声明阈值的实体带标记）。每个点带批次号，点击下钻到该期总表。界面 [charts.tsx](../../plugins/src/client/charts.tsx) 用内联 SVG 绘制，并在同一份数据上提供等价表格（读屏与复制），状态不只靠颜色（▲ 标记 + 表格文字）。[行为测试](../../backend/tests/test_charts.py) 覆盖 AC-1–3 与「无声明只给表格」；[浏览器旅程](../../plugins/tests/round1-journey.mjs) 断言表格与图同源，截图 `docs/evidence/round1-e13-e14/metric-charts.png`。剩余：点击下钻目前到该期总表，未定位到单个指标的公式输入单元格（D19）。

### English requirements and acceptance

- Actors: Management decision-maker (A04), Monthly consolidation lead (A03).
- Trigger: tables of numbers do not show trends, variances or outliers at a glance.
- Preconditions: data comes from declared metrics or E13-UC02 comparisons; chart types are declared, not chosen ad hoc by a model.
- Main flow: declared charts (multi-period trend lines, variance waterfall, department or project comparison bars) with conclusion titles, units, periods and threshold lines from the same declaration version; data points drill to sources; an equivalent table view accompanies every chart.
- Exceptions: fewer than two periods shows an explanation instead of a trend; missing periods are gaps; metrics without a chart declaration show tables only.
- Acceptance: AC-1 a three-point sign-off trend with the 95% threshold drills to July's source; AC-2 one period shows “at least two periods needed”; AC-3 the table view matches the chart and status is not colour-only.
- Postcondition: charts keep no separate copy of values.
- Evidence and gap (2026-09-19, round 7): charts are declared in the dictionary (`business_review.charts`); `conclusions/charts.py` turns a declaration into points and keeps no copy of any value, and `GET /conclusions/batches/{id}/charts` recomputes each period from that period's own batch. Three kinds: a multi-period trend with the threshold line taken from the same declared check, a variance waterfall reusing the E13-UC02 decomposition (the parts sum to the change), and entity bars marking declared breaches. Every point carries its batch so a click drills to that period's master. The studio draws them as inline SVG with an equivalent table from the same numbers, and status never rests on colour alone. `backend/tests/test_charts.py` covers AC-1–3 and the undeclared-charts case; the journey asserts the table matches the chart. Remaining: a click drills to the period's master, not yet to the individual formula input cell (D19).

## E13-UC04 — 月度报告文档导出 / Export the monthly report document

**Status: IMPLEMENTED_OFFLINE**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、管理层决策者（A04）。
- 触发：经营会、审计或存档需要一份格式规范、可离线阅读的月度报告。
- 前置：E13-UC01 的结论页已生成且未过期。
- 主流程：
  1. 用户选择导出格式（Word 或 PDF）。
  2. 系统按固定结构生成报告：封面（期间、批次、版本、生成时间）→ 本月结论 → 关键指标与对比 → 各部门研判摘要 → 需关注事项与负责人 → 待确认事项 → 口径假设与限制 → 附录（数据来源清单、公式、出处索引）。
  3. 数字与用词遵守 00-foundations §5；正文每个数字在附录有出处编号。
  4. 文件名包含期间与版本，例如 `月度经营结论-2024-07-v3.docx`。
- 异常：结论页过期时拒绝导出并提示重新生成；partial 报告导出时，封面与结论页首都标「部分完成」。
- 验收：
  - AC-1 Given 示例批次的结论页 When 导出 Word Then 文件包含上述 8 个章节，正文每个数字在附录能找到出处编号。
  - AC-2 Given 报告依赖 4 条口径假设 When 导出 Then「口径假设与限制」章节列出这 4 条及其确认状态。
  - AC-3 Given 结论页已过期 When 导出 Then 拒绝并提示重新生成，不导出旧内容。
- 后置：导出文件与其来源版本记录在产物列表；导出不改变批次或报告。
- 依赖：E13-UC01、E13-UC05、E13-UC06。与 E06-UC06 分工：E06-UC06 是季度、年度汇总与 PDF，保持延期；本 UC 只覆盖月度。
- 当前证据与缺口（2026-09-19 第八轮）：[conclusions/report.py](../../backend/src/bridgeflow/conclusions/report.py) 由结论页（E13-UC01）生成 Word 文档，八个章节齐备；正文每个数字带出处编号 `[Sn]`，在附录能查到公式、来源单元格数与依据等级。口径章节只列本报告实际依赖的口径及其确认状态（E13-UC05），确认后文档里的状态与依据来源同步变化，数值不变。结论页过期时拒绝导出（`stale` → 409）；partial 报告在封面标「部分完成」并列出缺失部门。接口 `GET /conclusions/batches/{id}/report`，界面在结论页右上角一键下载（[brief.tsx](../../plugins/src/client/brief.tsx)）。文档直接按 Office Open XML 写出，不引入新依赖（D21）。[行为测试](../../backend/tests/test_report.py) 覆盖 AC-1–3 与文件结构；[浏览器旅程](../../plugins/tests/round1-journey.mjs) 实际下载到 `月度经营结论-2024-07-*.docx`。剩余：只有 Word，不出 PDF（D22）；导出不写产物记录（D23）。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Management decision-maker (A04).
- Trigger: a management meeting, audit or archive needs a properly formatted offline monthly report.
- Preconditions: a current (not stale) E13-UC01 brief exists.
- Main flow: choose Word or PDF; generate a fixed structure (cover, conclusion, key metrics and comparison, department summaries, attention items and owners, open items, conventions and limitations, appendix of sources, formulas and provenance index); follow the presentation standards with a provenance number for every figure; name the file by period and version.
- Exceptions: a stale brief is refused; partial reports are labelled on the cover and first page.
- Acceptance: AC-1 eight sections with provenance numbers; AC-2 conventions listed with confirmation state; AC-3 stale brief refused.
- Postcondition: exports are listed as artifacts with source versions and change nothing.
- Relation: E06-UC06 remains the deferred quarter/year PDF path; this UC is monthly only.
- Evidence and gap (2026-09-19, round 8): `conclusions/report.py` builds the Word document from the brief, with all eight sections; every figure in the body carries a source number that resolves in the appendix to its formula, source-cell count and evidence grade. The conventions section lists only the ones the reported figures rest on, with their confirmation state, and a stale brief is refused (409) rather than exported. A partial review is marked on the cover. Served by `GET /conclusions/batches/{id}/report` and downloaded from the brief; written as Office Open XML directly, adding no dependency (D21). `backend/tests/test_report.py` covers AC-1–3 and the file structure; the browser journey downloads a real file. Remaining: Word only, no PDF (D22), and no export record is written (D23).

- Previous evidence and gap: the master workbook with open-item and convention sheets exists; no management report document exists.

## E13-UC05 — 口径假设确认与替换 / Confirm or replace declared conventions

**Status: IMPLEMENTED_OFFLINE**

### 中文需求与验收

- 参与者：字典与标准维护人（A05）、部门负责人（A02）、审批人（A06）。
- 触发：系统按通用做法补了口径，业务方要逐条确认或替换。
- 前置：口径以声明形式存在，每条有编号、依据、影响字段；确认人角色已声明。
- 主流程：
  1. 维护人打开「口径假设」清单，看到每条的内容、依据、影响的字段与当前批次中受影响的单元格数。
  2. 负责该口径的部门负责人选择「确认」或「替换」；替换时填写新值或新公式，并附来源（文件、会议纪要或书面说明）。
  3. 系统生成新声明版本草案，展示替换前后受影响单元格数与数值变化预览。
  4. 审批人通过原生审批发布新版本；已冻结的批次不改写，重新导入或重算才使用新版本。
  5. 确认后，依赖该口径的结论依据等级从 G3 升为 G2。
- 异常：无来源的替换被拒绝；替换导致公式无法计算时，草案不能发布；同一口径的并发修改按版本号冲突拒绝。
- 验收：
  - AC-1 Given 口径「增值税税率 13%」未确认 When 财务负责人附来源确认 Then 新版本发布后，重算批次中该口径的标注由「按通用做法」变为「已确认」，单方毛利的依据等级为 G2。
  - AC-2 Given 替换缺口公式但未附来源 When 提交 Then 拒绝并提示需要来源。
  - AC-3 Given 已冻结的 2024-07 批次 When 发布新口径版本 Then 该批次结果不变，界面提示「有更新的口径版本，可重算」。
  - AC-4 Given 两人同时修改同一口径 When 后提交者保存 Then 因版本冲突被拒绝，不覆盖前者。
- 后置：每个口径版本保留来源、确认人、时间与审批回执。
- 依赖：E05-UC01、E06-UC03、E09-UC01、E09-UC06、E13-UC06。
- 当前证据与缺口（2026-09-19 第三轮）：[conclusions/conventions.py](../../backend/src/bridgeflow/conclusions/conventions.py) 记录逐条口径的决定（版本号、来源、决定人、时间），[api/conventions.py](../../backend/src/bridgeflow/api/conventions.py) 提供工作室清单、影响试算与写入接口；写入走原生审批回执与 `convention_decide` 操作授权（只授予总表管理者，见 D11），无来源拒绝、版本冲突拒绝。确认后依据等级经 [grades.py](../../backend/src/bridgeflow/conclusions/grades.py) 的 `ConventionNode(confirmed=True)` 由 G3 升为 G2，总表视图与本月结论同步。插件工具 `convention_list / convention_preview / convention_decide`（[conventions.ts](../../plugins/src/tools/conventions.ts)），工作室在「按通用做法补的口径」块显示状态徽标与该改的声明内容（[master.tsx](../../plugins/src/client/master.tsx)）。[行为测试](../../backend/tests/test_conventions.py) 覆盖 AC-1–4。剩余：替换不自动生成新声明版本（D8，按设计如此），字段级「本批次受影响单元格数」只对常数给出试算（D10）。

### English requirements and acceptance

- Actors: Dictionary and standards steward (A05), Department owner (A02), Approver (A06).
- Trigger: conventions filled in by best practice must be confirmed or replaced by the business.
- Preconditions: conventions are declared with IDs, rationale and affected fields; confirming roles are declared.
- Main flow: list conventions with affected cell counts; the owning department confirms or replaces with a sourced value or formula; the system drafts a new declaration version with an impact preview; an approver publishes it natively; frozen batches are not rewritten; confirmed conventions lift dependent conclusions from G3 to G2.
- Exceptions: unsourced replacements are refused; drafts that break formulas cannot be published; concurrent edits conflict by version.
- Acceptance: AC-1 confirming the 13% VAT rate relabels it and grades margin G2 after recomputation; AC-2 an unsourced replacement is refused; AC-3 a frozen batch is unchanged and offers recomputation; AC-4 a concurrent edit is rejected.
- Postcondition: every version keeps its source, confirmer, time and approval receipt.
- Evidence and gap (2026-09-19, round 3): decisions are versioned and recorded with source, decider and time (`conclusions/conventions.py`), served and written through `api/conventions.py` behind a native approval receipt and the `convention_decide` grant held only by the master-table owner (D11); unsourced decisions and version conflicts are refused. Confirmation lifts dependent figures from G3 to G2 through `ConventionNode(confirmed=True)`, in both the master view and the monthly brief. Tools `convention_list / convention_preview / convention_decide`; the studio shows each convention's state and the declaration change to apply. Behaviour tests cover AC-1–4. Remaining by design: a replacement does not generate a declaration version (D8), and the impact dry run exists for constants only (D10).

## E13-UC06 — 结论依据等级标注 / Label conclusions with evidence grades

**Status: PARTIAL**

看板 / Issue: [#195](https://github.com/EricWang1358/BridgeFlow-AI/issues/195)

### 中文需求与验收

- 参与者：管理层决策者（A04）、部门负责人（A02）。
- 触发：读者需要知道一个结论有多可靠：依据来自原件、公式、口径假设还是模型判断。
- 前置：出处链完整：单元格出处、公式输入、口径依赖与子代理结论的证据已保存。
- 主流程：
  1. 系统按 00-foundations §5.3 为每个数字与结论计算依据等级 G1–G4，取依赖中最弱的一级。
  2. 结论页、报告与图表在数字旁显示等级标记，悬停或点开显示依赖链。
  3. 页首汇总本月结论的等级分布，例如「G1 12 · G2 9 · G3 4 · G4 3」。
- 异常：出处链断裂的数字不显示等级，标「出处缺失」，并进入待确认事项。
- 验收：
  - AC-1 Given 单方不含税毛利依赖未确认的 13% 增值税口径 When 显示该数字 Then 标记为 G3，依赖链列出该口径。
  - AC-2 Given 部门子代理的建议动作 When 显示 Then 标记为 G4，并显示其引用的指标。
  - AC-3 Given 一个数字缺少出处 When 生成结论页 Then 该数字标「出处缺失」，并出现在 E14-UC05 收件箱。
- 后置：等级是派生属性，随口径确认或数据更新重新计算，不单独保存。
- 依赖：E06-UC04、E07-UC04、E13-UC05。
- 当前证据与缺口（2026-09-17 第一轮）：[conclusions/grades.py](../../backend/src/bridgeflow/conclusions/grades.py) 以组合模式表示出处树并取最弱等级；结论页的关键指标、关注项与建议动作，以及总表视图的每个单元格都带等级与依赖链，页首显示分布；部门写法不一致而留空的单元格标「出处缺失」。AC-1、AC-2 已由测试覆盖。第三至八轮之后的剩余：口径确认后升级已做（E13-UC05），报告导出的附录已逐条打印依据等级（E13-UC04）；仍缺图表数据点上的等级标注（E13-UC03 画的是数值），以及把「出处缺失」的单元格送进待办收件箱（E14-UC05 目前接了四类来源，不含这一类）。

### English requirements and acceptance

- Actors: Management decision-maker (A04), Department owner (A02).
- Trigger: a reader needs to know how reliable a conclusion is and what it rests on.
- Preconditions: complete provenance chains for cells, formula inputs, convention dependencies and subagent evidence.
- Main flow: compute grades G1–G4 per §5.3 taking the weakest dependency; show a grade mark beside numbers in the brief, report and charts with the dependency chain on demand; summarise the grade distribution at the top.
- Exceptions: a broken chain shows “provenance missing” instead of a grade and raises an open item.
- Acceptance: AC-1 margin depending on the unconfirmed VAT rate is G3; AC-2 a subagent action is G4 with its cited metrics; AC-3 a missing provenance is labelled and reaches the E14-UC05 inbox.
- Postcondition: grades are derived and recomputed, never stored separately.
- Evidence and gap (round 1, 2026-09-17): a composite provenance tree graded by its weakest node; grades and chains on brief metrics, attention items, advice and every master cell, with a distribution summary; withheld cells show “provenance missing”. AC-1 and AC-2 are tested. Remaining after rounds 3–8: confirmation now upgrades a convention-bound figure to G2 (E13-UC05) and the exported report prints each figure's grade in its appendix (E13-UC04); still missing are grades on chart points (E13-UC03 draws values, not grades) and routing a cell whose provenance is broken into the open-item inbox (E14-UC05 wires four sources, not this one).

## 本轮设计判定与依据 / Design decisions and their evidence

需求没有写死的地方由开发侧评估决定，判定与依据记在这里，业务方可以直接推翻（改声明即可，不改代码）。

Where the requirement left a choice open, it was decided during implementation. Each decision and its evidence is recorded here; the business side can overturn any of them by changing a declaration, not code.

| # | 判定 / Decision | 依据 / Evidence | 落在哪 / Where |
| --- | --- | --- | --- |
| D1 | 基期取该期间**最新导入且调用者可见**的批次，更早的仍可按批次号访问 | 批次不可变，同一月份的多个批次互为更正（隔离处置派生、E14-UC04 单部门补传）；人说「上月」指的是最新那份 | `periods.latest_for` |
| D2 | 两期是否可比，看**字段声明**是否相同，而不是版本字符串 | 版本字符串会因注释、口径等与字段无关的改动而变；据此拒绝会挡住本来成立的对比。字段声明不同才会把两个不同的东西相减 | `comparison.declaration_differences`，测试 `test_a_changed_field_declaration_refuses_the_comparison` |
| D3 | 只有声明为 `additive` 的字段跨项目求和；合计再分解为新增、消失、持续三部分，三者之和恒等于总变化 | 单价与比率跨项目相加得到的数没有业务含义；分解让「总量降了」能追到是丢了项目还是存量项目下滑 | `integration.yaml` 的 `comparison.additive`；性质测试校验恒等式 |
| D4 | 拒绝分四类：无基期、基期不可用、声明已变、该基准不可用；单个数字基期为 0 时标「无法计算」 | 四种情况对读者的含义完全不同：等数据、修数据、改声明、换基准。混为一谈会让人做错下一步 | `Comparison.status`；测试 `test_without_a_base_batch...`、`test_a_zero_base_is_not_computable...` |
| D5 | 计划对比在业务方给出计划来源前一律拒绝 | 计划值没有声明来源，编一个基准等于编一个结论 | `DeclaredPlan.unavailable`，测试覆盖 |
| D6 | 实体键 = 总表主键去掉期间字段（按 `period_from` 识别，不写死字段名） | 主键含报表年月，保留它会让两期没有一行能对上，每行都显示为「新增」——实现时实测到这一点 | `comparison.entity_axis` |
| D7 | 指标本身是比率时（单位 %），变化按**百分点**给出，不给相对百分比 | 净利率 0.09% → −0.5% 的相对变化是 −679%，读者无法使用；界面初版就出现了这一幕 | `comparison.POINT_UNITS`；测试断言 `basis == "percentage_points"` |
| D21 | 直接按 Office Open XML 写出 .docx，不引入文档库 | 为一个功能加一个依赖，与「不要扩大范围」相冲突；报告只用到标题、段落与表格三种结构，写出来比引进来小，而且这里不解析任何文档 | `conclusions/report.py`；测试逐一检查包内各部件 |
| D22 | 本轮只出 Word，不出 PDF | PDF 需要排版/渲染依赖（字体、CJK 支持），体量远超本功能；Word 文档由使用者自行打印为 PDF，且 E06-UC06 的季度/年度 PDF 本就延期 | 需求正文已注明分工；本条为本轮范围说明 |
| D23 | 导出是**只读**动作，不写「已导出」产物记录 | 写一条导出记录，就产生了第二份关于「发布了什么」的事实，而文档封面已经写明它绑定的批次、报告与声明版本；真正的产物列表是研判报告本身 | `GET /conclusions/batches/{id}/report` 无副作用；封面表格列出全部绑定版本 |
| D19 | 下钻落在**该期总表行**，不是指标公式的每个输入单元格 | 一个指标的输入常有上百个单元格（求和），逐个列出既不可读也会把原始行推回上下文；总表行是既能定位又已带出处的最小单位 | `charts.Point.batch_id/key`；界面跳转到该批次总表 |
| D20 | 缺失期间**断线**，不插值、不补零 | 一条穿过没人报过的月份的线，是系统自己做出的断言；补零还会把「没报」显示成「掉到零」 | `charts.trend` 分段绘制；测试 `test_a_month_without_a_batch_is_a_gap_and_never_interpolated` |
| D8 | 「替换」只记录业务方的决定、来源与该改的声明内容，**不由系统改写公式、判定阈值或汇总口径**；只有常数替换能给出试算 | 需求主流程写的是「系统生成新声明版本草案」。但 CLAUDE.md 定下「字典由人预设、改 YAML 不改 Python」：让系统按一句自由文本重写 `derived` 树，等于让模型发明声明，且声明文件将不再是唯一事实来源。记录决定 + 指明该改哪一行，既留痕又把改动留在人手里 | `conventions.decide` 的 `replacement_requested` 状态与 `_declaration_change`；测试 `test_replacing_a_formula_asks_for_a_declaration_change...` |
| D9 | 「确认」是唯一会改变运行时行为的决定，且只改**依据等级**（G3→G2），不改任何数值 | 确认的含义是「这条通用做法就是我们的口径」，数值本来就是按它算的；若确认还改数值，说明之前展示的数是错的而不是待确认的 | `grades.ConventionNode(confirmed=True)`；测试 `test_confirming_lifts_the_figures_that_rest_on_it_from_g3_to_g2` |
| D10 | 影响试算是**干跑**：用替换值重新整合一次并逐格比对，返回变化单元格数、变化行数与字段名；给队长的返回值不含单元格值，浏览器端才给最多 20 格样例 | 20 万行时「影响多少」是可回答的，「影响了哪些格」不是；这与「工具返回值里也不能有原始行」是同一条约束 | `conventions.preview` 与 `/tools/convention-preview` 的裁剪；测试 `test_a_constant_can_be_previewed_and_the_captain_sees_counts_not_cells` |
| D11 | `convention_decide` 只授予总表管理者（`master_office_admin`），部门主管不得确认口径 | 口径是跨部门的总表声明，一条税率同时影响物资与市场的字段；与 `confirm_mapping` 同理，按单部门授权会让一个部门替全表定口径 | `data/mappings/access-control.yaml`；`write_authorization.OPERATIONS` 与批次可见性复核 |

## Epic 数据与实现设计 / Epic data and implementation design

对象、模式与时序见 [class-design.md](class-design.md) 第 2 节。要点：结论页是**只读投影**，由已保存报告、总表与声明版本确定性生成，不调用模型；比较策略、图表规格、报告渲染器都是声明驱动的可替换策略；口径版本沿用工作流基座的版本与乐观并发。

Objects, patterns and sequences are in class-design.md §2. The brief is a read-only projection built deterministically from saved reports, the master and declaration versions, without model calls; comparison, chart specs and report renderers are declared, swappable strategies; convention versions reuse the workflow foundation's versioning and optimistic concurrency.

建议实施顺序：E13-UC05 与 E13-UC06（让结论先可信）→ E13-UC01 与 E13-UC02（一页结论与对比）→ E13-UC03 → E13-UC04。

Suggested order: UC05 and UC06 first so conclusions are trustworthy, then UC01 and UC02, then UC03, then UC04.

## 发布与状态维护 / Release and status maintenance

每实现一个 UC，先跑主流程与每条拒绝路径的行为测试，再同步更新本文件索引、UC 正文状态、实现路径与剩余缺口，以及 [README](README.md) 的状态汇总与 [追溯矩阵](traceability.md)。界面改动需要浏览器旅程；真实业务验收单独记录。

For each delivered UC, run behavioral tests for the main flow and every refusal path, then update this index, the UC body, README totals and the traceability matrix together. UI changes need a browser journey; real business acceptance is recorded separately.
