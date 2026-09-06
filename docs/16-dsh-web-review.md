# 16 — DSH Web 重构与看板复核

复核日期：2026-09-06。依据：本地实现、GitHub issues 与 Projects 读取结果，以及官方锁定版本源码。这里记录判断、验收条件和排期建议；测试数字统一见 [00-status](00-status.md#原生-web-重构复测2026-09-06)。远端 issue 与看板尚未修改。

## 项目画像与根因

BridgeFlow 是面向中小制造企业的跨部门月度对账与研判工具。价值是解释生产、采购、财务、市场数据为何对不上，并把可计算事实、待确认关系和行动建议分开。DSH 承担代理运行时；Python 承担清洗、字典语义、计算与持久化。真实 OA 字典、财务科目和脱敏工作簿尚待业务确认，样例字典不能被当成客户事实。

已有资产是 Pydantic 契约、确定性计算、映射记忆、证据引用、DSH 工具与护栏接入。主要错误不是缺一个漂亮页面，而是入口仍围绕 Python `Orchestrator` 与自建审批控制台组织，DSH 会话、原生审批和轨迹没有成为用户工作的主路径。把 DSH 再包装成 `LLMProvider` 会继续丢掉这些能力。

本次默认入口改为官方 **DSH Web + BridgeFlow Client/Host 插件 + 私有 Python 领域服务**。上传不发起模型调用，生成可重开的独立批次；用户在原生会话继续分析。旧 `/analyze`、`/quote` 与 `/console` 默认关闭，遗留代码保留供迁移复核，其遗留编排不能算官方子代理实现；后续实现已替换为 `review_context → 父模型四次官方 subagent → review_finalize`，详见 [18](18-native-captain-and-state.md) 的新增验收，见 [17](17-business-mvp-acceptance.md)。

## DSH 复用边界

依据官方 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness/tree/dsh-v0.1.2-rc.1)，固定 tag `dsh-v0.1.2-rc.1`，commit `a66e4702047846cdaa10c66c9d3df3951f5ea70d`。所有 DSH npm 接口依赖与 Python SDK 对齐，不 fork 源码，不依赖 experimental。

| 能力 | 处理方式 | 依据 / 接缝 |
| --- | --- | --- |
| 页面外壳、会话列表、聊天、主题 | 直接保留 | 原生 Web composition |
| 登录凭证、Cookie、Host/Origin 校验 | 直接复用 | `ctx.connection.requestRejection()` |
| 审批、人机提问、工具细节与轨迹 | 保留原生服务；映射审批通过 composer slot 增加理由 | `ctx.approval`、原生 approval UI、trajectory |
| 批次导入、主表、修正与隔离查看 | 小范围新增业务组件 | `sidebar.footer.action` 打开数据面板，浏览器专用分页 API |
| 领域工具卡片 | 插入原生工具区域 | `tool.call.toolview`，兼容运行中、错误、完成状态 |
| 插件编辑、插件安装、模型/权限/预设选择 | 企业配置默认禁用入口 | `dsh/enterprise.patch.yml`；不删官方代码 |
| shell、编辑器、通用代码执行、任意预设 | 主机强制禁止 | 限定 preset roots + 单调 `tools.guard()` 白名单 |
| 原始文件引用与目录选择器 | 默认关闭 | 防止以原生文件功能绕过受控导入 |
| 原生工作区 | 原生服务登记启动目录 | 全新环境也可选工作区并开始会话；不是另外实现会话系统 |
| 官方 subagent 与祖先关系追踪 | 父模型同一响应四次官方 subagent，宿主校验角色、结构化输出、步数与时间上限 | 原生父子会话与并行生命周期已有浏览器及真实模型证据 |
| workflow / Agent Teams | 不启用 | 前者执行模型编写的脚本；后者属于实验能力，均不符合本项目约束 |

不能只隐藏按钮：Web 根配置关掉工具后，标准 agent preset 仍可能重新挂载它们。限定可加载 preset，并在真实工具派发时拒绝未授权名称，才构成执行约束。一般主题等展示设置不需要为了“企业版”重写。

权限选择器也由原生 composer 读取主机 projection 渲染，仅禁用 UI 插件不够，须同步禁用
`permission-presets` 主机服务。聊天附件入口关闭，但底层 `attachments` 保留：它是官方
session-controller 的必需依赖，直接移除会导致整个原生会话接口无法激活。

Web 启动采用同版本官方 npm CLI。rc1 Python SDK 打包的 Web 在本次环境不能生成完整内置客户端模块清单；它仍可用于既有 SDK 集成，但不作为默认浏览器启动器。`session-title-first-prompt-llm` 暂停，使用原生回退标题；插件客户端按官方模块加载协议构建，不另建 React 应用壳。

## 修复与仍有缺口的实现

| 问题 | 本次处置 | 不能据此声称的能力 |
| --- | --- | --- |
| 上传与工具计算脱节，可能回答仓库固定样本 | 新 `batch_id` 贯穿摘要、指标目录与计算；生产关闭样本回退 | 不能用样本成功证明真实 OA 数据兼容 |
| 同月重跑覆盖工作对象，字典变更改变旧批口径 | 独立批次文件，冻结字典；刷新仍返回原拒绝原因 | 尚无业务签发、版本 diff 与发布流程 |
| 字典缺席仍猜实体 | 新导入保留数据并标 `needs_configuration`，不生成猜测主表 | 字段配置向导仍待做 |
| 歧义日期被解析成错误月份后继续聚合 | 原文保留在隔离区；批次有隔离行即拒绝报总额 | 尚无按字典声明 locale 的自动解决；需修正源文件后新导入 |
| 输入可越过审批直接写映射 | 私有服务凭证 + 主机生成的短期、参数绑定、一次性 HMAC 回执；SQLite 防重放 | 共享认证会话不是员工实名审计 |
| 浏览器可直接请求领域写接口 | 复用 DSH 鉴权；同源代理仅开放上传与指定批次只读路由 | 不是多租户隔离、SSO 或企业 RBAC |
| 指标不存在时反复 409 | 错误内联冻结字典的候选名，提示停止猜测 | 尚未测得真实模型重试次数下降；还需结构性重试预算 |
| guard 只有正则单测 | 增加真实 DSH ToolRuntime 派发测试，包括后续 allow 不能翻案 | 未证明所有注入攻击均被阻止 |
| 旧测试默认读取开发者付费 provider 和持久目录 | 隔离测试配置、输出与映射记忆；离线测试明确使用 mock | mock 通过不是推理质量证据 |

上传支持 CSV 与单 sheet XLSX，限制总字节、解压大小、部门数量和行数。多 sheet 明确拒绝，等待显式 sheet/表头选择。界面分页仅是浏览器数据查看能力；模型只获得计数、公式与封顶证据样本。配置了行数上限不等于完成该规模性能验收。

还有实质风险须跟踪：当前业务报告保存文件、原始行/列引用，去空、去重和隔离不再重排行号；重复行交易身份不明时拒绝业务总额。未知文件的类型推断与更完整交易身份规则仍需适配；财务销售和成本口径、币种及缺值语义需要业务字典。主表能显示不等于已审定报表。普通聊天结论也还未全部经过后端 Finding 数值校验器。

## 对远端 issue / Kanban 的意见

看板：[BridgeFlow Project 1](https://github.com/users/EricWang1358/projects/1)。读取到的状态分布在 [00-status](00-status.md#原生-web-重构复测2026-09-06)。`Done` 混合了真正交付与拒绝范围：例如 AWS、自建前端、完整 RBAC、导出等关闭项，不能计入功能完成率。

| 顺序 | Issue | 建议重排与验收条件 |
| --- | --- | --- |
| P0 | [#40](https://github.com/EricWang1358/BridgeFlow-AI/issues/40)、[#87](https://github.com/EricWang1358/BridgeFlow-AI/issues/87) | 合并到“原生 DSH Web 工作入口与授权边界”里程碑；撤销“两窗口暂不迁移”的旧建议。验收上传→会话工具→原生批准/拒绝→文件结果与轨迹，包含刷新、取消、无权限负例。报价卡必须等计算口径成立，不能先画三档价格。 |
| P0 | [#38](https://github.com/EricWang1358/BridgeFlow-AI/issues/38) | 标题已纠正但正文仍要求 workflow 与退回 Orchestrator，应重写正文和里程碑描述。固定阶段 + 官方 spawn 四角色；只读工具白名单、同一批次、无横向通信、取消/超时/部分失败、结构化输出校验和原生父子 session 证据才算 Done。 |
| P0 | [#79](https://github.com/EricWang1358/BridgeFlow-AI/issues/79)、[#92](https://github.com/EricWang1358/BridgeFlow-AI/issues/92)、[#5](https://github.com/EricWang1358/BridgeFlow-AI/issues/5) | 先保证数字可信，再调模型。歧义日期隔离只是 #79 的安全兜底；补声明式日期格式。销售、成本、净额分别由字典声明；验证引用存在、期间/实体一致、数值和单位一致，不能只验证 evidence 非空。 |
| P1 | [#46](https://github.com/EricWang1358/BridgeFlow-AI/issues/46)、[#61](https://github.com/EricWang1358/BridgeFlow-AI/issues/61)、[#88](https://github.com/EricWang1358/BridgeFlow-AI/issues/88) | 做原生数据面板内的字段映射与隔离处理闭环。原批次不改，决定产生新版本；展示未裁决与低置信的区别。隔离查看不等于 release/discard 已交付。 |
| P1 | [#55](https://github.com/EricWang1358/BridgeFlow-AI/issues/55)、[#69](https://github.com/EricWang1358/BridgeFlow-AI/issues/69) | 将版本、插件加载、真实派发拒绝、审批与浏览器链路固化成可重复命令。记录 block 与审计事件；本次不引入已被项目排除的 CI。 |
| P1 | [#31](https://github.com/EricWang1358/BridgeFlow-AI/issues/31)、[#72](https://github.com/EricWang1358/BridgeFlow-AI/issues/72)、[#89](https://github.com/EricWang1358/BridgeFlow-AI/issues/89) | 从包装 `llm.complete` 改为原生 session/trajectory 证据；分别记录规则、离线脚本、真实模型三类运行。失败/取消/未裁决不能并成低置信；重试和成本预算要有硬上限。 |
| 业务依赖 | [#23](https://github.com/EricWang1358/BridgeFlow-AI/issues/23)、[#75](https://github.com/EricWang1358/BridgeFlow-AI/issues/75) | 明确等什么、负责人、最迟日期、没有材料时禁用哪些结论。业务阻塞独立于开发完成状态。 |

建议限制同时进行的主线：先原生入口与授权闭环，再可信数字与正式四角色 fan-out，最后扩大业务功能。每个 issue 的 Done 应包含“用户动作、状态变化、可见结果、拒绝路径、证据命令”，Review 与 Done 分开；范围拒绝用明确的 resolution，不能用卡片总完成数代表 rubric 分数。

## 按充分实现 Rubric 验收

| Rubric | 可展示的基础 | 充分实现仍须补齐 |
| --- | --- | --- |
| Goal & Scope | 跨部门月度对账，样例与拒绝边界清晰 | 业务方字典与成功判据确认 |
| Architecture & Reasoning Loop | 原生四角色 spawn、结构化校验、批次/报告持久化、部分失败不伪装成功 | 更完整的取消恢复与正式签发状态机 |
| Tool Use & Integration | typed tools 真正计算上传批次；错误与候选名可见 | 日期、财务口径、完整证据血缘与真实文件适配 |
| Autonomy & HITL | 原生审批门、后端一次性回执、策略可禁写 | 隔离处置、映射向导；企业身份提供方和角色授权 |
| Safety & Guardrails | 主机白名单、服务鉴权、分页数据/模型摘要分离 | 更完整攻击评测、业务级访问隔离与日志留存治理 |
| Observability & Eval | 原生轨迹、离线故障、真实模型用例与拒绝理由已有证据及用量记录 | 留出评测、真实文件质量与运营期费用治理 |
| Platform & Tooling | 官方 Web、slots、approval、tools、session、subagents 与可执行演示 | 版本升级契约与企业部署验收 |

目标是每项都有真实行为和证据，而非把采用某包、测试全绿或 UI 可见当成全项达标。本次未读取留出验收集；真实模型验收使用可见生成案例，记录在 [17](17-business-mvp-acceptance.md)，不将离线脚本输出作为模型研判效果。
