# EPIC 02：流程标准化、试点与业务流转

# EPIC 02: Workflow standardization, pilot and execution

需求来源 / Sources: [#144](https://github.com/EricWang1358/BridgeFlow-AI/issues/144), [#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127).

基线 / Baseline: `4a38904`, reviewed 2026-09-16. [状态规则与实施计划 / Status rules and delivery plan](README.md).

## 目标与角色 / Goal and actors

流程标准化、试点与业务流转。角色：模板负责人、一线填写者、复核者、下游接收者 / Template owners, frontline contributors, reviewers and downstream recipients。

Deliver workflow standardization, pilot and execution with explicit human decisions and verifiable evidence. Agent 2 owns both design (2A) and execution (2B); these are not additional agents.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E02-UC01 | 2A 详细流程与字段血缘 / 2A detailed workflow and field lineage | PARTIAL |
| E02-UC02 | 2A 模板试点、修订及发布 / 2A pilot, revise and release templates | PARTIAL |
| E02-UC03 | 2B 提取与多格式来源 / 2B extract heterogeneous inputs | PARTIAL |
| E02-UC04 | 2B 补问、校验与批准 / 2B clarify, validate and approve | PARTIAL |
| E02-UC05 | 2B API 入库与恢复 / 2B API submission and recovery | PARTIAL |
| E02-UC06 | 2B 就绪、通知与看板 / 2B readiness, notification and board | PARTIAL |
| E02-UC07 | 2B 下游开始、退回与完成 / 2B start, return and complete downstream work | IMPLEMENTED_OFFLINE |
| E02-UC08 | 2B 修订确认与影响控制 / 2B acknowledge revisions and control impact | IMPLEMENTED_OFFLINE |
| E02-UC09 | 试点度量与独立样例 / Pilot measurement and independent samples | BLOCKED_EXTERNAL |
| E02-UC10 | 飞书文件快捷调用 / Feishu file shortcuts | BLOCKED_EXTERNAL |

## E02-UC01 — 2A 详细流程与字段血缘 / 2A detailed workflow and field lineage

**Status: PARTIAL**

### 中文需求与验收

- 参与者：字典与标准维护人（A05）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：MVP 已批准，需要把选定流程细化为阶段、模板和字段血缘。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：承接已批准 MVP，逐阶段定义输入输出、键、期间、单位、公式及双向血缘，列出未确认项。
- 异常与验收：不得按第一列拼接；生产量、出厂量、实际量与产值、结算、收款分别保留。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：catalogue.py；GET /workflow/lineage/{template}/{field}；目录声明两跳（生产→市场→财务）；新记录只在已接收且仍有效的立项批准范围下进入（workflow/scope.py）/ two declared hops; new records only under an accepted, still-current MVP scope。

### English requirements and acceptance

- Actors: Dictionary and standards steward (A05), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: an approved MVP must be detailed into stages, templates and field lineage.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Starting with an approved MVP, define stage inputs, outputs, keys, periods, units, formulas and bidirectional lineage, including unresolved items.
- Exceptions and acceptance: Never join on the first column; preserve distinct production, shipment, actual quantity, output value, settlement and payment concepts.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: catalogue.py；GET /workflow/lineage/{template}/{field}；目录声明两跳（生产→市场→财务）；新记录只在已接收且仍有效的立项批准范围下进入（workflow/scope.py）/ two declared hops; new records only under an accepted, still-current MVP scope.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC02 — 2A 模板试点、修订及发布 / 2A pilot, revise and release templates

**Status: PARTIAL**

### 中文需求与验收

- 参与者：字典与标准维护人（A05）、部门填报员（A01）；写入操作按工具声明取得审批。
- 触发：模板草案需要在一线试用后修订并发布版本。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：邀请涉及部门实际填写者和下游验证字段可获得性、重复劳动、例外及输出可用性；记录反馈并批准新版本。
- 异常与验收：draft/proposed 不能收正式数据；单次记录批准不等于模板发布；旧版本保持可追溯。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：catalogue.runnable 已阻断未批准模板；试点治理待实现 / gate exists; pilot governance pending。

### English requirements and acceptance

- Actors: Dictionary and standards steward (A05), Department contributor (A01); writes follow the tool-declared approval policy.
- Trigger: draft templates need a frontline pilot before a version is released.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Have actual contributors and downstream users validate field availability, duplication, exceptions and output usability; record feedback and approve a new version.
- Exceptions and acceptance: Draft/proposed templates cannot accept operational data; approving a record does not release a template; preserve historical versions.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: catalogue.runnable 已阻断未批准模板；试点治理待实现 / gate exists; pilot governance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC03 — 2B 提取与多格式来源 / 2B extract heterogeneous inputs

**Status: PARTIAL**

### 中文需求与验收

- 参与者：部门填报员（A01）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：员工手里是非标准原件（表格、文字、图片），需要落到批准模板。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：受控解析器在主机侧读表格、文字或获准 OCR，返回候选与页码/单元格/区域引用；员工核对模糊项。
- 异常与验收：原始业务行不进代理上下文；不清晰图像不视作事实；未配置解析器明确拒绝。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：materials.py、intake.py；OCR 与通用提取待实现 / OCR and generic extraction pending。

### English requirements and acceptance

- Actors: Department contributor (A01), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: a staff member holds non-standard originals that must land on an approved template.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Host-side parsers read spreadsheets, text or approved OCR and return candidates with page/cell/region references; people verify ambiguity.
- Exceptions and acceptance: Raw business rows stay out of agent context; unclear images are not facts; unconfigured parsers refuse explicitly.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: materials.py、intake.py；OCR 与通用提取待实现 / OCR and generic extraction pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC04 — 2B 补问、校验与批准 / 2B clarify, validate and approve

**Status: PARTIAL**

### 中文需求与验收

- 参与者：部门填报员（A01）、审批人（A06）；写入操作按工具声明取得审批。
- 触发：抽取结果有缺项、冲突或需要确认的值。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：按批准字段匹配、规则转换和确定性计算；缺失/冲突提出聚焦问题；新信息重算；展示 digest 对应值审批。
- 异常与验收：不填零、不猜日期；变更使旧审批失效；拒绝/取消/不可用均不提交。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：intake.py、normalise.py、workflow_tools.py；真实连续对话待验收 / live conversation acceptance pending。

### English requirements and acceptance

- Actors: Department contributor (A01), Approver (A06); writes follow the tool-declared approval policy.
- Trigger: an extracted record has missing, conflicting or unconfirmed values.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Match approved fields, normalize declared formats and compute deterministically; ask focused questions for gaps/conflicts, recompute changes and approve the displayed digest.
- Exceptions and acceptance: Never fill missing values with zero or guess dates; changes invalidate approval; rejection, cancellation and unavailable approval do not submit.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: intake.py、normalise.py、workflow_tools.py；真实连续对话待验收 / live conversation acceptance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC05 — 2B API 入库与恢复 / 2B API submission and recovery

**Status: PARTIAL**

### 中文需求与验收

- 参与者：Captain 代理（S01）、外部系统（飞书、目标 API）（S03）；写入操作按工具声明取得审批。
- 触发：标准记录经批准，需要写入目标系统。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：批准标准草稿后提交指定目标，保存可核实回执、产物版本、幂等键；失败保留草稿并重试。
- 异常与验收：未知目标不假报成功；同请求不重复写入；同 ID 不同内容冲突；分项失败单独报告。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：service.py、ports.py 本地实现；真实目标待指定 / local implementation; real target not selected。

### English requirements and acceptance

- Actors: Captain agent (S01), External system (Feishu, target API) (S03); writes follow the tool-declared approval policy.
- Trigger: an approved standard record must be written to the target system.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Submit an approved draft to the configured target and retain verifiable receipts, artifact versions and idempotency keys; preserve failed drafts for retry.
- Exceptions and acceptance: Unknown targets cannot report success; retries do not duplicate writes; conflicting content for the same ID is refused; report item failures separately.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: service.py、ports.py 本地实现；真实目标待指定 / local implementation; real target not selected.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC06 — 2B 就绪、通知与看板 / 2B readiness, notification and board

**Status: PARTIAL**

### 中文需求与验收

- 参与者：部门负责人（A02）、外部系统（飞书、目标 API）（S03）；写入操作按工具声明取得审批。
- 触发：数据已就绪，需要通知下一个部门并在看板上可见。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：所有必要输入就绪后为每个下游创建交接；数据状态、通知状态、业务状态分列；通知可独立重试。
- 异常与验收：消息送达不等于已读或完成；缺收件路由不猜人；失败不回滚已成功数据。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：board.py、store.py 本地 outbox；交接按环节声明的 sla_hours 给出到期时间与超时时长，每条记录可读时间线（GET /workflow/history，不含字段值）；总览页汇总各环节与超时数 / handoffs carry a due time from the stage's sla_hours and an overdue count, each record has a value-free timeline, the overview page totals stages and overdue items；真实通知未接通 / real notification pending。

### English requirements and acceptance

- Actors: Department owner (A02), External system (Feishu, target API) (S03); writes follow the tool-declared approval policy.
- Trigger: ready data must notify the next department and appear on the board.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Create each downstream handoff only when every required input is ready; separate data, notification and work states; retry notification independently.
- Exceptions and acceptance: Delivery does not imply reading or completion; missing routes never trigger guessed recipients; delivery failure does not undo ready data.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: board.py、store.py 本地 outbox；交接按环节声明的 sla_hours 给出到期时间与超时时长，每条记录可读时间线（GET /workflow/history，不含字段值）；总览页汇总各环节与超时数 / handoffs carry a due time from the stage's sla_hours and an overdue count, each record has a value-free timeline, the overview page totals stages and overdue items；真实通知未接通 / real notification pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC07 — 2B 下游开始、退回与完成 / 2B start, return and complete downstream work

**Status: IMPLEMENTED_OFFLINE**

### 中文需求与验收

- 参与者：部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：下游部门收到交接，需要开始、退回或完成。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：读取交接 ID、seq、输入版本，审批具体操作后执行 start/return/complete；退回必须说明可操作原因。
- 异常与验收：过期 seq、无审批、非法迁移不写事件；waiting 不能直接完成；看板可取得执行所需 seq。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：service.act + workflow_handoff 原生审批工具 / native approval tool。

### English requirements and acceptance

- Actors: Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: a downstream department receives a handoff to start, return or complete.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Read handoff ID, sequence and input versions, approve a specific start/return/complete action and execute it; return requires an actionable reason.
- Exceptions and acceptance: Stale sequences, absent approval and invalid transitions append no events; waiting cannot complete directly; the board exposes the sequence needed for action.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: service.act + workflow_handoff 原生审批工具 / native approval tool.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


实现证据 / Implementation evidence: `workflow/service.py`, `api/workflow_tools.py`, `plugins/src/tools/workflow.ts`; `test_workflow_foundation.py`, `test_workflow_tools.py`, `plugins/tests/runtime.test.ts`. 原生工具与离线契约已实现；浏览器真实对话及业务签核未验证 / native tool and offline contracts implemented; live browser conversation and business acceptance unverified.

## E02-UC08 — 2B 修订确认与影响控制 / 2B acknowledge revisions and control impact

**Status: IMPLEMENTED_OFFLINE**

### 中文需求与验收

- 参与者：部门负责人（A02）、部门填报员（A01）；写入操作按工具声明取得审批。
- 触发：上游修订了已交接的记录，下游需要确认影响。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：上游修改后交接 stale；新版本重新就绪后，下游明确确认输入版本，再开始或完成工作。
- 异常与验收：上游尚未重新就绪不能清除 stale；未确认修订不能开始/完成；批准绑定当前 seq。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：stale 标记、就绪检查和审批工具已接入 / stale marking, readiness checks and approval tool implemented。

### English requirements and acceptance

- Actors: Department owner (A02), Department contributor (A01); writes follow the tool-declared approval policy.
- Trigger: an upstream revision affects a record already handed off.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Upstream revisions mark the handoff stale; after the revised version becomes ready, downstream explicitly acknowledges its inputs before starting or completing.
- Exceptions and acceptance: Do not clear stale while upstream is not ready; do not start/complete before acknowledging revisions; bind approval to the current sequence.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: stale 标记、就绪检查和审批工具已接入 / stale marking, readiness checks and approval tool implemented.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


实现证据 / Implementation evidence: `workflow/service.py`, `api/workflow_tools.py`, `plugins/src/tools/workflow.ts`; `test_workflow_foundation.py`, `test_workflow_tools.py`, `plugins/tests/runtime.test.ts`. 原生工具与离线契约已实现；浏览器真实对话及业务签核未验证 / native tool and offline contracts implemented; live browser conversation and business acceptance unverified.

## E02-UC09 — 试点度量与独立样例 / Pilot measurement and independent samples

**Status: BLOCKED_EXTERNAL**

### 中文需求与验收

- 参与者：独立评测人（A09）、字典与标准维护人（A05）；写入操作按工具声明取得审批。
- 触发：试点结束，需要用独立样例衡量正确性与人工负担。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：记录关键字段正确性、补问轮次、人工修正、耗时、下游可用性；业务方提供两组调优、一组独立留出及人工标准。
- 异常与验收：说明分母、时间窗、基线和版本；开发不读留出答案；合成数据不得标为客户验收。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：#141；事件含补问轮次；真实样例和指标契约待提供 / events track question rounds; real samples and metric contracts pending。

### English requirements and acceptance

- Actors: Independent evaluator (A09), Dictionary and standards steward (A05); writes follow the tool-declared approval policy.
- Trigger: a pilot ends and correctness and human effort must be measured on independent samples.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Measure key-field accuracy, clarification rounds, manual corrections, duration and downstream usability; obtain two tuning sets and one independently held-out set with human standards.
- Exceptions and acceptance: Declare denominators, windows, baselines and versions; developers do not inspect held-out answers; synthetic fixtures never count as customer acceptance.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: #141；事件含补问轮次；真实样例和指标契约待提供 / events track question rounds; real samples and metric contracts pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E02-UC10 — 飞书文件快捷调用 / Feishu file shortcuts

**Status: BLOCKED_EXTERNAL**

### 中文需求与验收

- 参与者：部门填报员（A01）、外部系统（飞书、目标 API）（S03）；写入操作按工具声明取得审批。
- 触发：部门文件放在飞书云文档里，需要直接取用或传回结果。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：通过已有审批工具下载指定文件导入，上传产出到指定文件夹并验证链接。
- 异常与验收：缺凭据明确未配置；文件内容不进上下文；不能当作通知或通用数据库接口。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：#140；feishu.py、test_feishu.py、scripts/feishu_live_check.py；真实租户待验收 / real tenant acceptance pending。

### English requirements and acceptance

- Actors: Department contributor (A01), External system (Feishu, target API) (S03); writes follow the tool-declared approval policy.
- Trigger: department files live in Feishu Drive and must be fetched or results sent back.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Use existing approval tools to download and import a specified file, upload an output to a selected folder and verify access.
- Exceptions and acceptance: Missing credentials report unconfigured; file contents stay out of context; this does not implement notification or a generic database API.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: #140；feishu.py、test_feishu.py、scripts/feishu_live_check.py；真实租户待验收 / real tenant acceptance pending.

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

## 本轮工具与迁移契约 / Tool and transition contracts delivered here

| Tool / endpoint | 输入 / Input | 输出与拒绝 / Output and refusal |
| --- | --- | --- |
| workflow_board / POST /tools/workflow-board | 无 / none | 最多 30 行、total/truncated；有 ID 的行含 seq；交接含 inputs/stale/notification / bounded rows with sequence and handoff context |
| workflow_handoff / POST /tools/workflow-handoff | handoff_id, action, expected_seq, reason | 当前交接快照；403 无审批或写开关关闭；404 未找到；409 过期或非法迁移；422 参数错误 / snapshot or explicit refusal |

审批请求与执行请求共用 `handoffBody`；请求含操作、版本和退回原因，修改任何一项都不能复用批准。前端复用原生审批卡，不直接从浏览器调用写入 API。已有 `/workflow/handoffs/...` 是仅供可信主机使用的领域端口，不能公开为员工直连 API。

Approval and execution share `handoffBody`; changes to action, version or return reason invalidate the approval. The client reuses native approval cards. Existing `/workflow/handoffs/...` endpoints are trusted-host domain ports, not employee-facing public mutation APIs.

| Current state | Action | Result / 条件 |
| --- | --- | --- |
| waiting | start | in_progress；不能 stale / must not be stale |
| waiting / in_progress | return | returned；非空原因 / nonempty reason |
| in_progress | complete | completed；不能 stale / must not be stale |
| any opened handoff with stale=true | acknowledge | 所有当前输入版本 data_ready 后清除 stale / clear only after all current input versions are ready |

修订确认本身不是重新完成业务；已完成的历史交接仍保留完成状态并显示修订标记。这一实现不自动创建额外返工任务；若业务要求重新验收，需在批准流程设计中明确。

Acknowledgment does not re-perform business work. A historical completed handoff keeps its state while revisions are marked. This implementation does not automatically create rework tasks; any required re-acceptance must be declared in the approved process.
