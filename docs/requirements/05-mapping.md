# E05 — 字段字典、语义匹配与记忆

# E05 — Dictionaries, semantic matching and memory

## 范围与角色 / Scope and actors

字典负责人、映射复核人 / Dictionary owners and mapping reviewers。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Frozen human dictionary → shape profiling → closed candidate set → native approval → persistent mapping memory. Evidence fingerprint changes invalidate reuse; no dictionary invention.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E05-UC01 | 读取人工字典与拒绝猜字段 / Read declared fields without guessing | IMPLEMENTED |
| E05-UC02 | 无原始值的列特征画像 / Profile columns without exposing cell values | IMPLEMENTED |
| E05-UC03 | 列候选、审批与拒绝恢复 / Review field candidates and recover after refusal | IMPLEMENTED |
| E05-UC04 | 跨部门实体关系与同类别名 / Resolve cross-department relations and aliases | IMPLEMENTED |
| E05-UC05 | 映射记忆、审计与失效 / Persist mapping memory with evidence invalidation | IMPLEMENTED |
| E05-UC06 | 会议规则上下文接入 / Ingest meeting context for mapping rules | DESIGNED |

## E05-UC01 — 读取人工字典与拒绝猜字段 / Read declared fields without guessing

**Status: IMPLEMENTED**

来源 / Sources: [#32](https://github.com/EricWang1358/BridgeFlow-AI/issues/32), [#44](https://github.com/EricWang1358/BridgeFlow-AI/issues/44), [#45](https://github.com/EricWang1358/BridgeFlow-AI/issues/45).

### 中文用例

- 参与者：字典与标准维护人（A05）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：导入或研判需要知道每一列在字典里代表什么。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：从冻结字典取得实体、关系、连接键和指标；缺声明时提示配置缺失。
- 异常、验收和边界：默认路径不猜第一列；遗留关闭路径不能当成现行产品能力。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: import or review needs the declared meaning of each column.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Read entities, relations, join keys and measures from the frozen dictionary; missing declarations require configuration.
- Exceptions, acceptance and boundary: The default path never guesses the first column; disabled legacy paths are not current product capabilities.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/agents/semantic_resolver.py)；[行为测试 / Behavioral tests](../../backend/tests/test_no_guessing.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E05-UC02 — 无原始值的列特征画像 / Profile columns without exposing cell values

**Status: IMPLEMENTED**

来源 / Sources: [#46](https://github.com/EricWang1358/BridgeFlow-AI/issues/46), [#58](https://github.com/EricWang1358/BridgeFlow-AI/issues/58), [#61](https://github.com/EricWang1358/BridgeFlow-AI/issues/61).

### 中文用例

- 参与者：Captain 代理（S01）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：有未知列需要匹配，但不能把单元格内容交给模型。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：计算唯一度、填充率、类型及跨部门重合度，帮助判断需要匹配的列。
- 异常、验收和边界：工具不带真实单元格；特征不等于字段语义已获批准。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Captain agent (S01), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: unknown columns need matching without exposing cell values to the model.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Compute uniqueness, fill ratio, type and cross-department overlap to identify matching needs.
- Exceptions, acceptance and boundary: Tools omit actual cells; statistical shape does not approve field semantics.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/profiling.py)；[行为测试 / Behavioral tests](../../backend/tests/test_profiling.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E05-UC03 — 列候选、审批与拒绝恢复 / Review field candidates and recover after refusal

**Status: IMPLEMENTED**

来源 / Sources: [#46](https://github.com/EricWang1358/BridgeFlow-AI/issues/46), [#61](https://github.com/EricWang1358/BridgeFlow-AI/issues/61), [#102](https://github.com/EricWang1358/BridgeFlow-AI/issues/102), [#122](https://github.com/EricWang1358/BridgeFlow-AI/issues/122), [#124](https://github.com/EricWang1358/BridgeFlow-AI/issues/124).

### 中文用例

- 参与者：月度汇总负责人（A03）、审批人（A06）；写入操作按工具声明取得审批。
- 触发：上传件列名与字典不一致，需要提议匹配并由人审批。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：从已声明字段生成候选，显示依据；人审批后记录映射；拒绝后提示补规则、改匹配或搁置。
- 异常、验收和边界：候选集外目标拒绝；无审批不保存；新映射只影响后续导入。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Approver (A06); writes follow the tool-declared approval policy.
- Trigger: uploaded column names differ from the dictionary and a match must be proposed and approved.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Offer candidates from declared fields with evidence, persist after approval and provide correction/configuration/defer paths after refusal.
- Exceptions, acceptance and boundary: Reject targets outside the closed set and writes without approval; apply new mappings to later imports only.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/column_matches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_column_matches.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E05-UC04 — 跨部门实体关系与同类别名 / Resolve cross-department relations and aliases

**Status: IMPLEMENTED**

来源 / Sources: [#3](https://github.com/EricWang1358/BridgeFlow-AI/issues/3), [#4](https://github.com/EricWang1358/BridgeFlow-AI/issues/4), [#24](https://github.com/EricWang1358/BridgeFlow-AI/issues/24), [#25](https://github.com/EricWang1358/BridgeFlow-AI/issues/25), [#51](https://github.com/EricWang1358/BridgeFlow-AI/issues/51), [#72](https://github.com/EricWang1358/BridgeFlow-AI/issues/72).

### 中文用例

- 参与者：字典与标准维护人（A05）、审批人（A06）；写入操作按工具声明取得审批。
- 触发：不同部门用不同写法指同一实体，或实体之间有业务关系。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：使用字典关系、行内共现及残余裁决；只对同一实体的别名使用相似度。
- 异常、验收和边界：产品与原料不因名称相似自动建立关系；未知与低置信分别保留。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Approver (A06); writes follow the tool-declared approval policy.
- Trigger: departments name the same entity differently or entities are related.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Use declared relations, within-row co-occurrence and residual adjudication; similarity applies only to aliases of the same entity.
- Exceptions, acceptance and boundary: Do not infer product/material relations from name similarity; distinguish unresolved from low-confidence results.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/agents/semantic_resolver.py)；[行为测试 / Behavioral tests](../../backend/tests/test_resolver.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E05-UC05 — 映射记忆、审计与失效 / Persist mapping memory with evidence invalidation

**Status: IMPLEMENTED**

来源 / Sources: [#29](https://github.com/EricWang1358/BridgeFlow-AI/issues/29), [#82](https://github.com/EricWang1358/BridgeFlow-AI/issues/82), [#102](https://github.com/EricWang1358/BridgeFlow-AI/issues/102), [#123](https://github.com/EricWang1358/BridgeFlow-AI/issues/123).

### 中文用例

- 参与者：月度汇总负责人（A03）、字典与标准维护人（A05）；写入操作按工具声明取得审批。
- 触发：下个月再导入时，希望复用已批准的匹配，且依据变化时失效。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：保存批准的关系及依据；跨批次复用；按语义证据或列形状变更重新询问。
- 异常、验收和边界：文字改写不必失效；事实变化不能复用；批准身份仍受共享会话边界限制。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Dictionary and standards steward (A05); writes follow the tool-declared approval policy.
- Trigger: next month's import should reuse approved matches and invalidate them when evidence changes.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Persist approved relations and evidence for reuse; ask again when semantic evidence or column shape changes.
- Exceptions, acceptance and boundary: Wording changes need not invalidate memory; changed facts do; approval identity retains shared-session limits.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/mappings.py)；[行为测试 / Behavioral tests](../../backend/tests/test_mapping_memory.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E05-UC06 — 会议规则上下文接入 / Ingest meeting context for mapping rules

**Status: DESIGNED**

来源 / Sources: [#121](https://github.com/EricWang1358/BridgeFlow-AI/issues/121).

### 中文用例

- 参与者：字典与标准维护人（A05）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：会议上口头约定了字段规则，需要作为有来源的规则上下文登记。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：登记会议/文档来源，提取规则候选，人工确认后作为封闭映射依据。
- 异常、验收和边界：现有候选证据不等于通用音频转写或会议文档解析；未发现该通用管线的交付证据。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: field rules agreed verbally in a meeting must be registered with their source.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: register meeting/document references, extract proposed rules and confirm them before matching.
- Exceptions, acceptance and boundary: Existing candidate evidence is not general transcription or meeting parsing; no delivered general pipeline was found.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/column_matches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_column_matches.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
