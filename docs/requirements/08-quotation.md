# E08 — 声明式报价与签发

# E08 — Declared quotation and release

## 范围与角色 / Scope and actors

报价分析者、销售负责人、批准人 / Quote analysts, sales owners and approvers。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

StructuredDocument facts + human quotation contract → evidence/units checks → Decimal expression engine → internal draft or refusal. Raw contract extraction and external release remain separate gates.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E08-UC01 | 报价声明与输入责任 / Read quotation requirements and ownership | IMPLEMENTED |
| E08-UC02 | 基于声明计算内部草稿 / Compute an evidence-backed internal draft | IMPLEMENTED |
| E08-UC03 | 真实客户原件提取 / Extract facts from real customer originals | BLOCKED_EXTERNAL |
| E08-UC04 | 多方案比较及批准签发 / Compare scenarios and approve release | DESIGNED |
| E08-UC05 | 内部草稿与禁止自动外发 / Keep drafts internal without automatic sending | IMPLEMENTED |

## E08-UC01 — 报价声明与输入责任 / Read quotation requirements and ownership

**Status: IMPLEMENTED**

来源 / Sources: [#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7), [#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104).

### 中文用例

- 参与者：报价负责人（A07）；写入操作按工具声明取得审批。
- 触发：收到询价，需要知道报价要哪些输入、各由谁提供。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：查看人工配置的报价字段、单位、必需依据、公式与决策角色。
- 异常、验收和边界：无配置明确拒绝；政策系数不是合同事实；只读目录不算已生成报价。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Quotation owner (A07); writes follow the tool-declared approval policy.
- Trigger: an inquiry arrives and the owner needs the required inputs and who supplies them.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Read configured quote fields, units, required evidence, formulas and decision roles.
- Exceptions, acceptance and boundary: Refuse missing configuration; policy factors are not contract facts; reading a catalogue is not producing a quote.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/documents.py)；[行为测试 / Behavioral tests](../../backend/tests/test_declared_documents.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E08-UC02 — 基于声明计算内部草稿 / Compute an evidence-backed internal draft

**Status: IMPLEMENTED**

来源 / Sources: [#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7), [#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104).

### 中文用例

- 参与者：报价负责人（A07）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：输入齐备，需要按声明政策算出内部报价草稿。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：验证结构化事实后用 Decimal 与声明舍入计算价格档及风险检查，绑定输入版本。
- 异常、验收和边界：缺成本/产能/付款依据、错误单位、循环或除零不给半成品价格；实现限结构化事实。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Quotation owner (A07), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: inputs are complete and an internal draft must be computed from the declared policy.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Validate structured facts, calculate price bands using Decimal and declared rounding, and bind the draft to input versions.
- Exceptions, acceptance and boundary: Missing cost/capacity/payment evidence, wrong units, cycles or division by zero yield no partial prices; implementation accepts structured facts.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/documents.py)；[行为测试 / Behavioral tests](../../backend/tests/test_declared_documents.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E08-UC03 — 真实客户原件提取 / Extract facts from real customer originals

**Status: BLOCKED_EXTERNAL**

来源 / Sources: [#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104), [#23](https://github.com/EricWang1358/BridgeFlow-AI/issues/23).

### 中文用例

- 参与者：报价负责人（A07）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：输入还在客户合同、会话记录等原件里。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：按获准解析器从真实合同、条款和附件提取事实及页/段引用，再进入报价计算。
- 异常、验收和边界：当前只有结构化/合成事实验证；真实样板、格式适配及语义验收均未完成。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Quotation owner (A07), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: inputs are still inside customer contracts or conversation records.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: use approved parsers to extract facts and page/paragraph references from real contracts and attachments before computation.
- Exceptions, acceptance and boundary: Current evidence covers structured/synthetic facts only; real samples, format adapters and semantic acceptance remain open.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/documents.py)；[行为测试 / Behavioral tests](../../backend/tests/test_mock_quotation.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E08-UC04 — 多方案比较及批准签发 / Compare scenarios and approve release

**Status: DESIGNED**

来源 / Sources: [#20](https://github.com/EricWang1358/BridgeFlow-AI/issues/20), [#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104).

### 中文用例

- 参与者：报价负责人（A07）、审批人（A06）；写入操作按工具声明取得审批。
- 触发：需要比较价格、账期、交期等方案并批准对外版本。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：比较至少三组价格与账期，展示成本、毛利、产能及风险，批准具体版本才可外用。
- 异常、验收和边界：价格档计算不等于方案审批；当前通用审批框架不代表报价签发已接入。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Quotation owner (A07), Approver (A06); writes follow the tool-declared approval policy.
- Trigger: price, terms and delivery scenarios must be compared and one approved for release.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: compare at least three price/term scenarios with costs, margin, capacity and risks; approve an exact version for external use.
- Exceptions, acceptance and boundary: Price-band computation is not scenario approval; the generic approval framework does not establish quote release integration.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/quotation.tsx)；[行为测试 / Behavioral tests](../../backend/tests/test_declared_documents.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E08-UC05 — 内部草稿与禁止自动外发 / Keep drafts internal without automatic sending

**Status: IMPLEMENTED**

来源 / Sources: [#20](https://github.com/EricWang1358/BridgeFlow-AI/issues/20).

### 中文用例

- 参与者：报价负责人（A07）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：草稿完成后，有人或代理试图直接外发。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：返回草稿性质、输入依据和限制，由用户决定后续人工业务动作。
- 异常、验收和边界：未批准不得声称可对外使用；当前没有客户自动发送通道。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Quotation owner (A07), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: after drafting, a person or agent attempts to send it externally.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Return draft status, input evidence and limitations for subsequent human business action.
- Exceptions, acceptance and boundary: Unapproved drafts cannot be claimed externally usable; no automatic customer sending channel is implemented.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/documents.py)；[行为测试 / Behavioral tests](../../backend/tests/test_declared_documents.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
