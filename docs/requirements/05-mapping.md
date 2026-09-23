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
| E05-UC07 | 聚合画像与字典起草 / Aggregate profiles and draft a dictionary | IMPLEMENTED_OFFLINE |
| E05-UC08 | 草案逐条审核与发布 / Review draft entries and publish a version | IMPLEMENTED_OFFLINE |

> E05-UC07/UC08 实现记录（2026-09-22，`feature/usability-20260921`）：起草有两条路——
> `dictionary_import` 把业务自己的 OA 字典表（字段名称/关联部门/数据类型/描述/来源表字段/变更说明）
> **确定性转写**成草案（真实样例：hackathon 材料里的 字典.xlsx，77 行）；`dictionary_draft`
> 按原设计吃 `profile` 统计走模型起草（计费留痕，宿主侧丢弃无证据条目）。两条路汇进同一个
> `dictionary_decide`（逐条接受/修改/拒绝，度量必须同时定 rollup）与 `dictionary_publish`
> （全部有决定才可发布；发布前重跑导入侧同级校验；写 `versions/` 新版本；旧批次不动）。
> 行为测试：`backend/tests/test_dictionary_draft.py`。

## E05-UC07 — 聚合画像与字典起草 / Aggregate profiles and draft a dictionary

**Status: DESIGNED**

来源 / Sources: [#205](https://github.com/EricWang1358/BridgeFlow-AI/issues/205)（2026-09-18 业务负责人拍板）。本 UC 是 2026-09-07「字典由人预设」边界的**显式修订**：起草从「纯人工」变为「模型提议 + 人逐条审核」，其余硬约束全部保留。

### 中文需求与验收

- 参与者：总表管理者 / 总经办（A05）、部门填报员（A01，只提供上传件）。
- 触发：新客户接入或新一版模板到位，四部门已各自上传文件，但还没有能用的字典，导入因此冻结在 `needs_configuration`。
- 前置：至少一个部门有上传件；起草人具备 `dictionary_draft` 操作许可；起草是**人发起的显式动作**，不随导入自动触发。
- 主流程：
  1. 起草人把已上传的部门文件放进同一工作区，看到按部门列出的**列结构画像**：列名、推断类型、填充率、唯一度、跨部门值重合度。画像不含任何单元格内容。
  2. 缺部门时明确标注为缺失，不按已有部门推断缺失部门的声明。
  3. 起草人发起起草。模型的输入只有画像统计与（可选的）标准模板表头；输出是字典草案：可连接实体列、期间列、度量、汇总口径，可含研判契约输入（日期列、非负列、币种列）。
  4. 草案每条带证据（来自哪个部门的哪一列、凭哪几项统计特征）与不确定标注；模型给不出证据的条目不进草案。
  5. 草案可保存、可恢复，交给 E05-UC08 逐条审核。
- 异常：没有任何上传件时拒绝起草并说明先上传；画像读不出时该部门标为「未画像」，不参与起草；模型调用失败时保留已有草案，不产生半份草案。
- 验收：
  - AC-1 Given 四部门已上传 When 打开聚合视图 Then 每个部门的列画像可见，且响应中不含任何单元格内容（按字节检索原始值应为 0 命中）。
  - AC-2 Given 只有三个部门上传 When 发起起草 Then 草案只覆盖这三个部门，缺失部门在草案与界面上标为缺失，不生成其声明。
  - AC-3 Given 起草完成 When 展开任一条目 Then 显示其证据（部门、列名、统计特征），无证据条目不存在。
  - AC-4 Given 起草动作 When 统计其模型调用 Then 调用次数 ≥ 1 且费用被记录；mock 输出不作为生成质量证据。
- 后置：草案是独立对象，不触碰现行字典，也不影响任何已冻结批次。
- 依赖：E05-UC02（画像）、E05-UC03（列候选）、E09-UC01（审批）、E04-UC01（上传）。

### English requirements and acceptance

- Actors: Master-table owner / management office (A05); department contributors only supply files.
- Trigger: a new client or a new template version — four departments have uploaded, no usable dictionary exists, and import is frozen at `needs_configuration`.
- Preconditions: at least one department has a file; the drafter holds `dictionary_draft`; drafting is an explicit human action, never triggered by import.
- Main flow: show per-department column profiles (name, inferred type, fill rate, uniqueness, cross-department value overlap — never cell contents); mark missing departments as missing; on request, the model drafts declarations from those statistics and, optionally, the approved template headers; every entry carries its evidence and any uncertainty; the draft is saved for entry-by-entry review.
- Exceptions: no uploads means refusal; an unprofilable department is marked unprofiled and excluded; a failed model call leaves the existing draft intact rather than producing half a draft.
- Acceptance: AC-1 profiles visible with zero cell contents in the response; AC-2 a three-department draft marks the fourth missing and declares nothing for it; AC-3 every entry shows its evidence and evidence-free entries do not exist; AC-4 drafting is a billed call with recorded cost, and mock output is not evidence of quality.
- Postcondition: the draft is a separate object; the active dictionary and every frozen batch are untouched.

## E05-UC08 — 草案逐条审核与发布 / Review draft entries and publish a version

**Status: DESIGNED**

来源 / Sources: [#205](https://github.com/EricWang1358/BridgeFlow-AI/issues/205).

### 中文需求与验收

- 参与者：总表管理者（A05）、审批人（A06）。
- 触发：字典草案已生成，需要逐条决定并发布为可用版本。
- 前置：草案存在；发布人具备 `dictionary_publish` 操作许可；发布走原生审批回执。
- 主流程：
  1. 审核人逐条接受、修改或拒绝；拒绝可填理由；修改后以修改值为准。
  2. 全部条目都有决定后才允许发布。
  3. 发布前做与导入侧**同级**的合法性校验（没有可连接列、`date_order` 非法等）；不合法则拒绝发布并给出与导入一致的错误语义。
  4. 发布写入新版本，记录版本指纹、决定人、时间与每条依据的证据；当前版本指针指向它。
  5. 发布只影响之后的导入。
- 异常：还有条目未决定时拒绝发布并列出剩余条数；并发发布按版本冲突拒绝；校验失败不产生新版本。
- 验收：
  - AC-1 Given 草案 12 条，其中 2 条被拒绝 When 发布 Then 新版本只含 10 条，被拒条目不出现在终稿，拒绝理由留痕。
  - AC-2 Given 还有 1 条未决定 When 发布 Then 拒绝并说明还剩 1 条。
  - AC-3 Given 发布成功 When 查看此前的批次 Then 其 `summary.dictionary` 与结果完全不变；之后导入的新批次冻结新版本指纹。
  - AC-4 Given 草案缺少可连接列 When 发布 Then 拒绝，错误语义与导入侧一致（「没有声明可连接实体列」），不产生新版本。
- 后置：版本、审批回执与每条证据一并留档；旧版本不被覆盖。
- 依赖：E05-UC07、E09-UC01、E04-UC01、E06-UC03。

### English requirements and acceptance

- Actors: Master-table owner (A05), Approver (A06).
- Trigger: a draft exists and must be decided entry by entry and published.
- Preconditions: the publisher holds `dictionary_publish`; publishing consumes a native approval receipt.
- Main flow: accept, edit or reject each entry with a reason; publishing requires every entry decided; validate exactly as import does before publishing; write a new version with its fingerprint, decider, time and per-entry evidence, and point the active version at it; only later imports are affected.
- Exceptions: undecided entries refuse publication and say how many remain; concurrent publication conflicts by version; failed validation produces no version.
- Acceptance: AC-1 rejected entries are absent from the published version and their reasons are kept; AC-2 an undecided entry blocks publication; AC-3 earlier batches and their `summary.dictionary` are unchanged while later imports freeze the new fingerprint; AC-4 a draft without a joinable column is refused with import's own error.

## 本轮设计判定与依据 / Design decisions and their evidence（E05-UC07/UC08）

需求记录（#205）留了 6 个待确认问题。能由开发侧按既有约束推定的，判定与依据记在这里；真正属于业务方的，单列在下面。

The requirement record left six open questions. The ones that follow from constraints already in force are decided here, with evidence; the ones that are genuinely the business side's are listed separately.

| # | 判定 / Decision | 依据 / Evidence |
| --- | --- | --- |
| D28 | 标准模板是**可选参考**，不是起草的必需输入 | docs/01 说客户「没有数据团队，每家的表都不一样」；把模板设为必需，等于要求新客户先有一份标准件，而这正是字典要解决的门槛 |
| D29 | **允许按已到齐的部门部分起草**，缺部门明确标为缺失，不替它生成声明 | 与 E14-UC01 D17、E13-UC02 D4 同一原则：说不知道比猜一个完整答案有用；并且四部门到齐才起草会让接入停在最慢的那个部门 |
| D30 | 发布写**新版本文件**并移动当前版本指针，绝不原地覆盖 | `store.py` 已有同一惯例（`versions/`）：已发布的东西不被悄悄改写。字典是批次冻结的对象，覆盖会让旧批次的指纹无从解释 |
| D31 | 与 #46/#102 列匹配向导的次序：**先起草声明，再用向导匹配上传列** | 向导的候选集必须来自「已声明字段」（CLAUDE.md「匹配不是创造」）；没有声明时向导无候选可给，所以起草在前 |
| D32 | 操作许可为 `dictionary_draft`（起草）与 `dictionary_publish`（发布，需审批），**只授予总表管理者** | 字典是跨部门的唯一事实来源，与 `convention_decide`（E13-UC05 D11）同理：按单部门授权会让一个部门替全表定义字段 |
| D33 | 首期起草**不含跨部门 relations**，只做单部门列声明、期间列、度量与汇总口径 | 「跨部门映射不靠字符串相似度」是硬约束，关系的证据门槛高于列声明（`SKU-A1` 与 `RM-Alu-6061` 实测相似度 35.3）；关系留给向导与人工 |

仍需业务方回答 / Still the business side's to answer：

1. 谁是字典草案的最终批准人——总经办管理者本人，还是另设复核角色？（影响 `dictionary_publish` 的授予范围）
2. 起草的计费运行由谁授权、按什么频率（每次接入一次，还是每版模板一次）？
3. 被拒绝条目的理由是否需要回流给上传部门，还是只在总经办内部留痕？

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
