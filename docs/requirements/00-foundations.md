# 00 — 需求基础：进展盘点、角色、非功能需求与结论规范

# 00 — Requirements foundations: progress review, actors, quality attributes and presentation standards

基线 / Baseline: `692d3d5`, reviewed 2026-09-17. 本文件不定义 UC，只定义所有 epic 共用的角色、质量属性、结论呈现规范与验收写法；UC 仍只由编号 epic 文件定义。

This file defines no UCs. It holds what every epic shares: actors, quality attributes, presentation standards and the acceptance format. UCs are defined only in the numbered epic files.

## 1 进展盘点：三个视角 / Progress review from three perspectives

2026-09-17 对照 `main@692d3d5` 的代码与 12 个 epic、73 个 UC，按三个视角检查缺口。结论：**核心月度对账链路完整，但「谁来用、怎么省事、结论怎么读」三件事在需求层面没有被写成 UC**；已有 UC 的写法也不够专业。

Reviewed against `main@692d3d5` and the existing 12 epics / 73 UCs. The core monthly reconciliation chain is complete, but who uses it, how it saves effort and how its conclusions are read were never captured as UCs, and existing UC wording is not yet professional.

### 1.1 项目完整性 / Completeness

| 发现 / Finding | 处置 / Resolution |
| --- | --- |
| 结论只停留在单月：没有与上月、同期或计划的比较，而经营判断几乎都依赖对比 / conclusions are single-month; no comparison with prior period, last year or plan | 新增 E13-UC02 |
| 口径假设（增值税、缺口公式、诊断阈值、按日汇总）已标注，但没有业务方确认与替换的流程 / declared conventions are labelled but have no confirmation workflow | 新增 E13-UC05 |
| 月度报告只有 XLSX 总表；E06-UC06 只覆盖季度、年度与 PDF，且已延期 / only the master workbook exists; E06-UC06 covers quarter/year PDF and is deferred | 新增 E13-UC04（月度，与 E06-UC06 分工） |
| 全部 UC 缺少角色画像、非功能需求与优先级 / no actor catalogue, quality attributes or priorities | 本文件第 2、4、6 节 |

### 1.2 流程便民性 / Ease of use

| 发现 / Finding | 处置 / Resolution |
| --- | --- |
| 月度对账没有进度清单：汇总负责人看不到还差哪个部门、差什么 / no monthly checklist of who still owes what | 新增 E14-UC01 |
| 员工每月从零填模板，上月可沿用的值要重抄 / staff refill templates from scratch each month | 新增 E14-UC02 |
| 文件只有导入时才被拒绝，员工无法提交前自检 / files are only rejected at import time | 新增 E14-UC03 |
| 一个部门的文件出错要四个部门整批重导 / one wrong file forces a four-file reimport | 新增 E14-UC04 |
| 待确认事项分散在总表、隔离行、列匹配、填报草稿四处 / open items are scattered across four modules | 新增 E14-UC05 |
| 飞书只能逐个文件取用 / Feishu import is file by file | 新增 E14-UC06 |

### 1.3 结论直观性与专业性 / Clarity and professionalism of conclusions

| 发现 / Finding | 处置 / Resolution |
| --- | --- |
| 研判结果是四张部门卡片，管理层没有一页式结论 / the review is four department cards, not a one-page brief | 新增 E13-UC01 |
| 指标只有数字表格，没有趋势、差异与异常的图 / metrics are tables without charts | 新增 E13-UC03 |
| 读者无法区分结论依据是原件、公式、口径假设还是模型判断 / readers cannot tell what a conclusion rests on | 新增 E13-UC06 |
| 数字格式、单位、状态用词、禁用表述没有统一规范 / no standard for number formats, units, status words or prohibited claims | 本文件第 5 节 |
| 73 个 UC 的触发句、52 个 UC 的参与者是同一句模板话；验收条件多为定性描述 / boilerplate triggers and actors; qualitative acceptance | 第 3 节逐 UC 给出参与者与触发事件，并已替换各 epic 正文；新 UC 用第 6 节的可测写法 |

补充后目录为 **14 个 epic、85 个 UC**。新增 12 个 UC 均未实现或部分实现，不改变已有 UC 的状态。

After this change the catalogue has **14 epics and 85 UCs**. The 12 new UCs are designed or partial; no existing status changes.

## 2 角色目录 / Actor catalogue

角色是职责，不是岗位名称；同一人可兼任多个角色。系统里的访问范围以端点实际授权为准，不从角色名推定（见 E09）。

Actors are responsibilities, not job titles; one person may hold several. Access is enforced per endpoint, never inferred from a role name (see E09).

| ID | 角色 | Actor | 职责 / Responsibility | 不能做 / Must not |
| --- | --- | --- | --- | --- |
| A01 | 部门填报员 | Department contributor | 按模板提交本部门数据，回答补问 / submit department data on the template and answer clarifications | 批准自己的数据或标准 / approve own data or standards |
| A02 | 部门负责人 | Department owner | 对本部门数据与研判结论负责，处理指派给本部门的事项 / own department data, findings and assigned items | 替其他部门确认 / confirm for other departments |
| A03 | 月度汇总负责人 | Monthly consolidation lead | 组织月度对账、发起研判、整理结论（通常是经营分析或财务 BP） / run the monthly close, start reviews, prepare conclusions | 改动部门原始数据 / alter department originals |
| A04 | 管理层决策者 | Management decision-maker | 阅读结论、做出经营与立项决定 / read conclusions, make business and project decisions | 以 AI 排名代替决定 / let an AI ranking stand in for a decision |
| A05 | 字典与标准维护人 | Dictionary and standards steward | 维护字典、模板、口径与规则的版本 / maintain dictionary, template, convention and rule versions | 让模型发明标准 / let a model invent standards |
| A06 | 审批人 | Approver | 在原生审批中批准或拒绝具体操作 / approve or reject specific actions natively | 事后补批 / approve after the fact |
| A07 | 报价负责人 | Quotation owner | 组织报价输入、比较方案、提交放行 / assemble quotation inputs, compare scenarios, request release | 未批准外发 / send without approval |
| A08 | 落地支持负责人 | Adoption support lead | 收集一线反馈、提出支持与培训建议 / gather feedback, propose support and training | 自动作人事或资源决定 / make HR or resourcing decisions |
| A09 | 独立评测人 | Independent evaluator | 保管留出集，运行独立验收 / hold held-out data and run independent evaluation | 把留出集给开发 / share held-out data with development |
| A10 | 平台运维管理员 | Platform operator | 部署、预检、凭据与运行时维护 / deploy, preflight, credentials and runtime | 把引导变量写进项目文件 / put bootstrap variables in project files |
| S01 | Captain 代理 | Captain agent | 组织工具调用、带人补问、提出操作请求 / orchestrate tools, clarify with people, request actions | 自行批准写入；读取原始行 / self-approve writes; read raw rows |
| S02 | 部门研判子代理 | Department review subagent | 在声明职责内给出带证据的判断 / produce evidence-bound judgements within its declared responsibility | 越权决定或互相协商 / exceed responsibility or negotiate |
| S03 | 外部系统 | External system (Feishu, target API) | 存放文件、接收标准记录、发送通知 / store files, receive records, deliver notifications | 被视为已接通而未验证 / be treated as connected without verification |

## 3 每个 UC 的主参与者与触发事件 / Primary actors and triggers per UC

下表替代原先各 UC 里「本 epic 的授权使用者」「用户需要……」一类模板句，已同步写入各 epic 正文。触发事件描述业务上发生了什么，而不是用户点了哪个按钮。

This table replaces the boilerplate actor and trigger lines; each epic body has been updated to match. Triggers describe the business event, not a button click.

| UC | 主参与者 | 触发事件 | Primary actors | Trigger |
| --- | --- | --- | --- | --- |
| E01-UC01 | 月度汇总负责人、字典与标准维护人 | 项目启动时收到部门报表、说明或会议纪要，需要先弄清手里有哪些材料 | Monthly consolidation lead, Dictionary and standards steward | project kickoff brings department reports, notes or minutes that must be inventoried first |
| E01-UC02 | 月度汇总负责人、Captain 代理 | 材料登记完成后，需要找出值得改进的跨部门工作场景 | Monthly consolidation lead, Captain agent | registered materials need to be turned into candidate cross-department work scenarios |
| E01-UC03 | 月度汇总负责人、部门负责人 | 业务方选定要深入的候选场景，需要看清信息与文件如何在部门间流转 | Monthly consolidation lead, Department owner | the business picks a candidate scenario and needs to see how information and files move between departments |
| E01-UC04 | 管理层决策者、月度汇总负责人 | 候选场景超过一个，管理层需要按落地难度与价值排序 | Management decision-maker, Monthly consolidation lead | more than one candidate exists and management needs them ranked by effort and value |
| E01-UC05 | 月度汇总负责人、Captain 代理 | 管理层初选了项目，需要组织相关部门开会确认 | Monthly consolidation lead, Captain agent | management shortlists projects and a cross-department meeting must be prepared |
| E01-UC06 | 管理层决策者、部门负责人 | 会议结束，需要记录共识、投票并确认 MVP 范围 | Management decision-maker, Department owner | the meeting ends and consensus, votes and the MVP scope must be recorded |
| E02-UC01 | 字典与标准维护人、部门负责人 | MVP 已批准，需要把选定流程细化为阶段、模板和字段血缘 | Dictionary and standards steward, Department owner | an approved MVP must be detailed into stages, templates and field lineage |
| E02-UC02 | 字典与标准维护人、部门填报员 | 模板草案需要在一线试用后修订并发布版本 | Dictionary and standards steward, Department contributor | draft templates need a frontline pilot before a version is released |
| E02-UC03 | 部门填报员、Captain 代理 | 员工手里是非标准原件（表格、文字、图片），需要落到批准模板 | Department contributor, Captain agent | a staff member holds non-standard originals that must land on an approved template |
| E02-UC04 | 部门填报员、审批人 | 抽取结果有缺项、冲突或需要确认的值 | Department contributor, Approver | an extracted record has missing, conflicting or unconfirmed values |
| E02-UC05 | Captain 代理、外部系统（飞书、目标 API） | 标准记录经批准，需要写入目标系统 | Captain agent, External system (Feishu, target API) | an approved standard record must be written to the target system |
| E02-UC06 | 部门负责人、外部系统（飞书、目标 API） | 数据已就绪，需要通知下一个部门并在看板上可见 | Department owner, External system (Feishu, target API) | ready data must notify the next department and appear on the board |
| E02-UC07 | 部门负责人 | 下游部门收到交接，需要开始、退回或完成 | Department owner | a downstream department receives a handoff to start, return or complete |
| E02-UC08 | 部门负责人、部门填报员 | 上游修订了已交接的记录，下游需要确认影响 | Department owner, Department contributor | an upstream revision affects a record already handed off |
| E02-UC09 | 独立评测人、字典与标准维护人 | 试点结束，需要用独立样例衡量正确性与人工负担 | Independent evaluator, Dictionary and standards steward | a pilot ends and correctness and human effort must be measured on independent samples |
| E02-UC10 | 部门填报员、外部系统（飞书、目标 API） | 部门文件放在飞书云文档里，需要直接取用或传回结果 | Department contributor, External system (Feishu, target API) | department files live in Feishu Drive and must be fetched or results sent back |
| E03-UC01 | 部门填报员、落地支持负责人 | 员工上岗或流程变更后，不知道数据该交到哪、下一步是什么 | Department contributor, Adoption support lead | after onboarding or a process change a staff member does not know where data goes next |
| E03-UC02 | 部门填报员、落地支持负责人 | 一线员工遇到问题，需要提交反馈并核实事实 | Department contributor, Adoption support lead | a frontline employee hits a problem and files feedback that must be verified |
| E03-UC03 | 落地支持负责人 | 反馈累积，需要区分技术、模板、权限与培训问题并给出支持建议 | Adoption support lead | feedback accumulates and must be classified into technical, template, permission or training issues |
| E03-UC04 | 落地支持负责人、管理层决策者 | 推广需要人手、预算或分阶段计划，须由管理层决定 | Adoption support lead, Management decision-maker | rollout needs people, budget or staging that management must decide |
| E03-UC05 | 落地支持负责人、管理层决策者 | 措施执行一段时间后，需要复盘效果并把改动送回 Agent 1/2 | Adoption support lead, Management decision-maker | measures have run for a while and outcomes must be reviewed and routed back to Agents 1/2 |
| E04-UC01 | 月度汇总负责人 | 月末收到四个部门的报表，需要导入成一个可复现的批次 | Monthly consolidation lead | month-end department reports must be imported as one reproducible batch |
| E04-UC02 | 月度汇总负责人、字典与标准维护人 | 工作簿有多个工作表或表头不在第 1 行 | Monthly consolidation lead, Dictionary and standards steward | a workbook has several sheets or its header is below row 1 |
| E04-UC03 | 月度汇总负责人 | 导入的表格存在格式不一、重复、错位等质量问题 | Monthly consolidation lead | an imported sheet has inconsistent formats, duplicates or shifted rows |
| E04-UC04 | 字典与标准维护人、月度汇总负责人 | 日期写法有歧义（如 03/11/2025），需要按部门声明解读 | Dictionary and standards steward, Monthly consolidation lead | dates are ambiguous (e.g. 03/11/2025) and must be read by department declaration |
| E04-UC05 | 月度汇总负责人、部门负责人 | 需要核对某处清洗改动对应原件的哪一格 | Monthly consolidation lead, Department owner | a cleaning change must be traced to its original cell |
| E04-UC06 | 月度汇总负责人、审批人 | 有行被隔离，需要决定放行或丢弃 | Monthly consolidation lead, Approver | quarantined rows must be released or discarded |
| E04-UC07 | 月度汇总负责人、部门负责人 | 需要在浏览器里翻看上传原件核对内容 | Monthly consolidation lead, Department owner | uploaded originals must be browsed page by page |
| E04-UC08 | 字典与标准维护人、月度汇总负责人 | 报表出现不同币种、单位或缺少某个月份 | Dictionary and standards steward, Monthly consolidation lead | reports mix currencies or units, or a month is missing |
| E05-UC01 | 字典与标准维护人、Captain 代理 | 导入或研判需要知道每一列在字典里代表什么 | Dictionary and standards steward, Captain agent | import or review needs the declared meaning of each column |
| E05-UC02 | Captain 代理、月度汇总负责人 | 有未知列需要匹配，但不能把单元格内容交给模型 | Captain agent, Monthly consolidation lead | unknown columns need matching without exposing cell values to the model |
| E05-UC03 | 月度汇总负责人、审批人 | 上传件列名与字典不一致，需要提议匹配并由人审批 | Monthly consolidation lead, Approver | uploaded column names differ from the dictionary and a match must be proposed and approved |
| E05-UC04 | 字典与标准维护人、审批人 | 不同部门用不同写法指同一实体，或实体之间有业务关系 | Dictionary and standards steward, Approver | departments name the same entity differently or entities are related |
| E05-UC05 | 月度汇总负责人、字典与标准维护人 | 下个月再导入时，希望复用已批准的匹配，且依据变化时失效 | Monthly consolidation lead, Dictionary and standards steward | next month's import should reuse approved matches and invalidate them when evidence changes |
| E05-UC06 | 字典与标准维护人、部门负责人 | 会议上口头约定了字段规则，需要作为有来源的规则上下文登记 | Dictionary and standards steward, Department owner | field rules agreed verbally in a meeting must be registered with their source |
| E06-UC01 | 月度汇总负责人 | 部门按日或按周填报，需要归并到月份口径 | Monthly consolidation lead | departments report daily or weekly and figures must roll up to the month |
| E06-UC02 | 月度汇总负责人 | 四部门批次就绪，需要生成业务方设计的跨部门总表 | Monthly consolidation lead | a four-department batch is ready and the business-designed master table must be built |
| E06-UC03 | 月度汇总负责人、部门负责人 | 总表生成后，需要核对部门填写值与字典公式、跨部门数字是否一致 | Monthly consolidation lead, Department owner | the master must check department values against formulas and across departments |
| E06-UC04 | 月度汇总负责人、管理层决策者 | 有人质疑总表里的某个数字 | Monthly consolidation lead, Management decision-maker | someone questions a number in the master table |
| E06-UC05 | 月度汇总负责人 | 总表需要交给不使用本系统的人 | Monthly consolidation lead | the master must be handed to people outside the system |
| E06-UC06 | 管理层决策者、月度汇总负责人 | 季度或年度经营会需要汇总表和正式报告 | Management decision-maker, Monthly consolidation lead | a quarterly or annual meeting needs consolidated tables and a formal report |
| E07-UC01 | Captain 代理、月度汇总负责人 | 研判开始前，需要知道有哪些声明指标并确定性算出 | Captain agent, Monthly consolidation lead | before review, declared metrics must be listed and computed deterministically |
| E07-UC02 | 部门研判子代理、月度汇总负责人 | 研判或人工核对需要某个指标的值及其来源 | Department review subagent, Monthly consolidation lead | review or a person needs a metric value with its sources |
| E07-UC03 | 月度汇总负责人、Captain 代理 | 批次就绪，汇总负责人发起四部门研判 | Monthly consolidation lead, Captain agent | the batch is ready and the consolidation lead starts the four-department review |
| E07-UC04 | Captain 代理、部门负责人 | 部门子代理提交结论，需要校验数值、证据与职责边界 | Captain agent, Department owner | a department subagent submits findings that must be validated |
| E07-UC05 | 月度汇总负责人、Captain 代理 | 研判中途超时、失败或服务重启 | Monthly consolidation lead, Captain agent | a review times out, fails partway or the service restarts |
| E07-UC06 | 月度汇总负责人、独立评测人 | 研判结束，需要保存报告、用量与轨迹供复查 | Monthly consolidation lead, Independent evaluator | a finished review must retain its report, usage and trace |
| E07-UC07 | 部门负责人、审批人 | 报告里有需关注项，需要指派、处置并审批关闭 | Department owner, Approver | a report contains attention items to assign, handle and close with approval |
| E08-UC01 | 报价负责人 | 收到询价，需要知道报价要哪些输入、各由谁提供 | Quotation owner | an inquiry arrives and the owner needs the required inputs and who supplies them |
| E08-UC02 | 报价负责人、Captain 代理 | 输入齐备，需要按声明政策算出内部报价草稿 | Quotation owner, Captain agent | inputs are complete and an internal draft must be computed from the declared policy |
| E08-UC03 | 报价负责人、Captain 代理 | 输入还在客户合同、会话记录等原件里 | Quotation owner, Captain agent | inputs are still inside customer contracts or conversation records |
| E08-UC04 | 报价负责人、审批人 | 需要比较价格、账期、交期等方案并批准对外版本 | Quotation owner, Approver | price, terms and delivery scenarios must be compared and one approved for release |
| E08-UC05 | 报价负责人、Captain 代理 | 草稿完成后，有人或代理试图直接外发 | Quotation owner, Captain agent | after drafting, a person or agent attempts to send it externally |
| E09-UC01 | 审批人、Captain 代理 | 代理要执行写入或跨边界操作 | Approver, Captain agent | an agent attempts a write or boundary-crossing action |
| E09-UC02 | 审批人、Captain 代理 | 审批人拒绝了一次操作并给出理由 | Approver, Captain agent | an approver rejects an action with a reason |
| E09-UC03 | Captain 代理、平台运维管理员 | 模型输入或工具参数中出现指令式文本或超界数据 | Captain agent, Platform operator | instruction-shaped text or over-bounded data appears in model input or tool arguments |
| E09-UC04 | 部门填报员、平台运维管理员 | 员工通过飞书身份登录门户并打开应用 | Department contributor, Platform operator | an employee signs in through Feishu and opens the application |
| E09-UC05 | 部门负责人、平台运维管理员 | 员工只应看到本部门有权查看的批次 | Department owner, Platform operator | an employee must see only batches their department may view |
| E09-UC06 | 审批人、平台运维管理员 | 需要限定谁能批准哪类操作，并留下个人审计记录 | Approver, Platform operator | who may approve which action must be restricted and individually audited |
| E10-UC01 | 月度汇总负责人 | 汇总负责人在同一页面上看来源、与 captain 对话、查看产物 | Monthly consolidation lead | the consolidation lead works with sources, chat and artifacts on one page |
| E10-UC02 | 月度汇总负责人 | 工作需要分多次完成，离开后要回到原处 | Monthly consolidation lead | work spans sessions and must resume where it stopped |
| E10-UC03 | 月度汇总负责人、管理层决策者 | 第一次试用或演示，还没有自己的数据 | Monthly consolidation lead, Management decision-maker | a first trial or demo happens before real data exists |
| E10-UC04 | 部门填报员、月度汇总负责人 | 新用户第一次打开工作面，不知道从哪开始 | Department contributor, Monthly consolidation lead | a new user opens the workspace for the first time |
| E10-UC05 | 部门填报员、管理层决策者 | 用户使用英文界面、深色主题、手机窄屏或只用键盘 | Department contributor, Management decision-maker | a user needs English UI, dark theme, a narrow screen or keyboard-only use |
| E10-UC06 | 部门填报员、月度汇总负责人 | 页面加载失败，或用户粘贴了系统不支持的图片 | Department contributor, Monthly consolidation lead | a page fails to load or an unsupported image is pasted |
| E11-UC01 | 平台运维管理员 | 部署或本机启动服务 | Platform operator | the service is started locally or on a server |
| E11-UC02 | 平台运维管理员 | 升级后旧会话打不开，或会话需要长期保留 | Platform operator | old sessions fail to open after an upgrade or must be retained |
| E11-UC03 | 独立评测人、平台运维管理员 | 版本冻结或提交前需要证明质量与安全 | Independent evaluator, Platform operator | a version freeze or submission requires evidence of quality and safety |
| E11-UC04 | 平台运维管理员 | 代码合并到主干，需要自动检查并部署 | Platform operator | code merges to main and must be checked and deployed |
| E11-UC05 | 平台运维管理员 | 生产环境出现异常，需要发现、处置与升级 | Platform operator | production misbehaves and must be detected, handled and escalated |
| E12-UC01 | 字典与标准维护人 | 企业制度、手册或录音需要成为可检索的知识 | Dictionary and standards steward | policies, manuals or recordings must become searchable knowledge |
| E12-UC02 | 字典与标准维护人、平台运维管理员 | 知识资料更新，需要保留版本并重建索引 | Dictionary and standards steward, Platform operator | knowledge materials change and versions and indexes must be maintained |
| E12-UC03 | 部门填报员、Captain 代理 | 员工提问，需要在其权限内引用资料回答 | Department contributor, Captain agent | an employee asks a question answered only from authorized, cited materials |
| E13-UC01 | 管理层决策者、月度汇总负责人 | 月度研判完成，管理层需要一页看懂本月结论与要做的决定 | Management decision-maker, Monthly consolidation lead | the monthly review is done and management needs one page with the conclusions and decisions |
| E13-UC02 | 月度汇总负责人、管理层决策者 | 本月结论需要与上月、去年同期或计划对比才有意义 | Monthly consolidation lead, Management decision-maker | this month's figures only mean something against last month, last year or plan |
| E13-UC03 | 管理层决策者、月度汇总负责人 | 表格里的数字难以一眼看出趋势、差异和异常 | Management decision-maker, Monthly consolidation lead | tables of numbers do not show trends, variances or outliers at a glance |
| E13-UC04 | 月度汇总负责人、管理层决策者 | 经营会、审计或存档需要一份格式规范、可离线阅读的月度报告 | Monthly consolidation lead, Management decision-maker | a management meeting, audit or archive needs a properly formatted offline monthly report |
| E13-UC05 | 字典与标准维护人、部门负责人、审批人 | 系统按通用做法补了口径，业务方要逐条确认或替换 | Dictionary and standards steward, Department owner, Approver | conventions filled in by best practice must be confirmed or replaced by the business |
| E13-UC06 | 管理层决策者、部门负责人 | 读者需要知道一个结论有多可靠：依据来自原件、公式、口径假设还是模型判断 | Management decision-maker, Department owner | a reader needs to know how reliable a conclusion is and what it rests on |
| E14-UC01 | 月度汇总负责人 | 进入新月份，汇总负责人需要知道对账走到哪一步、还差谁什么 | Monthly consolidation lead | a new month starts and the consolidation lead needs progress and who still owes what |
| E14-UC02 | 部门填报员、字典与标准维护人 | 部门员工每月要填同一张模板，且部分字段可沿用上月 | Department contributor, Dictionary and standards steward | staff fill the same template monthly and some fields carry over from last month |
| E14-UC03 | 部门填报员 | 员工提交前想先知道文件能不能被系统接受 | Department contributor | a staff member wants to know before submitting whether the file will be accepted |
| E14-UC04 | 月度汇总负责人、部门填报员 | 批次导入后只有一个部门的文件需要更正 | Monthly consolidation lead, Department contributor | after import only one department's file needs correcting |
| E14-UC05 | 部门负责人、月度汇总负责人 | 待确认事项分散在总表、隔离行、列匹配和填报草稿里，没人知道自己该处理什么 | Department owner, Monthly consolidation lead | open items are scattered across modules and nobody knows what is theirs |
| E14-UC06 | 月度汇总负责人、外部系统（飞书、目标 API） | 部门文件都放在一个飞书文件夹里，逐个选择太慢 | Monthly consolidation lead, External system (Feishu, target API) | department files sit in one Feishu folder and picking them one by one is slow |

## 4 非功能需求 / Quality attributes

数值上限取自现行代码；「目标」一列尚未实测的，一律标「待实测」，实测结果只记在 [docs/00](../00-status.md)。

Limits come from current code. Targets not yet measured are marked as such; measurements belong only in docs/00.

| ID | 属性 / Attribute | 要求 / Requirement | 依据或度量 / Basis or measure |
| --- | --- | --- | --- |
| NFR01 | 数据规模 / Volume | 单批次最多 200,000 行；单次上传 25 MiB；XLSX 解压后 100 MiB / 200,000 rows per batch; 25 MiB upload; 100 MiB expanded workbook | `config.py`、`batches.py` 的现行上限 / current limits |
| NFR02 | 模型上下文 / Model context | 任何代理不接收原始行；工具返回为计数、公式与封顶样本，分页每页不超过 100 条 / no raw rows to any agent; bounded returns; pages ≤ 100 items | CLAUDE.md 硬约束；每个新工具评审时回答「20 万行时返回多大」 |
| NFR03 | 响应时间 / Latency | 导入四部门文件并生成主表、打开跨部门总表、生成一页结论：目标待实测，实测后写入 docs/00 / import and master build, master view, one-page brief: targets to be measured | 按冻结版本、固定样例、同一机器计时 |
| NFR04 | 研判时限 / Review deadline | 四部门研判有统一期限（现行 180 秒），超时后迟到结果不得覆盖终态 / one review deadline (currently 180 s); late results cannot overwrite a terminal state | `review-batch.ts` 的 `REVIEW_DEADLINE_MS` |
| NFR05 | 可靠性 / Reliability | 所有写入幂等；服务重启后在途研判收尾、批次与笔记本可恢复 / idempotent writes; in-flight reviews closed and state recoverable after restart | E07-UC05、E10-UC02 的行为测试 |
| NFR06 | 可追溯性 / Traceability | 展示给人的每个数字都能回到原件单元格或公式输入 / every displayed number traces to an original cell or formula inputs | E06-UC04；E13-UC06 |
| NFR07 | 安全 / Security | 写入需一次性审批回执；引导变量与凭据只来自启动 shell；拒绝时失败关闭 / one-use approval receipts; credentials only from the launching shell; fail closed | E09 |
| NFR08 | 隐私 / Privacy | 真实原件不因目标含图片等理由发往外部模型；留出集不给开发 / originals are not sent to external models by default; held-out data never reaches development | docs/27；E02-UC09 |
| NFR09 | 可用性 / Usability | 中英双语、深浅主题、760 px 窄屏、全键盘操作、尊重「减少动态效果」 / bilingual, themed, 760 px layouts, keyboard operation, reduced motion | E10-UC05 |
| NFR10 | 成本 / Cost | 导入、规则计算、总表与结论页不调用模型；付费运行有请求数与 token 上限 / import, rules, master and brief are model-free; billed runs have request and token caps | docs/28 |

## 5 结论呈现规范 / Presentation standards for conclusions

适用于界面、导出文件与模型叙述。目的：同一个数字在任何地方读起来都一样，读者一眼能分清事实、推断与待确认。

Applies to the UI, exports and model narration, so the same number reads the same everywhere and readers can separate fact, inference and open questions.

### 5.1 数字与单位 / Numbers and units

| 类型 / Kind | 规则 / Rule | 示例 / Example |
| --- | --- | --- |
| 金额 / Amount | 千分位；保留 2 位小数；万元以上的摘要可用「万元」并保留 2 位；注明含税或不含税 / thousands separators, 2 decimals, state tax basis | 5,240,640.00 元（含税）；524.06 万元 |
| 方量与数量 / Quantity | 按业务精度（商砼方量 1 位）；单位必写 / business precision, unit always shown | 5,600.0 方 |
| 比率 / Ratio | 百分比 1–2 位；同一张表统一位数；分母为 0 时显示「无法计算」，不显示 0% / 1–2 decimals, consistent per table, “not computable” on zero denominators | 85.26% |
| 变化 / Change | 同时给绝对变化与相对变化，并标明比较基期 / absolute and relative change with the base period | +320.0 方（+6.1%，较 2024-06） |
| 期间 / Period | `YYYY-MM`；跨期对比写清两个期间 / `YYYY-MM`; name both periods in comparisons | 2024-07 对 2024-06 |

### 5.2 状态用词 / Status vocabulary

| 界面用词 / Label | 含义 / Meaning | 不得表述为 / Never shown as |
| --- | --- | --- |
| 正常 / OK | 声明检查通过 / declared check passed | 「无风险」 / no risk |
| 需关注 / Attention | 触及声明阈值 / declared threshold reached | 「违规」「坏账」 / violation, bad debt |
| 部分完成 / Partial | 有部门或检查未完成 / a department or check is incomplete | 「已完成」 / complete |
| 待确认 / Open question | 需要人判断的差异或缺项 / a difference or gap requiring a person | 系统替人选定的值 / a value chosen by the system |
| 已拒绝 / Refused | 输入不足或违反声明，不出结果 / insufficient or invalid input, no result | 「0」或空白 / zero or blank |

### 5.3 依据等级 / Evidence grades

每条结论标注依据等级，读者据此决定需要多少复核（E13-UC06）。

Every conclusion carries an evidence grade so readers know how much review it needs (E13-UC06).

| 等级 / Grade | 依据 / Basis | 示例 / Example |
| --- | --- | --- |
| G1 原件 / Source | 直接来自部门原件单元格 / a department's original cell | 生产部实际量 |
| G2 公式 / Formula | 字典写明的公式，由原件计算 / dictionary-stated formula over sources | 签收率 = 实际量 ÷ 出厂量 |
| G3 口径假设 / Convention | 依赖业务方尚未确认的口径 / depends on an unconfirmed convention | 按 13% 增值税折算的毛利 |
| G4 模型判断 / Model judgement | 部门子代理在声明职责内的解释与建议 / a subagent's explanation within its responsibility | 「建议复核低签收车次」 |

结论取其依赖中最弱的等级：用了 G3 的数字，结论至少是 G3。

A conclusion takes the weakest grade among its inputs.

### 5.4 表述规则 / Wording rules

- 先结论、后依据：一句话结论 → 关键数字 → 依据与出处 → 建议动作与负责人。 / Lead with the conclusion, then figures, evidence and the owner of the next action.
- 区分事实、推断与假设，推断必须写「可能」「待核实」。 / Mark inference and assumption explicitly.
- 不作因果断言，除非有声明规则支持；不给出未声明的阈值、评级或预测。 / No causal claims, thresholds, ratings or forecasts without a declaration.
- 各部门 `unsupported_topics` 中的词，即使在否定句中也不出现。 / Terms in a role's unsupported topics never appear, not even negated.
- 颜色只作辅助：状态同时用文字表达，满足色弱可读。 / Colour is never the only carrier of status.

### 5.5 图表规则 / Chart rules

- 每张图回答一个问题，标题写成结论句；坐标轴标单位与期间。 / One question per chart, conclusion as title, units and periods on axes.
- 趋势用折线，构成用堆叠条，差异用瀑布或对比条；不用饼图表达超过 5 类。 / Lines for trends, stacked bars for composition, waterfall for variance.
- 阈值线与数据来自同一声明版本；点击数据点可下钻到 E06-UC04 的出处。 / Threshold lines share the declaration version; points drill down to sources.
- 缺失期间显示为断点，不插值。 / Missing periods show as gaps, never interpolated.

## 6 优先级与验收写法 / Priority and acceptance format

### 6.1 优先级 / Priority (MoSCoW)

| 级别 / Level | 含义 / Meaning |
| --- | --- |
| Must | 没有它，月度对账或结论不可用、不可信 / without it the monthly close or its conclusions are unusable or untrustworthy |
| Should | 明显减少人工或误读，提交前应尽量完成 / clearly reduces effort or misreading; target before submission |
| Could | 体验增强，可在提交后完成 / enhancement, may follow submission |
| Won't (this phase) | 本期不做，保留需求 / retained but not in this phase |

### 6.2 验收条件写法 / Acceptance criteria

新 UC 的验收条件使用 Given / When / Then，每条可以用合成样例或浏览器旅程直接验证；不写「体验良好」「清晰直观」这类不可测描述。

New UCs use Given / When / Then; every criterion is directly testable with a synthetic fixture or browser journey. Unmeasurable phrases such as “good experience” are not acceptance criteria.

```text
AC-n  Given <前置状态 / precondition, including data and version>
      When  <参与者的动作或业务事件 / actor action or business event>
      Then  <可观察结果，含数值、状态、出处或拒绝原因 / observable result with values, status, provenance or refusal>
```

完成定义（DoD）：主流程与每条拒绝路径各有行为测试；界面变更有浏览器旅程；文档状态与实现路径同步更新；真实业务验收单独记录，不以离线结果代替。

Definition of done: behavioral tests for the main flow and each refusal path; a browser journey for UI changes; status and implementation links updated together; real business acceptance recorded separately, never substituted by offline results.
