# 15 — dsh 插件设计

> 骨架文档。读官方文档得到的插件形态结论落在这一页，不要散进 `HANDOFF.md`（那份自己声明会过期）。
> 已确认的官方事实进 [`13` 第七节](13-golden-standard.md)，怎么落成插件进本文。
>
> 现状：`plugins/` 已存在并跑通（PR #53）。三个工具落地，端到端验证过一次：模型调
> `aggregate_metric` → 到达 Python → 返回 4,030 units 并列出五行来源。剩下的主要是 UI 槽位（#40）
> 与审批接线（#39），两件都已在后续 sprint 完成，见 `18`。

## 一 已知的形状

### 1.1 一个工具长什么样（已确认，`docs/user/develop/basic/tool.md`）

```ts
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'greet-tool'
export const inject = ['tools']          // 让 Cordis 等待工具注册表

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'greet',
    description: 'Greet someone by name.',
    parameters: { name: { type: 'string', required: true, description: '...' } },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],   // → 模型可见内容
    },
    async execute(args) { return `Hello, ${args.name}!` },
  }))
}
```

`defineTool` 从 `parameters` 推导并校验 `args`；`execute` 返回 `output.schema` 声明的规范值。

### 1.2 配置怎么写（`docs/user/develop/basic/config.md`）

导出 `Config` 类型加同名 Schemastery schema，默认值直接写在字段上。dsh 自己的设计原则是
「不要硬编码可调值」：两个部署可能想设成不同值的东西，一律是配置字段；判据是
「`cordis.yml` 能不能不改代码就改掉它」。

这跟 `CLAUDE.md` 第八条硬约束（字段名绝不写进代码）是同一条原则，只是对象不同：那条管客户的表结构，
这条管部署参数。

### 1.2b 为什么 Python 侧关不上这个口子（已核实）

`deepseek_harness` 整个包 911 行、零处 `tool`，认识的 method 只有 `session/prompt` 与几个事件名。
反向通道（`HarnessClient.next_request` / `respond`）存在，但高层 `DeepSeekHarness.run()` 完全没有泵它。

它是客户端，不是插件宿主。rubric 第 3、4、5、7 项之所以长期不达标而 pipeline 跑得好好的，
就是因为它们不在运行时的同一侧：把工具、审批、护栏写在 TS 那一侧，Python 才能被当工具调用。

### 1.3 补丁层（已实测）

profile 的组成顺序是：`package.json` 的 `dsh.profile.bundles` 各层 → `cordis.patch.yml` →
`--patch` 覆盖层。补丁条目支持 id 定向的配置覆盖、disable 与 insert 列表。

```yaml
# 关掉工具
- id: persistent-bash
  disabled: true

# 装自己的插件
- insert:
    - id: bridgeflow-tools
      name: './plugins/src/tools.ts'
      config: { ... }
```

实测：`dsh/no-shell.patch.yml` 关掉 bash 之后，一次裁决从 12 步工具调用变成 0 步。

已知限制：`disabled: true` 只在基础条目本身已声明 `disabled` 字段时才生效
（`persistent-bash` / `persistent-pwsh` 有，`str-replace-editor` 没有，所以关不掉）。见 #37。

### 1.4 `sdk-minimal` 的工具册（已实测）

`persistent-bash`、`persistent-pwsh`、`str-replace-editor`，外加基础设施插件。approval 插件未加载，
所以 bash 没有闸门。

```bash
$RUNTIME --profile sdk-minimal --dump-config | grep '^- id:'
```

### 1.5 Web Client 是一整套槽位系统（已读）

不是只有工具卡片可以定制。`docs/subsystems/slots.md`：`root` 是唯一内置声明，其余整个界面由约 50 个
typed React 槽位组成，插件通过 `ctx.slots.register()` 贡献。

```text
root
├─ sidebar          brand.mark · brand.name · footer.action · workspaces · settings
├─ conversation     view · chat.node · tool.call.toolview · session.header.actions
│                   conversation.approval.detail   ← 审批 UI 的现成槽位（#39 / #30）
│                   composer.bar · input.dock · hero.brand.mark
├─ details          conversation.details.tool
└─ shell.overlay
```

规则里明写 "Treat `single` and an occupied keyed cell as replacement points"，也就是可以替换已有占位，
不只是往里加。

工具卡片仍然要写两半：Host 侧的 `presentCall` / `presentResult` dsh web 不消费，web 卡片走 Client 插件
注册进 `tool.call.toolview` 加 `output.presentationMeta`。但这是工具卡片的局部规则，不是 UI 的边界。

### 1.6 guard 挂载点（已确认并落地）

| 扩展点 | 用途 |
| --- | --- |
| `tools/pre-execute` | 可扩展的 allow / deny / ask 策略 |
| `ctx.tools.guard()` | 最终单调拒绝，后续监听器无法撤销 |
| `tools/execute` | 包住 dispatch，加超时、重试、埋点 |
| `tools/post-execute` | 替换呈现内容或返回值、拦结果 |
| `tools/result` | 观察不可变的规范化结果 |

`plugins/src/guards/untrusted-input.ts` 用的是 `guard()` 而不是 `pre-execute`：pre-execute 是
可扩展的策略，任何可扩展的东西将来都能被 argue 掉；一条可以被推翻的信任边界不是信任边界。

### 1.7 长任务

`ctx.jobs.start({ kind, label, owner: exec.agent, run })`，由 `run_in_background` 的 producer config 开关。
成功的后台分支返回 `{ kind: 'background', jobId }` 这样的规范句柄，PTC 模式不去解析人话里的 id。
发布 id 之后要改用 task 自己的取消信号，不再用 `exec.signal`：外层调用取消只停止等待，
不会杀掉已经发布出去的工作。

## 一之二 工作室的信息架构（2026-09-20 重构）

设计稿（Claude Design 画布，团队可见）：<https://claude.ai/artifact/MMeAdd9m4M6Eo4PdvfUZCx> —
七块画板：信息架构对照、主骨架、结论页（中文 / 英文两版）、数据时间线、本月任务、
可观测（一次运行一张图）。代码与画板保持同一套语言；改了界面就同步改画板，不要让两边各说一套。

十一轮迭代之后，工作室出现了典型的堆叠症状：新功能总是加在「最近的那个面板」上，于是同一件事有了两个入口。
重构只改归属与层级，不改配色，也没有自建前端（仍是 dsh web 的深度定制）。

**四个去处，按「人在做什么」分**，取代此前并列的八个按钮：

| 去处 | 回答的问题 | 里面有什么 |
| --- | --- | --- |
| 本月任务 | 我还要做什么 | 进度清单（E14-UC01）、待确认事项（E14-UC05）、发起研判、工作流状态 |
| 数据 | 这个月的数据长什么样 | 四部门文件行（取模板 E14-UC02、上传、单部门补传 E14-UC04、来源预览）、数据质量、跨部门总表 |
| 结论 | 这个月得出了什么 | 一页结论（E13-UC01）、对比（UC02）、图表（UC03）、导出（UC04）、关注项与出处 |
| 记录 | 谁在什么时候定了什么 | 批次版本链、口径决定（E13-UC05）、预警处置（E07-UC07）、产物清单 |

三条规则：

1. **同一功能只在一个去处有入口**，别处只能给一个「去处理」的跳转。收件箱本来就是这样做的，其余照抄。
   2026-09-20 复查时发现第一轮只改了主导航，另外两条路还在：侧栏底部的「数据工作区」按钮、会话头部的
   「部门文件」抽屉（里面是第二个导入表单）。两个插槽已撤，旧弹窗降级为**批次数据表**——它只保留自己独有的
   行级表格（清洗记录、待确认映射、列匹配、隔离行、研判报告），发起研判、版本链提示、批次计数这些已经有家的
   东西从它身上删掉，并且它不再有自己的入口，只能从「数据」页点进去。`tests/tool-catalogue.test.ts` 钉死这条：
   再出现第二个入口必须是一次明确的改动。
2. **右侧固定栏只陈述当前批次的事实**（完整行、待确认数、声明版本），不放操作；操作跟着内容走。
3. **结论页分三层**：一眼看完 → 数字 → 展开核对。管理层读完第一层可以走，出处、图与口径默认折叠。

进度清单与收件箱合并的理由值得单记：它们读的是同一份事实（清单说「总表待确认 4 条」，收件箱把那 4 条列出来），
分成两个面板等于让人把同一个数读两遍，还要自己判断哪个更新。现在它们并排且互相定位——聚焦某一步，右侧只留它在等的事项。

**字体按中英双语定**：展示面最终是英文，所以拉丁字体必须排在字体栈第一位——
标题 `Source Serif 4`、正文 `Source Sans 3`，中文回落思源宋体 / 思源黑体（同一超家族，
混排如「批次 68e801a9」不会一半粗一半细），数字统一 `tabular-nums`。让思源黑体去排英文是这套里唯一不能犯的错。

**打开的页面排在产物之前**：第一轮把它放在工作室栏的产物列表之后，于是点开「数据」要先滚过一屏工具和产物才看得到内容——
截图上一眼就看出来了。现在开着的去处紧跟在四个磁贴下面，「其他工作区」降为安静的单行。

**窄栏下用换行，不用挤**：运行泳道与决策明细原先是固定列宽网格，在 370px 的工作室栏里会把标签压成「r」「ba」这种
读不出来的碎片。改为按内容换行；泳道区保留最小宽度并允许横向滚动——宁可让人滑一下，也不给一排看不懂的色块。

**新页面不按视口排版**：它们渲染在宽度与窗口无关的侧栏里，`@media (max-width)` 会在窄栏下把两栏叠在一起
（浏览器旅程实测点不到补传按钮），因此一律按内容宽度换行（`flex-wrap` + `flex-basis`）。

## 二 剩下的设计项

| 要设计的 | 依赖哪份文档 | issue |
| --- | --- | --- |
| 其余领域工具的签名与返回值形状 | `docs/cookbook/adding-a-tool.md`（已读） | #27 |
| 三张 toolview 卡片怎么注册 | `docs/subsystems/slots.md`（已读，见 §1.5） | #40 |
| guard 插件拦注入的挂载点 | 已确认并落地：`ctx.tools.guard()`，见 §1.6 | #26 |
| 审批点怎么接 `ctx.approval` | `docs/subsystems/approval.md`（已读，见 `13` §7.3） | #39 |
| 四角色 subagent fan-out | `packages/subagent` | #38 |
| 决策追踪怎么查 | `docs/subsystems/session-query.md`（只读了纲要） | #31 |

## 三 已经排除的做法

| 做法 | 为什么不做 | 出处 |
| --- | --- | --- |
| 用 `permission-presets` 砍工具 | 它只捆 sandbox 与 approval 两个旋钮，不决定有哪些工具 | `13` §7.1 |
| 用 sandbox 挡信息泄漏 | 只管写不管读，网络与进程可见性也在词汇表之外 | `13` §7.2 |
| 用 `workflow` 取代 `Orchestrator` | 那是模型自己写编排脚本，与「财务数字必须可复现」冲突 | `13` §7.4 |
| 用 plan mode 当护栏 | soft guidance，什么都不强制 | `13` §7.5 |
| fork dsh | 版本全是预发布且明示会破坏性变更 | `CLAUDE.md` |
| Agent Teams | 在 `packages/experimental/` 里，而且四个角色不需要互相说话 | `CLAUDE.md`、`13` 第四节 |
