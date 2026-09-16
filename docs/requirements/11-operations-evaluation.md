# E11 — 运行维护、评测与交付

# E11 — Operations, evaluation and delivery

## 范围与角色 / Scope and actors

开发、部署负责人、评测人 / Developers, deployment owners and evaluators。本文件追溯既有需求，不表示本轮新增这些实现。基线：`main@4a38904`，2026-09-16 代码与测试盘点。

This file traces existing requirements; it does not claim these features were newly built this turn. Baseline: `main@4a38904`, code/test audit on 2026-09-16.

[全项目索引与状态定义 / Project index and status definitions](README.md) · [历史验收记录 / Historical verification](../00-status.md).

## 设计 / Design

Pinned official runtime + launcher/preflight + offline CI and isolated model evaluations. Domain recovery is implemented; autonomous enterprise operations is a separate deferred scope.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E11-UC01 | 启动预检与官方运行时修复 / Preflight and launch the pinned runtime | IMPLEMENTED |
| E11-UC02 | 会话保留与日志兼容修复 / Retain sessions and repair known metadata safely | IMPLEMENTED |
| E11-UC03 | 离线与对抗评测及用量证据 / Run offline and adversarial evaluations | IMPLEMENTED |
| E11-UC04 | CI、部署预检与生产联调 / Validate CI and production deployment | PARTIAL |
| E11-UC05 | 自动巡检、自愈与升级 / Autonomous inspection, recovery and escalation | DEFERRED |

## E11-UC01 — 启动预检与官方运行时修复 / Preflight and launch the pinned runtime

**Status: IMPLEMENTED**

来源 / Sources: [#9](https://github.com/EricWang1358/BridgeFlow-AI/issues/9), [#42](https://github.com/EricWang1358/BridgeFlow-AI/issues/42), [#55](https://github.com/EricWang1358/BridgeFlow-AI/issues/55), [#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97).

### 中文用例

- 参与者：平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：部署或本机启动服务。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：验证官方运行时和插件环境，启动私有后端及原生 Web，修复已知模块定位问题。
- 异常、验收和边界：不 fork DSH；预检失败给原因；不将测试替身称真实模型运行。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: the service is started locally or on a server.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Validate runtime/plugin setup, start the private backend and native Web, and recover known module-resolution failures.
- Exceptions, acceptance and boundary: Do not fork DSH; expose preflight failures; test fixtures are not live model runs.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../scripts/start_web.py)；[行为测试 / Behavioral tests](../../backend/tests/test_start_web.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E11-UC02 — 会话保留与日志兼容修复 / Retain sessions and repair known metadata safely

**Status: IMPLEMENTED**

来源 / Sources: [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40), [#113](https://github.com/EricWang1358/BridgeFlow-AI/issues/113).

### 中文用例

- 参与者：平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：升级后旧会话打不开，或会话需要长期保留。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：检查会话及已知历史元数据问题，显式应用时备份原始字节；按保留策略维护证据。
- 异常、验收和边界：不改未知必需事件或业务内容；修复需明确 apply；正常启动不静默删日志。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: old sessions fail to open after an upgrade or must be retained.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Inspect sessions and known historical metadata issues, back up bytes before explicit repair and retain evidence by policy.
- Exceptions, acceptance and boundary: Do not alter unknown required events/business content; repairs require explicit apply; normal startup does not silently delete logs.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../scripts/repair_session_metadata.py)；[行为测试 / Behavioral tests](../../backend/tests/test_session_metadata_repair.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E11-UC03 — 离线与对抗评测及用量证据 / Run offline and adversarial evaluations

**Status: IMPLEMENTED**

来源 / Sources: [#2](https://github.com/EricWang1358/BridgeFlow-AI/issues/2), [#28](https://github.com/EricWang1358/BridgeFlow-AI/issues/28), [#59](https://github.com/EricWang1358/BridgeFlow-AI/issues/59), [#67](https://github.com/EricWang1358/BridgeFlow-AI/issues/67), [#69](https://github.com/EricWang1358/BridgeFlow-AI/issues/69).

### 中文用例

- 参与者：独立评测人（A09）、平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：版本冻结或提交前需要证明质量与安全。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：用标准答案和攻击样例验证规则、引用与护栏，隔离 mock 与真实模型记录及用量。
- 异常、验收和边界：开发集不冒充留出；真实数据评测归 E02-UC09；本轮只盘点没有新付费调用。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Independent evaluator (A09), Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: a version freeze or submission requires evidence of quality and safety.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Evaluate rules, citations and guards against independent answers and attacks, distinguishing mock from live runs and usage.
- Exceptions, acceptance and boundary: Development fixtures are not held-out evidence; real-data evaluation belongs to E02-UC09; no new billed run occurred in this audit.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/eval/__init__.py)；[行为测试 / Behavioral tests](../../backend/tests/test_eval_suite.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E11-UC04 — CI、部署预检与生产联调 / Validate CI and production deployment

**Status: PARTIAL**

来源 / Sources: [#10](https://github.com/EricWang1358/BridgeFlow-AI/issues/10), [#138](https://github.com/EricWang1358/BridgeFlow-AI/issues/138).

### 中文用例

- 参与者：平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：代码合并到主干，需要自动检查并部署。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：通过离线检查、构建和部署预检，按已配置域名、SSH 及服务配置发布。
- 异常、验收和边界：脚本存在不等于真实生产已部署；#138 外部凭据/域名仍是独立验收。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: code merges to main and must be checked and deployed.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Use offline checks, builds and deployment preflight before deploying with configured domain, SSH and services.
- Exceptions, acceptance and boundary: Scripts do not prove production deployment; #138 credentials/domain remain separate acceptance requirements.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../deploy/preflight.sh)；[行为测试 / Behavioral tests](../../backend/tests/test_deploy_config.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.


## E11-UC05 — 自动巡检、自愈与升级 / Autonomous inspection, recovery and escalation

**Status: DEFERRED**

来源 / Sources: [#120](https://github.com/EricWang1358/BridgeFlow-AI/issues/120), [#132](https://github.com/EricWang1358/BridgeFlow-AI/issues/132), [#133](https://github.com/EricWang1358/BridgeFlow-AI/issues/133), [#134](https://github.com/EricWang1358/BridgeFlow-AI/issues/134), [#135](https://github.com/EricWang1358/BridgeFlow-AI/issues/135).

### 中文用例

- 参与者：平台运维管理员（A10）；写入操作按工具声明取得审批。
- 触发：生产环境出现异常，需要发现、处置与升级。
- 前置：选定正确批次/会话或配置版本；读取范围由实际端点授权，不从角色名称推定。未实现项的前置条件是目标设计，并非已有系统保证。
- 主流程：目标：按授权信号巡检，分级诊断、有限重试、审批有副作用动作，失败升级并留验证证据。
- 异常、验收和边界：已有事件信号与恢复机制不是完整定时运维 Agent；未发现通用巡检、资源监控、升级通知交付。
- 后置：成功时返回与本次输入、版本一致的结果；失败明确说明并保留可恢复输入，不伪造成功或替换历史结果。

### English use case

- Actors: Platform operator (A10); writes follow the tool-declared approval policy.
- Trigger: production misbehaves and must be detected, handled and escalated.
- Preconditions: identify the correct batch/session or configuration version; enforce access at the actual endpoint rather than infer it from a role label. Preconditions for unimplemented work are design goals, not existing guarantees.
- Main flow: Target: inspect authorized signals, diagnose by action level, retry within limits, approve side effects and escalate failures with verification.
- Exceptions, acceptance and boundary: Existing signals and recovery are not a scheduled operations agent; general inspection, resource monitoring and escalation delivery are unimplemented.
- Postcondition: success returns an input/version-consistent result; failures preserve recoverable inputs and explicitly report refusal rather than invent success or replace history.

### 实现与验证 / Implementation and verification

[代码或范围记录 / Code or scope record](../../backend/src/bridgeflow/workflow/adoption.py)；[行为测试 / Behavioral tests](../../backend/tests/test_workflow_foundation.py)。

验收应同时检查主流程和上列拒绝路径、引用及版本；不能仅凭 issue 关闭或 HTTP 200 标记完成。IMPLEMENTED 表示已找到现行实现和相关验证资产，不代表本轮重新跑过每条用户旅程，也不表示真实企业签核。

Validate the flow, refusal paths, citations and versions. Neither issue closure nor HTTP 200 proves completion. IMPLEMENTED identifies current implementation and relevant verification assets; it does not claim a fresh user-journey run or enterprise sign-off.
