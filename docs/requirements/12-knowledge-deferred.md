# E12 — 历史知识库与问答范围

# E12 — Historical knowledge and Q&A scope

## 范围与角色 / Scope and actors

知识维护者、部门员工 / Knowledge maintainers and employees。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Historical #131 was explicitly closed as out of current scope. These UCs preserve traceability; no new knowledge platform is authorized or implied by the three-agent product baseline.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E12-UC01 | 知识材料转写、解析与切块 / Transcribe, parse and chunk knowledge materials | DEFERRED |
| E12-UC02 | 知识版本存储与索引 / Store and index versioned knowledge | DEFERRED |
| E12-UC03 | 按权限检索并引用回答 / Retrieve authorized knowledge and answer with citations | DEFERRED |

## E12-UC01 — 知识材料转写、解析与切块 / Transcribe, parse and chunk knowledge materials

**Status: DEFERRED**

来源 / Sources: [#128](https://github.com/EricWang1358/BridgeFlow-AI/issues/128), [#131](https://github.com/EricWang1358/BridgeFlow-AI/issues/131).

### 中文用例

- 参与者：字典与标准维护人（A05）；写入操作按工具声明取得审批。
- 触发：企业制度、手册或录音需要成为可检索的知识。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：历史目标：音频或文档转写解析为带来源、部门、时间的切块，解析失败进入人工处理。
- 异常、验收和边界：#131 关闭理由为本轮不做；工作流材料结构检查不是知识接入管线。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05); writes follow the tool-declared approval policy.
- Trigger: policies, manuals or recordings must become searchable knowledge.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Historical target: transcribe/parse audio or documents into source-, department- and time-tagged chunks, routing failures to people.
- Exceptions, acceptance and boundary: The closure reason is out of current scope; workflow shape inspection is not a knowledge ingestion pipeline.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../docs/24-meeting-2026-09-13.md)；未发现实现与行为测试 / No implementation or behavioral tests identified。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E12-UC02 — 知识版本存储与索引 / Store and index versioned knowledge

**Status: DEFERRED**

来源 / Sources: [#129](https://github.com/EricWang1358/BridgeFlow-AI/issues/129), [#131](https://github.com/EricWang1358/BridgeFlow-AI/issues/131).

### 中文用例

- 参与者：字典与标准维护人（A05）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：知识资料更新，需要保留版本并重建索引。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：历史目标：持久知识原文、切块与索引，修订使旧片段失效，删除同步清理。
- 异常、验收和边界：不存在交付的通用知识索引；批次/映射持久化不能计作知识库。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Dictionary and standards steward (A05), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: knowledge materials change and versions and indexes must be maintained.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Historical target: persist originals/chunks/indexes, invalidate old revisions and propagate deletions.
- Exceptions, acceptance and boundary: No delivered general knowledge index was found; batch/mapping persistence is not a knowledge base.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../docs/24-meeting-2026-09-13.md)；未发现实现与行为测试 / No implementation or behavioral tests identified。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E12-UC03 — 按权限检索并引用回答 / Retrieve authorized knowledge and answer with citations

**Status: DEFERRED**

来源 / Sources: [#130](https://github.com/EricWang1358/BridgeFlow-AI/issues/130), [#131](https://github.com/EricWang1358/BridgeFlow-AI/issues/131).

### 中文用例

- 参与者：部门填报员（A01）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：员工提问，需要在其权限内引用资料回答。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：历史目标：先按部门权限裁剪检索，再以有界片段回答，引用原文；无依据明确拒答。
- 异常、验收和边界：指标工具和字段字典查询不等于企业文档问答；不纳入已实现数量。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department contributor (A01), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: an employee asks a question answered only from authorized, cited materials.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Historical target: filter retrieval by department permission, answer from bounded passages with citations and refuse unsupported answers.
- Exceptions, acceptance and boundary: Metric tools and dictionary lookup are not enterprise document Q&A; exclude this from delivered counts.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../docs/24-meeting-2026-09-13.md)；未发现实现与行为测试 / No implementation or behavioral tests identified。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
