# EPIC 03：岗位上手、组织支持与持续改进

# EPIC 03: Role onboarding, organizational support and improvement

需求来源 / Sources: [#145](https://github.com/EricWang1358/BridgeFlow-AI/issues/145), [#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127).

基线 / Baseline: `4a38904`, reviewed 2026-09-16. [状态规则与实施计划 / Status rules and delivery plan](README.md).

## 目标与角色 / Goal and actors

岗位上手、组织支持与持续改进。角色：员工、业务负责人、支持角色、管理层 / Employees, business owners, support roles and management。

Deliver role onboarding, organizational support and improvement with explicit human decisions and verifiable evidence. Agent 2 owns both design (2A) and execution (2B); these are not additional agents.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E03-UC01 | 岗位指引与数据去向 / Role guidance and data destination | PARTIAL |
| E03-UC02 | 一线反馈与事实核验 / Frontline feedback and fact verification | DESIGNED |
| E03-UC03 | 障碍分类与支持建议 / Classify obstacles and propose support | PARTIAL |
| E03-UC04 | 资源协调与分阶段推广 / Resource coordination and staged rollout | DESIGNED |
| E03-UC05 | 复盘、效果验证与回流 / Review outcomes and route improvements | DESIGNED |

## E03-UC01 — 岗位指引与数据去向 / Role guidance and data destination

**Status: PARTIAL**

### 中文需求与验收

- 参与者：部门填报员（A01）、落地支持负责人（A08）；写入操作按工具声明取得审批。
- 触发：员工上岗或流程变更后，不知道数据该交到哪、下一步是什么。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：按声明阶段/角色展示入口、输入输出模板、完成凭据、数据目的地、看板和求助角色；未知支持信息明确缺失。
- 异常与验收：本地 sink 不称公司平台；角色名称不代表有查看权限；未声明岗位不编造指引。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：workflow/guidance.py + workflow_guidance 已实现只读岗位指引；真实联系人、专用页面和员工验收待补 / read-only role guidance implemented; real contacts, dedicated page and employee acceptance pending。

### English requirements and acceptance

- Actors: Department contributor (A01), Adoption support lead (A08); writes follow the tool-declared approval policy.
- Trigger: after onboarding or a process change a staff member does not know where data goes next.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: For a declared stage/role, explain entry, input/output templates, completion receipts, destination, board and support role; identify missing support configuration.
- Exceptions and acceptance: A local sink is not a company platform; a role label grants no access; undeclared roles receive no invented guidance.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: workflow/guidance.py + workflow_guidance 已实现只读岗位指引；真实联系人、专用页面和员工验收待补 / read-only role guidance implemented; real contacts, dedicated page and employee acceptance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E03-UC02 — 一线反馈与事实核验 / Frontline feedback and fact verification

**Status: DESIGNED**

### 中文需求与验收

- 参与者：部门填报员（A01）、落地支持负责人（A08）；写入操作按工具声明取得审批。
- 触发：一线员工遇到问题，需要提交反馈并核实事实。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：记录反馈来源、关联项目/阶段/版本、观察事实、影响、原因假设和待核验项；先检查回执与权限。
- 异常与验收：不从延迟推断态度；不采集私人通信；无法复现保持待核验而非已解决。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：待实现；adoption.assess 只有事件信号 / pending; assess only provides event signals。

### English requirements and acceptance

- Actors: Department contributor (A01), Adoption support lead (A08); writes follow the tool-declared approval policy.
- Trigger: a frontline employee hits a problem and files feedback that must be verified.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Record the feedback source, project/stage/version, observation, impact, causal hypotheses and unknowns; inspect receipts and access first.
- Exceptions and acceptance: Do not infer attitude from delay or ingest private messages; unreproduced problems remain unverified, not resolved.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 待实现；adoption.assess 只有事件信号 / pending; assess only provides event signals.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E03-UC03 — 障碍分类与支持建议 / Classify obstacles and propose support

**Status: PARTIAL**

### 中文需求与验收

- 参与者：落地支持负责人（A08）；写入操作按工具声明取得审批。
- 触发：反馈累积，需要区分技术、模板、权限与培训问题并给出支持建议。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：区分技术、权限、模板、交互、流程、资源；每项建议列证据、建议动作、确认角色及验证方式。
- 异常与验收：故障不能用培训掩盖；管理层目标和一线证据都保留；不生成人员排名。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：adoption.py 事件分类；反馈与建议治理待实现 / event classification exists; feedback and proposal governance pending。

### English requirements and acceptance

- Actors: Adoption support lead (A08); writes follow the tool-declared approval policy.
- Trigger: feedback accumulates and must be classified into technical, template, permission or training issues.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Separate technical, access, template, interaction, process and resource issues; attach evidence, proposed action, decision role and verification method.
- Exceptions and acceptance: Training cannot conceal failures; retain management goals and frontline evidence; never rank employees.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: adoption.py 事件分类；反馈与建议治理待实现 / event classification exists; feedback and proposal governance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E03-UC04 — 资源协调与分阶段推广 / Resource coordination and staged rollout

**Status: DESIGNED**

### 中文需求与验收

- 参与者：落地支持负责人（A08）、管理层决策者（A04）；写入操作按工具声明取得审批。
- 触发：推广需要人手、预算或分阶段计划，须由管理层决定。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：提出支持时间、岗位材料、试点范围、检查点和停止条件；公司确认负责人、预算与排期。
- 异常与验收：建议不自动派人、不更权限、不发送管理指令；没有确认保留草案。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：待实现 / pending。

### English requirements and acceptance

- Actors: Adoption support lead (A08), Management decision-maker (A04); writes follow the tool-declared approval policy.
- Trigger: rollout needs people, budget or staging that management must decide.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Propose support time, role materials, pilot scope, checkpoints and stop conditions; the company decides owners, budget and schedule.
- Exceptions and acceptance: Proposals do not assign people, change permissions or send management instructions; unconfirmed plans remain drafts.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 待实现 / pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E03-UC05 — 复盘、效果验证与回流 / Review outcomes and route improvements

**Status: DESIGNED**

### 中文需求与验收

- 参与者：落地支持负责人（A08）、管理层决策者（A04）；写入操作按工具声明取得审批。
- 触发：措施执行一段时间后，需要复盘效果并把改动送回 Agent 1/2。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：记录措施、实施证据、基线/后测窗口与效果；范围/价值回 Agent 1，流程/模板/执行回 Agent 2，技术故障关联运维。
- 异常与验收：关闭需验证证据；建议不能覆盖已批准目录；缺基线显示不可比较；不自动定时跟踪。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：待实现；关联 #135 而非替代 / pending; links to rather than replaces #135。

### English requirements and acceptance

- Actors: Adoption support lead (A08), Management decision-maker (A04); writes follow the tool-declared approval policy.
- Trigger: measures have run for a while and outcomes must be reviewed and routed back to Agents 1/2.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Record actions, execution evidence, baseline/follow-up windows and outcomes; route scope/value to Agent 1, workflow/template/execution to Agent 2 and technical failures to operations.
- Exceptions and acceptance: Closure requires verification; proposals never overwrite approved catalogues; missing baselines mean not comparable; no implicit scheduled tracking.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 待实现；关联 #135 而非替代 / pending; links to rather than replaces #135.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## 设计与交互契约 / Design and interaction contract

继续使用 DSH 原生聊天、工具、审批和 Client slot；Python 负责校验、状态、计算与持久化。代理不能绕过工具调用底层 shell。复用 `backend/src/bridgeflow/workflow/`，不新增自建编排框架。设计中的新对象应包含 `id/project_id/version/status/source_refs/created_at`；写入使用 `expected_seq`，审批绑定实际请求，冲突返回可恢复的错误。

Use DSH native chat, tools, approval and Client slots. Python owns validation, state, arithmetic and persistence. Reuse the workflow domain; do not introduce another orchestration framework. Proposed new objects carry identity, project, version, status, source references and timestamp. Use optimistic sequence checks and exact-request approval for writes.

浏览器在工作室展示完整的授权视图，模型工具仅提供有界摘要和引用。工具输出在大数据量下必须有上限、真实总数和截断标记；业务原始行不进入代理上下文。错误须区分未配置、未找到、无权限、输入非法、版本冲突和外部失败。新增能力的读取范围不能假称已经实现部门级授权。

The Studio displays authorized human-facing views; model tools return bounded summaries and references. Large datasets require limits, real totals and truncation indicators; raw business rows stay outside agent context. Distinguish unconfigured, missing, forbidden, invalid input, version conflict and external failure. Do not claim department-level authorization for a new surface without enforcement.

## 发布与状态维护 / Release and status maintenance

每实现一个 UC，先运行针对性行为测试，再同时更新本文件索引与 UC 正文状态、实现路径及未覆盖部分。`IMPLEMENTED_OFFLINE` 只表示本地确定性契约通过；不意味着真实模型、真实员工或真实公司 API 验收。测量和命令统一记录到 [docs/00](../00-status.md)。

For each delivered UC, run focused behavioral checks and update both its index and detailed status, implementation links and remaining gaps. `IMPLEMENTED_OFFLINE` means local deterministic contracts passed, not acceptance by a live model, employee or company API. Record measured results and commands in [docs/00](../00-status.md).

## Epic 数据、接口与交互设计 / Epic data, API and interaction design

本轮只读 `workflow_guidance`（`POST /tools/workflow-guidance`）接收一个已声明 stage ID，返回目录版本、角色、输入/输出模板版本、步骤、目的地、成功凭据、看板入口及支持角色。模板列表封顶并带总数、截断标记。未知 stage 返回 404；读指引不受 workflow 写入开关影响，也不创建业务事件。当前中英说明同时返回；单语言排版与岗位专用图形页仍待实现。

The read-only `workflow_guidance` tool accepts a declared stage ID and returns catalogue version, role, input/output template versions, steps, destination, receipt criteria, board entry and support role. Template lists are bounded with totals and truncation flags. Unknown stages return 404. Guidance remains available with workflow writes disabled and creates no business events. Instructions currently contain both languages; locale-specific presentation and a dedicated role page remain work.

反馈与复盘的待实现对象：

| Object | Fields | Rules |
| --- | --- | --- |
| Feedback | id, project, stage, template_version, source_ref, observation, impact, hypotheses | 事实和假设分栏；来源必填 / separate facts from hypotheses; require source |
| ImprovementItem | feedback_ids, category, proposal, decision_role, route_to, status, expected_seq | proposed → approved → applied → verified；另有 rejected；批准不等于实施 / approval is not execution |
| Review | improvement_id, baseline_window, followup_window, denominator, observations, evidence, outcome | 无基线则不可比较；关闭需实测 / missing baseline means not comparable; closure requires evidence |

建议路由：范围/价值 → Agent 1；流程/模板/交互/执行 → Agent 2；实际技术失败 → #135 运维；权限/预算/职责 → 有权人员。运行日志原有 returned_work 指向 Agent 1 的历史规则需后续细分，不能假称所有回流已按新产品分工完成。

Proposed routing: scope/value to Agent 1; workflow/template/interaction/execution to Agent 2; technical failures to #135 operations; access/budget/responsibility to authorized people. The existing event rule routing returned_work to Agent 1 still needs refinement; it does not implement the full revised product routing.
