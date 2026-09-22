# E04 — 数据导入、清洗与隔离

# E04 — Data intake, cleaning and quarantine

## 范围与角色 / Scope and actors

部门上传者、数据管理员 / Department contributors and data administrators。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Upload → immutable BatchSnapshot + frozen dictionary → sanitizer → correction/quarantine ledger → approved derived batch. 浏览器原件与模型摘要分别读取 / Browser originals and model summaries have separate read paths.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E04-UC01 | 多文件批次与冻结版本 / Import files into frozen batches | IMPLEMENTED |
| E04-UC02 | 明确工作表和表头位置 / Select declared sheets and headers | IMPLEMENTED |
| E04-UC03 | 格式规范与质量问题 / Normalize formats and detect quality problems | IMPLEMENTED |
| E04-UC04 | 歧义日期的声明与恢复 / Resolve date ambiguity by declaration | IMPLEMENTED |
| E04-UC05 | 清洗差异与原件定位 / Trace corrections to original sources | IMPLEMENTED |
| E04-UC06 | 隔离记录批准放行或丢弃 / Approve quarantine release or discard | IMPLEMENTED |
| E04-UC07 | 原件列表和分页预览 / Browse original sources with pagination | IMPLEMENTED |
| E04-UC08 | 币种换算、单位治理与缺月补齐 / Currency conversion, unit governance and missing periods | PARTIAL |
| E04-UC09 | 导入问题的 agent 可读明细 / Agent-readable issue details | IMPLEMENTED_OFFLINE |

## E04-UC01 — 多文件批次与冻结版本 / Import files into frozen batches

**Status: IMPLEMENTED**

来源 / Sources: [#12](https://github.com/EricWang1358/BridgeFlow-AI/issues/12), [#15](https://github.com/EricWang1358/BridgeFlow-AI/issues/15).

### 中文用例

- 参与者：月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：月末收到四个部门的报表，需要导入成一个可复现的批次。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：选择期间、部门及 CSV/XLSX 文件，保存批次标识、来源和冻结字典；重启后读取同一结果。
- 异常、验收和边界：重跑产生可定位版本；不得静默重写旧结果；不等于任意来源连接器。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: month-end department reports must be imported as one reproducible batch.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Select period, departments and CSV/XLSX files; persist batch identity, sources and dictionary snapshot; reload after restart.
- Exceptions, acceptance and boundary: Reruns retain addressable versions without silently rewriting old results; this is not a generic connector.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/batches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_store_and_grain.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC02 — 明确工作表和表头位置 / Select declared sheets and headers

**Status: IMPLEMENTED**

来源 / Sources: [#47](https://github.com/EricWang1358/BridgeFlow-AI/issues/47).

### 中文用例

- 参与者：月度汇总负责人（A03）、字典与标准维护人（A05）；写入操作按工具声明取得审批。
- 触发：工作簿有多个工作表或表头不在第 1 行。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：按声明或用户选择解析工作表、表头与数据起始行，保留原始坐标。
- 异常、验收和边界：多个候选不能猜第一张表；选错或结构不符给出恢复动作。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Dictionary and standards steward (A05); writes follow the tool-declared approval policy.
- Trigger: a workbook has several sheets or its header is below row 1.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Parse the declared or selected sheet, header and data start while retaining source coordinates.
- Exceptions, acceptance and boundary: Do not guess the first sheet among multiple candidates; expose recovery for incompatible layouts.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/batches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_sheet_layout.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC03 — 格式规范与质量问题 / Normalize formats and detect quality problems

**Status: IMPLEMENTED**

来源 / Sources: [#1](https://github.com/EricWang1358/BridgeFlow-AI/issues/1), [#16](https://github.com/EricWang1358/BridgeFlow-AI/issues/16).

### 中文用例

- 参与者：月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：导入的表格存在格式不一、重复、错位等质量问题。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：规范可确定的数值、日期及空行，检测重复和错列，输出修复日志或隔离项。
- 异常、验收和边界：可疑重复交易不能等同于可删重复行；关键值不由模型补全；行为受声明约束。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: an imported sheet has inconsistent formats, duplicates or shifted rows.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Normalize unambiguous numbers, dates and blank rows; detect duplicates and shifted columns; produce corrections or quarantine entries.
- Exceptions, acceptance and boundary: Suspected duplicate transactions are not automatically disposable rows; models never fill critical values; declarations control behavior.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/agents/sanitizer.py)；[行为测试 / Behavioral tests](../../backend/tests/test_quality_detection.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC04 — 歧义日期的声明与恢复 / Resolve date ambiguity by declaration

**Status: IMPLEMENTED**

来源 / Sources: [#79](https://github.com/EricWang1358/BridgeFlow-AI/issues/79).

### 中文用例

- 参与者：字典与标准维护人（A05）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：日期写法有歧义（如 03/11/2025），需要按部门声明解读。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：歧义日期进入待确认；按字典日期顺序解释后重新导入或处置。
- 异常、验收和边界：未声明日/月顺序不得猜测；按行日期归期而不是强塞批次月份。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: dates are ambiguous (e.g. 03/11/2025) and must be read by department declaration.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Flag ambiguous dates, apply a declared date order and reimport or resolve the quarantined record.
- Exceptions, acceptance and boundary: Do not guess day/month order; assign periods from row dates rather than forcing the batch month.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/agents/sanitizer.py)；[行为测试 / Behavioral tests](../../backend/tests/test_declared_date_order.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC05 — 清洗差异与原件定位 / Trace corrections to original sources

**Status: IMPLEMENTED**

来源 / Sources: [#14](https://github.com/EricWang1358/BridgeFlow-AI/issues/14), [#63](https://github.com/EricWang1358/BridgeFlow-AI/issues/63).

### 中文用例

- 参与者：月度汇总负责人（A03）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：需要核对某处清洗改动对应原件的哪一格。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：查看原值、修复值、规则、文件、表和单元格，核对来源与总数。
- 异常、验收和边界：引用缺关键部分不能编造；模型只获有界引用，不返还整表。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: a cleaning change must be traced to its original cell.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Inspect original/corrected values, rule, file, sheet and cell with source counts.
- Exceptions, acceptance and boundary: Do not fabricate missing provenance; model tools return bounded citations, never whole tables.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/schemas/__init__.py)；[行为测试 / Behavioral tests](../../backend/tests/test_traceability.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC06 — 隔离记录批准放行或丢弃 / Approve quarantine release or discard

**Status: IMPLEMENTED**

来源 / Sources: [#77](https://github.com/EricWang1358/BridgeFlow-AI/issues/77), [#88](https://github.com/EricWang1358/BridgeFlow-AI/issues/88).

### 中文用例

- 参与者：月度汇总负责人（A03）、审批人（A06）；写入操作按工具声明取得审批。
- 触发：有行被隔离，需要决定放行或丢弃。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：查看失败检查；提交修正及处置原因；审批后重校验，应用为派生批次。
- 异常、验收和边界：无审批或重校验失败不放行；原批次不变；丢弃有审计记录。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Approver (A06); writes follow the tool-declared approval policy.
- Trigger: quarantined rows must be released or discarded.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Inspect failed checks, propose fixes and a disposition reason, approve, revalidate and create a derived batch.
- Exceptions, acceptance and boundary: Absent approval or failed revalidation blocks release; preserve the original batch and audit discards.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/quarantine.py)；[行为测试 / Behavioral tests](../../backend/tests/test_quarantine_dispositions.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC07 — 原件列表和分页预览 / Browse original sources with pagination

**Status: IMPLEMENTED**

来源 / Sources: [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40), [#63](https://github.com/EricWang1358/BridgeFlow-AI/issues/63).

### 中文用例

- 参与者：月度汇总负责人（A03）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：需要在浏览器里翻看上传原件核对内容。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：从批次来源列表打开实际保留的原始解析视图，按页定位。
- 异常、验收和边界：缺原件明确不可预览；清洗结果不冒充原件；网页读取不成为模型读取。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: uploaded originals must be browsed page by page.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Open retained source previews from a batch source list and locate records by page.
- Exceptions, acceptance and boundary: Missing originals are unavailable rather than substituted with cleaned rows; browser access does not expose rows to models.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/batches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_business_mvp.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC08 — 币种换算、单位治理与缺月补齐 / Currency conversion, unit governance and missing periods

**Status: PARTIAL**

来源 / Sources: [#17](https://github.com/EricWang1358/BridgeFlow-AI/issues/17).

### 中文用例

- 参与者：字典与标准维护人（A05）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：报表出现不同币种、单位或缺少某个月份。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：现有计算检查声明币种并拒绝不一致；填报可按声明规范单位。
- 异常、验收和边界：通用汇率版本、跨币换算、缺月补齐尚未实现；#17 因范围缩减关闭，不记作完成。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: reports mix currencies or units, or a month is missing.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Current computation checks declared currency and rejects mismatches; intake normalizes declared units.
- Exceptions, acceptance and boundary: General FX versioning, cross-currency conversion and missing-month completion remain unimplemented; #17 was closed for scope, not delivery.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/business.py)；[行为测试 / Behavioral tests](../../backend/tests/test_business_mvp.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E04-UC09 — 导入问题的 agent 可读明细 / Agent-readable issue details

**Status: IMPLEMENTED_OFFLINE**

来源 / Sources: [#245](https://github.com/EricWang1358/BridgeFlow-AI/issues/245)（2026-09-22 业务方提出：右侧栏看得到、agent 够不着）；实施计划 [docs/36](../36-agent-readable-issues-plan.md)。

`POST /tools/batch-issues` 把一个批次全部待办——清洗修正（before/after/规则/出处）、隔离行（仅检查名，不含值）、intake 发现、被剔列、失效匹配、列问题、未决映射——按条投影，每条带能解决它的工具名；与浏览器视图同一事实源（`clean_tables` / `quarantine.entries` / `intake_checks`），不是第二套口径。行为测试：`backend/tests/test_agent_issues.py`。

The listing projects every open item — sanitizer corrections (before/after/rule/source), quarantined rows (checks only, no values), intake findings, dropped columns, stale matches, column questions, unresolved mappings — each with the tool that settles it, from the same facts the browser shows. Behavioral tests: `backend/tests/test_agent_issues.py`.
