# E06 — 总表整合、口径核对与导出

# E06 — Master integration, reconciliation and export

## 范围与角色 / Scope and actors

业务分析者、部门复核人 / Analysts and department reviewers。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Frozen integration declaration + retained source sheets → declared keys/rollups → checked master cells + lineage → browser table/XLSX. Model summary exposes counts, not conflicting cell contents.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E06-UC01 | 日周粒度归并到月 / Roll daily and weekly data onto months | IMPLEMENTED |
| E06-UC02 | 按声明构建跨部门总表 / Build a declared cross-department master | IMPLEMENTED |
| E06-UC03 | 公式核对与跨部门差异 / Verify formulas and cross-department differences | IMPLEMENTED |
| E06-UC04 | 单元格下钻与源文件跳转 / Drill from master cells to source files | IMPLEMENTED |
| E06-UC05 | 总表 XLSX 导出 / Export the master workbook | IMPLEMENTED |
| E06-UC06 | 季度年度总表与 PDF 报告 / Quarter/year masters and PDF reports | DEFERRED |

## E06-UC01 — 日周粒度归并到月 / Roll daily and weekly data onto months

**Status: IMPLEMENTED**

来源 / Sources: [#18](https://github.com/EricWang1358/BridgeFlow-AI/issues/18).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「日周粒度归并到月」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：按度量声明归并日周数据，保留原始期间和来源供下钻。
- 异常、验收和边界：未裁决日期不参与；数量、价格、存量不得统一盲目求和。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to roll daily and weekly data onto months.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Roll daily/weekly measurements onto months using declared semantics while retaining contributing periods and sources.
- Exceptions, acceptance and boundary: Exclude unresolved dates; do not blindly sum quantities, prices and stocks alike.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/grain.py)；[行为测试 / Behavioral tests](../../backend/tests/test_store_and_grain.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E06-UC02 — 按声明构建跨部门总表 / Build a declared cross-department master

**Status: IMPLEMENTED**

来源 / Sources: [#44](https://github.com/EricWang1358/BridgeFlow-AI/issues/44), [#92](https://github.com/EricWang1358/BridgeFlow-AI/issues/92), [#143](https://github.com/EricWang1358/BridgeFlow-AI/issues/143).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「按声明构建跨部门总表」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：按业务模板顺序与公共键整合部门文件；生产明细依声明汇总，缺部门显示部分记录。
- 异常、验收和边界：同名不同编码不合并；未声明多行汇总拒绝；冻结批次不借用当前规则。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to build a declared cross-department master.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Integrate departments using declared common keys and template order; roll up production as declared and mark missing departments.
- Exceptions, acceptance and boundary: Do not merge matching names with different codes; reject undeclared rollups; frozen batches do not borrow current policy.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/integration.py)；[行为测试 / Behavioral tests](../../backend/tests/test_company_integration.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E06-UC03 — 公式核对与跨部门差异 / Verify formulas and cross-department differences

**Status: IMPLEMENTED**

来源 / Sources: [#92](https://github.com/EricWang1358/BridgeFlow-AI/issues/92).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「公式核对与跨部门差异」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：比较上传值与声明公式，检查数量、名称和财务分类，显示冲突和未确认假设。
- 异常、验收和边界：缺税率不标已验证；缺数值不能只加剩余行；收入与成本口径分离。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to verify formulas and cross-department differences.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Compare supplied values against formulas and check quantities, names and financial classes, exposing conflicts and assumptions.
- Exceptions, acceptance and boundary: Missing VAT prevents verification; missing values cannot yield partial sums presented as complete; separate revenue and costs.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/integration.py)；[行为测试 / Behavioral tests](../../backend/tests/test_integration_boundaries.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E06-UC04 — 单元格下钻与源文件跳转 / Drill from master cells to source files

**Status: IMPLEMENTED**

来源 / Sources: [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40), [#63](https://github.com/EricWang1358/BridgeFlow-AI/issues/63).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「单元格下钻与源文件跳转」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：点击总表单元格查看计算或引用，再定位对应部门原件；失败可重试。
- 异常、验收和边界：引用与当前批次一致；没有出处不能以另一批次补齐。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to drill from master cells to source files.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Open a master cell to inspect its calculation/citations and navigate to its departmental source; allow retry after failure.
- Exceptions, acceptance and boundary: Citations must belong to the current batch; never substitute sources from another batch.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/master.tsx)；[行为测试 / Behavioral tests](../../plugins/tests/cells.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E06-UC05 — 总表 XLSX 导出 / Export the master workbook

**Status: IMPLEMENTED**

来源 / Sources: [#22](https://github.com/EricWang1358/BridgeFlow-AI/issues/22).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「总表 XLSX 导出」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：下载当前冻结批次的总表工作簿，保留模板列和未决问题。
- 异常、验收和边界：公式形状的不可信文本保持文本；此能力不代表全部报告 PDF 导出。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to export the master workbook.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Download the frozen batch master workbook with template columns and open issues.
- Exceptions, acceptance and boundary: Untrusted formula-shaped strings remain text; this does not implement general report PDF export.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/integration.py)；[行为测试 / Behavioral tests](../../backend/tests/test_integration_boundaries.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E06-UC06 — 季度年度总表与 PDF 报告 / Quarter/year masters and PDF reports

**Status: DEFERRED**

来源 / Sources: [#22](https://github.com/EricWang1358/BridgeFlow-AI/issues/22).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「季度年度总表与 PDF 报告」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：在批准聚合口径后生成季/年结果，并按明确筛选及版本生成 PDF。
- 异常、验收和边界：现有月度总表和 XLSX 不满足该完整需求；未发现完整交付路径，保留为范围缺口。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to quarter/year masters and pdf reports.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: generate quarter/year results under approved aggregation policies and PDF reports with version/filter context.
- Exceptions, acceptance and boundary: Monthly masters and XLSX do not satisfy this scope; no complete delivery path was found.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/integration.py)；[行为测试 / Behavioral tests](../../backend/tests/test_company_integration.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
