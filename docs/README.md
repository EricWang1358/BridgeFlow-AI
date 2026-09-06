# 文档索引

编号反映的是写作顺序，不是阅读顺序——`10` 是从 `07` 改号迁来的（`07` 让给了业务 PRD），
`05` 已被取代但还占着号。**所以先看这张表，别按号读。**

## 先读什么

| 你是谁 | 读这三篇，够了 |
| --- | --- |
| **想直接把它跑起来** | [`../HANDOFF.md`](../HANDOFF.md) 的「怎么把它跑起来」一节，就够了 |
| 接手开发的人 | [`../CLAUDE.md`](../CLAUDE.md) → [`../HANDOFF.md`](../HANDOFF.md) → [`13`](13-golden-standard.md) |
| 评委 / 外部读者 | [`17`](17-business-mvp-acceptance.md) → [`00`](00-status.md) → [`01`](01-problem-and-hmw.md) |
| 想知道某个数字 | [`00`](00-status.md)，只有这一处 |

## 三份常驻文档的分工

**不重叠。** 同一件事只写在一处，其余单向链接过去——重复的内容一旦过期，
就会变成三处互相矛盾的事实。

| | 管什么 | 不管什么 |
| --- | --- | --- |
| [`../CLAUDE.md`](../CLAUDE.md) | **硬约束**：不随进度改变的规矩 | 进度、数字、缺陷清单 |
| [`../HANDOFF.md`](../HANDOFF.md) | **易变状态**：怎么跑起来、当前进度、下一步、已知缺陷 | 硬约束、架构论证 |
| [`13`](13-golden-standard.md) | **架构决策**：为什么这样设计、官方能力边界 | 进度、排期 |
| [`00`](00-status.md) | **所有实测数字的唯一来源** | 结论与解释 |

## 全部文档

**状态**：🟢 权威（冲突时以它为准）· 🔵 参考（内容有效，但不是权威）· ⚪ 已取代（只剩重定向）

| | 状态 | 语言 | 读者 | 一句话 |
| --- | --- | --- | --- | --- |
| [`00-status.md`](00-status.md) | 🟢 | 中 | 所有人 | 每一个实测数字的唯一来源 |
| [`01-problem-and-hmw.md`](01-problem-and-hmw.md) | 🟢 | EN | 评委 · 新人 | HMW、目标客户、三个痛点 |
| [`02-architecture.md`](02-architecture.md) | 🔵 | EN | 开发 | 各 Agent 的输入输出契约 |
| [`03-data-contracts.md`](03-data-contracts.md) | 🔵 | EN | 开发 | Pydantic 模型逐个说明 |
| [`04-demo-plan.md`](04-demo-plan.md) | 🟢 | EN | 演示人 · 评委 | 六分钟脚本，**含每一拍今天能不能真跑** |
| [`05-roadmap.md`](05-roadmap.md) | ⚪ | 中 | — | 已被里程碑取代，只剩重定向 |
| [`06-deepseek-harness.md`](06-deepseek-harness.md) | 🔵 | 中 | 开发 | dsh 的事实与 API |
| [`07-prd-v0.1.md`](07-prd-v0.1.md) | 🔵 | 中 | 开发 · 业务方 | 业务方 PRD。**是需求基线，不是交付承诺** |
| [`08-prd-traceability.md`](08-prd-traceability.md) | 🔵 | 中 | 开发 | PRD 逐条 FR 对照代码现状 |
| [`09-rubric-assessment.md`](09-rubric-assessment.md) | 🔵 | 中 | 开发 | 为什么这样排优先级（计分以 `00` 为准） |
| [`10-proposal.md`](10-proposal.md) | 🔵 | EN | 评委 · 团队 | 三周范围与工作量（顺序以里程碑为准） |
| [`11-proposal-review.md`](11-proposal-review.md) | 🔵 | 中 | 团队 | 对 `10` 的复核记录 |
| [`12-delivery-controls.md`](12-delivery-controls.md) | 🟢 | EN | 评委 | 提交表单内容。**每行带 Status，区分已实现与承诺** |
| [`13-golden-standard.md`](13-golden-standard.md) | 🟢 | 中 | 开发 | **架构权威**，与其他文档冲突时以它为准 |
| [`14-wsl-setup.md`](14-wsl-setup.md) | 🔵 | 中 | 开发 | WSL 环境搭建，每步带验证 |
| [`17-business-mvp-acceptance.md`](17-business-mvp-acceptance.md) | 🟢 | 中 | 业务用例负责人 · 演示人 | 当前 MVP 演示、模拟负责人验收与复演命令 |
| [`16-dsh-web-review.md`](16-dsh-web-review.md) | 🔵 | 中 | 开发 · 团队 | 原生 Web 复用、权限边界、issue 重排与 Rubric 验收 |
| [`15-plugin-design.md`](15-plugin-design.md) | 🔵 | 中 | 开发 | dsh 插件设计，读完官方文档后的结论落这里 |
| [`20-quotation-brief.md`](20-quotation-brief.md) | 🟢 | 中 | 接手报价功能的人 | **报价功能任务书**：并列功能而非转向，分三步，第一步现在可做 |

## 语言规则

**对外的用英文，内部工程记录用中文。** 之前这是个隐约的习惯，现在写出来：

- **英文**：会被评委读到或在台上讲的（`01` `02` `03` `04` `10` `12`）
- **中文**：内部工程与决策记录（`00` `06`–`09` `11` `13`–`15`，以及 `CLAUDE.md`、`HANDOFF.md`）
- **代码、注释、commit message、issue 标题**：一律英文
- issue 正文与 `docs/` 中文文档：跟随所在语境

新增文档时先决定读者，再决定语言。

- [18 — 原生队长、业务状态页与会话治理](18-native-captain-and-state.md)
- [一站式业务 Demo](../demo-walkthrough/README.md)

- [19 — 跨操作链路审计、已修缺陷与恢复缺口](19-chain-audit.md)
