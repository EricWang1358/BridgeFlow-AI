# 文档索引

编号记的是写作顺序，不是阅读顺序。`10` 是从 `07` 迁出来的（那个位置让给了业务方 PRD），
`05` 已经作废，只剩一个指路牌。所以先查这张表，不要按号往下读。

## 按读者给的路径

| 你是谁、想干什么 | 读这几篇就够 |
| --- | --- |
| 用这个产品 | [使用说明书](user-guide.zh.md)（[English](user-guide.en.md)），也在产品「会话与设置 → 使用说明书」里 |
| 把它跑起来 | [`../HANDOFF.md`](../HANDOFF.md) 的「怎么把它跑起来」，一屏命令 |
| 接手开发 | [`../CLAUDE.md`](../CLAUDE.md) 的规矩 → [`../HANDOFF.md`](../HANDOFF.md) 的现状 → [`13`](13-golden-standard.md) 的理由 |
| 评委或外部读者 | [`17`](17-business-mvp-acceptance.md) 现在能演示什么 → [`00`](00-status.md) 数字 → [`01`](01-problem-and-hmw.md) 问题从哪来 |
| 要一个数字 | [`00`](00-status.md)。只有这一处有数字，别写的是链接 |
| 上台演示 | [`04`](04-demo-plan.md) 逐拍能不能真跑 + [一站式 Demo](../demo-walkthrough/README.md) |
| 做报价功能 | [`20`](20-quotation-brief.md) 任务书 → [`21`](21-quotation-design.md) 设计边界 |

## 四份常驻文档的分工

彼此不重叠。同一件事只写在一处，别处单向链接过去：重复的内容一旦过期，就会变成三个版本互相矛盾的事实，
而这正是本项目已经犯过的错（测试数同时存在 19 和 21，样本行数同时存在 21 和 22）。

| 文档 | 管什么 | 明确不管 |
| --- | --- | --- |
| [`../CLAUDE.md`](../CLAUDE.md) | 不随进度改变的硬约束 | 进度、数字、缺陷清单 |
| [`../HANDOFF.md`](../HANDOFF.md) | 怎么跑起来、当前进度、下一步、已知缺陷 | 硬约束、架构论证 |
| [`13`](13-golden-standard.md) | 架构决策与官方能力边界；与其他文档冲突时以它为准 | 进度、排期 |
| [`00`](00-status.md) | 所有实测数字的唯一来源 | 结论与解释 |

## 全项目需求与用例

[全项目双语 epic、UC、设计与实施状态](requirements/README.md)：覆盖既有导入清洗、映射、总表、研判、报价、安全审批、工作室、运维评测，以及 #143/#144/#145 新主线；[追溯矩阵](requirements/traceability.md) 映射 FR01–26 与全部历史 issue。

## 全部文档

状态一词的含义：**权威**指冲突时以它为准；**参考**指内容有效但不作裁判；**已取代**指只剩指路作用。

| 文档 | 状态 | 语言 | 主要读者 | 里面是什么 |
| --- | --- | --- | --- | --- |
| [`00-status.md`](00-status.md) | 权威 | 中 | 所有人 | 每一轮验收的实测数字、复现命令与不能声称的部分 |
| [`01-problem-and-hmw.md`](01-problem-and-hmw.md) | 权威 | EN | 评委、新人 | HMW、目标客户画像、三个痛点如何变成可测目标 |
| [`02-architecture.md`](02-architecture.md) | 参考 | EN | 开发 | 四个 Agent 各自的输入输出契约（dsh 的位置看 `13`） |
| [`03-data-contracts.md`](03-data-contracts.md) | 参考 | EN | 开发 | Pydantic 模型逐个说明，跨 Agent 边界的类型定义 |
| [`04-demo-plan.md`](04-demo-plan.md) | 权威 | EN | 演示人 | 五分钟脚本：每一拍点哪里、说什么、对应哪几项评分，以及现场出错怎么应对 |
| [`05-roadmap.md`](05-roadmap.md) | 已取代 | 中 | — | 旧 M0–M5 排期，基于已废弃的自建前端与自建编排 |
| [`06-deepseek-harness.md`](06-deepseek-harness.md) | 参考 | 中 | 开发 | dsh 的版本事实、SDK API、三条必知约束 |
| [`07-prd-v0.1.md`](07-prd-v0.1.md) | 参考 | 中 | 开发、业务方 | 业务方需求原文。是需求基线，不是交付承诺，正文不改 |
| [`08-prd-traceability.md`](08-prd-traceability.md) | 参考 | 中 | 开发 | FR 01–26 逐条对照代码，缺口写清楚（对照的是脚手架时期） |
| [`09-rubric-assessment.md`](09-rubric-assessment.md) | 参考 | 中 | 开发 | 排优先级的理由：rubric 考什么、PRD 里哪些不计分 |
| [`10-proposal.md`](10-proposal.md) | 参考 | EN | 评委、团队 | 三周范围与工作量估算；实现顺序以看板为准 |
| [`11-proposal-review.md`](11-proposal-review.md) | 参考 | 中 | 团队 | 对 `10` 的复核：六处改动，每条挂一个实测结果 |
| [`12-delivery-controls.md`](12-delivery-controls.md) | 权威 | EN | 评委 | 交付表单内容，每行带 Status，承诺与现状分得开 |
| [`13-golden-standard.md`](13-golden-standard.md) | 权威 | 中 | 开发 | 架构权威：dsh 为什么是基座、能力边界、走过的弯路 |
| [`14-wsl-setup.md`](14-wsl-setup.md) | 参考 | 中 | 开发 | WSL 环境搭建，每步一条验证命令，不过不往下走 |
| [`15-plugin-design.md`](15-plugin-design.md) | 参考 | 中 | 开发 | 插件形态的设计结论与已排除的做法 |
| [`16-dsh-web-review.md`](16-dsh-web-review.md) | 参考 | 中 | 开发、团队 | 原生 Web 复用边界、权限边界、issue 重排建议、rubric 验收条件 |
| [`17-business-mvp-acceptance.md`](17-business-mvp-acceptance.md) | 权威 | 中 | 业务用例负责人、演示人 | 当前 MVP 的演示步骤、模拟负责人验收、复演命令 |
| [`18-native-captain-and-state.md`](18-native-captain-and-state.md) | 参考 | 中 | 开发 | 原生队长调用链、业务状态页、会话与证据保留策略 |
| [`19-chain-audit.md`](19-chain-audit.md) | 权威 | 中 | 开发 | 跨操作链路的身份归属、已修故障、尚未收尾的 P0/P1 |
| [`20-quotation-brief.md`](20-quotation-brief.md) | 权威 | 中 | 接手报价的人 | 报价功能任务书：并列的第二条路径，分三步，第一步现在可做 |
| [`21-quotation-design.md`](21-quotation-design.md) | 参考 | 中 | 接手报价的人 | 报价声明与自由文本证据边界，设计先于实现写定 |
| [`22-lightsail-deploy.md`](22-lightsail-deploy.md) | 参考 | 中 | 开发、运维 | Lightsail 部署 runbook：实例引导、GitHub Actions 流水线、Caddy 反代与回滚 |
| [`user-guide.zh.md`](user-guide.zh.md) / [`.en`](user-guide.en.md) | 权威 | 中 / EN | 使用者 | 使用说明书，由 `plugins/src/client/user-guide.ts` 生成，与产品内的说明书同源 |
| [`29-interactive-onboarding.md`](29-interactive-onboarding.md) | 参考 | 中 | 开发、体验者 | 真实页面引导、重播恢复、案例留档与验证边界 |
| [`28-rehearsal-authorization.md`](28-rehearsal-authorization.md) | 交接 | 高 | 项目负责人 | 录制版本复跑彩排的付费授权书草案：命令、预算硬上限、停止条件，签署前不运行 |
| [`27-external-inputs.md`](27-external-inputs.md) | 交接 | 高 | 业务方、部署与飞书负责人 | 剩余 issue 所需的外部输入：要什么、怎么安全交付、到手后跑哪条验收命令 |
| [`26-erp-comparison.md`](26-erp-comparison.md) | 参考 | 中 | 团队、写 PPT 的人 | 与 ERP 定制化三痛点逐条对比，每条指向已合并实现；列出值得借鉴但未做的 |
| [`25-workflow-foundation.md`](25-workflow-foundation.md) | 参考 | 中 | 开发 | 三个 Agent 共用的工作流基座：分层、设计模式及理由、状态机、未完成项 |
| [`24-meeting-2026-09-13.md`](24-meeting-2026-09-13.md) | 参考 | 中 | 团队 | 9/13 讨论：不自建数据平台；飞书只做上传下载快捷调用，权限是远景；样例数据 2+1 是主线阻塞 |
| [`27-login-portal.md`](27-login-portal.md) | 参考 | 中 | 开发、接手认证的人 | 统一登录门户与飞书 RBAC：JWT/JWKS 为什么是形态、权限映射为什么应用自持、本期粒度与明确不做 |
| [`30-feishu-user-docs.md`](30-feishu-user-docs.md) | 权威 | 中 | 开发 | 飞书用户态云文档读写实施计划：user token 管线、加密 Cookie、三步端点、明确不做与人工前置项 |
| [`31-feishu-wiki.md`](31-feishu-wiki.md) | 权威 | 中 | 开发 | 飞书知识库读写实施计划：wiki_token/obj_token 双轨、先落 Drive 再挂载的两步写回、scope 与人工前置项 |
| [`32-feishu-sheets-bitable-read.md`](32-feishu-sheets-bitable-read.md) | 权威 | 中 | 开发 | 在线表格/多维表格读取需求规格：合理性、接口面、FR-1~7、复杂字段降级与 20 万行纪律 |
| [`33-feishu-sheets-bitable-impl.md`](33-feishu-sheets-bitable-impl.md) | 权威 | 中 | 开发 | 在线表格/多维表格读取实施计划：复用面锚点、六个设计决策、四步落地与验收对照 |
| [`34-web-refactor-plan.md`](34-web-refactor-plan.md) | 权威 | 中 | 开发、运维 | 全 Web 化与单租户部署实施计划：复用面锚点、六步落地、验收对照与文档同步（形态决策见 issue #227） |
| [`36-online-demo.md`](36-online-demo.md) | 权威 | 中 | 负责人、开发、运维 | 线上演示为中心：免登录评委入口、首屏零点击、本机模型闸门与分层防盗刷、访客席位池，待拍板项单列 |

两份 README 是同一套图文操作指引的中英版本（顶部可切换）：[`../README.md`](../README.md)（English）
与 [`../README.zh.md`](../README.zh.md)（简体中文）。截图是 `../docs/images/` 里的稳定副本，
来源与外壳版本记在 [`images/README.md`](images/README.md)。

仓库内其他入口：[`../plugins/README.md`](../plugins/README.md)（插件的运行时契约）、
[`../data/README.md`](../data/README.md)（开发集与留出的验收集为何分开）、
[`../data/mappings/README.md`](../data/mappings/README.md)（字段字典格式）、
[`../demo-walkthrough/README.md`](../demo-walkthrough/README.md)（一站式演示包）。

## 语言规则

对外可读或在台上讲的用英文：`01` `02` `03` `04` `10` `12`，以及根 README 与插件 README。
内部工程与决策记录用中文：`00` `06`–`09` `11` `13`–`26` `34`，以及 `CLAUDE.md`、`HANDOFF.md`。
代码、注释、commit message、issue 标题一律英文。新增文档先定读者，再定语言。

## 写作约定

下面这些是为了让下一位作者不再把文档写成现在这样。改文档时按这几条办：

1. **一件事只写在一处。** 数字只进 `00`；硬约束只进 `CLAUDE.md`；架构理由只进 `13`。其余地方给链接，不复述。
2. **结论在前，证据在后。** 说「已实现」就挂 PR 或 issue 号，说「通过」就附复现命令，说「不通过」就附失败输出。
3. **过期内容就地改正文，不挂横幅。** 曾经各篇顶上都写着「部分已过时」而正文原样保留，等于让读者做人肉 diff，
   而横幅拦不住跳读的人。整篇作废就改成指路牌，旧内容留在 git 历史里。
4. **一段只说一件事。** 分号串起来的三四个动作，拆成列表或分开成句。
5. **表格放可枚举的事实**（契约、状态、数字），**正文放理由和取舍**。整段文字塞进表格单元格，两边都不讨好。
6. **中文正文用全角标点**；命令、路径、代码、issue 编号原样保留。
7. **加粗只留给必须被看见的规矩**，一篇不超过五处。
8. **不确定就写不确定。** 「待实测」「未确认」「本例不能推广到真实数据」这类句子是文档最有价值的部分，不要为了读起来顺把它删掉。

产品用途、工具注册与授权策略的扩展约定见 [产品扩展契约](23-extension-contracts.md)。
