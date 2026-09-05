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

**不是。** `DshProvider` 只调 `harness.run()`，把 dsh 当文本补全后端。
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
   │  profile: sdk-minimal 起步，按需最小加法          │
   │  ├── workflow          阶段编排（取代 Orchestrator）│
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
   │  read_table · aggregate_metric · lookup_dictionary │
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

现状 = `main` 分支当前代码。目标 = 第五节架构。

| # | Rubric | 目标形态 | 现状 | 符合 |
| --- | --- | --- | --- | --- |
| 1 | Goal & Scope | HMW + PRD + 自洽样本数据 | 已完备 | ✅ |
| 2 | Architecture & Reasoning Loop | dsh `workflow` 编排；状态与记忆落在 session 持久化 | 自建 `Orchestrator`；状态在模块级 dict，重启即失 | ❌ |
| 3 | Tool Use & Integration | `defineTool` 领域工具，参数与返回值双向校验 | **零工具**，仅 `llm.complete()` | ❌ |
| 4 | Autonomy & HITL | `ctx.approval`（fail-closed + 审计事件对）+ `tool-ask-user` + `permission-presets` | 仅类型层的 `unresolved` 队列，**无人可介入** | ❌ |
| 5 | Safety & Guardrails | guard 插件拦截注入；`sdk-minimal` 最小工具册；least-privilege | **0 分，且 `evaluator.py:85` 有真实注入漏洞** | ❌ |
| 6 | Observability & Eval | `session-query` + `session-telemetry` + JSONL + approval 审计 | 有 `CorrectionLog` 与强制 evidence；**无代理级追踪，无 eval 套件** | ⚠️ |
| 7 | Platform & Tooling | 官方 subagent fan-out + workflow + dsh web 定制 | dsh 被塞进 `LLMProvider`，**反模式** | ❌ |

**当前 7 项中仅 1 项达标。**

这不是退步——是把"看起来能跑"换成了"照标准量"。第 2、3、4、5、7 项不达标的**同一个根因**是错误一：
dsh 被放在了错误的位置，因此它原生提供的编排、工具、审批、护栏、多代理能力全部闲置，
而我们用自建代码填补了其中一部分、遗漏了其余。

**换言之：修正架构本身就同时修正五项。** 这是当前投入产出比最高的动作，
远高于继续按 PRD 补功能。

---

## 七 待验证与未读

**未读文档**（影响设计细节，不影响上述结论）：

- `docs/subsystems/plan.md` / `goal.md` —— 可能直接提供 rubric 第 2 项的 planning pattern
- `docs/subsystems/permission-presets.md` —— least-privilege 的现成预设
- `docs/subsystems/session-query.md` —— 追踪能力的具体查询面
- `docs/user/develop/basic/tool.md` —— 第一个工具的有序教程，决定 TS→Python 的连接方式
- `packages/workflow/README.md` —— 工作流的表达能力边界
- Client 插件机制（`tool.call.toolview` 的具体注册方式）

**未验证的假设**：

- WSL2 下 `dsh web` 的端口转发未实测
- `sdk-minimal` 能否满足我们的工具需求（它只带 Bash + 编辑器 + 本地执行 + JSONL 会话）
- 单个 dsh runtime 的并发模型对 subagent fan-out 的影响
  （现已知 runtime 不能交错 turn，subagent 是否受同一限制未确认）

**与其他文档的冲突，待同步**：

- `docs/02-architecture.md:34` 仍描述已废弃的字符串相似度候选生成
- `docs/06` 的"第一层 / 第二层"框架已被本文推翻
- `docs/09` 把 rubric 第 4 项评为"设计强、实现弱"，实为**机制存在、体验不存在**
- `docs/10` 的三周计划基于自建前端与自建编排，需按本文重排
