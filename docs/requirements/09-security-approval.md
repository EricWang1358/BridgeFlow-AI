# E09 — 身份、授权、审批与安全边界

# E09 — Identity, authorization, approval and safety

## 范围与角色 / Scope and actors

操作者、审批人、部署管理员 / Operators, approvers and deployment administrators。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Browser identity via portal JWT/JWKS is distinct from shared host authentication and one-use approval receipts. Tool declarations drive write policy; monotonic guards reject unsafe execution.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E09-UC01 | 原生审批与一次性回执 / Require native approval and one-use receipts | IMPLEMENTED |
| E09-UC02 | 拒绝理由与结果一致 / Carry refusal reasons into tool outcomes | IMPLEMENTED |
| E09-UC03 | 工具护栏与数据上下文边界 / Enforce tool guards and context boundaries | IMPLEMENTED |
| E09-UC04 | 飞书登录与应用令牌 / Authenticate through Feishu and application tokens | PARTIAL |
| E09-UC05 | 浏览器批次部门可见性 / Enforce departmental batch visibility | PARTIAL |
| E09-UC06 | 审批操作角色与个人审计 / Authorize approver roles and individual audit | PARTIAL |

## E09-UC01 — 原生审批与一次性回执 / Require native approval and one-use receipts

**Status: IMPLEMENTED**

来源 / Sources: [#30](https://github.com/EricWang1358/BridgeFlow-AI/issues/30), [#39](https://github.com/EricWang1358/BridgeFlow-AI/issues/39), [#84](https://github.com/EricWang1358/BridgeFlow-AI/issues/84).

### 中文用例

- 参与者：审批人（A06）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：代理要执行写入或跨边界操作。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：对工具声明的写操作展示请求，原生批准后签发绑定参数的单次回执并消费。
- 异常、验收和边界：拒绝/取消/无人应答均不写；重放或改参失败；不能从提示词绕过。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Approver (A06), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: an agent attempts a write or boundary-crossing action.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Display declared mutations and consume a one-use parameter-bound receipt only after native approval.
- Exceptions, acceptance and boundary: Rejection, cancellation and no answer cause no write; replay and parameter changes fail; prompts cannot bypass policy.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/security.py)；[行为测试 / Behavioral tests](../../backend/tests/test_approval_gate.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E09-UC02 — 拒绝理由与结果一致 / Carry refusal reasons into tool outcomes

**Status: IMPLEMENTED**

来源 / Sources: [#86](https://github.com/EricWang1358/BridgeFlow-AI/issues/86), [#87](https://github.com/EricWang1358/BridgeFlow-AI/issues/87), [#96](https://github.com/EricWang1358/BridgeFlow-AI/issues/96).

### 中文用例

- 参与者：审批人（A06）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：审批人拒绝了一次操作并给出理由。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：在审批卡录入理由并按会话/调用绑定，拒绝结果将未执行事实反馈给模型。
- 异常、验收和边界：拒绝写入不等于保存负映射；无回复不称作人工拒绝；备注不能串调用。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Approver (A06), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: an approver rejects an action with a reason.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Bind decision notes to session/call and relay the fact that the operation did not execute to the model.
- Exceptions, acceptance and boundary: Refusing a write differs from saving a negative mapping; no answer is not human rejection; notes cannot cross calls.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/approval/notes.ts)；[行为测试 / Behavioral tests](../../plugins/tests/runtime.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E09-UC03 — 工具护栏与数据上下文边界 / Enforce tool guards and context boundaries

**Status: IMPLEMENTED**

来源 / Sources: [#26](https://github.com/EricWang1358/BridgeFlow-AI/issues/26), [#37](https://github.com/EricWang1358/BridgeFlow-AI/issues/37), [#58](https://github.com/EricWang1358/BridgeFlow-AI/issues/58), [#69](https://github.com/EricWang1358/BridgeFlow-AI/issues/69).

### 中文用例

- 参与者：Captain 代理（S01）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：模型输入或工具参数中出现指令式文本或超界数据。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：限制工具册、禁 shell/editor，拒绝指令形状的非可信输入；模型仅取有界摘要。
- 异常、验收和边界：后来 allow 策略不能撤销拒绝；不能声称提示词防御足够或全面消除注入。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Captain agent (S01), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: instruction-shaped text or over-bounded data appears in model input or tool arguments.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Restrict tools, disable shells/editors and reject instruction-shaped untrusted input; models receive bounded summaries.
- Exceptions, acceptance and boundary: Later allow policies cannot undo denial; prompts alone are insufficient and no universal injection immunity is claimed.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../plugins/src/guards/untrusted-input.ts)；[行为测试 / Behavioral tests](../../plugins/tests/runtime.test.ts)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E09-UC04 — 飞书登录与应用令牌 / Authenticate through Feishu and application tokens

**Status: PARTIAL**

来源 / Sources: [#126](https://github.com/EricWang1358/BridgeFlow-AI/issues/126), [#21](https://github.com/EricWang1358/BridgeFlow-AI/issues/21).

### 中文用例

- 参与者：部门填报员（A01）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：员工通过飞书身份登录门户并打开应用。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：门户 OAuth 确认身份，按应用签 JWT，后端用 JWKS 校验；浏览器令牌失败有登录恢复。
- 异常、验收和边界：协议测试已存在；真实飞书租户未验收；门户认证不等于全 API 部门隔离。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department contributor (A01), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: an employee signs in through Feishu and opens the application.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Use portal OAuth, application-scoped JWTs and backend JWKS verification, with browser login recovery.
- Exceptions, acceptance and boundary: Protocol tests exist; real tenant acceptance is pending; portal authentication does not provide department isolation on every API.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../portal/src/portal_app/main.py)；[行为测试 / Behavioral tests](../../portal/tests/test_portal.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E09-UC05 — 浏览器批次部门可见性 / Enforce departmental batch visibility

**Status: PARTIAL**

来源 / Sources: [#126](https://github.com/EricWang1358/BridgeFlow-AI/issues/126).

### 中文用例

- 参与者：部门负责人（A02）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：员工只应看到本部门有权查看的批次。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：按人工访问配置限制上传和批次读取，不可见批次返回 404；未配置失败关闭。
- 异常、验收和边界：浏览器批次、总表/XLSX 与工作流目录/看板/草稿/信号现已按身份过滤。工具路径仍为共享主机权限，个人操作授权待补。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Department owner (A02), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: an employee must see only batches their department may view.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Use human access configuration to restrict uploads and batch reads; hidden batches return 404 and missing configuration fails closed.
- Exceptions, acceptance and boundary: Browser batches, master/XLSX and workflow catalogue/board/drafts/signals now enforce identity scope. Tools retain shared host authority; individual operation authorization remains open.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/access.py)；[行为测试 / Behavioral tests](../../backend/tests/test_identity.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E09-UC06 — 审批操作角色与个人审计 / Authorize approver roles and individual audit

**Status: PARTIAL**

来源 / Sources: [#21](https://github.com/EricWang1358/BridgeFlow-AI/issues/21), [#126](https://github.com/EricWang1358/BridgeFlow-AI/issues/126), [#124](https://github.com/EricWang1358/BridgeFlow-AI/issues/124).

### 中文用例

- 参与者：审批人（A06）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：需要限定谁能批准哪类操作，并留下个人审计记录。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：将批准动作绑定员工身份、角色权限和审计记录，分离查看、上传和批准权限。
- 异常、验收和边界：批准写入已绑定验签员工、明确操作权限和精确请求；拒绝审计及原生会话读取仍未实现员工隔离，不可把 confirmed_by 文本当身份认证。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Approver (A06), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: who may approve which action must be restricted and individually audited.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: bind approval to employee identity, operation roles and audit records, separating view/upload/approval permissions.
- Exceptions, acceptance and boundary: Approved mutations bind the verified employee, explicit operation grants and exact request. Refusal audit and native session reads still lack employee isolation; confirmed_by text is not authentication.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/security.py)；[行为测试 / Behavioral tests](../../backend/tests/test_approvals.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.

### 本轮实现边界 / Current implementation boundary

门户开启时，浏览器先为正在等待原生审批的调用申请员工许可。后端验证 JWT、`operations` 和对象/部门范围，许可只绑定该操作及精确请求内容，60 秒有效且只能消费一次。主机在原生批准后将许可加入签名回执；后端执行前再次核对权限，撤权即拒绝。许可不返回模型或浏览器。门户关闭时保留明确的共享会话本地模式。

With portal identity enabled, the browser requests authorization for an active native approval. The backend verifies JWT, explicit operation grants and object scope, issuing a one-use, 60-second permit bound to the operation and exact body. After native approval the host signs the permit into its receipt; execution rechecks current grants. Permits are not exposed to the browser or model. Portal-disabled local mode retains shared identity.

上传与报告备注分别要求 `batch_import`、`review_note`；报告备注保存验证过的作者。`employee_authorizations` 记录授权被消费，不能当作业务执行成功凭据。剩余：拒绝/取消的个人审计、原生会话与模型读取的员工隔离、管理员权限管理界面，以及真实门户企业联调。因此仍为 PARTIAL。

Uploads and report notes require `batch_import` and `review_note`; notes persist the verified author. The authorization ledger records consumption, not successful business execution. Remaining: personal refusal/cancellation audit, employee isolation of native sessions/model reads, administration UI and live enterprise integration. Status remains PARTIAL.

实现：[员工授权](../../backend/src/bridgeflow/write_authorization.py)、[原生审批](../../plugins/src/approval/gate.ts)。验证：[权限与回执测试](../../backend/tests/test_employee_approval.py)、[浏览器旅程](../../plugins/tests/web-smoke.mjs)；实际结果见 [实测状态](../00-status.md)。
