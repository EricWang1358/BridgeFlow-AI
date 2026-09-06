# 13 — 黄金标准：dsh 为基座的架构决策与 rubric 符合性

本文是 BridgeFlow 关于 **DeepSeek Harness 如何被使用** 的唯一权威记录。
覆盖：决策问答、已纠正的错误、官方能力边界、目标架构、rubric 逐条比对。

与其他文档的关系：`06` 记录 dsh 的事实与 API，`09` 是 rubric 自评，`10/11` 是三周计划与复核。
**本文与它们冲突时以本文为准**，冲突处已在文末列出待同步项。

---

## 一 核心原则

> **围绕 dsh 官方内置插件构建。**
> 目的是消除一切可能导致 **输出错误 / 幻觉 / 子代理越权 / 未定义行为** 的来源。
> 第三方与 experimental 插件可选用，但必须逐个论证，且不得进入关键路径。

这条原则不是保守，是**可审计性的前提**。财务数字要能被签字，就不能建立在"行为未定义"的组件上。

### 模型做匹配，不做创造（2026-09-07 业务方定）

同一条可审计性，在字典这件事上给出的答案是:**标准格式与初始字典由人事先预设**。
业务方原话:「这个东西没有知识库,LLM 做不出来的」。

| | 谁做 |
| --- | --- |
| 标准格式模板、初始字典 | **人,事先** |
| 上传件清洗 | 系统,自动 |
| **上传列 → 已声明字段 的匹配** | **模型提议,人审核** |

**匹配的候选集是封闭的**——只能来自字典里已声明的字段,所以每条候选都能附证据、
让人做选择题;创造是开放的,签不了字。这与「结论必须带证据」是同一条原则的两面。

工具可以**描述列的形状**(`profile_batch`:唯一度、填充率、跨部门值重合度,全部不含
单元格)来支撑匹配;**不可以据此凭空生成声明**。硬约束原文见
[`../CLAUDE.md`](../CLAUDE.md)。

---

## 二 决策问答（已核实）

### Q1 — 能否 WSL 部署 + 反代，Windows 直连？

**能，而且大概率不需要反代。** WSL2 默认 localhostForwarding，`dsh web` 在 WSL 内监听，
Windows 浏览器开 `localhost:<port>` 即可。反代只在需要固定域名 / HTTPS / 同端口多服务时才引入。

**约束：`DSH_HOME` 必须位于 WSL 文件系统内（`/home/...`），不得放在 `/mnt/d`。**
跨文件系统 IO 会严重拖慢运行时。SDK 刻意不发现 `~/.dsh`，此项必填无默认值。

### Q2 — 客户前端先不做，先用 dsh 做实验？

**采纳，已执行。** 自建 Next.js 前端（`frontend/`）已删除——它是范围蔓延，且与"复用 dsh web 深度定制"冲突。
同批删除的还有 Dockerfile、docker-compose、CI workflow：部署目标未定，先加是错的。

定制入口已确认：Client 插件把工具的 wire name 注册进 **`tool.call.toolview` 键槽**，
从 `ToolCallBlock` 的参数、内容、错误、元数据派生组件 props。
「修复日志卡片」「待确认映射卡片」「报价对比卡片」都走这条路。

### Q3 — 当前是否是插件工作流？

当前默认入口已使用原生 DSH 领域工具与官方子代理，见第九节。旧路径中的 `DshProvider` 只调 `harness.run()`，把 dsh 当文本补全后端。
无 plugin、无 tool、未使用会话与工具执行。详见第三节的错误记录。

### Q4 — 能否禁用大部分功能以求干净 + 抗注入？

**能，这正是 `sdk-minimal` profile 的用途。** 它是**独立的显式组合树**，
不是 `dsh-base` 的覆盖层，只提供持久 Bash、字符串替换编辑器、本地执行、JSONL 会话；
settings、托管凭据、遥测、Web 工具、完整工具册都在另外的 `sdk` 与 `web` profile 中。
再用 profile 的 `$DSH_HOME/profiles/<p>/cordis.patch.yml` 继续做减法。

**抗注入的正确落点是策略层，不是提示词：**

| 扩展点 | 用途 |
| --- | --- |
| `tools/pre-execute` | 可重排的 allow / deny / ask 策略，返回 `{kind:'deny', reason}` |
| `ctx.tools.guard()` | **单调终局拒绝**，后续监听者无法撤销 |
| `tools/execute` | 包裹派发：超时、重试、指标 |
| `tools/post-execute` | 替换展示内容或返回值、阻断结果 |
| `tools/result` | 观察不可变的最终结果 |

注入防御应是一个 **guard 插件**，而非散落在提示词里的边界标记。框架层拦截是硬约束，提示词是软约束。

### Q5 — 能否用 dsh 自带工具检查工具调用历史？

**能，且基本白拿。** 官方提供 `packages/session-query`（reads / traces / filters / search）、
`session-telemetry` + otel、`session-persistence-jsonl`。
`ctx.approval` 另外提供成对审计事件 `approval/asked` + `approval/decided`。

### Q6 — 操作 xls 用 Python 还是 TypeScript？

**分两层：工具定义必须是 TS，实现体可调 Python。**
`defineTool` / `ctx.tools` 是 Cordis 的 TS API。xlsx / pandas 留在 Python 是对的。
形态为「TS 薄插件（schema + 调度）→ Python 计算」。

**注意：`packages/experimental/code-runtime-python` 是实验性的**，
因此"让模型在 dsh 内直接跑 Python"这条路不走。Python 以进程/服务方式位于工具实现体之后。

具体连接方式（subprocess vs 本地 HTTP）待读 `user/develop/basic/tool.md` 后确定。

### Q7 — 复用 dsh web 深度定制，三周工作量，能执行？

**能。** 且此决定同时修正两个既有错误：不再自建前端（砍掉大块无谓工作）、
dsh 从"文本补全后端"回到基座位置（rubric 第 3、7 项由弱转强）。

---

## 三 已纠正的错误（含证据）

记录在案，因为它们解释了为什么现有代码需要重构。

### 错误一：把 dsh 塞进为「可互换模型后端」设计的抽象

`LLMProvider` 协议是给 anthropic / deepseek / hermes 这类**模型后端**用的：`complete()` 进，文本出。
把 dsh 套进去，等于主动丢弃工具执行、会话、子代理、上下文压缩、hooks、策略层、session query。

**结构性后果**：`dsh.py` 的 `_build_prompt()` 把 system + 所有轮次 + schema 折成一根字符串。
到那一步工作流已被 Python 全部决定，**dsh 没有任何控制点**。

**症状**：`_parse()` 用正则从自由文本里刮 JSON。
需要写这个函数本身就是位置错误的信号——正确形态下输出结构由 typed tool schema 约束，
不存在"从文本里刮 JSON"这一步。

**"第一层 → 第二层"的说法也是错的。** 第一层形状就错，不是通往第二层的台阶。

### 错误二：手写了框架已有的东西

`MultiRoleEvaluatorAgent` 用 `asyncio.gather` 手写四角色并发。
dsh 官方 `packages/subagent/` 提供 fan-out，并自动保留**祖先关系追踪**
（`HarnessClient` 保留子代理血缘，`RunResult.notifications` 按 wire order 收根 + 已知后代），
还支持 `ctx.subagentModelSelection` **按子代理选模型**。

### 错误三：`Orchestrator` 被当成资产

我反复把"`Orchestrator` 不含框架依赖"讲成优点。
在以 dsh 为基座的设计里，**它正是要被替换的对象**。

### 错误四：范围蔓延

Docker / compose / AWS Linux 章节 / LF 规范化 / CI 三件套 / 自建 Next.js 前端——
均非需求，在"仅做木桩与前期准备"阶段自行加入。

---

## 四 能力边界：官方内置 vs 实验性（已核实）

### 可用——官方顶层包组

| 包组 | 关键包 | 用途 |
| --- | --- | --- |
| `core` | `tools`, `agent`, `agent-loop`, `system-prompt`, `session`, `scope` | 工具注册与代理循环 |
| `subagent` | `subagent`, `tool-subagent`, `tool-subagent-control`, `subagent-in-process-driver`, `subagent-fork-in-process` | **子代理 fan-out** |
| `interaction` | **`user-approval`**, `tool-ask-user`, `user-questions`, `permission-presets`, `commands` | **人在环内** |
| `workflow` | `workflow`, `tool-workflow`, `workflow-worker-thread` | **工作流定制** |
| `guard` | `repeat-tool-reminder`, `timeout-policy` | 策略护栏 |
| `plan` | `plan-mode` | 规划模式 |
| `goal` | `goal`, `tool-goal`, `goal-round-driver` | 目标驱动 |
| `todo` | `tool-todo` | 任务清单 |
| `session-query` | — | 追踪、检索、过滤 |
| `skill` | `skill`, `tool-skill`, `skill-filesystem` | 技能 |
| `hooks` | `hook-protocol` | 拦截协议 |
| `sandbox` / `spill` / `typert` / `jobs` | — | 沙箱、溢出、类型注册、后台作业 |

### 不用——`packages/experimental/`

`agent-team`、`tool-agent-team`、`client-ui-agent-team`、`agent-team-profile`、
`agent-team-web-profile`、**`code-runtime-python`**、`inspector`、`webworker-*`。

### 关于 Agent Teams 的判断

**不是因为它实验性才不用，是语义上就不该用。**

Agent Teams 是对等队友模型：持久化 mailbox（Steer 投递）、共享任务 DAG（`blockedBy` 边 + `writeScopes`）、Lead 会话。
而我们的四个角色**读同一份数据、各自独立出结论、从不需要互相说话**——tension 是事后的合并步骤，不是一场谈判。

PRD 明确要求跨角色冲突交由人裁决、系统不自动调和。
给它们一条协商通道，正是我们不想要的行为。**这同时也是"子代理越权"风险的来源。**

结论：用官方 `subagent` fan-out。父收集结果，子代理之间无通信通道。

---

## 五 目标架构

```
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

**保留的既有资产只有两样**，且它们成为工具边界：
Pydantic 类型契约（`bridgeflow.schemas`）与确定性 pandas 计算。

**输出如何受控**（这是选用 dsh 的理由）：

1. `defineTool` 在 `execute` 前校验模型生成的 `arguments`
2. `output.schema` 对返回值做校验 + 冻结，非法值即 `isError`
3. `tools/pre-execute` + `guard()` 在派发前拒绝
4. `ctx.approval` **fail-closed**：`allowed-once` 之外一律拒绝，
   答复者缺失 / 抛错 / 不合规均归为 `unavailable`，同样拒绝
5. 子代理无横向通道，越权面收敛

---

## 六 rubric 逐条比对

目标架构以第五节与第七节核实结论为准；不要把采用某项 DSH 能力直接换算成 rubric 满分。
当前逐项验收条件与远端 issue 建议见 [16 的 Rubric 表](16-dsh-web-review.md#按充分实现-rubric-验收)，
实测数字见 [00](00-status.md#原生-web-重构复测2026-09-06)。

- 编排采用固定阶段与官方 subagent fan-out，**不是模型编写的 workflow**。
- 工具必须执行真实批次并校验输入输出，不能退回 completion 包装。
- 人工批准必须绑定具体调用和参数；UI 隐藏不能替代主机权限。
- 护栏、原生审批、父子 session、失败恢复都要有可执行验收。
- 模型结论必须通过数值、口径与引用校验；规则测试不代替研判质量评测。

本节原来的“零工具、无 eval、模块 dict、仅一项达标”等描述已过期，删除该计分，
避免它继续驱动错误排期。历史测量仍保留在 `00` 的原实验记录。

---

## 七 已读文档的结论（2026-09-06）

六份文档已读（#42）。**其中四条推翻了本文此前的假设，逐条列出。**

### 7.1 permission-presets 不控制工具册 ⚠️ 推翻假设

它捆的是两个**互相独立**的旋钮：`sandbox/mode` 与 `approval/policy`。
默认表只有两项：`workspace-write`（workspace-write + ask）与
`danger-full-access`（danger-full-access + never）。名字 `custom` 是保留字，
是"不匹配任何预设"的派生态，不能作为切换目标。

它**要求** `ctx.shell` 是 confining 的执行器、并且**要求** `ctx.approval`；
在不 confining 的 bash 执行器上组合会在插件加载期直接抛错。

> **所以「用 permission preset 做一个没有 bash 的 profile」这条路不成立。**
> 工具册由 profile 的 bundle 决定（加载了哪些插件），不由 preset 决定。

### 7.2 sandbox 只管写，不管读 ⚠️ 推翻假设

`SandboxMode` 的原文是 "governs filesystem effects only"：

| 模式 | 含义 |
| --- | --- |
| `read-only` | **拒绝写**，只放行 shell 必需的 sink（如 `/dev/null`） |
| `workspace-write` | 允许写 workspace root 与后端约定的 temp 区 |
| `danger-full-access` | 不约束 |

而且明写 **"Network and process visibility are outside this vocabulary."**

> **这意味着 #25 观测到的那 12 步 bash——读 README、读源码、读测试、读 `git log`、
> 读 `CLAUDE.md`——在 `read-only` 下会一模一样地发生。**
> sandbox 不是信息泄漏的答案，它只挡破坏。

另外 `workspaceRoot` 来自会话的不可变 cwd，且做了 filesystem 语义的规范化
（`symlink/..` 会被解成进程真正运行的目录）。`enforcement` 是一个**上报的事实**，
`partial` 表示后端或旧内核 ABI 只能治理一部分——需要绝对边界的调用方**不得**把
`partial` 当成 `full`。

### 7.3 `ctx.approval` 比我们写的还严格 ✅ 确认且加强

- `ApprovalOutcome` 是封闭四值：`allowed-once` / `rejected` / `cancelled` / `unavailable`
- **缺失、不认领、抛异常、不合规的 answerer 一律变成 `unavailable`，而不是打开闸门**
- 审计事件成对：`approval/asked` + `approval/decided`，由 `ApprovalRequestId` 配对
- policy `never` 的语义是**每次 ask 确定性返回 `rejected`**，不是"自动放行"。
  它是 CI / 无人值守的严格立场
- **`dsh-tool-bash` 自己就消费这个 outcome，fail closed unless `allowed-once`**

> **推论（待实测）：把 approval policy 设成 `ask` 且不挂任何 answerer，
> bash 应当被 `unavailable` 拒掉。如果成立，这是 #26 的即时缓解手段，且是零代码的。**
> 这条必须先验证再写进方案——我们目前观测到 bash 畅通无阻，说明 `sdk-minimal`
> 要么配了 answerer，要么 service config 的默认值不是 `ask`。

### 7.4 `workflow` 不是我们要的东西 ⚠️ 推翻假设

`packages/workflow` 的定位是"**模型自己写的**编排脚本，把工作 fan out 给多个 subagent"。
而且它自己声明：**"containment, not a security boundary"**。

这跟 `docs/10` 里"Why a fixed pipeline rather than a planning agent"直接冲突——
财务数字要可审计、可复现，审批人不能签一个两次跑出不同结果的数。
让模型现场写编排脚本，正是我们明确排除的东西。

> **#38「用 dsh workflow 取代自建 Orchestrator」的前提是错的。**
> rubric 第 2 项的正解更可能是：固定阶段仍由我们编排，
> 但**状态与记忆落到 session 持久化**，并用官方 `subagent` 做四角色 fan-out
> （这本来就是本文第五节的结论）。#38 需要改写。

### 7.5 plan mode 是软引导，不是执行约束

原文：plan mode is **soft guidance**；"Sandbox mode and approval policy enforce
restrictions independently; neither reads or writes plan state"。
它贡献一个 `plan:policy` 提示词段落，注册 `exit_plan_mode` 工具和 `/plan` 命令。

> 不是 rubric 第 2 项的答案。别把它当护栏。

### 7.6 `goal` 是事件溯源的同会话目标服务

`GoalId` 是 branded id，`GoalRef` 做 compare-and-set：每次被接受的持久化变更递增 revision。
可能是 rubric 第 2 项 state/memory 的一块，但它是**同会话**的，跨月记忆（#29）要另找机制。

### 7.7 `defineTool` 的形状已确认 ✅

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

> **`output.render` 就是 #40 UI 卡片的邻居。** 教程末尾指向
> `cookbook/adding-a-tool.md`，那里才有 nested schemas、canonical values、
> background work、policy hooks、PTC mode 和 **UI cards**——#27 与 #40 的真正参考，**尚未读**。

### 7.8 插件加载方式与本文此前写的不一致 ⚠️ 待核实

教程用的是：

```sh
pnpm dsh web --patch ./scratch-plugin/cordis.yml
```

而 `CLAUDE.md` 写的是 `dsh plugin --profile sdk-minimal add file:<绝对路径>`。
两者是不是同一条路、`--patch` 是否支持 watch，**未确认**。这直接决定插件开发循环的速度。

---

## 八 仍未验证与未读

**未读**：

- `cookbook/adding-a-tool.md` —— #27 与 #40 的真正参考（UI cards 在这里）
- `docs/subsystems/workflow.md` —— 只读了 package README
- `docs/subsystems/session-query.md` —— 只读了纲要，追踪能力（#31）的细节未提取
Client 插件与 `tool.call.toolview` 注册现已实际接入并通过浏览器复演，见第九节。

**待实测**（这些不能靠读文档定论）：

- **把 approval policy 设成 `ask` 且不挂 answerer，bash 会不会被拒**（见 7.3，#26 的即时手段）
- `sdk-minimal` 当前的 approval policy 默认值到底是什么——我们观测到 bash 畅通
- 禁用 shell 已由原生 Web composition 与终局 guard 实测，后续仍需版本升级回归
- `--patch` 是否支持 link/watch（7.8）
- WSL2 下 `dsh web` 的端口转发
- 官方 spawn 已在独立子会话并行实测；不再把 SDK 同一会话限制套在子会话上

**与其他文档的冲突：已全部就地修完，本清单清空。**

之前这里挂着一张"待同步"表，而各文档顶上挂着"部分已过时"的横幅、正文原样保留——
等于要求读者做人肉 diff，而横幅拦不住跳读的人。现在的处理：

| 文档 | 做法 |
| --- | --- |
| `docs/02` | 语义对齐一节**就地改写**，字符串相似度的描述已删 |
| `docs/05` | 整篇被取代 → 改成重定向存根，旧内容留在 git 历史 |
| `docs/06` | "第一层 / 第二层"框架已删，两处错误改记成"免得有人再走一遍" |
| `docs/09` | 第 4 项评价已改；计分改为引用 `00-status` |
| `docs/10` | PR #43 已重排，加了新旧顺序对照表 |

**新规矩：发现冲突就地改，不要盖横幅。**

## 九 原生 Web 复用决策

默认产品入口使用官方 npm `dsh web`，加载 `dsh/enterprise.patch.yml` 与本地 Client/Host 插件。
保留原生会话、聊天、审批、轨迹与展示设置；新增领域数据面板和工具卡片。
配置关闭插件编辑、模型/权限/预设选择等能力，并以主机白名单约束实际执行。
原始数据分页接口仅供已认证浏览器，模型工具只收摘要、公式与有上限的证据引用。
企业认证先复用 DSH 凭证，员工身份与角色权限须另有明确实现，不能用自称姓名填补。

映射审批通过官方 composer slot 增加备注输入，决定仍由原生 PendingApproval 结算；备注绑定会话、调用及临时票据，不授予写权限。

`review_batch` 通过官方 `ctx.subagents.start('spawn')` 创建部门子会话；子只提交 `structured_output`，主机限制步骤、深度与时限。Python 从冻结字典计算事实，逐条校验数值、单位、状态、动作及来源；报告将补充文字明确标为模型建议。实证与验收见 [17](17-business-mvp-acceptance.md)。

原生 UI 接缝、rc1 打包限制与本次实现审查见 [16](16-dsh-web-review.md)。

### Notebook 外层定制的边界

来源、原生会话、Studio 的整页布局保留官方 AppFrame 与原生占用者，只在 `shell.overlay` 增加面板，并通过宿主公开的 `data-slot` 样式锚点定制几何与主题。不得覆盖 `root` 后复制会话组件或搬移原生 DOM；根槽覆盖会丢失原生子槽的渲染权。会话与设置保留原生抽屉，工具详情仍由 `ctx.layout` 开关。报价声明在 Studio 中预览，月度状态页继续使用原生 `conversation.view`。来源与产物的只读浏览器接口复用 DSH 鉴权，来源正文不进入模型工具。设计与实际可用范围见 [报价设计](21-quotation-design.md)，验证以 [实测状态](00-status.md) 为准。

### Web 与 SDK 的运行时必须一致

同一 `DSH_HOME` 下的 profiles 共用模块 fallback。Python 打包运行时会写入只在其进程内可用的 `/snapshot` 代理；正在运行的 npm Web 随后动态挂载 preset 时无法导入它们。项目 Web 启动器、遗留 SDK provider 与 SDK smoke 共用 `bridgeflow.dsh_runtime.native_command`，SDK 显式传官方 `dsh_bin`，统一使用锁定版本的 npm 安装。SDK smoke 不再从 `.env` 读取引导变量。直接试验打包 SDK 时必须另设独立 `DSH_HOME`。

已经被改写的 fallback 由官方 npm 启动流程自愈；停止并重启 Web 也清除此前失败的模块导入缓存。不手改生成入口，不删除用户 profiles、插件、凭据或会话；不同 profile 名称不能隔离共享 fallback。


笔记本书签与审批备注使用官方 storage-domain；普通会话身份、标题、历史与持久化仍属于 DSH。不得通过 Session.append 写入原生冷读取器不认识且不能标记为可忽略的插件事件。研判生命周期从原生工具调用和结果投影，旧信息事件的兼容修复必须停机、保留原始备份且显式运行；不得为此改写 DSH 事件白名单或跳过未知必需事件校验。具体恢复语义见 [报价与笔记本设计](21-quotation-design.md)。
