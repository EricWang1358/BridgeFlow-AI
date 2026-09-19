# 全项目需求追溯 / Project requirement traceability

核对日期 / Reviewed: 2026-09-16；E13/E14 于 2026-09-17 补入。 来源为 PRD、当前代码和测试、GitHub issue 正文及关键关闭评论。该矩阵是索引，不额外定义 UC。

Sources: PRD, current code/tests, issue bodies and material closure comments. This matrix is an index and adds no UCs.

## PRD FR01–26

| FR | 需求 / Requirement | UC |
| --- | --- | --- |
| FR01 | 多文件批次 / Multi-file batches | [E04-UC01](04-intake-quality.md) |
| FR02 | 质量问题识别 / Quality detection | [E04-UC02](04-intake-quality.md), [E04-UC03](04-intake-quality.md), [E04-UC04](04-intake-quality.md) |
| FR03 | 修复建议与人工处置 / Repairs and human disposition | [E04-UC05](04-intake-quality.md), [E04-UC06](04-intake-quality.md) |
| FR04 | 关键字段不自动补全 / No critical-field fabrication | [E04-UC03](04-intake-quality.md), [E02-UC04](02-standardization.md) |
| FR05 | 换算和缺月补齐 / Conversion and missing months | [E04-UC08](04-intake-quality.md) |
| FR06 | 原件与差异 / Originals and corrections | [E04-UC05](04-intake-quality.md), [E04-UC07](04-intake-quality.md) |
| FR07 | 统一实体目录 / Entity catalogue | [E05-UC01](05-mapping.md), [E05-UC04](05-mapping.md) |
| FR08 | 多对多映射 / Many-to-many mapping | [E05-UC04](05-mapping.md), [E05-UC05](05-mapping.md) |
| FR09 | 时间粒度 / Time grain | [E06-UC01](06-master-integration.md) |
| FR10 | 候选与人工确认 / Candidates and review | [E05-UC03](05-mapping.md), [E05-UC04](05-mapping.md) |
| FR11 | 版本与冻结结果 / Versioned frozen results | [E04-UC01](04-intake-quality.md), [E05-UC05](05-mapping.md) |
| FR12 | 生产视角 / Production review | [E07-UC01](07-review.md), [E07-UC03](07-review.md), [E07-UC04](07-review.md) |
| FR13 | 财务视角 / Finance review | [E07-UC01](07-review.md), [E07-UC03](07-review.md), [E07-UC04](07-review.md) |
| FR14 | 物资视角 / Procurement review | [E07-UC01](07-review.md), [E07-UC03](07-review.md), [E07-UC04](07-review.md) |
| FR15 | 市场视角 / Marketing review | [E07-UC01](07-review.md), [E07-UC03](07-review.md), [E07-UC04](07-review.md) |
| FR16 | 预警证据与阈值 / Finding evidence and thresholds | [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| FR17 | 风险状态 / Risk lifecycle | [E07-UC07](07-review.md) |
| FR18 | 月季年总表 / Month-quarter-year masters | [E06-UC01](06-master-integration.md), [E06-UC02](06-master-integration.md), [E06-UC06](06-master-integration.md) |
| FR19 | 权限视图及下钻 / Scoped views and drilldown | [E06-UC04](06-master-integration.md), [E09-UC05](09-security-approval.md) |
| FR20 | 报告与审批卡 / Reports and approval cards | [E07-UC06](07-review.md), [E07-UC07](07-review.md), [E09-UC01](09-security-approval.md) |
| FR21 | XLSX/PDF 导出 / XLSX/PDF export | [E06-UC05](06-master-integration.md), [E06-UC06](06-master-integration.md) |
| FR22 | 报价草稿 / Quote drafts | [E08-UC01](08-quotation.md), [E08-UC02](08-quotation.md), [E08-UC03](08-quotation.md) |
| FR23 | 多组合试算 / Scenario computation | [E08-UC02](08-quotation.md), [E08-UC04](08-quotation.md) |
| FR24 | 区间与依据 / Price bands and evidence | [E08-UC02](08-quotation.md) |
| FR25 | 比较与签发 / Comparison and release | [E08-UC04](08-quotation.md) |
| FR26 | 禁止自动外发 / No automatic sending | [E08-UC05](08-quotation.md) |

原始 FR 范围可能大于当前 UC 的已交付部分：FR05 换算/补齐、FR17 风险状态、FR18 季年、FR21 PDF、FR25 签发仍有缺口。实体有效期、关系分摊比例及通用治理生命周期也不能从“已有映射”推定完成。FR03 的逐项建议不等于已经支持全部批量修复交互。详细状态与限制见对应 epic。

An original FR can exceed a delivered UC slice: currency/completion, risk lifecycle, quarter/year masters, PDF and quote release still have gaps. Entity validity periods, allocation ratios and full governance cannot be inferred from existing mappings. Individual repair support does not imply all bulk repair interactions.

## GitHub issue 全量映射 / Complete issue mapping

OPEN/CLOSED 是 GitHub 状态，不是实现状态；实现状态以 UC 正文和代码证据为准。表格覆盖本轮 `gh issue list --state all --limit 300` 返回的全部 issue（不含 PR）。

OPEN/CLOSED is tracker state, not delivery state. Use UC details and implementation evidence. This table covers every issue returned by the audit query, excluding pull requests.

| Issue | GitHub | 标题 / Title | UC |
| --- | --- | --- | --- |

| [#1](https://github.com/EricWang1358/BridgeFlow-AI/issues/1) | CLOSED | M1: Sanitizer — LLM fallback for values rules can't fix | [E04-UC03](04-intake-quality.md) |
| [#2](https://github.com/EricWang1358/BridgeFlow-AI/issues/2) | CLOSED | M1: Author a harder set of messy sample spreadsheets | [E11-UC03](11-operations-evaluation.md) |
| [#3](https://github.com/EricWang1358/BridgeFlow-AI/issues/3) | CLOSED | M2: Resolver — persist confirmed mappings across periods | [E05-UC05](05-mapping.md) |
| [#4](https://github.com/EricWang1358/BridgeFlow-AI/issues/4) | CLOSED | M2: Resolver — batch adjudication into one call per relation type | [E05-UC04](05-mapping.md), [E07-UC03](07-review.md) |
| [#5](https://github.com/EricWang1358/BridgeFlow-AI/issues/5) | CLOSED | M3: Evaluator — enforce that evidence cites real Master Table rows | [E07-UC01](07-review.md), [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| [#6](https://github.com/EricWang1358/BridgeFlow-AI/issues/6) | CLOSED | M3: Evaluator — sharpen tension detection | [E07-UC01](07-review.md), [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| [#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7) | OPEN | Quotation: compute every price band from declared costs and policies | [E08-UC01](08-quotation.md), [E08-UC02](08-quotation.md), [E08-UC03](08-quotation.md), [E08-UC04](08-quotation.md) |
| [#8](https://github.com/EricWang1358/BridgeFlow-AI/issues/8) | CLOSED | M4: Expose per-agent endpoints for deepseek-harness plugins | [E07-UC02](07-review.md), [E09-UC03](09-security-approval.md) |
| [#9](https://github.com/EricWang1358/BridgeFlow-AI/issues/9) | CLOSED | Spike: evaluate deepseek-harness before committing to it | [E11-UC01](11-operations-evaluation.md) |
| [#10](https://github.com/EricWang1358/BridgeFlow-AI/issues/10) | CLOSED | CD: deploy to AWS on push to main | [E11-UC04](11-operations-evaluation.md) |
| [#11](https://github.com/EricWang1358/BridgeFlow-AI/issues/11) | CLOSED | M5: Frontend — build the three demo screens | [E10-UC01](10-workspace.md), [E10-UC02](10-workspace.md), [E06-UC04](06-master-integration.md), [E08-UC04](08-quotation.md) |
| [#12](https://github.com/EricWang1358/BridgeFlow-AI/issues/12) | CLOSED | M0: Replace the in-memory result store | [E04-UC01](04-intake-quality.md) |
| [#13](https://github.com/EricWang1358/BridgeFlow-AI/issues/13) | CLOSED | 架构: 研判层改为「规则算数、模型解释」 | [E07-UC01](07-review.md), [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| [#14](https://github.com/EricWang1358/BridgeFlow-AI/issues/14) | CLOSED | 地基: 补齐 schema 的可追溯字段 | [E04-UC05](04-intake-quality.md), [E06-UC04](06-master-integration.md) |
| [#15](https://github.com/EricWang1358/BridgeFlow-AI/issues/15) | CLOSED | FR 01/11: 引入导入批次与结果版本 | [E04-UC01](04-intake-quality.md) |
| [#16](https://github.com/EricWang1358/BridgeFlow-AI/issues/16) | CLOSED | FR 02: 补齐列错位、重复行、字段名拼写差异的识别 | [E04-UC03](04-intake-quality.md) |
| [#17](https://github.com/EricWang1358/BridgeFlow-AI/issues/17) | CLOSED | FR 05: 币种与单位归一，以及按月补齐时间序列 | [E04-UC08](04-intake-quality.md) |
| [#18](https://github.com/EricWang1358/BridgeFlow-AI/issues/18) | CLOSED | FR 09: 日周月粒度统一到月度，保留原始粒度 | [E06-UC01](06-master-integration.md) |
| [#19](https://github.com/EricWang1358/BridgeFlow-AI/issues/19) | OPEN | Risk decisions: define business-owned disposition and approval states | [E07-UC07](07-review.md) |
| [#20](https://github.com/EricWang1358/BridgeFlow-AI/issues/20) | OPEN | Quotation: compare declared scenarios and require approval before release | [E08-UC04](08-quotation.md), [E08-UC05](08-quotation.md) |
| [#21](https://github.com/EricWang1358/BridgeFlow-AI/issues/21) | CLOSED | PRD 第十一章: 权限、角色与审计日志 | [E09-UC01](09-security-approval.md), [E09-UC04](09-security-approval.md), [E09-UC06](09-security-approval.md) |
| [#22](https://github.com/EricWang1358/BridgeFlow-AI/issues/22) | CLOSED | FR 21: 导出 XLSX 与 PDF | [E06-UC05](06-master-integration.md), [E06-UC06](06-master-integration.md) |
| [#23](https://github.com/EricWang1358/BridgeFlow-AI/issues/23) | OPEN | Business inputs: confirm templates, policies and quotation ownership | [E02-UC09](02-standardization.md), [E08-UC01](08-quotation.md), [E08-UC03](08-quotation.md) |
| [#24](https://github.com/EricWang1358/BridgeFlow-AI/issues/24) | CLOSED | 严重: 语义对齐产出 0 条映射——字符串相似度无法跨部门匹配 | [E05-UC04](05-mapping.md), [E07-UC03](07-review.md) |
| [#25](https://github.com/EricWang1358/BridgeFlow-AI/issues/25) | CLOSED | 架构: 裁决类调用不该经过 dsh agent 循环（现象是 739 秒 / 52 倍 token） | [E05-UC04](05-mapping.md), [E07-UC03](07-review.md) |
| [#26](https://github.com/EricWang1358/BridgeFlow-AI/issues/26) | CLOSED | 🔴 注入防御: 建立输入信任边界 | [E09-UC03](09-security-approval.md) |
| [#27](https://github.com/EricWang1358/BridgeFlow-AI/issues/27) | CLOSED | 🔴 把数据操作暴露为 typed tools | [E07-UC02](07-review.md), [E09-UC03](09-security-approval.md) |
| [#28](https://github.com/EricWang1358/BridgeFlow-AI/issues/28) | CLOSED | 🔴 eval 套件: golden-path + adversarial | [E11-UC03](11-operations-evaluation.md) |
| [#29](https://github.com/EricWang1358/BridgeFlow-AI/issues/29) | CLOSED | 🟡 跨月映射记忆: 确认一次，下月复用 | [E05-UC05](05-mapping.md) |
| [#30](https://github.com/EricWang1358/BridgeFlow-AI/issues/30) | CLOSED | 🟡 人工确认动作: 让 escalation checkpoint 看得见 | [E09-UC01](09-security-approval.md) |
| [#31](https://github.com/EricWang1358/BridgeFlow-AI/issues/31) | CLOSED | Trace native review decisions and complete failure-state attribution | [E07-UC06](07-review.md) |
| [#32](https://github.com/EricWang1358/BridgeFlow-AI/issues/32) | CLOSED | 🔴 字段字典是唯一事实来源，代码不得绕过（字段名不进 Python） | [E05-UC01](05-mapping.md) |
| [#33](https://github.com/EricWang1358/BridgeFlow-AI/issues/33) | CLOSED | dsh 结构化输出: 模型回 JSON Schema 外壳，_parse 不剥 | [E07-UC04](07-review.md) |
| [#37](https://github.com/EricWang1358/BridgeFlow-AI/issues/37) | CLOSED | 🔴 least-privilege: 做一个没有 bash 的 dsh profile | [E09-UC03](09-security-approval.md) |
| [#38](https://github.com/EricWang1358/BridgeFlow-AI/issues/38) | CLOSED | Native review fan-out: finish in-flight recovery and end-to-end deadlines | [E07-UC03](07-review.md), [E07-UC05](07-review.md) |
| [#39](https://github.com/EricWang1358/BridgeFlow-AI/issues/39) | CLOSED | 🔴 审批机制: ctx.approval fail-closed + 审计事件对 | [E09-UC01](09-security-approval.md) |
| [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40) | OPEN | Native notebook UI: complete quotation artifacts and functional journeys | [E10-UC01](10-workspace.md), [E10-UC02](10-workspace.md), [E06-UC04](06-master-integration.md), [E08-UC04](08-quotation.md) |
| [#41](https://github.com/EricWang1358/BridgeFlow-AI/issues/41) | OPEN | Business demo: complete continuous rehearsal and owner acceptance | [E10-UC03](10-workspace.md), [E10-UC04](10-workspace.md), [E11-UC03](11-operations-evaluation.md), [E02-UC09](02-standardization.md) |
| [#42](https://github.com/EricWang1358/BridgeFlow-AI/issues/42) | CLOSED | ⛰️ 前置 Spike: 读完六份 dsh 官方文档，把结论写回 docs/13 | [E11-UC01](11-operations-evaluation.md) |
| [#44](https://github.com/EricWang1358/BridgeFlow-AI/issues/44) | CLOSED | 🔴 缺陷: 猜不到主键就拿第一列 join，静默出错 | [E05-UC01](05-mapping.md) |
| [#45](https://github.com/EricWang1358/BridgeFlow-AI/issues/45) | CLOSED | 🟡 EntityKind 与关系表改成字典驱动的开放集合 | [E05-UC01](05-mapping.md) |
| [#46](https://github.com/EricWang1358/BridgeFlow-AI/issues/46) | CLOSED | Field mapping wizard: match uploads to a human-authored dictionary | [E05-UC02](05-mapping.md), [E05-UC03](05-mapping.md) |
| [#47](https://github.com/EricWang1358/BridgeFlow-AI/issues/47) | CLOSED | Support confirmed spreadsheet structures without guessing file layouts | [E04-UC02](04-intake-quality.md) |
| [#51](https://github.com/EricWang1358/BridgeFlow-AI/issues/51) | CLOSED | 🔴 缺陷: 四角色的 asyncio.gather 是假并发，被 DshProvider 的锁串行化 | [E05-UC04](05-mapping.md), [E07-UC03](07-review.md) |
| [#55](https://github.com/EricWang1358/BridgeFlow-AI/issues/55) | CLOSED | 🟡 复核建议(#42): dsh 事实应固化成测试，不只是文档散文 | [E11-UC01](11-operations-evaluation.md) |
| [#58](https://github.com/EricWang1358/BridgeFlow-AI/issues/58) | CLOSED | 🔴 不变量: 任何代理都不得把原始数据行读进上下文（含工具返回值） | [E09-UC03](09-security-approval.md) |
| [#59](https://github.com/EricWang1358/BridgeFlow-AI/issues/59) | CLOSED | 🔴 三套行业数据集 + 开发集/验收集分离（含投毒变体与 ground truth） | [E11-UC03](11-operations-evaluation.md) |
| [#61](https://github.com/EricWang1358/BridgeFlow-AI/issues/61) | CLOSED | Guide unjoinable uploads into approved field matching | [E05-UC02](05-mapping.md), [E05-UC03](05-mapping.md) |
| [#63](https://github.com/EricWang1358/BridgeFlow-AI/issues/63) | CLOSED | 🟡 复核建议(#14): 可追溯字段存在但不强制，演示当天很可能全是空的 | [E04-UC05](04-intake-quality.md), [E06-UC04](06-master-integration.md) |
| [#65](https://github.com/EricWang1358/BridgeFlow-AI/issues/65) | CLOSED | 🔴 复核建议(#13): 规则算数有了骨架，但算不出 demo 要讲的四句话 | [E07-UC01](07-review.md), [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| [#67](https://github.com/EricWang1358/BridgeFlow-AI/issues/67) | CLOSED | 🔴 复核建议(#59): 验收集没有任何东西在跑它——建议把 #28 提到第一周 | [E11-UC03](11-operations-evaluation.md) |
| [#69](https://github.com/EricWang1358/BridgeFlow-AI/issues/69) | CLOSED | Validate guard enforcement and adversarial journeys in the native runtime | [E11-UC03](11-operations-evaluation.md) |
| [#72](https://github.com/EricWang1358/BridgeFlow-AI/issues/72) | CLOSED | 🟡 复核建议(#4/#51): lane 的代价没量过；批量裁决把「未裁决」和「低置信」压成了一种状态 | [E05-UC04](05-mapping.md), [E07-UC03](07-review.md) |
| [#75](https://github.com/EricWang1358/BridgeFlow-AI/issues/75) | CLOSED | Confirm business-owned capacity limits and customer-tier policies | [E02-UC09](02-standardization.md), [E08-UC01](08-quotation.md), [E08-UC03](08-quotation.md) |
| [#77](https://github.com/EricWang1358/BridgeFlow-AI/issues/77) | CLOSED | 🔴 复核建议(#16): 验收集的「留出」已用掉一次；quarantine 检测得越多、黑洞越大 | [E04-UC06](04-intake-quality.md) |
| [#79](https://github.com/EricWang1358/BridgeFlow-AI/issues/79) | CLOSED | Date alignment: add declared ambiguity resolution and a safe recovery path | [E04-UC04](04-intake-quality.md) |
| [#82](https://github.com/EricWang1358/BridgeFlow-AI/issues/82) | CLOSED | Mapping memory: distinguish semantic evidence changes from wording changes | [E05-UC05](05-mapping.md) |
| [#84](https://github.com/EricWang1358/BridgeFlow-AI/issues/84) | CLOSED | Approval gate: derive write protection from tool declarations | [E09-UC01](09-security-approval.md) |
| [#86](https://github.com/EricWang1358/BridgeFlow-AI/issues/86) | CLOSED | 拒绝之后模型仍然回 done —— 被拒的写没有回到叙述里 | [E09-UC02](09-security-approval.md), [E10-UC06](10-workspace.md) |
| [#87](https://github.com/EricWang1358/BridgeFlow-AI/issues/87) | CLOSED | Approval: finish decision-note consistency and document identity boundaries | [E09-UC02](09-security-approval.md), [E10-UC06](10-workspace.md) |
| [#88](https://github.com/EricWang1358/BridgeFlow-AI/issues/88) | CLOSED | Quarantine: add audited release and discard without rewriting frozen batches | [E04-UC06](04-intake-quality.md) |
| [#89](https://github.com/EricWang1358/BridgeFlow-AI/issues/89) | CLOSED | evaluator 已经读过指标目录，然后连要 13 个不在目录里的指标（全部 409） | [E07-UC01](07-review.md), [E07-UC02](07-review.md), [E07-UC04](07-review.md) |
| [#92](https://github.com/EricWang1358/BridgeFlow-AI/issues/92) | CLOSED | Keep sales and cost semantics separate in the financial master table | [E06-UC03](06-master-integration.md), [E07-UC01](07-review.md) |
| [#96](https://github.com/EricWang1358/BridgeFlow-AI/issues/96) | CLOSED | Localize approval decision details and finish business-facing UI copy | [E09-UC02](09-security-approval.md), [E10-UC06](10-workspace.md) |
| [#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97) | CLOSED | Fix browser smoke startup and verify native approval interactions | [E11-UC01](11-operations-evaluation.md) |
| [#99](https://github.com/EricWang1358/BridgeFlow-AI/issues/99) | CLOSED | 粘图片报「请切换支持图片的模型」，但模型选择器是我们自己禁掉的 | [E10-UC06](10-workspace.md) |
| [#102](https://github.com/EricWang1358/BridgeFlow-AI/issues/102) | CLOSED | Persist approved field matches and provide actionable refusal recovery | [E05-UC02](05-mapping.md), [E05-UC03](05-mapping.md) |
| [#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104) | OPEN | Quotation: declared drafts delivered; integrate customer samples and approval | [E08-UC01](08-quotation.md), [E08-UC02](08-quotation.md), [E08-UC03](08-quotation.md), [E08-UC04](08-quotation.md) |
| [#110](https://github.com/EricWang1358/BridgeFlow-AI/issues/110) | CLOSED | Default to English and complete Chinese/English UI localization | [E10-UC05](10-workspace.md) |
| [#111](https://github.com/EricWang1358/BridgeFlow-AI/issues/111) | CLOSED | Enforce a host-level guard for partial-review human notes | [E07-UC03](07-review.md), [E07-UC05](07-review.md) |
| [#112](https://github.com/EricWang1358/BridgeFlow-AI/issues/112) | CLOSED | Apply the review deadline across parent, children and finalization | [E07-UC03](07-review.md), [E07-UC05](07-review.md) |
| [#113](https://github.com/EricWang1358/BridgeFlow-AI/issues/113) | CLOSED | Recover or terminate in-flight reviews and make finalization idempotent | [E07-UC03](07-review.md), [E07-UC05](07-review.md) |
| [#119](https://github.com/EricWang1358/BridgeFlow-AI/issues/119) | CLOSED | 参考ERP/ACP系统设计，对比目前实现分析优化之处 | [E01-UC02](01-discovery.md), [E02-UC01](02-standardization.md), [E03-UC05](03-adoption.md) |
| [#120](https://github.com/EricWang1358/BridgeFlow-AI/issues/120) | CLOSED | Agent运维 | [E11-UC05](11-operations-evaluation.md) |
| [#121](https://github.com/EricWang1358/BridgeFlow-AI/issues/121) | CLOSED | [需求评审] 业务规则上下文接入：会议纪要音频与文档作为映射依据 | [E05-UC06](05-mapping.md), [E01-UC01](01-discovery.md) |
| [#122](https://github.com/EricWang1358/BridgeFlow-AI/issues/122) | CLOSED | [需求评审] 基于规则上下文的跨部门字段映射（同义列归并到标准字典） | [E05-UC02](05-mapping.md), [E05-UC03](05-mapping.md) |
| [#123](https://github.com/EricWang1358/BridgeFlow-AI/issues/123) | CLOSED | [需求评审] 字典映射持久化：构成数据中台的一部分 | [E05-UC05](05-mapping.md) |
| [#124](https://github.com/EricWang1358/BridgeFlow-AI/issues/124) | CLOSED | [需求评审] 字典映射的人工审核流程（human-in-the-loop） | [E05-UC02](05-mapping.md), [E05-UC03](05-mapping.md) |
| [#125](https://github.com/EricWang1358/BridgeFlow-AI/issues/125) | OPEN | [需求评审] 业务四象限分析视图（实现难易度 effort × 商业价值） | [E01-UC04](01-discovery.md) |
| [#126](https://github.com/EricWang1358/BridgeFlow-AI/issues/126) | CLOSED | [需求评审] RBAC：按部门隔离字段映射与业务数据可见性 | [E09-UC04](09-security-approval.md), [E09-UC05](09-security-approval.md), [E09-UC06](09-security-approval.md) |
| [#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127) | OPEN | [Main Overview] BridgeFlow AI：SMB 三 Agent 闭环——立项提案、流程标准化与组织落地 | [E01-UC06](01-discovery.md), [E02-UC01](02-standardization.md), [E03-UC05](03-adoption.md) |
| [#128](https://github.com/EricWang1358/BridgeFlow-AI/issues/128) | CLOSED | [需求评审][P2] 知识内容接入与解析：会议纪要转写、文档解析、切块与元数据 | [E12-UC01](12-knowledge-deferred.md) |
| [#129](https://github.com/EricWang1358/BridgeFlow-AI/issues/129) | CLOSED | [需求评审][P2] 知识存储与索引：数据中台知识层 | [E12-UC02](12-knowledge-deferred.md) |
| [#130](https://github.com/EricWang1358/BridgeFlow-AI/issues/130) | CLOSED | [需求评审][P2] 检索与员工问答 Agent：带引用的可追溯回答 | [E12-UC03](12-knowledge-deferred.md) |
| [#131](https://github.com/EricWang1358/BridgeFlow-AI/issues/131) | CLOSED | [需求评审][P2] Agent Part 2 总览：企业知识库与问答（获取→解析→储存→检索） | [E12-UC01](12-knowledge-deferred.md), [E12-UC02](12-knowledge-deferred.md), [E12-UC03](12-knowledge-deferred.md) |
| [#132](https://github.com/EricWang1358/BridgeFlow-AI/issues/132) | CLOSED | [需求评审][P3] 监控与巡检：系统健康、数据管线与任务质量信号 | [E11-UC05](11-operations-evaluation.md) |
| [#133](https://github.com/EricWang1358/BridgeFlow-AI/issues/133) | CLOSED | [需求评审][P3] 自动诊断与自愈：处置动作分级与审批边界 | [E11-UC05](11-operations-evaluation.md) |
| [#134](https://github.com/EricWang1358/BridgeFlow-AI/issues/134) | CLOSED | [需求评审][P3] 告警与升级：面向无专职运维客户的通知、路由与运维报告 | [E11-UC05](11-operations-evaluation.md) |
| [#135](https://github.com/EricWang1358/BridgeFlow-AI/issues/135) | CLOSED | [需求评审][P3] Agent 自动化运维总览：巡检、自愈与升级（面向无专职运维的中小企业） | [E11-UC05](11-operations-evaluation.md) |
| [#138](https://github.com/EricWang1358/BridgeFlow-AI/issues/138) | OPEN | Deployment blocked: configure production SSH credentials and public domain | [E11-UC04](11-operations-evaluation.md) |
| [#140](https://github.com/EricWang1358/BridgeFlow-AI/issues/140) | OPEN | Feishu pilot: upload and download file shortcuts | [E02-UC10](02-standardization.md) |
| [#141](https://github.com/EricWang1358/BridgeFlow-AI/issues/141) | OPEN | Business sample data: two tuning sets and one held-out set for field mapping | [E02-UC09](02-standardization.md) |
| [#143](https://github.com/EricWang1358/BridgeFlow-AI/issues/143) | OPEN | [需求评审] 从部门材料梳理信息流与文件流，共创标准模板并识别 AI 接入环节 | [E01-UC01](01-discovery.md), [E01-UC02](01-discovery.md), [E01-UC03](01-discovery.md), [E01-UC04](01-discovery.md), [E01-UC05](01-discovery.md), [E01-UC06](01-discovery.md), [E02-UC01](02-standardization.md) |
| [#144](https://github.com/EricWang1358/BridgeFlow-AI/issues/144) | OPEN | [需求评审][Agent 2] 一线试点验证部门模板，辅助补全标准表并经 API 入库 | [E02-UC01](02-standardization.md), [E02-UC02](02-standardization.md), [E02-UC03](02-standardization.md), [E02-UC04](02-standardization.md), [E02-UC05](02-standardization.md), [E02-UC06](02-standardization.md), [E02-UC07](02-standardization.md), [E02-UC08](02-standardization.md), [E02-UC09](02-standardization.md) |
| [#145](https://github.com/EricWang1358/BridgeFlow-AI/issues/145) | OPEN | [需求评审][Agent 3] Consulting Agent：员工上手、组织资源协调与持续落地闭环 | [E03-UC01](03-adoption.md), [E03-UC02](03-adoption.md), [E03-UC03](03-adoption.md), [E03-UC04](03-adoption.md), [E03-UC05](03-adoption.md) |
| [#147](https://github.com/EricWang1358/BridgeFlow-AI/issues/147) | CLOSED | [MVP 案例] 生产记录缺失补问 → 标准化 → 本地 API 入库 → 模拟市场部交接（已跑通） | [E02-UC04](02-standardization.md), [E02-UC05](02-standardization.md), [E02-UC06](02-standardization.md) |

## 2026-09-17 需求盘点新增 / Added by the 2026-09-17 review

这些 UC 来自三视角盘点，不对应单独的 issue；来源与理由见 [00-foundations §1](00-foundations.md#1-进展盘点三个视角--progress-review-from-three-perspectives)。

These UCs come from the three-perspective review rather than individual issues; see foundations §1 for sources and rationale.

| UC | 视角 / Perspective | 关联 issue / Related issues | 状态 / Status |
| --- | --- | --- | --- |
| [E13-UC01](13-conclusions.md) 一页月度结论 / One-page brief | 结论直观性 / Clarity | [#127](https://github.com/EricWang1358/BridgeFlow-AI/issues/127)、[#190](https://github.com/EricWang1358/BridgeFlow-AI/issues/190) | PARTIAL |
| [E13-UC02](13-conclusions.md) 跨期对比 / Period comparison | 完整性 / Completeness | [#191](https://github.com/EricWang1358/BridgeFlow-AI/issues/191) | IMPLEMENTED_OFFLINE |
| [E13-UC03](13-conclusions.md) 指标可视化 / Metric charts | 结论直观性 / Clarity | [#192](https://github.com/EricWang1358/BridgeFlow-AI/issues/192) | IMPLEMENTED_OFFLINE |
| [E13-UC04](13-conclusions.md) 月度报告文档 / Monthly report | 完整性、专业性 / Completeness, professionalism | [#22](https://github.com/EricWang1358/BridgeFlow-AI/issues/22)（季度年度 PDF 仍归 E06-UC06） | PARTIAL |
| [E13-UC05](13-conclusions.md) 口径假设确认 / Convention confirmation | 完整性 / Completeness | [#23](https://github.com/EricWang1358/BridgeFlow-AI/issues/23) | IMPLEMENTED_OFFLINE |
| [E13-UC06](13-conclusions.md) 依据等级 / Evidence grades | 专业性 / Professionalism | [#195](https://github.com/EricWang1358/BridgeFlow-AI/issues/195) | PARTIAL |
| [E14-UC01](14-monthly-convenience.md) 进度清单 / Close checklist | 便民性 / Ease of use | [#197](https://github.com/EricWang1358/BridgeFlow-AI/issues/197) | IMPLEMENTED_OFFLINE |
| [E14-UC02](14-monthly-convenience.md) 模板预填 / Template carry-over | 便民性 / Ease of use | — | DESIGNED |
| [E14-UC03](14-monthly-convenience.md) 提交前自检 / Self-check | 便民性 / Ease of use | [#47](https://github.com/EricWang1358/BridgeFlow-AI/issues/47)、[#199](https://github.com/EricWang1358/BridgeFlow-AI/issues/199) | IMPLEMENTED_OFFLINE |
| [E14-UC04](14-monthly-convenience.md) 单部门补传 / Single-department correction | 便民性 / Ease of use | [#200](https://github.com/EricWang1358/BridgeFlow-AI/issues/200) | IMPLEMENTED_OFFLINE |
| [E14-UC05](14-monthly-convenience.md) 待确认收件箱 / Open-item inbox | 便民性 / Ease of use | [#201](https://github.com/EricWang1358/BridgeFlow-AI/issues/201) | IMPLEMENTED_OFFLINE |
| [E14-UC06](14-monthly-convenience.md) 飞书文件夹导入 / Feishu folder import | 便民性 / Ease of use | [#140](https://github.com/EricWang1358/BridgeFlow-AI/issues/140) | DESIGNED |

## 关闭原因与实现不能混同 / Closure is not delivery

- #17：关闭评论明确为黑客松范围外；现有币种拒绝和单位规范不能替代通用换算及补齐。
- #22：历史关闭为不做；后来增加了总表 XLSX，仍没有完整 PDF 交付证据，因此拆为两个 UC。
- #131：2026-09-13 关闭评论明确“本轮不做”，旧知识问答不等于新 Agent 2；E12 保留历史范围，不算已交付。
- #132–135：没有发现完整自动巡检、自愈与升级 Agent 的实现；现有 workflow 事件诊断是局部基础能力。关闭本身不能成为实现证据。
- #126：已有门户协议与浏览器批次权限测试，但个人审批身份、全部端点隔离及真实租户验收仍需区分。
- #147：固定合成案例和主应用工作流基座有证据，不等于 Agent 2 的全部试点及真实接口验收。

#17 was scoped out; #22 was scoped out before later XLSX work, without complete PDF delivery; #131 was explicitly excluded from the current product scope. Closure of operations issues does not prove an autonomous operations agent. Identity tests do not establish full endpoint isolation or individual approval identity. The synthetic #147 demonstration does not satisfy the whole Agent 2 scope.

## 共用能力与计数边界 / Reuse and counting

E04–E11 是存量产品/平台能力分组，不代表新增八个运行时 Agent。E01–E03 消费这些能力：例如 E02 的业务填报复用 E09 审批，但不把每个审批 API 再算一遍；飞书文件与真实业务数据仍仅在 E02-UC10/09 定义。四部门研判归 E07，不与三个新业务 Agent 混数。

E04–E11 group existing product/platform capabilities, not eight new runtime agents. E01–E03 reuse them; approval APIs are not counted again per consumer. Feishu files and real samples remain defined in E02-UC10/09. Four-department review belongs to E07 and is separate from the three business agents.
