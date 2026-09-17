# E10 — 原生工作室、笔记本与使用引导

# E10 — Native workspace, notebooks and onboarding

## 范围与角色 / Scope and actors

首次体验者、日常操作者、演示者 / New users, operators and presenters。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Official DSH shell and session identity + Client slots → Sources/chat/Studio. Notebook bookmarks use official storage-domain; layout preferences and tour progress have narrower browser scope.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E10-UC01 | 来源、聊天与工作室并行操作 / Use Sources, native chat and Studio together | IMPLEMENTED |
| E10-UC02 | 笔记本创建、保存与恢复 / Create, save and restore notebooks | IMPLEMENTED |
| E10-UC03 | 真实合成样例的无模型导入 / Import the retained synthetic case without model calls | IMPLEMENTED |
| E10-UC04 | 可恢复的页面操作导览 / Follow and resume the product tour | IMPLEMENTED |
| E10-UC05 | 双语、主题、窄屏与键盘操作 / Use bilingual, themed and accessible layouts | IMPLEMENTED |
| E10-UC06 | 错误恢复与图片能力说明 / Recover from UI errors and explain image support | IMPLEMENTED |

## E10-UC01 — 来源、聊天与工作室并行操作 / Use Sources, native chat and Studio together

**Status: IMPLEMENTED**

来源 / Sources: [#11](https://github.com/EricWang1358/BridgeFlow-AI/issues/11), [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40).

### 中文用例

- 参与者：月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：汇总负责人在同一页面上看来源、与 captain 对话、查看产物。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：在官方工作面切换来源预览、原生对话与业务产物，按笔记本用途展示功能。
- 异常、验收和边界：不替换原生输入框或另建聊天存储；配置预览与真实产物分开。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: the consolidation lead works with sources, chat and artifacts on one page.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Use the official workspace to navigate sources, native conversation and artifacts according to notebook purpose.
- Exceptions, acceptance and boundary: Do not replace the native composer or build another chat store; distinguish configuration previews from actual artifacts.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/shell.tsx)；[行为测试 / Behavioral tests](../../plugins/tests/notebook-capabilities.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E10-UC02 — 笔记本创建、保存与恢复 / Create, save and restore notebooks

**Status: IMPLEMENTED**

来源 / Sources: [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40).

### 中文用例

- 参与者：月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：工作需要分多次完成，离开后要回到原处。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：创建原生会话，编辑名称用途与来源，等待标题和书签落盘后确认保存，重开恢复。
- 异常、验收和边界：未保存切换提供保存/放弃/取消；写失败保留输入；不能冒充已保存。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: work spans sessions and must resume where it stopped.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Create native sessions, edit title/purpose/sources, await persisted titles/bookmarks before acknowledging save and restore later.
- Exceptions, acceptance and boundary: Offer save/discard/cancel for dirty navigation; preserve input on failure and never falsely acknowledge saving.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/notebooks.ts)；[行为测试 / Behavioral tests](../../plugins/tests/notebooks.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E10-UC03 — 真实合成样例的无模型导入 / Import the retained synthetic case without model calls

**Status: IMPLEMENTED**

来源 / Sources: [#41](https://github.com/EricWang1358/BridgeFlow-AI/issues/41), [#141](https://github.com/EricWang1358/BridgeFlow-AI/issues/141).

### 中文用例

- 参与者：月度汇总负责人（A03）、管理层决策者（A04）；写入操作按工具声明取得审批。
- 触发：第一次试用或演示，还没有自己的数据。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：导入仓库保留的 v2 模板案例及冻结字典，展示总表与原件，用户另行发起研判。
- 异常、验收和边界：不修改部署字典；合成样例不能算真实客户或独立留出验收。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Monthly consolidation lead (A03), Management decision-maker (A04); writes follow the tool-declared approval policy.
- Trigger: a first trial or demo happens before real data exists.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Import the retained v2 template case with its frozen dictionary, show master/sources and leave review as a separate user action.
- Exceptions, acceptance and boundary: Do not change the deployment dictionary; synthetic examples are neither customer acceptance nor independent held-out acceptance.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/api/batches.py)；[行为测试 / Behavioral tests](../../backend/tests/test_sample_notebook.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E10-UC04 — 可恢复的页面操作导览 / Follow and resume the product tour

**Status: IMPLEMENTED**

来源 / Sources: [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40), [#41](https://github.com/EricWang1358/BridgeFlow-AI/issues/41).

### 中文用例

- 参与者：部门填报员（A01）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：新用户第一次打开工作面，不知道从哪开始。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：欢迎、样例导入、总表、差异、出处、下载、命名和保存按实际事件推进，支持稍后与重播。
- 异常、验收和边界：不能伪造完成标记；刷新可恢复；关闭标签不保证继续；不自动审批或调用模型。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department contributor (A01), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: a new user opens the workspace for the first time.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Advance welcome/import/master/differences/sources/download/name/save steps from actual events, with defer and replay.
- Exceptions, acceptance and boundary: Reject forged completion; refresh can resume but tab closure need not; never auto-approve or invoke a model.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/tour/state.ts)；[行为测试 / Behavioral tests](../../plugins/tests/tour.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E10-UC05 — 双语、主题、窄屏与键盘操作 / Use bilingual, themed and accessible layouts

**Status: IMPLEMENTED**

来源 / Sources: [#110](https://github.com/EricWang1358/BridgeFlow-AI/issues/110), [#96](https://github.com/EricWang1358/BridgeFlow-AI/issues/96).

### 中文用例

- 参与者：部门填报员（A01）、管理层决策者（A04）；写入操作按工具声明取得审批。
- 触发：用户使用英文界面、深色主题、手机窄屏或只用键盘。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：切换中英文、深浅主题与窄屏面板，保留焦点、键盘动作和可读错误。
- 异常、验收和边界：现有历史浏览器证据见 docs/00；未声称每个新工具均有本轮视觉复验。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department contributor (A01), Management decision-maker (A04); writes follow the tool-declared approval policy.
- Trigger: a user needs English UI, dark theme, a narrow screen or keyboard-only use.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Switch Chinese/English, themes and narrow panels while preserving focus, keyboard actions and readable errors.
- Exceptions, acceptance and boundary: See docs/00 for historical browser evidence; this does not claim a fresh visual run for every new tool.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/ui.ts)；[行为测试 / Behavioral tests](../../plugins/tests/tour.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E10-UC06 — 错误恢复与图片能力说明 / Recover from UI errors and explain image support

**Status: IMPLEMENTED**

来源 / Sources: [#99](https://github.com/EricWang1358/BridgeFlow-AI/issues/99), [#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97), [#96](https://github.com/EricWang1358/BridgeFlow-AI/issues/96).

### 中文用例

- 参与者：部门填报员（A01）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：页面加载失败，或用户粘贴了系统不支持的图片。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：审批详情加载失败可重试；无效来源/会话链接报错；图片不支持时说明可用路径。
- 异常、验收和边界：错误不显示空成功；图片入口说明不等于 OCR 或多模态提取已实现。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department contributor (A01), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: a page fails to load or an unsupported image is pasted.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Retry failed approval detail loads, show errors for invalid source/session links and explain supported paths when images cannot be handled.
- Exceptions, acceptance and boundary: Errors cannot appear as empty success; image guidance is not delivered OCR or multimodal extraction.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/client/approval.tsx)；[行为测试 / Behavioral tests](../../plugins/tests/runtime.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
