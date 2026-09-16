# EPIC 01：立项发现与 MVP 决策

# EPIC 01: Discovery and MVP decisions

需求来源 / Sources: [#143](https://github.com/EricWang1358/BridgeFlow-AI/issues/143), [#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127).

基线 / Baseline: `4a38904`, reviewed 2026-09-16. [状态规则与实施计划 / Status rules and delivery plan](README.md).

## 目标与角色 / Goal and actors

立项发现与 MVP 决策。角色：业务负责人、部门代表、管理层 / Business owners, department representatives, management。

Deliver discovery and mvp decisions with explicit human decisions and verifiable evidence. Agent 2 owns both design (2A) and execution (2B); these are not additional agents.

## UC 索引 / UC index

| UC | 中文 / English | Status |
| --- | --- | --- |
| E01-UC01 | 材料分类与来源登记 / Classify materials and register provenance | PARTIAL |
| E01-UC02 | 有依据的候选场景卡 / Evidence-backed opportunity cards | PARTIAL |
| E01-UC03 | 信息流与文件流草图 / Information and document flow drafts | PARTIAL |
| E01-UC04 | 四象限与优先级 / Quadrants and prioritization | PARTIAL |
| E01-UC05 | 会议准备与实施路线草案 / Meeting preparation and implementation proposal | PARTIAL |
| E01-UC06 | MVP 决策、投票与修订 / MVP decision, voting and revision | PARTIAL |

## E01-UC01 — 材料分类与来源登记 / Classify materials and register provenance

**Status: PARTIAL**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、字典与标准维护人（A05）；写入操作按工具声明取得审批。
- 触发：项目启动时收到部门报表、说明或会议纪要，需要先弄清手里有哪些材料。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：上传表格、说明或会议材料；按文件版本、部门、期间登记，区分空模板、实际数据及规则陈述。
- 异常与验收：空模板只能产出结构描述；解析失败给出文件级原因，不生成业务记录。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：workflow/materials.py、discovery.py、material_uploads.py；持久清单、批准登记与授权读取已接；真实材料与扩展解析待验收 / inventory, approved registration and scoped reads implemented; real materials and extended parsing remain。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Dictionary and standards steward (A05); writes follow the tool-declared approval policy.
- Trigger: project kickoff brings department reports, notes or minutes that must be inventoried first.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Register uploaded spreadsheets, narratives and meeting materials by version, department and period; distinguish empty templates, records and rule statements.
- Exceptions and acceptance: An empty template produces structure only; parsing failures identify the file and never fabricate records.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: workflow/materials.py、discovery.py、material_uploads.py；持久清单、批准登记与授权读取已接；真实材料与扩展解析待验收 / inventory, approved registration and scoped reads implemented; real materials and extended parsing remain.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E01-UC02 — 有依据的候选场景卡 / Evidence-backed opportunity cards

**Status: PARTIAL**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：材料登记完成后，需要找出值得改进的跨部门工作场景。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：根据材料提出业务问题、涉及部门、输入、预期输出、人工节点、规则依赖和价值假设；每项关联来源。
- 异常与验收：同名字段不能证明交接；证据不足保留问题，不能自动批准候选。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：待实现 / pending。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: registered materials need to be turned into candidate cross-department work scenarios.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Propose a business problem, departments, inputs, outputs, human checkpoints, rule dependencies and value hypotheses with source references.
- Exceptions and acceptance: Matching field names do not prove a handoff; retain open questions and never auto-approve opportunities.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 待实现 / pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E01-UC03 — 信息流与文件流草图 / Information and document flow drafts

**Status: PARTIAL**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：业务方选定要深入的候选场景，需要看清信息与文件如何在部门间流转。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：先记录阶段触发、角色、输入输出与证据，再展示支持并行、分支和返工的图；文件边包含版本。
- 异常与验收：每条边区分 confirmed/inferred/missing/conflict；未知阶段不能按部门名称排序。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：discovery_graph.py 已提供版本化图领域，原生审批/授权 API 已接，浏览器图形和编辑已接，真实业务共创待验收 / graph API, approval, visualization and editing connected; real co-design acceptance pending。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: the business picks a candidate scenario and needs to see how information and files move between departments.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Record stage triggers, roles, inputs, outputs and evidence, then render parallel branches and rework; document edges include versions.
- Exceptions and acceptance: Each edge distinguishes confirmed/inferred/missing/conflict; department names never determine ordering.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: discovery_graph.py 已提供版本化图领域，原生审批/授权 API 已接，浏览器图形和编辑已接，真实业务共创待验收 / graph API, approval, visualization and editing connected; real co-design acceptance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E01-UC04 — 四象限与优先级 / Quadrants and prioritization

**Status: PARTIAL**

### 中文需求与验收

- 参与者：管理层决策者（A04）、月度汇总负责人（A03）；写入操作按工具声明取得审批。
- 触发：候选场景超过一个，管理层需要按落地难度与价值排序。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：以候选项目为本轮评分对象，记录 effort、value、评分人、量表版本及依据；坐标点击可追溯。
- 异常与验收：缺任一评分或依据不落点；量表、分界线和权重需业务确认；排序不是立项。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：关联 #125；声明评分领域、授权审批及四象限浏览器已接，真实量表/企业验收仍缺 / #125; declared scoring, scoped approval and quadrant browser implemented; real policy and enterprise acceptance pending。

### English requirements and acceptance

- Actors: Management decision-maker (A04), Monthly consolidation lead (A03); writes follow the tool-declared approval policy.
- Trigger: more than one candidate exists and management needs them ranked by effort and value.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Use candidate projects as the proposed scoring object; record effort, value, scorer, scale version and evidence; expose evidence for each point.
- Exceptions and acceptance: Missing scores or evidence prevent plotting; scales, boundaries and weights need business confirmation; ranking is not approval.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 关联 #125；声明评分领域、授权审批及四象限浏览器已接，真实量表/企业验收仍缺 / #125; declared scoring, scoped approval and quadrant browser implemented; real policy and enterprise acceptance pending.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E01-UC05 — 会议准备与实施路线草案 / Meeting preparation and implementation proposal

**Status: PARTIAL**

### 中文需求与验收

- 参与者：月度汇总负责人（A03）、Captain 代理（S01）；写入操作按工具声明取得审批。
- 触发：管理层初选了项目，需要组织相关部门开会确认。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：初选候选后生成范围、风险、资源依赖、阶段退出条件和待讨论问题；记录会议输入版本。
- 异常与验收：估算标记假设，不承诺未测节省时间；会议记录变化须保留来源。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：会议领域、授权 API、原生审批与编辑/详情页面已接；真实业务复核和未批准草稿恢复待补 / meeting domain, scoped API, native approval and editor/details connected; real business review and unsaved draft recovery remain。

### English requirements and acceptance

- Actors: Monthly consolidation lead (A03), Captain agent (S01); writes follow the tool-declared approval policy.
- Trigger: management shortlists projects and a cross-department meeting must be prepared.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Prepare scope, risks, resource dependencies, stage exit criteria and discussion questions against a frozen input version.
- Exceptions and acceptance: Label estimates as assumptions; do not promise unmeasured savings; retain sources for meeting changes.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 会议领域、授权 API、原生审批与编辑/详情页面已接；真实业务复核和未批准草稿恢复待补 / meeting domain, scoped API, native approval and editor/details connected; real business review and unsaved draft recovery remain.

### 验证设计 / Verification design

对主流程构造声明驱动的合成样例；对上述异常分别验证拒绝与无意外写入。检查版本、来源和状态，而不只检查 HTTP 200。真实业务验收另需业务方提供材料和签核。

Use declared synthetic fixtures for the main flow and independently exercise the exception cases above. Assert versions, provenance, state and absence of unintended writes, not just HTTP 200. Real business acceptance requires business-owned inputs and sign-off.


## E01-UC06 — MVP 决策、投票与修订 / MVP decision, voting and revision

**Status: PARTIAL**

### 中文需求与验收

- 参与者：管理层决策者（A04）、部门负责人（A02）；写入操作按工具声明取得审批。
- 触发：会议结束，需要记录共识、投票并确认 MVP 范围。
- 前置：用户可访问所需材料；明确项目及输入版本。运行时写入沿用主机授权和审批；设计草稿不视为批准标准。
- 主流程：记录候选、投票或确认、决定人、理由、条件和排除范围；批准后交 Agent 2。
- 异常与验收：未定投票规则不能自动计票生效；条件未满足保留条件式决定；修订新建版本。
- 后置：保存或返回可追溯的结果；只有实际成功才推进状态。失败保留原记录和可操作原因。
- 当前证据与缺口：声明政策、版本提案、验签选票、条件确认和决定领域/API/原生工具已实现；决策浏览器已接，Agent 2 消费端待接 / declared policy, versioned proposals, verified votes, condition confirmation and decisions implemented in domain/API/native tools/browser; Agent 2 consumer pending。

### English requirements and acceptance

- Actors: Management decision-maker (A04), Department owner (A02); writes follow the tool-declared approval policy.
- Trigger: the meeting ends and consensus, votes and the MVP scope must be recorded.
- Preconditions: authorized access to the required materials and identified project/input versions. Runtime writes use host authorization and approval; design drafts are not approved standards.
- Main flow: Record candidates, votes or confirmations, decision owner, rationale, conditions and exclusions; hand the approved scope to Agent 2.
- Exceptions and acceptance: No automatic approval without agreed voting rules; unresolved conditions remain explicit; revisions create versions.
- Postcondition: retain or return a traceable result; advance state only after actual success. Preserve the previous record and an actionable failure reason otherwise.
- Evidence and gap: 声明政策、版本提案、验签选票、条件确认和决定领域/API/原生工具已实现；决策浏览器已接，Agent 2 消费端待接 / declared policy, versioned proposals, verified votes, condition confirmation and decisions implemented in domain/API/native tools/browser; Agent 2 consumer pending.

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

## Epic 数据与实现设计 / Epic data and implementation design

以下为待实现契约，不表示已有接口：

| Object | 字段 / Fields | 不变量 / Invariant |
| --- | --- | --- |
| MaterialVersion | id, digest, department, kind, period, parser_status, references | 同一文件修订新版本；空表不是记录 / new version on revision; empty template is not a record |
| Opportunity | id, project, departments, problem, input_refs, output, review_points, assumptions | 至少一个来源；推断不升级为事实 / at least one source; inference is not fact |
| Score | opportunity_id, effort, value, scale_version, evidence, scorer | 两轴依据齐全才展示；不默认权重 / plot only with both axes supported; no default weights |
| ProjectDecision | id, revision, candidates, selection, conditions, exclusions, decision_refs, status | proposed → conditional/approved/rejected；旧决定不可覆盖 / preserve earlier decisions |

建议 API：材料检查后显式登记来源；候选建立/修订；读取图投影与评分；记录会议决定。写操作全部走 DSH 审批回执并校验 expected_seq。图数据以节点/边结构返回浏览器；代理只取有界摘要，不能通过图端点间接读整张原始业务表。

Proposed APIs register material references after inspection, create/revise opportunities, project graphs/scores and record meeting decisions. All mutations use DSH receipts and expected sequences. Graph node/edge data is for the browser; agents receive bounded summaries, never whole source tables through graph endpoints.

实施顺序：先材料清单和候选，再结构化图与证据跳转，再评分与会议决定。若业务方尚未定义评分量表，界面可保存带依据的草案，但不能自动生成正式坐标或通过投票发布 MVP。

Implement inventory/opportunities first, then structured diagrams with evidence navigation, then scoring and decisions. Until the business defines a scale, retain evidence-backed drafts without fabricating coordinates or approving an MVP through unspecified voting rules.

### 材料与候选领域实现（2026-09-16） / Discovery domain implementation

E01-UC01/02 已增加 [discovery.py](../../backend/src/bridgeflow/workflow/discovery.py) 和 [行为测试](../../backend/tests/test_discovery.py)，已提供部门授权的只读 API，候选已接原生审批写工具，材料上传 API 和批准登记工具已接，浏览器材料页和登记旅程已接，候选逐项编辑与修订已接，图形共创和真实业务验收仍待完善。材料文件按 SHA256 保存于主机，事件存储保存项目、部门、期间、声明类型、检测类型、版本、解析状态、结构摘要和操作人。CSV/XLSX 复用结构检查；UTF-8 TXT/Markdown 只记录字符/行数，正文不进入返回值；不支持格式和解析失败仍留档，不能作为候选依据。

E01-UC01/02 now have a discovery domain and behavioral tests; department-scoped read APIs are available; candidate writes use native approval; material upload APIs and native registration are connected; the browser material page is connected; structured opportunity editing/revision is connected; graphical co-design and business acceptance remain incomplete. Content-addressed host blobs retain originals; events retain project, scope, period, declared/detected kind, version, parsing status, structural metadata and actor. CSV/XLSX use structural inspection; UTF-8 text/Markdown projections contain counts only. Unsupported or failed materials remain in inventory but cannot support claims.

候选陈述区分问题、输入、输出、人工节点、规则依赖和价值假设，每项必须引用同项目的当前可解析材料版本，并保留 reported/inferred。候选仅为 proposed，审批状态 not_decided；来源修订产生 stale_sources，不覆盖旧依据。保存候选时以同一事务检查来源序号，避免检查后并发修订漏过。部门范围不可通过修订改变。

Claims distinguish problems, inputs, outputs, human checkpoints, rule dependencies and value hypotheses, each referencing a current parsed source version in the same project. Reported/inferred labels persist; proposals are never automatically approved. Source changes surface stale references while preserving history. Transactional sequence guards prevent source changes between validation and saving. Department scope cannot change through revision.

剩余边界：图形共创及业务确认、模型辅助候选生成及人工复核。locator 已检查来源位置存在，但不证明内容支持陈述；解析成功也不证明业务规则有效。领域调用者必须提供已验身份，不能直接相信请求中的 actor。并发失败可留下未被事件引用的内容寻址文件，尚需保留/清理策略。音频、PDF/OCR 及真实企业材料/签核仍未验证。因此两个 UC 保持 PARTIAL。

Remaining: graphical co-design and business confirmation, model-assisted proposals and human review. Validated source locations are not proof of entailment; parse success does not validate business policy. Transport callers must supply a verified actor. Failed concurrent writes may leave unreferenced blobs pending a retention/cleanup policy. Audio, PDF/OCR and real enterprise acceptance remain unverified; both UCs stay PARTIAL.

### 来源位置与读取契约 / Source locations and read contract

引用 locator 为结构化对象：`{kind: header, sheet}`、`{kind: rows, sheet, start, end}` 或 `{kind: lines, start, end}`；行号从 1 开始，区间两端包含。表格实际行数保留空行位置，不能用非空业务行计数替代物理行号。未知/截断未检查的工作表、无表头、行越界或来源格式不匹配均拒绝。位置存在不代表陈述正确，reported/inferred 标签和人工复核仍保留。

Locators are structured header, workbook-row or text-line references; ranges are inclusive and one-based. Physical workbook rows retain blank-row positions. Unknown/uninspected sheets, absent headers, out-of-range positions and format mismatches are refused. Existence does not prove semantic support; claims still require human review.

`GET /discovery/{project}/{material|opportunity}` 提供最多 50 条的分页摘要，total 仅计算授权对象。`GET /discovery/{project}/{kind}/{id}?version=N` 读取已授权详情/历史。复用门户 JWT 和 `workflow_departments`，跨部门候选须覆盖全部来源部门；无权限详情返回 404。DSH 浏览器代理只放行这些 GET，不开放写入或原件路径。清单查询项目名称使用精确前缀匹配，区分大小写且 `_` 不作为 SQL 通配符。当前存储枚举仍扫描项目流，未验证大规模性能。

Read endpoints return scoped paginated summaries and authorized current/historical details. Portal JWT and explicit workflow departments are required; invisible objects return 404. The browser proxy allows only these GET routes. Project prefixes are literal and case-sensitive. Stream enumeration remains a project scan; large-scale performance is not yet validated.

### 候选原生审批保存 / Native proposal approval

`discovery_propose` 调用 `/tools/discovery-propose`，受工作流写开关及原生审批回执控制；门户模式另要求同名操作权限并验证提案部门、全部来源部门及已有候选范围。执行前重查权限；保存使用领域版本/来源并发保护。审批卡完整展示提案 JSON（包括陈述和所有引用），超出有界展示容量拒绝提交，不静默截断；返回模型的仅是 ID、项目、版本、状态和验证过的操作人。保存状态始终 proposed，不批准 MVP。

The native tool requires the workflow-write switch and native receipt; portal mode also checks explicit operation grants, proposed scope, every source department and any existing candidate scope. Execution rechecks authorization and source/version concurrency. Approval shows the complete bounded proposal and rejects oversize content rather than silently clipping. Model output is a compact acknowledgement; saved status remains proposed, never approved.

仍缺上传表单、候选浏览器卡和同版本浏览器旅程验证。不得因保存工具已注册而把 E01-UC01/02 标为完成。

Browser upload forms/cards and an end-to-end browser journey remain unfinished. Tool registration alone does not complete either UC.

### 模型材料检索 / Model material lookup

`discovery_materials` 已注册为原生只读工具，按明确 project_id 返回材料 ID、版本、摘要指纹、声明/检测类型及解析状态。每次最多 10 份材料、每份最多 5 张工作表；包括真实材料总数、工作表总数、分页及解析截断标记。指定 material_id 和 sheet_offset 可读取其余已检查工作表。原结构解析器仅检查前 20 张表，超过部分明确标记 inspection_truncated，不编造其位置。

The native read tool returns versioned material references and structural locations for a specified project. Results are capped at ten materials and five sheets each, with true totals, pagination and inspection truncation flags. An exact material ID and sheet offset allow further inspected sheets. The structural parser inspects at most twenty sheets; remaining sheets are explicitly uninspected.

模型返回排除原始行、表头标签、标题、文本正文和来源描述；只给物理行数、表头行号和文本行数。模型必须向人确认业务含义，不能把结构推断为业务事实。此工具与既有模型读取一样属于可信主机权限，不是员工隔离读取；浏览器通用代理不允许访问 `/tools/*`。原生会话/模型读取的个人隔离仍是 E09 未完成边界。

Model output excludes raw rows, header labels, titles, text bodies and source descriptions. Structural positions do not establish business meaning. Like existing model reads, this endpoint uses trusted-host authority and does not provide employee isolation; browser proxies cannot access tool endpoints. E09 session/model-read identity isolation remains incomplete.

### 材料上传与批准登记 / Upload and approved registration

`POST /discovery/uploads` 接收 multipart 文件和 MaterialInput 元数据。门户模式要求 `discovery_upload` 及明确部门权限；部署工作流写开关关闭则拒绝。单文件限制 20 MiB，文件名必须匹配元数据，不接受路径。文件与元数据先保存为不可变暂存记录，返回随机 upload_id、SHA256、元数据及到期时间；此时正式清单没有新增版本。

Multipart uploads require the deployment write switch and, in portal mode, explicit upload and department grants. Files are limited to 20 MiB and filenames must match metadata. Immutable staged uploads return an ID, digest, metadata and expiry; staging alone does not register evidence.

`discovery_register` 原生审批展示完整暂存标识、摘要和元数据；后端只接受精确匹配，并在门户模式校验同名操作权限和部门范围。正式登记保存验证过的批准人，原件不进入模型。版本冲突不覆盖旧记录；解析失败或不支持格式明确留档，不能当作已解析证据。成功后删除暂存记录；失败可保留至到期。24 小时后不能登记，后续上传会清理过期待审记录（非后台定时清理，SQLite 空闲页不等于安全擦除）。同一来源版本的并发登记仍由事件序号保护。

Native registration approval binds the full staging ID, digest and metadata. The backend verifies exact matches, current operation/scope grants and version sequence, then persists the verified actor. Successful registration removes staging; failures remain retryable until expiry. Expired uploads cannot register and are lazily cleaned on subsequent uploads, not by a background scheduler or secure erasure. Parsing failures remain explicit inventory records, not usable evidence.

尚未完成：图形共创、生产清理调度、真实企业材料/解析验收。材料浏览器旅程已用本地验签员工及离线模型验证，不能替代企业验收，两个 UC 保持 PARTIAL。

Remaining: graphical co-design, production cleanup scheduling and real enterprise material/parser acceptance. The material browser journey is verified with locally signed employee identity and an offline model, not enterprise acceptance. Both UCs remain PARTIAL.

### 工作室材料页 / Studio material page

工作室新增“立项材料与候选”：输入项目标识、上传带来源声明的材料、查看待审批摘要，复制登记请求到原生对话。复制不发送消息、不触发模型或批准；审批仍由原生卡片决定。批准后刷新分页清单，查看当前版本详情或下载指定版本原件。候选清单与只读详情可查看，尚无候选图形编辑器。

The Studio page opens a project, stages a sourced upload and provides a registration request to copy into native chat. Copying neither sends a message nor invokes a model or approval. After native approval, refresh the paginated inventory, inspect version details and download that exact original. Opportunity listing/details are available; graphical co-design is not implemented.

原件 API 在读取文件前校验当前/历史部门权限，读取后核对 SHA256；未授权返回 404、损坏返回 409、缺失返回 503。原件只走浏览器 API，不进入模型工具。浏览器验证覆盖上传、暂存、原生批准、版本出现和下载字节一致；尚未覆盖真实 OAuth、企业材料和全部候选生命周期。

Original reads authorize current/historical scope before file access and verify the content digest. Unauthorized, corrupt and missing originals return 404, 409 and 503 respectively. Originals remain browser-only. The tested journey covers upload, staging, native approval, persisted version and byte-identical download; real OAuth, business materials and the full opportunity lifecycle remain unverified.

### 暂存资源治理 / Staging resource management

暂存配额默认每员工 20 份、100 MiB，全部员工合计 1 GiB；通过 `DISCOVERY_UPLOAD_OWNER_COUNT`、`DISCOVERY_UPLOAD_OWNER_BYTES`、`DISCOVERY_UPLOAD_TOTAL_BYTES` 配置正数。它们是部署资源上限，不是业务判定规则。检查与插入共用 SQLite 写事务，并发不能越过额度；超额返回 429，保留已有文件和正式材料。门户关闭时共用本地会话额度。

Default deployment limits are 20 pending uploads/100 MiB per employee and 1 GiB globally. Positive environment settings override them. Quota checks and insertion share a write transaction; refusal returns 429 without altering existing evidence. Portal-disabled local sessions share one quota identity.

使用与服务相同的 RESULT_STORE_PATH 执行 `python scripts/cleanup_discovery_uploads.py`，默认只报告过期份数/载荷字节；加 `--apply` 删除过期暂存记录。不会删未过期暂存、正式事件或原件。后续上传也会惰性清理。生产任务调度尚未安装；SQLite 空闲页用于复用，不保证立即缩小文件或安全擦除。失败事务留下的未引用正式 blob 不在此命令范围，需要另定保留策略。

Run the cleanup script with the service's result-store configuration. Default mode reports expired count/payload bytes; `--apply` deletes only expired staging records. No scheduler is installed. SQLite reuses freed pages without guaranteed physical shrinking or secure erasure. Unreferenced content-addressed blobs from failed domain writes are outside this cleanup policy.

### 候选逐项编辑与版本修订 / Structured opportunity editing and revision

候选页新增结构化编辑器：每项陈述选择六类之一，保留 reported/inferred，填写材料 ID、版本、表头/行区间/文本行位置；最多 30 项陈述、每项 10 条来源。部门和待确认问题按行填写。生成请求前检查必填、正整数位置、区间和审批展示容量；来源存在性、权限及并发仍以后端校验为准。

The editor captures typed claims, reported/inferred basis, multiple versioned material references and structured locations. It supports up to thirty claims and ten references per claim, plus department scope and open questions. Form validation does not replace backend evidence, authorization and concurrency checks.

“修订此候选”读取当前已授权版本，显示来源过期提示；标识/部门范围不可改，expected_seq 来自读取结果。表单修改后清空旧审批请求，必须重新生成。生成和复制均不保存；用户粘贴到原生对话，由原生审批工具决定是否保存新版本。保存只得到 proposed/not_decided，不代表立项批准。详情保留全部引用及待确认问题。

Revision loads the authorized current version and flags stale sources. Identity/scope remain immutable and the read sequence guards saving. Editing clears any prepared request. Preparing/copying does not save; the user pastes into native chat and approves the exact proposed revision. Saved proposals remain unapproved.

当前编辑草稿仅在页面内保留，关闭页面会丢失未复制/未批准内容；已批准版本持久化。素材选择暂以精确 ID/版本输入，尚无来源选择器、自动语义抽取、会议协同或图形编辑；不能将此编辑器视为 E01 所有共创功能已完成。

Unsaved edits currently live only in the page and are lost when it closes; approved versions persist. References use exact ID/version inputs, not a source picker. Semantic extraction, meeting collaboration and graphical editing remain outside this implementation.

### 信息流/文件流领域图 / Information and document graph domain

[discovery_graph.py](../../backend/src/bridgeflow/workflow/discovery_graph.py) 复用追加式事件存储，以项目、候选 ID/版本、图版本、部门范围和验证过的操作者保存草图。节点记录角色、触发、输入输出与来源；边记录信息/文件类型、条件、返工标记、状态、说明和来源。节点/边 ID 必须唯一、端点必须存在；允许显式分支、并行、返工环路和孤立未知阶段，不按部门名称推断顺序。

The graph domain reuses append-only events, retaining project, exact opportunity version, graph revision, scope and verified actor. Nodes capture roles, triggers, inputs/outputs and sources. Edges capture information/document type, condition, rework, status, rationale and sources. Explicit branches, cycles and disconnected unknown stages are supported; department names never determine ordering.

confirmed 要求来源及人工确认说明，inferred 要求来源，missing 允许没有来源但必须说明未知点，conflict 要求至少两条不同引用。所有引用校验项目、部门、解析状态和实际位置。图保存时在同一事务检查候选及其全部来源版本（包括未画在图中的候选依据），防止并发修订漏检。来源/候选变化后旧图保留，读取给出 stale_sources/opportunity_stale；修订写新版本，不覆盖历史。

Confirmed edges require explicit human confirmation and evidence; inferred edges require evidence; missing edges retain a rationale without fabricated sources; conflicts need two distinct references. Saving transactionally guards the opportunity and every source version, including candidate evidence not drawn in the graph. Old revisions persist and expose staleness after evidence changes.

图已接部门授权 API 及原生审批保存；浏览器渲染与节点/边逐项编辑已接。确认文本保存时绑定验签操作者，仍须人审查语义依据。图始终 draft，不产生业务交接、通知或 MVP 批准。E01-UC03 保持 PARTIAL，行为验证见 [test_discovery_graph.py](../../backend/tests/test_discovery_graph.py)。

Scoped graph APIs and native approved writes are connected; browser visualization and structured node/edge editing are connected. The saved graph binds confirmation to the verified actor; a person must still assess semantic evidence. Graphs stay drafts and create no handoffs, notifications or MVP approvals. E01-UC03 remains PARTIAL.

### 图授权与原生工具 / Graph authorization and native tool

`GET /discovery/{project}/graph` 与图详情/历史复用部门范围过滤及 404 隐藏。`discovery_graph_save` 通过 `/tools/discovery-graph-save` 保存，门户模式要求同名操作授权，同时覆盖候选、节点/边来源及现有图的部门。执行时重查权限；原生审批展示完整图而非截断摘要，超出展示上限拒绝。保存返回仅包含 ID、版本、draft 状态、验签操作者和来源过期标记。浏览器代理仍不放行图写接口。

Graph list/detail/history reads use departmental filtering and invisible-object 404 responses. The native save tool requires explicit operation grants, scope over the candidate, every source and existing graph, plus an exact native receipt. Approval displays the complete bounded graph; oversize content is refused. Model output contains only a compact revision acknowledgement. Browser proxies do not expose graph writes.

API、原生工具及浏览器旅程的最新验证见 docs/00；实现图形交互不代表真实业务共创通过。

See docs/00 for current API, native-tool and browser evidence. Graphical interaction does not establish real business co-design acceptance.

### 浏览器图编辑与可视化 / Browser graph editing and visualization

在候选清单选择“设计流程草图”，绑定读取到的候选版本和部门。用户逐项添加节点、触发/角色/输入输出、来源引用，再添加关系类型、状态、条件、返工及确认说明。生成请求后粘贴到原生会话批准保存；编辑不直接写数据库。已保存图可从图清单查看/修订，使用已读 seq，范围/候选不在编辑器中自动改变。

Start a graph from an authorized candidate version. Add explicit nodes, role/trigger/input/output declarations, source references and typed edges with status, condition, rework and confirmation. Generated requests go through native chat approval. Saved graphs can be viewed/revised against their read sequence; the editor never changes scope or candidate implicitly.

SVG 用确定性网格布置节点，只依据显式箭头表达关系，不从布局推导顺序。关系同时提供带状态文字的按钮列表，不能只靠颜色区分。节点可键盘选择，节点/边详情展示触发、条件、说明和材料版本引用。缺失关系可在没有证据时保留未知，但不能升级为 confirmed；冲突至少两个不同来源。

The SVG uses a deterministic grid for readability, not inferred execution order. Edges also appear as text-labelled selectable entries; color alone does not encode state. Keyboard-selectable nodes and edge details expose triggers, conditions, rationale and versioned evidence. Missing edges remain unknown, and confirmed/conflicting evidence requirements are enforced by the backend.

尚缺：拖拽布局与持久坐标、图内来源原件跳转、跨会话未批准草稿恢复、多人同时编辑合并和真实业务共创。当前逐项编辑/有界图可视化不是完整协同图编辑器；版本冲突保留服务端旧图并要求重新核对。

Remaining: drag layout/persisted positions, original-source navigation within the diagram, recovery of unapproved edits across sessions, collaborative merging and real business co-design. The structured editor is not a complete collaborative diagramming system; conflicts preserve stored history and require review.

### 声明评分政策与坐标领域 / Declared scoring policy and coordinates

[discovery_scoring.py](../../backend/src/bridgeflow/workflow/discovery_scoring.py) 新增人工声明的 ScoringPolicy：项目、版本、声明人、声明依据，以及 effort/value 两轴的标题、单位、上下限、分界线、高低含义和分界点归属。文件读取失败或尺度非法明确拒绝；没有内置业务量表、权重或自动优先级。规范化声明内容计算指纹，评分保存完整政策快照和指纹。

The scoring domain loads a human-declared project policy: version, declarer, source and axis titles/units/bounds/splits/meanings/tie rules. Missing or invalid declarations fail closed. No default business scale, weights or automatic ranking are invented. Scores retain the policy snapshot and fingerprint.

评分对象关联候选精确版本，各轴保存 Decimal 分值、说明和材料版本引用。缺轴、分数、理由或来源可保存草案，但 coordinates 为空且给出不落点原因；越界和非有限数字拒绝。两轴完备时按声明计算归一化坐标及 high/low 归属。评分人由调用层验证后传入，结果始终 approval=not_decided，不批准项目也不承诺节省金额/时间。

Each rating binds an exact opportunity version and records decimal values, rationale and source versions per axis. Incomplete drafts persist without coordinates; out-of-range/non-finite values are refused. Complete supported ratings receive normalized coordinates and declared high/low sides, never automatic project approval or savings promises.

保存事务检查候选及全部相关材料版本；旧评分不可覆盖。读取时发现候选、来源或当前政策改变，保留历史内容但不再提供当前坐标。配置路径、员工授权和原生审批已接，浏览器评分输入/四象限/依据点击已接，真实政策签核仍待业务方。测试使用明确合成量表，不能作为生产量表。

Saving transactionally guards candidate and material versions. Historical ratings persist; changed candidates, evidence or policy withhold current coordinates. Configuration, employee authorization and native approval are connected; browser rating/quadrant/evidence interaction is connected; real policy acceptance remains pending. Test scales are synthetic, not production policy.

### 评分政策配置、授权与原生保存 / Policy configuration, authorization and native save

`DISCOVERY_SCORING_POLICY_PATH` 指向人工维护的 ScoringPolicy YAML/JSON。默认未配置，不回退量表；当前一个部署配置文件对应一个项目，其他项目政策请求返回 404。政策新增明确 departments，员工须覆盖全部政策部门才能读取。`GET /discovery/{project}/scoring-policy` 返回声明内容及指纹；评分列表/版本详情同样按部门过滤，列表只投影有界坐标和不落点原因。

A configured human-maintained policy file defines the current project; absent configuration fails closed and no scale is invented. The policy declares departments; readers require all of them. Policy reads return its fingerprint. Score list/detail/history reads enforce scope and expose current coordinates or explicit withholding reasons. The current deployment uses one project policy file.

原生 `discovery_score_save` 绑定完整评分、政策指纹、候选版本及 expected_seq；门户下要求同名操作授权，检查候选及所有来源部门，执行前重查权限和政策指纹。政策改变、权限撤销、未批准或版本冲突均不保存。模型只接简短结果、坐标/不落点原因，不能据此宣称立项批准。评分详情需要当前可读取的政策；政策文件缺失时返回 503，不暗中使用旧尺度。

Native saves bind the full rating, policy fingerprint, candidate version and expected sequence. Portal mode checks operation grants and candidate/source scope, then rechecks grants and the policy at execution. Changed policy, revoked access, missing approval or conflicts refuse the write. Model output is a compact result, not a project decision. Score projection requires a readable current policy; unavailable policy returns 503 rather than silently using a historical scale.

评分表单和四象限已通过员工模式离线浏览器旅程；真实业务量表及签核未验证，E01-UC04 保持 PARTIAL。

The rating form and quadrants passed an offline employee-mode browser journey. Real business policy and acceptance remain unverified; E01-UC04 stays PARTIAL.

### 评分表单与四象限浏览器 / Rating editor and quadrant browser

工作室从候选精确版本建立评分；先展示量表声明人、来源、版本、边界及高低含义。各轴可留空，录入分值、理由和材料位置后准备原生审批请求；复制不会发送或保存。修订使用当前候选版本及已有评分序号，保存仍由后端检查政策和来源是否变化。

The Studio starts ratings from an exact candidate version and displays the policy declarer, provenance, version, bounds and meanings. Axes may remain blank. Scores, rationale and material locations form a native approval request; copying neither sends nor saves it. Revisions bind the current candidate and existing rating sequence; the backend rechecks policy and evidence.

四象限只绘制当前页、当前政策指纹且依据完备的评分。缺项、政策/候选/来源变化明确列出未落点原因；重合点可从列表分别打开评分人和依据。政策与列表并发读取时若指纹不一致，也不混用尺度。数值计算在 Python，浏览器仅把归一化结果定位到 SVG，不生成排名或默认权重。

The chart plots only complete ratings on the current page under the current policy fingerprint. Missing or revised inputs have explicit reasons; overlapping points are individually accessible through the list. A policy/list fingerprint mismatch also suppresses plotting. Python computes coordinates; the browser positions normalized values without inventing ranks or weights.

离线旅程覆盖完整/缺项评分的原生批准保存、点击依据以及量表修订后撤点，证据见 [docs/00](../00-status.md)。剩余边界：未批准编辑的持久恢复、真实量表配置与企业签核；当前仍为每部署一个项目的政策文件，政策不可用时历史评分详情也返回 503。

The offline journey covers native-approved complete/incomplete ratings, evidence inspection and withdrawing points after a policy revision; see [measured evidence](../00-status.md). Remaining: recovery of unsaved edits, real policy and enterprise acceptance. Policy configuration still serves one project per deployment; unavailable policy also yields 503 for historical rating details.

### 会议准备与纪要领域 / Meeting preparation and minutes domain

[discovery_meetings.py](../../backend/src/bridgeflow/workflow/discovery_meetings.py) 保存范围、排除项、风险、资源假设、阶段依赖/责任角色/退出条件和讨论问题。每次修订关联候选精确版本、保存候选快照及材料版本，包含变更原因和调用层验证的记录人。报告型陈述必须有来源；估算及建议明确为 assumption，引用存在不证明语义真实。

The meeting domain stores scope, exclusions, risks, resource assumptions, stage dependencies/roles/exit criteria and discussion questions. Each revision binds exact candidates, retains candidate snapshots and material versions, and records the change reason and transport-verified recorder. Reported statements require sources; estimates and proposals are explicit assumptions. Valid references do not prove semantic truth.

会后纪要要求参会者记录和纪要正文；参会姓名仅为记录人提供的信息，不构成身份验证、投票或批准。旧版本不可覆盖，会后纪要不能回退为会前准备。候选或来源变化时旧快照保留并显示 needs_review；保存事务同时保护所有输入版本，拒绝陈旧写入。阶段依赖必须存在且无环。永不自动批准 MVP、创建交接或发通知。

Minutes require reported participants and notes; reported attendance is not verified identity, a vote or approval. Revisions preserve history; minutes cannot revert to preparation. Changed candidates or sources retain the frozen snapshot with needs_review; transactional guards reject stale writes. Stage dependencies must exist and be acyclic. This domain never approves an MVP, creates a handoff or sends notifications.

领域、授权 API、原生工具和浏览器编辑/详情已接；正式决定人权限、投票规则和 Agent 2 批准交接尚未实现。调用者必须先验证身份及全部来源范围。E01-UC05 保持 PARTIAL，E01-UC06 不变。

The domain, scoped API, native tools and browser editor/details are connected. Formal decision roles, voting policy and approved Agent 2 handoff remain pending. Callers must verify identity and all source scope before invoking the domain. E01-UC05 is PARTIAL; E01-UC06 is unchanged.

### 会议授权、原生审批与工作室 / Meeting authorization, native approval and Studio

`GET /discovery/{project}/meeting` 及版本详情复用部门范围过滤；列表仅含摘要、阶段和过期标记。`discovery_meeting_save` 要求明确同名员工操作权限及原生批准回执；批准前及执行前检查所有候选、全部引用来源和旧会议范围。完整有界会议内容展示给审批人，超出展示上限拒绝而非截断。模型返回仅保存回执，不回传候选快照或纪要正文。

Meeting lists and version details filter by department scope; lists contain only summaries, phase and stale markers. The native save tool requires an explicit employee operation grant and native receipt, checking all candidates, references and previous scope both before approval and before execution. The approver sees the full bounded meeting input; oversized content is rejected rather than clipped. Model output contains only the save acknowledgement, not candidate snapshots or minutes.

工作室从候选准备会议，支持多候选版本、范围/风险/资源陈述及来源、阶段依赖/退出条件、问题和排除范围；可修订为会后纪要。详情按业务栏目展示冻结候选、记录人、假设、依据、阶段及纪要；不会将会议记录当成项目决定。准备/复制请求不保存，仍须在原生对话审查批准。输入错误和冲突保留旧记录；未批准编辑尚无持久恢复、多人共编或自动会议摘要。浏览器验证结果见 [docs/00](../00-status.md)。

Studio prepares meetings from candidates and supports multiple candidate versions, sourced scope/risk/resource statements, stage dependencies/exit criteria, questions and exclusions, followed by minutes revisions. Details show frozen candidates, recorder, assumptions, references, stages and notes in readable sections. Preparing/copying a request does not save it; native chat approval remains required. Errors and conflicts preserve the previous record. Unsaved draft recovery, collaborative editing and automatic meeting summarization remain unimplemented; browser evidence is recorded in [docs/00](../00-status.md).

### MVP 决策政策与版本状态 / MVP decision policy and versioned state

[discovery_decisions.py](../../backend/src/bridgeflow/workflow/discovery_decisions.py) 引入人工声明的 DecisionPolicy：项目/部门、版本/出处、提案人、投票人、决定人、条件确认人、法定人数、最低赞成票、反对票是否阻止通过、弃权是否计入人数及 Agent 2 接收角色。人数使用一人一票的明确阈值，不推定多数、权重或默认规则。声明缺失/非法拒绝；DISCOVERY_DECISION_POLICY_PATH 指向 YAML/JSON，当前每部署一个项目政策文件。提案保存完整政策快照及指纹，任何内容变化均要求修订后重新投票。

DecisionPolicy explicitly declares project/departments, provenance/version, eligible proposers/voters/deciders/condition confirmers, quorum, minimum yes votes, veto treatment, abstention participation and the Agent 2 owner role. Votes use declared one-person-one-vote thresholds, not inferred majority or weights. Missing/invalid policy fails closed; DISCOVERY_DECISION_POLICY_PATH loads YAML/JSON for one project per deployment. Proposals retain the full snapshot/fingerprint; any policy change requires a revision and new votes.

提案绑定会议纪要的精确版本及全部候选/来源，明确选中候选、批准范围、排除范围、理由和待满足条件。会前准备不能直接发起决定；选中项必须在会议中。修订新建版本，并清空旧选票/条件确认，不复用历史批准。每次动作校验 expected_seq 和 proposal_version，事务保护会议、候选和来源版本。

Proposals bind exact meeting minutes and all candidate/source versions, naming selected candidates, scope, exclusions, rationale and conditions. Preparation alone is insufficient and selections must belong to the meeting. Revisions retain history while clearing votes/condition confirmations; historical approvals are not reused. Every action checks expected_seq and proposal_version with transactional guards over all inputs.

投票人取验签身份，不能提交他人 actor；同一人重投替换当前票但历史保留。票数达标仍为 proposed，必须由声明的决定人明确批准。决定人可带理由拒绝；批准必须满足投票条件。有未满足条件则只记录 conditional；指定确认人提交当前来源依据后仍需决定人再次批准。参与者名单不算投票，模型不得代签。

The verified subject is the voter; caller-supplied actor fields are rejected. Recasting replaces the current vote while retaining history. A passing tally remains proposed until an eligible decider explicitly approves. A decider may reject with rationale; approval requires the voting rules. Unresolved conditions yield conditional status; sourced confirmations by assigned subjects still require another explicit final approval. Reported attendees are not votes and the model cannot sign for people.

读取发现政策、会议、候选或材料变化时保留 recorded_status，但当前状态变为 needs_review，agent2_handoff 为空。历史版本也不提供可用交接。只有当前有效 approved 才返回带决定序号、候选版本、范围、排除范围、会议和政策指纹的 Agent 2 范围清单；当前尚未接模板治理消费端，不创建业务交接或通知。业务语义和来源真实性仍须人审查。

Reads retain recorded_status but mark revised policy/meeting/candidate/source inputs needs_review, withholding agent2_handoff. Historical versions also withhold it. Only a current valid approval yields an Agent 2 scope manifest with decision sequence, candidate versions, scope/exclusions, meeting and policy fingerprint. Template governance does not yet consume this manifest; no operational handoff or notification is created. People must still assess semantic evidence and authenticity.

### 决策授权接口与原生操作 / Decision authorization and native operations

决策政策、清单和版本详情按部门过滤。四个原生操作 discovery_decision_propose/vote/resolve/finalize 各需明确员工操作权限，并额外匹配政策中相应身份角色；执行前重查 ACL、角色、政策和来源。原生审批显示完整有界提案或动作，超限拒绝，不截断决定依据。模型只返回状态、票数、未满足条件及版本回执，不回传会议正文、快照或全部选票。

Policy/list/version reads enforce department scope. Each native operation requires its explicit employee ACL grant plus its declared policy role, rechecked with policy and source scope at execution. Native approval displays the complete bounded proposal/action and rejects oversized input. Model acknowledgements contain only status, tally, pending conditions and versions, not meeting text, snapshots or the full ballot ledger.

决策专用浏览器已接，两个验签身份顺序投票的离线旅程通过。剩余：真实多员工/隔离会话验收、Agent 2 对有效决定的原子消费/失效检查、真实业务规则与签核。当前政策不可读时历史详情也不可读，未提供跨项目政策管理或未批准草稿恢复。领域/API/工具证据见 [docs/00](../00-status.md)，E01-UC06 保持 PARTIAL。

Decision browser interaction and an offline sequential two-identity voting journey are connected and verified. Remaining: real employee/isolated-session acceptance, atomic Agent 2 consumption/invalidation checks, and real policy/acceptance. Unavailable current policy also blocks historical detail; multi-project policy management and unsaved draft recovery are absent. See [measured evidence](../00-status.md); E01-UC06 remains PARTIAL.

### 阶段暂停时的决策页面 / Decision browser at the phase pause

按用户要求，本阶段于 2026-09-16 整理交接后停止新增开发。决策页显示规则、服务端验签身份及可用动作，支持提案/修订、本人投票、指定条件确认和明确决定；请求仍经原生对话审批。连续离线旅程验证两名验签身份顺序投票、达标不自动批准、条件确认后仍需再次批准，以及政策修订撤下有效范围。此验证不覆盖原生会话隔离/多人并发，Agent 2 消费端未接，E01-UC06 保持 PARTIAL。

At the user's request, this phase pauses after handoff on 2026-09-16. The decision page displays policy, server-verified identity and available actions; proposal/revision, own voting, assigned confirmation and explicit decisions still require native chat approval. The offline journey verifies sequential signed identities, no automatic approval from votes or condition confirmation, explicit final release, and invalidation on policy change. It does not establish session isolation/concurrent collaboration. Agent 2 consumption remains unconnected; E01-UC06 stays PARTIAL.
