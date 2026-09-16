# E07 — 确定性指标与四角色研判

# E07 — Deterministic metrics and four-role review

## 范围与角色 / Scope and actors

分析发起者、四部门复核人、决策负责人 / Analysts, departmental reviewers and decision owners。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Python computes declared metrics; native DSH captain dispatches independent children; host validates evidence, numbers and deadlines before storing a report. Four review roles are not the three product agents.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E07-UC01 | 列出可用指标并确定性计算 / Discover and compute declared metrics | IMPLEMENTED |
| E07-UC02 | 带来源的指标查询 / Query metrics with bounded provenance | IMPLEMENTED |
| E07-UC03 | 原生队长分派四部门研判 / Dispatch four departmental reviews natively | IMPLEMENTED |
| E07-UC04 | 验证数值、证据与责任边界 / Validate findings, evidence and responsibility | IMPLEMENTED |
| E07-UC05 | 部分结果、超时与重启恢复 / Preserve partial reviews and recover interrupted runs | IMPLEMENTED |
| E07-UC06 | 保存报告、用量与轨迹 / Retain reports, usage and review traces | IMPLEMENTED |
| E07-UC07 | 风险处置审批生命周期 / Approve and track risk dispositions | DESIGNED |

## E07-UC01 — 列出可用指标并确定性计算 / Discover and compute declared metrics

**Status: IMPLEMENTED**

来源 / Sources: [#13](https://github.com/EricWang1358/BridgeFlow-AI/issues/13), [#65](https://github.com/EricWang1358/BridgeFlow-AI/issues/65), [#89](https://github.com/EricWang1358/BridgeFlow-AI/issues/89), [#92](https://github.com/EricWang1358/BridgeFlow-AI/issues/92).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「列出可用指标并确定性计算」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：从字典列可算指标，按声明公式和科目分类计算产能、成本、毛利、账期及订单差。
- 异常、验收和边界：缺字段、币种不符或零分母拒绝；不让模型补数字。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to discover and compute declared metrics.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: List computable metrics and calculate capacity, cost, margin, terms and order gaps using declared formulas and account classes.
- Exceptions, acceptance and boundary: Refuse missing fields, currency mismatches or zero denominators; models do not fill numbers.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/business.py)；[行为测试 / Behavioral tests](../../backend/tests/test_rules_compute.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC02 — 带来源的指标查询 / Query metrics with bounded provenance

**Status: IMPLEMENTED**

来源 / Sources: [#5](https://github.com/EricWang1358/BridgeFlow-AI/issues/5), [#27](https://github.com/EricWang1358/BridgeFlow-AI/issues/27), [#58](https://github.com/EricWang1358/BridgeFlow-AI/issues/58).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「带来源的指标查询」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：按批次/实体查询指标，返回公式、引用样本和真实计数。
- 异常、验收和边界：未知指标拒绝；有界样本不冒充全部来源；不得返回完整原始行。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to query metrics with bounded provenance.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Query metrics by batch/entity with formulas, sampled citations and true counts.
- Exceptions, acceptance and boundary: Refuse unknown metrics; distinguish samples from full provenance; never return all raw rows.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/tools.py)；[行为测试 / Behavioral tests](../../backend/tests/test_tool_endpoints.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC03 — 原生队长分派四部门研判 / Dispatch four departmental reviews natively

**Status: IMPLEMENTED**

来源 / Sources: [#38](https://github.com/EricWang1358/BridgeFlow-AI/issues/38), [#51](https://github.com/EricWang1358/BridgeFlow-AI/issues/51).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「原生队长分派四部门研判」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：队长取得上下文，通过官方子代理分派四部门，收集独立结果并保留父子会话。
- 异常、验收和边界：不使用遗留 Python provider 的伪并发；本轮没有重新验证真实模型质量。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to dispatch four departmental reviews natively.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: The captain reads context, dispatches four official subagents and collects independent results with parent/child sessions.
- Exceptions, acceptance and boundary: Do not equate legacy provider serialization with native concurrency; live model quality was not rerun this turn.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/tools/review-batch.ts)；[行为测试 / Behavioral tests](../../plugins/tests/runtime.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC04 — 验证数值、证据与责任边界 / Validate findings, evidence and responsibility

**Status: IMPLEMENTED**

来源 / Sources: [#5](https://github.com/EricWang1358/BridgeFlow-AI/issues/5), [#6](https://github.com/EricWang1358/BridgeFlow-AI/issues/6), [#13](https://github.com/EricWang1358/BridgeFlow-AI/issues/13).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「验证数值、证据与责任边界」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：核对模型解释的数值、阈值、依据及责任；自由文本标为建议。
- 异常、验收和边界：阈值不能冒充批准额度；无证据或篡改数值拒绝；角色冲突不自动调和。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to validate findings, evidence and responsibility.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Validate interpreted numbers, thresholds, evidence and decision ownership; label free text as advice.
- Exceptions, acceptance and boundary: Thresholds are not approved limits; reject unsupported or altered numbers; do not silently reconcile role conflicts.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/business.py)；[行为测试 / Behavioral tests](../../backend/tests/test_business_mvp.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC05 — 部分结果、超时与重启恢复 / Preserve partial reviews and recover interrupted runs

**Status: IMPLEMENTED**

来源 / Sources: [#111](https://github.com/EricWang1358/BridgeFlow-AI/issues/111), [#112](https://github.com/EricWang1358/BridgeFlow-AI/issues/112), [#113](https://github.com/EricWang1358/BridgeFlow-AI/issues/113).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「部分结果、超时与重启恢复」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：贯穿父子任务同一截止时间；保留失败归属；重启终结在途任务；重复汇总幂等。
- 异常、验收和边界：迟到成功不能覆盖超时；人工备注不补造部门结论，也不能触发重跑。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to preserve partial reviews and recover interrupted runs.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Apply a common deadline, retain failure attribution, terminate interrupted runs after restart and finalize idempotently.
- Exceptions, acceptance and boundary: Late success cannot overwrite timeout; human notes neither fabricate missing findings nor trigger reruns.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/review_runs.py)；[行为测试 / Behavioral tests](../../backend/tests/test_review_runs.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC06 — 保存报告、用量与轨迹 / Retain reports, usage and review traces

**Status: IMPLEMENTED**

来源 / Sources: [#31](https://github.com/EricWang1358/BridgeFlow-AI/issues/31), [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「保存报告、用量与轨迹」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：保存真实报告身份，按阶段记录用量，链接原生会话并恢复历史报告。
- 异常、验收和边界：未发生研判不生成报告；失效链接显示错误；历史证据不冒充同版本重跑。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to retain reports, usage and review traces.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Persist report identity and per-stage usage, link native sessions and reopen saved reports.
- Exceptions, acceptance and boundary: No review means no report; expired links are explicit; historical evidence is not a rerun of the current build.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/reviews.py)；[行为测试 / Behavioral tests](../../backend/tests/test_review_runs.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E07-UC07 — 风险处置审批生命周期 / Approve and track risk dispositions

**Status: DESIGNED**

来源 / Sources: [#19](https://github.com/EricWang1358/BridgeFlow-AI/issues/19).

### 中文用例

- 参与者：本 epic 的授权使用者；有写入时按工具声明取得审批。
- 触发：用户需要「风险处置审批生命周期」。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：确认、驳回、指派、备注及关闭风险，保存授权人和处置时间。
- 异常、验收和边界：已有 Finding 和报告备注不构成完整状态机；业务责任与关闭规则待定。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actor: an authorized epic user; mutations follow the tool-declared approval policy.
- Trigger: the user requests to approve and track risk dispositions.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: confirm, reject, assign, annotate and close risk findings with authorized actor and timestamp.
- Exceptions, acceptance and boundary: Finding schemas and report notes do not implement the full state machine; ownership and closure rules remain undecided.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/schemas/__init__.py)；[行为测试 / Behavioral tests](../../backend/tests/test_traceability.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
