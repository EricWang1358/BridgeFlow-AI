# 13 — 黄金标准：以 dsh 为基座的架构决策

本文回答一个问题：dsh 在这个产品里被怎么用，以及为什么只能这么用。内容包括决策问答、走过的弯路、
官方能力边界、目标架构和 rubric 符合性。与其他文档冲突时以本文为准。

分工：[`06`](06-deepseek-harness.md) 记 dsh 的版本事实与 API，[`09`](09-rubric-assessment.md) 是 rubric 自评与优先级理由，
[`10`](10-proposal.md) / [`11`](11-proposal-review.md) 是三周计划与复核，所有实测数字在
[`00`](00-status.md)。

---

## 一 核心原则

> 围绕 dsh 的官方内置插件构建。第三方与 experimental 插件可以用，但必须逐个论证，且不得进入关键路径。

这条原则的动机不是保守，是可审计性：财务数字要有人签字，就不能建立在行为未定义的组件上。
「输出错误、幻觉、子代理越权、未定义行为」这四类东西，是这套产品最贵的失败方式。

### 模型做匹配，不做创造（2026-09-07 业务方定）

同一条可审计性，落到字典这件事上，答案是：标准格式与初始字典由人事先预设。业务方原话是
「这个东西没有知识库，LLM 做不出来的」。

| 事项 | 谁做 |
| --- | --- |
| 标准格式模板、初始字典 | 人，事先 |
| 上传件的清洗 | 系统，自动 |
| 上传列到已声明字段的匹配 | 模型提议，人审核 |

匹配的候选集是封闭的，只能来自字典里已声明的字段，所以每条候选都能附上证据，让人做一道选择题。
创造是开放式的，没有知识库它立不住，签不了字。这与「结论必须带证据」是同一条原则的两面。

工具可以描述列的形状（`profile_batch` 给出唯一度、填充率与跨部门值重合度，全部不含单元格内容）来支撑匹配，
但不能据此凭空生成声明。硬约束原文见 [`../CLAUDE.md`](../CLAUDE.md)。

---

## 二 决策问答

**Q1：能否 WSL 部署 + 反向代理，Windows 直连？**
能，而且大概率不需要反代。WSL2 默认开启 localhostForwarding，`dsh web` 在 WSL 内监听，
Windows 浏览器开 `localhost:<port>` 就行。只有需要固定域名、HTTPS 或同端口多服务时才引入反代。
约束是 `DSH_HOME` 必须位于 WSL 文件系统内（`/home/...`），不得放在 `/mnt/d`：跨文件系统 IO 会严重拖慢运行时。
SDK 刻意不去发现 `~/.dsh`，这一项必填且无默认值。

**Q2：客户前端先不做，用 dsh 做实验？**
采纳并已执行。自建 Next.js 前端（`frontend/`）已删除，它是范围蔓延，也与「复用 dsh web 深度定制」冲突。
同批删除的还有 Dockerfile、docker-compose 与 CI workflow：部署目标没定之前就加，是错的。
定制入口已确认：Client 插件把工具的 wire name 注册进 `tool.call.toolview` 键槽，
从 `ToolCallBlock` 的参数、内容、错误、元数据派生组件 props。「修复日志卡片」「待确认映射卡片」
「报价对比卡片」都走这条路。

**Q3：当前是否是插件工作流？**
当前默认入口已经使用原生 DSH 领域工具与官方子代理（见第九节）。旧路径里的 `DshProvider` 只调 `harness.run()`，
把 dsh 当文本补全后端：没有 plugin、没有 tool，也没有用会话与工具执行。为什么这是错的，见第三节的错误记录。

**Q4：能否禁用大部分功能，换取干净与抗注入？**
能，这正是 `sdk-minimal` profile 的用途。它是独立的显式组合树，不是 `dsh-base` 的覆盖层，
只提供持久 Bash、字符串替换编辑器、本地执行与 JSONL 会话；settings、托管凭据、遥测、Web 工具与完整工具册
都在另外的 `sdk` 与 `web` profile 里。再用 profile 的 `$DSH_HOME/profiles/<p>/cordis.patch.yml` 继续做减法。

抗注入的落点是策略层，不是提示词。可用的扩展点：

| 扩展点 | 用途 |
| --- | --- |
| `tools/pre-execute` | 可重排的 allow / deny / ask 策略，返回 `{kind:'deny', reason}` |
| `ctx.tools.guard()` | 单调终局拒绝，后续监听者无法撤销 |
| `tools/execute` | 包裹派发：超时、重试、指标 |
| `tools/post-execute` | 替换展示内容或返回值、阻断结果 |
| `tools/result` | 观察不可变的最终结果 |

所以注入防御应该是一个 guard 插件，而不是散落在提示词里的边界标记。框架层拦截是硬约束，提示词是软约束。

**Q5：能否用 dsh 自带工具检查工具调用历史？**
能，而且基本是白拿。官方提供 `packages/session-query`（reads / traces / filters / search）、
`session-telemetry` + otel、`session-persistence-jsonl`。`ctx.approval` 另外提供成对审计事件
`approval/asked` + `approval/decided`。

**Q6：操作 xls 用 Python 还是 TypeScript？**
分两层：工具定义必须是 TS（`defineTool` / `ctx.tools` 是 Cordis 的 API），实现体可以调 Python。
xlsx 与 pandas 留在 Python 是对的，形态就是「TS 薄插件（schema + 调度）→ Python 计算」。
注意 `packages/experimental/code-runtime-python` 是实验性的，所以「让模型在 dsh 内直接跑 Python」这条路不走；
Python 以进程或服务的身份待在工具实现体之后。具体连接方式（subprocess 还是本地 HTTP）在读完
`user/develop/basic/tool.md` 后确定。

**Q7：复用 dsh web 深度定制，三周做得完吗？**
能。而且这个决定同时修掉两个既有错误：不再自建前端（砍掉大块无谓工作），
dsh 从「文本补全后端」回到基座位置（rubric 第 3、7 项由弱转强）。

---

## 三 走过的弯路（含证据）

留档是为了说明为什么现有代码需要重构，不是为了自我批评。

**错误一：把 dsh 塞进一个为「可互换模型后端」设计的抽象。**
`LLMProvider` 协议是给 anthropic / deepseek / hermes 这类模型后端用的：`complete()` 进，文本出。
把 dsh 套进去，等于主动丢弃工具执行、会话、子代理、上下文压缩、hooks、策略层与 session query。
结构性后果写在 `dsh.py` 里：`_build_prompt()` 把 system、所有轮次与 schema 折成一根字符串，
到那一步工作流已经被 Python 全部决定，dsh 没有任何控制点。症状也是同一个：`_parse()` 用正则从自由文本里刮 JSON。
需要写这个函数，本身就是位置错了的信号。正确形态下输出结构由 typed tool schema 约束，
不存在「从文本里刮 JSON」这一步。当时说的「先第一层、再第二层」也是错的：第一层的形状就错了，
它不是通往第二层的台阶。

**错误二：手写了框架已经有的东西。**
`MultiRoleEvaluatorAgent` 用 `asyncio.gather` 手写四角色并发。官方 `packages/subagent/` 提供 fan-out，
自动保留祖先关系（`HarnessClient` 保留子代理血缘，`RunResult.notifications` 按 wire order 收根与已知后代），
还支持 `ctx.subagentModelSelection` 按子代理选模型。

**错误三：把 `Orchestrator` 当成资产。**
「`Orchestrator` 不含框架依赖」被我反复讲成优点。在以 dsh 为基座的设计里，它正是要被替换的对象。

**错误四：范围蔓延。**
Docker、compose、AWS 章节、LF 规范化、CI 三件套、自建 Next.js 前端，都不是需求，
是在「仅做木桩与前期准备」的阶段自行加进去的。

---

## 四 能力边界：官方内置与实验性

### 可用：官方顶层包组

| 包组 | 关键包 | 用途 |
| --- | --- | --- |
| `core` | `tools`, `agent`, `agent-loop`, `system-prompt`, `session`, `scope` | 工具注册与代理循环 |
| `subagent` | `subagent`, `tool-subagent`, `tool-subagent-control`, `subagent-in-process-driver`, `subagent-fork-in-process` | 子代理 fan-out |
| `interaction` | **`user-approval`**, `tool-ask-user`, `user-questions`, `permission-presets`, `commands` | 人在环内 |
| `workflow` | `workflow`, `tool-workflow`, `workflow-worker-thread` | 工作流定制（本项目不用，见 7.4） |
| `guard` | `repeat-tool-reminder`, `timeout-policy` | 策略护栏 |
| `plan` | `plan-mode` | 规划模式（软引导，见 7.5） |
| `goal` | `goal`, `tool-goal`, `goal-round-driver` | 目标驱动 |
| `todo` | `tool-todo` | 任务清单 |
| `session-query` | — | 追踪、检索、过滤 |
| `skill` | `skill`, `tool-skill`, `skill-filesystem` | 技能 |
| `hooks` | `hook-protocol` | 拦截协议 |
| `sandbox` / `spill` / `typert` / `jobs` | — | 沙箱、溢出、类型注册、后台作业 |

### 不用：`packages/experimental/`

`agent-team`、`tool-agent-team`、`client-ui-agent-team`、`agent-team-profile`、
`agent-team-web-profile`、`code-runtime-python`、`inspector`、`webworker-*`。

### 关于 Agent Teams：不是因为实验性才不用

Agent Teams 是对等队友模型：持久化 mailbox（Steer 投递）、共享任务 DAG（`blockedBy` 边 + `writeScopes`）、
Lead 会话。我们的四个角色读同一份数据、各自独立出结论、从不需要互相说话；tension 是事后的合并步骤，
不是一场谈判。PRD 明确要求跨角色冲突交人裁决、系统不自动调和。给它们一条协商通道，正是我们不想要的行为，
也是「子代理越权」风险的来源。

结论：用官方 `subagent` fan-out。父收集结果，子代理之间没有通信通道。

---

## 五 目标架构

```text
                     dsh（基座）
   ┌──────────────────────────────────────────────────┐
   │  profile: 原生 Web，按企业策略默认禁用部分功能   │
   │  ├── 固定领域阶段       不运行模型编写的 workflow  │
   │  ├── subagent fan-out  四角色，无横向通信          │
   │  ├── ctx.approval      映射确认 / 隔离处置 / 报价放行│
   │  ├── tools.guard()     注入防御（单调终局拒绝）     │
   │  ├── session-query     调用追踪与检索              │
   │  └── tool.call.toolview  dsh web 自定义卡片        │
   └───────────────────────┬──────────────────────────┘
                           │ defineTool（TS 薄插件）
                           ▼
   ┌──────────────────────────────────────────────────┐
   │  BridgeFlow 领域工具（Python 实现体）              │
   │  batch_summary · aggregate_metric · lookup_dictionary│
   │  compute_capacity_load · compute_unit_cost         │
   │  —— pandas / openpyxl，确定性，结果不经模型         │
   └──────────────────────────────────────────────────┘
```

保留下来的既有资产只有两样，它们构成工具边界：Pydantic 类型契约（`bridgeflow.schemas`）
与确定性 pandas 计算。

输出之所以受控（这是选 dsh 的理由，也是它必须待在基座位置的理由）：

1. `defineTool` 在 `execute` 之前校验模型生成的 `arguments`；
2. `output.schema` 校验并冻结返回值，非法值即 `isError`；
3. `tools/pre-execute` 加 `guard()` 在派发前拒绝；
4. `ctx.approval` fail-closed：`allowed-once` 之外一律拒绝，答复者缺失、抛错、不合规都归为 `unavailable`，
   同样拒绝；
5. 子代理没有横向通道，越权面收敛。

---

## 六 rubric 符合性

不要把「采用了某项 DSH 能力」直接换算成 rubric 得分。目标架构以第五节与第七节为准，
当前逐项验收条件与远端 issue 建议见 [16 的 rubric 表](16-dsh-web-review.md#按充分实现-rubric-验收)，
实测数字见 [00](00-status.md)。

- 编排是固定阶段加官方 subagent fan-out，不是模型编写的 workflow。
- 工具必须执行真实批次并校验输入输出，不能退回 completion 包装。
- 人工批准必须绑定具体调用与参数；UI 隐藏不等于主机权限。
- 护栏、原生审批、父子 session、失败恢复都要有可执行验收。
- 模型结论必须通过数值、口径与引用校验；规则测试不代替研判质量评测。

本节原先写着「零工具、无 eval、模块 dict、仅一项达标」，那是对遗留 pipeline 的计分，已删除，
避免它继续驱动错误的排期。历史测量留在 `00` 的原实验记录里。

---

## 七 读官方文档得到的结论（2026-09-06）

六份文档读完（#42）。其中四条推翻了本文此前的假设，逐条列出。

**7.1 permission-presets 不控制工具册。** 它捆的是两个互相独立的旋钮：`sandbox/mode` 与 `approval/policy`。
默认表只有两项：`workspace-write`（workspace-write + ask）与 `danger-full-access`（danger-full-access + never）。
名字 `custom` 是保留字，表示「不匹配任何预设」的派生态，不能作为切换目标。它要求 `ctx.shell` 是 confining
的执行器，也要求 `ctx.approval`；在不 confining 的 bash 执行器上，组合会在插件加载期直接抛错。
所以「用 permission preset 做一个没有 bash 的 profile」这条路不成立：工具册由 profile 的 bundle 决定
（加载了哪些插件），不由 preset 决定。

**7.2 sandbox 只管写，不管读。** `SandboxMode` 的原文是 "governs filesystem effects only"：
`read-only` 拒绝写、只放行 shell 必需的 sink（如 `/dev/null`）；`workspace-write` 允许写 workspace root
与后端约定的 temp 区；`danger-full-access` 不约束。原文还明写
"Network and process visibility are outside this vocabulary."

这直接影响 #25 的解释：那 12 步 bash 干的是读 README、读源码、读测试、读 `git log`、读 `CLAUDE.md`，
在 `read-only` 下一模一样会发生。sandbox 不是信息泄漏的答案，它只挡破坏。
另外 `workspaceRoot` 来自会话的不可变 cwd，并做了 filesystem 语义的规范化（`symlink/..` 会解成
进程真正运行的目录）；`enforcement` 是一个上报的事实，`partial` 表示后端或旧内核 ABI 只能治理一部分，
需要绝对边界的调用方不能把 `partial` 当 `full` 用。

**7.3 `ctx.approval` 比我们以为的更严格。** `ApprovalOutcome` 是封闭四值：`allowed-once` /
`rejected` / `cancelled` / `unavailable`。缺失、不认领、抛异常、不合规的 answerer 一律变成
`unavailable`，而不是打开闸门。审计事件成对（`approval/asked` + `approval/decided`，由
`ApprovalRequestId` 配对）。policy `never` 的语义是每次 ask 确定性返回 `rejected`，不是自动放行，
它是 CI 与无人值守的严格立场。`dsh-tool-bash` 自己就消费这个 outcome：fail closed unless
`allowed-once`。

推论（待实测）：把 approval policy 设成 `ask` 且不挂任何 answerer，bash 应当被 `unavailable` 拒掉。
如果成立，这是 #26 的零代码即时缓解手段。这条必须先验证再写进方案，因为我们观测到 bash 畅通无阻，
说明 `sdk-minimal` 要么配了 answerer，要么 service config 的默认值不是 `ask`。

**7.4 `workflow` 不是我们要的东西。** 它的定位是模型自己写的编排脚本，把工作 fan out 给多个 subagent，
并且自己声明 "containment, not a security boundary"。这与 `docs/10` 里「Why a fixed pipeline rather than a
planning agent」直接冲突：财务数字要可审计、可复现，审批人不能签一个两次跑出不同结果的数。
让模型现场写编排脚本，正是我们明确排除的东西。

由此，#38「用 dsh workflow 取代自建 Orchestrator」的前提是错的，需要改写。rubric 第 2 项的正解更可能是：
固定阶段仍由我们编排，但状态与记忆落到 session 持久化，并用官方 `subagent` 做四角色 fan-out
（这本来就是第五节的结论）。

**7.5 plan mode 是软引导，不是执行约束。** 原文：plan mode is soft guidance；"Sandbox mode and approval
policy enforce restrictions independently; neither reads or writes plan state." 它贡献一个
`plan:policy` 提示词段落、注册 `exit_plan_mode` 工具与 `/plan` 命令。它不是 rubric 第 2 项的答案，别当护栏用。

**7.6 `goal` 是事件溯源的同会话目标服务。** `GoalId` 是 branded id，`GoalRef` 做 compare-and-set，
每次被接受的持久化变更递增 revision。它可能是 rubric 第 2 项 state/memory 的一块，但它是同会话的；
跨月记忆（#29）要另找机制。

**7.7 `defineTool` 的形状已确认。**

```ts
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'greet-tool'
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'greet',
    description: 'Greet someone by name.',
    parameters: { name: { type: 'string', required: true, description: '...' } },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) { return `Hello, ${args.name}!` },
  }))
}
```

`inject` 让 Cordis 等待工具注册表；`defineTool` 从 `parameters` 推导并校验 `args`；
`execute` 返回 `output.schema` 声明的规范值，`output.render` 把它转成模型可见内容。
`output.render` 就是 #40 UI 卡片的邻居。教程末尾指向 `cookbook/adding-a-tool.md`，
那里才有 nested schemas、canonical values、background work、policy hooks、PTC mode 与 UI cards
（#27 与 #40 的真正参考）。

**7.8 插件加载方式与本文此前写的不一致，待核实。** 教程用的是
`pnpm dsh web --patch ./scratch-plugin/cordis.yml`，而 `CLAUDE.md` 写的是
`dsh plugin --profile sdk-minimal add file:<绝对路径>`。两者是不是同一条路、`--patch` 是否支持 watch，
尚未确认。这直接决定插件开发循环的速度。

---

## 八 仍未验证与未读

未读：`docs/cookbook/adding-a-tool.md`（#27 与 #40 的真正参考，UI cards 在这里）、
`docs/subsystems/workflow.md`（只读了 package README）、
`docs/subsystems/session-query.md`（只读了纲要，追踪能力 #31 的细节未提取）。
Client 插件与 `tool.call.toolview` 注册现已实际接入并通过浏览器复演，见第九节。

待实测（这些不能靠读文档定论）：

- 把 approval policy 设成 `ask` 且不挂 answerer，bash 会不会被拒（见 7.3，#26 的即时手段）；
- `sdk-minimal` 当前的 approval policy 默认值到底是什么，因为我们观测到 bash 畅通；
- 禁用 shell 已由原生 Web composition 与终局 guard 实测，后续版本升级仍需回归；
- `--patch` 是否支持 link / watch（7.8）；
- WSL2 下 `dsh web` 的端口转发；
- 官方 spawn 已在独立子会话并行实测，不再把 SDK 同一会话的限制套在子会话上。

与其他文档的冲突已全部就地改完。这一节曾经挂着一张「待同步」表，而各文档顶上挂着「部分已过时」的横幅、
正文原样保留，等于要求读者做人肉 diff，而横幅拦不住跳读的人。现在的规矩写在
[`docs/README.md`](README.md) 的写作约定里：发现冲突就地改正文，整篇作废就改成指路牌。
当时的具体处理：`02` 就地改写了语义对齐一节（删掉字符串相似度的描述）；`05` 改成重定向存根，
旧内容留在 git 历史；`06` 删掉「第一层 / 第二层」框架，两处错误改记成「免得有人再走一遍」；
`09` 改了第 4 项评价，计分改为引用 `00-status`；`10` 由 PR #43 重排并加了新旧顺序对照表。

---

## 九 原生 Web 复用决策

默认产品入口使用官方 `dsh web`，加载 `dsh/enterprise.patch.yml` 与本地 Client/Host 插件。
保留原生会话、聊天、审批、轨迹与展示设置，新增的是领域数据面板与工具卡片。配置侧关掉插件编辑、
模型 / 权限 / 预设选择等能力，实际执行由主机白名单约束。原始数据分页接口只给已认证浏览器，
模型工具只收摘要、公式与有上限的证据引用。企业认证先复用 DSH 凭证；员工身份与角色权限须另有明确实现，
不能用自称姓名填补。

映射审批通过官方 composer slot 增加备注输入，决定仍由原生 `PendingApproval` 结算；
备注绑定会话、调用与临时票据，不授予写权限。

`review_batch` 通过官方 `ctx.subagents.start('spawn')` 创建部门子会话；子代理只提交 `structured_output`，
主机限制步骤、深度与时限。Python 从冻结字典计算事实，逐条校验数值、单位、状态、动作与来源，
报告里把模型的补充文字明确标为建议。实证与验收见 [17](17-business-mvp-acceptance.md)，
原生 UI 接缝、rc1 打包限制与实现审查见 [16](16-dsh-web-review.md)。

### Notebook 外层定制的边界

来源、原生会话、Studio 的整页布局保留官方 AppFrame 与原生占用者，只在 `shell.overlay` 增加面板，
并通过宿主公开的 `data-slot` 样式锚点定制几何与主题。不覆盖 `root` 后复制会话组件，也不搬移原生 DOM：
根槽覆盖会让原生子槽失去渲染权。会话与设置保留原生抽屉，工具详情仍由 `ctx.layout` 开关；
月度对账照常可用，报价声明在 Studio 中预览，月度状态页继续使用原生 `conversation.view`。
来源与产物走只读浏览器接口并复用 DSH 鉴权，来源正文不进入模型工具。
设计与实际可用范围见 [报价设计](21-quotation-design.md)，验证结果以 [实测状态](00-status.md) 为准。

### Web 与 SDK 的运行时必须一致

同一 `DSH_HOME` 下的 profiles 共用模块 fallback。Python 打包运行时会写入只在其进程内可用的
`/snapshot` 代理，正在运行的 npm Web 随后动态挂载 preset 时导入不了它们。所以项目 Web 启动器、
遗留 SDK provider 与 SDK smoke 共用 `bridgeflow.dsh_runtime.native_command`，SDK 显式传官方 `dsh_bin`，
统一使用锁定版本的 npm 安装，SDK smoke 也不再从 `.env` 读引导变量。直接试验打包 SDK 时必须另设独立
`DSH_HOME`：不同 profile 名称并不隔离共享 fallback。

已被改写的 fallback 由官方 npm 启动流程自愈，停止并重启 Web 也会清掉此前失败的模块导入缓存。
不手改生成入口，不删除用户 profiles、插件、凭据或会话。

### 插件元数据不写进原生日志

笔记本书签与审批备注使用官方 storage-domain；普通会话的身份、标题、历史与持久化仍归 DSH。
不能通过 `Session.append` 写入原生冷读取器不认识、又不能标记为可忽略的插件事件。
研判状态的生命周期从原生工具调用与结果投影而来；旧信息事件的兼容修复必须停机、保留原始备份、
显式运行。不要为此改写 DSH 的事件白名单，也不要跳过未知必需事件的校验。
恢复语义见 [报价与笔记本设计](21-quotation-design.md)。

### 产品扩展点

笔记本用途通过共享能力声明组合工作流，进度与完整页面以视图注册表渲染。用途仅控制呈现，不赋予工具权限。
领域工具的执行政策与官方工具定义同处声明，注册目录同时作为父工具授权来源；审批 gate 通过注入的目录取得说明、拒绝影响与回执请求体，避免与注册清单漂移。原生子代理限制及后端回执校验保持独立。
具体扩展步骤、OCP 的适用边界与验证方式见 [产品扩展契约](23-extension-contracts.md)。
