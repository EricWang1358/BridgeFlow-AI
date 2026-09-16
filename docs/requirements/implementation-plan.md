# 未完成边界的实施顺序 / Implementation order for remaining boundaries

2026-09-16 开始执行；同日按用户要求整理交接并暂停，后续工作留给下一阶段。范围是全项目 UC 中尚未完成的实现、验证及验收边界，包含已经标为 IMPLEMENTED 但正文仍指出的限制；不能只把状态列变绿。下表是依赖顺序，不是已完成清单，不是工期承诺。

Execution began on 2026-09-16 and paused at the user’s request after handoff on the same date; remaining work belongs to the next phase. Scope includes unfinished implementation, verification and acceptance boundaries across all UCs, including limitations inside IMPLEMENTED entries. Changing status labels alone does not close a boundary. This is a dependency order, not a completion list or schedule promise.

| Order | 工作包 / Work package | UC / Boundary | 当前执行 / Current execution |
| --- | --- | --- | --- |
| 1 | 读取权限与请求身份 / Read scope and identity | E09-UC04/05；E04/E06/E02 数据面 | 已补总表预览/下载与工作流浏览器视图的身份和范围检查；JWT 必需字段与 JWKS 失败路径加固；后端完整回归通过，个人操作授权仍在下一包 / backend regression passed; individual operation authorization remains next |
| 2 | 操作角色与个人审批 / Operation roles and individual approval | E09-UC06；E05-UC03；E02-UC07/08 | 已接员工许可、精确请求回执及执行前撤权检查；拒绝审计与原生会话隔离未完 / verified permits and revocation checks implemented; refusal audit and native session isolation remain |
| 3 | 材料清单、候选与规则来源 / Materials, opportunities and rule sources | E01-UC01/02；E05-UC06；E02-UC03 | 已实现来源/候选版本存储与并发保护；已补来源位置及授权分页读取，候选审批写已接，模型结构检索、材料暂存/批准登记已接，材料页与员工离线旅程通过，暂存配额/清理已补，候选逐项编辑/修订已接，图形共创待补，音频/OCR 需处理方式 / domain persistence implemented; scoped reads and locators implemented; candidate approved writes implemented; bounded model reads and staged registration implemented; material UI/journey verified offline; staging quotas/cleanup implemented; structured candidate editing implemented; graphical co-design pending |
| 4 | 图、评分、会议和决策 / Graphs, scores, meetings and decisions | E01-UC03–06 | 结构化图领域已实现；图审批/授权 API 已接；逐项图编辑/可视化已接；评分政策/坐标领域已实现，评分审批/授权 API 已接，评分页面/四象限及员工离线旅程已接；会议草案/纪要版本领域已实现，会议授权 API/原生工具/编辑与详情页面已接，声明投票/条件式批准领域/API/原生工具已接，决策浏览器及顺序双身份离线旅程已接，Agent 2 消费端待接；评分尺度/投票规则必须声明 / graph domain/authorized API/native approval implemented; graph editor/visualization connected; scoring policy/coordinate domain implemented; scoring approval/API/editor/quadrants connected and browser journey verified offline; versioned meeting domain implemented; meeting API/tools/editor/details connected; declared voting/conditional decision domain/API/native tools connected; decision UI/sequential two-identity offline journey verified; Agent 2 consumer pending |
| 5 | 模板治理与试点 / Template governance and pilot | E02-UC01/02/09 | 待版本修订、试点反馈、指标和发布门禁；真实试点是外部验收 / versioned governance and metrics pending, real pilot externally verified |
| 6 | 反馈、支持与复盘 / Feedback, support and review | E03-UC01–05 | 待反馈持久化、分类处置、支持方案、措施复盘及回流；不得自动改职责预算 / pending feedback/action lifecycle without autonomous management changes |
| 7 | 风险与报价业务闭环 / Risk and quotation lifecycle | E07-UC07；E08-UC03/04 | 待风险处置状态机、报价方案比较和精确版本审批；实际定价政策及样板外部确认 / pending dispositions, scenario comparison and exact-version approval |
| 8 | 补齐通用数据能力 / Remaining data capabilities | E04-UC08；E06-UC06；FR07/08 生命周期细节 | 待明确换算、补齐、实体有效期和分摊策略后实现；季年汇总/PDF 不从 XLSX 推定完成 / implement declared FX/completion/validity/allocation and separate quarter/year/PDF paths |
| 9 | 真实目标及运维 / Live targets and operations | E02-UC05/06/10；E11-UC04/05 | 可先实现配置与适配器契约，真实入库、通知、飞书及部署需提供凭据和路由 / adapters can be local; live verification requires credentials and routes |
| 9a | 结论可信与可读 / Trustworthy, readable conclusions | E13-UC05/06 → E13-UC01/02 → E13-UC03/04 | 第一轮（2026-09-17）已实现 E13-UC06 依据等级与 E13-UC01 一页结论的主流程，其余设计未实现；口径确认需业务方参与，其余可离线实现 / designed, not implemented; convention confirmation needs business participation |
| 9b | 月度流程便民 / Monthly convenience | E14-UC03 → UC04 → UC01 → UC05 → UC02 → UC06 | 第一轮（2026-09-17）E14-UC03 离线实现完成，其余设计未实现；UC06 真实验收依赖飞书凭据 / designed, not implemented; UC06 acceptance needs Feishu credentials |
| 10 | 历史知识范围与全旅程验收 / Historical knowledge scope and final acceptance | E12；E10；所有 UC / all UCs | 知识库曾明确排除；需确认与当前产品的启用边界、资料授权及保留策略；其余能力完成后做连续浏览器旅程和真实模型验收 / resolve historical scope and data policy, then verify complete journeys |

## 真正的外部输入 / Actual external inputs

下列是不能伪造的业务事实，等待期间继续做不依赖它们的工程实现。缺项不自动让整个工作包变成“已完成”。

These are external facts that cannot be fabricated. Continue independent engineering while waiting; their absence never turns an entire work package into completed work.

| Input | Needed for | 交付与验收 / Handoff and acceptance |
| --- | --- | --- |
| 脱敏原件与人工标准、2 组调优和独立留出 / Originals, standards and split datasets | E02-UC03/09、E08-UC03 | 业务方提供来源/脱敏说明；留出交独立评测人，不给开发预览 / source/de-identification notes, independently held-out evaluation |
| 评分尺度、投票、模板发布、风险及定价政策 / Decision and business policies | E01/E02/E07/E08 | 配置或有来源的批准记录，含生效版本与责任角色 / versioned configuration or sourced approval |
| 目标 API、飞书测试空间、通知路由 / Target API, Feishu and notification routes | E02-UC05/06/10 | 在 shell/密钥管理中配置；提供受限测试目标及可核对回执 / secret-managed configuration and verifiable test receipts |
| 真实员工支持角色及试点参与 / Support roles and pilot participation | E02-UC02、E03 | 一线和下游参与，真实基线与后测记录 / frontline/downstream participation and before/after evidence |
| 部署域名/SSH、真实模型预算 / Deployment configuration and live-model budget | E11-UC04、最终验收 / final acceptance | 采用现有预检与预算停止条件；不得凭离线结果代签 / use existing preflight and spend limits |
| 知识资料授权、保留删除和处理方式 / Knowledge permissions and retention | E12 | 明确重启历史范围后再接真实资料；不因原 issue CLOSED 声称实现 / define reactivation before ingesting real knowledge |

## 本轮读取权限契约 / Read authorization contract added this turn

启用门户后：总表与 XLSX 使用与批次相同的可见性；工作流使用 ACL 中独立的 `workflow_departments`，值必须为 catalogue 中的准确部门名称。未声明则空集，不自动把 `production` 翻译成“生产部”。目录隐藏无权限模板、阶段、血缘；跨部门阶段必须能查看该阶段及全部输入输出模板；看板、草稿、落地信号同步过滤。无权限对象返回 404，不透露是否存在。

With the portal enabled, master/XLSX reads use batch visibility. Workflow reads require explicit `workflow_departments` matching exact catalogue labels, defaulting to no grants. There is no inferred translation from fixed import department IDs. Filter templates, stages, lineage, board rows, drafts and adoption signals. A cross-department stage requires scope for the stage and all input/output templates. Invisible objects return 404.

模型读取仍使用可信主机权限。批准写入已接个人许可与原生审批，上传/备注有独立操作权限；拒绝审计与原生会话隔离尚未解决，不能宣称完整员工级授权。门户关闭时保留本地演示模式。

Model reads retain trusted-host authority. Approved mutations now require individual permits and native approval; uploads/notes have explicit grants. Refusal audit and native session isolation remain incomplete. Portal-disabled local mode remains supported.
