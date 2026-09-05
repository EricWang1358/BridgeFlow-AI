# 15 — dsh 插件设计

> **骨架文档。** 读完官方文档得到的插件形态结论**落在这里**，不要再散进 `HANDOFF.md`——
> 那份声明自己会过期。已确认的事实进 [`13`](13-golden-standard.md) 第七节，
> **怎么落成插件**进本文。
>
> 当前状态：**`plugins/` 已存在并跑通**（PR #53）。三个工具落地，端到端验证过：
> 模型调 `aggregate_metric` → 到达 Python → 返回 4,030 units 并列出五行来源。
> 剩下的是 UI 槽位（#40）与审批接线（#39）。

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

导出 `Config` 类型 + 同名 Schemastery schema，默认值直接写在字段上。
**dsh 自己的设计原则是「不要硬编码可调值」**——「两个部署可能想设成不同值的东西一律是配置字段」，
判据是「`cordis.yml` 能不能不改代码就改掉它」。

> 这跟 `CLAUDE.md` 第八条硬约束（字段名绝不写进代码）是同一条原则。

### 1.2b 为什么 Python 关不上这个口子（已核实）

`deepseek_harness` 整个包 **911 行，零处 `tool`**，认识的 method 只有 `session/prompt`
与几个事件名。反向通道（`HarnessClient.next_request` / `respond`）存在，但高层
`DeepSeekHarness.run()` **完全没有泵它**。

**它是客户端，不是插件宿主。** rubric 第 3/4/5/7 项之所以长期是 ❌ 而 pipeline 跑得好好的，
就是因为它们不在运行时的同一侧。

### 1.3 补丁层（已实测）

profile 的组成是：`package.json` 的 `dsh.profile.bundles` 各层 → `cordis.patch.yml`
→ `--patch` 覆盖层。补丁条目支持 **id 定向的配置覆盖、disable、insert 列表**。

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

实测：`dsh/no-shell.patch.yml` 关掉 bash 后，一次裁决从 12 步工具调用变成 0 步。
**⚠️ 已知限制：`disabled: true` 只在基础条目本身已声明 `disabled` 时才生效**
（`persistent-bash` / `persistent-pwsh` 有，`str-replace-editor` 没有，关不掉）。见 #37。

### 1.4 `sdk-minimal` 的工具册（已实测）

`persistent-bash` · `persistent-pwsh` · `str-replace-editor`，外加基础设施插件。
**approval 插件未加载**——所以 bash 没有闸门。

```bash
$RUNTIME --profile sdk-minimal --dump-config | grep '^- id:'
```

### 1.5 Web Client 是一整套槽位系统（已读）

**不是只有工具卡片可以定制。** `docs/subsystems/slots.md`：`root` 是唯一内置声明，
其余整个界面由约 50 个 typed React 槽位组成，插件通过 `ctx.slots.register()` 贡献。

```
root
├─ sidebar          brand.mark · brand.name · footer.action · workspaces · settings
├─ conversation     view · chat.node · tool.call.toolview · session.header.actions
│                   conversation.approval.detail   ← 审批 UI 的现成槽位（#39 / #30）
│                   composer.bar · input.dock · hero.brand.mark
├─ details          conversation.details.tool
└─ shell.overlay
```

规则里明写「**Treat `single` and an occupied keyed cell as replacement points**」——
**可以替换已有占位**，不只是往里加。

工具卡片仍然要写两半：Host 侧的 `presentCall` / `presentResult` **dsh web 不消费**，
web 卡片走 Client 插件注册进 `tool.call.toolview` + `output.presentationMeta`。
但这是工具卡片的局部规则，不是 UI 的边界。

### 1.6 guard 挂载点（已确认并落地）

| 扩展点 | 用途 |
| --- | --- |
| `tools/pre-execute` | 可扩展的 allow / deny / ask 策略 |
| **`ctx.tools.guard()`** | **最终单调拒绝，后续监听器无法撤销** |
| `tools/execute` | 包住 dispatch，加超时、重试、埋点 |
| `tools/post-execute` | 替换呈现内容或返回值、拦结果 |
| `tools/result` | 观察不可变的规范化结果 |

`plugins/src/guards/untrusted-input.ts` 用的是 `guard()` 而不是 `pre-execute`：
**可以被后面的人argue回去的信任边界，不是信任边界。**

### 1.7 长任务

`ctx.jobs.start({ kind, label, owner: exec.agent, run })`，由 `run_in_background`
producer config 开关。成功的后台分支返回 `{ kind: 'background', jobId }` 这样的
规范句柄——**PTC 模式绝不能去解析人话里的 id**。

发布 id 之后要改用 task 自己的取消信号，不再用 `exec.signal`：外层调用取消只停止等待，
不会杀掉已发布的工作。

## 二 待设计（读完剩余文档后填）

| 要设计的 | 依赖哪份文档 | issue |
| --- | --- | --- |
| 其余领域工具的签名与返回值形状 | `docs/cookbook/adding-a-tool.md`（**已读**） | #27 |
| 三张 toolview 卡片怎么注册 | `docs/subsystems/slots.md`（**已读**，见 §1.5） | #40 |
| ~~guard 插件拦注入的挂载点~~ | 已确认并落地：`ctx.tools.guard()`，见 §1.6 | #26 |
| 审批点怎么接 `ctx.approval` | `docs/subsystems/approval.md`（已读，见 `13` §7.3） | #39 |
| 四角色 subagent fan-out | `packages/subagent`（**未读**） | #38 |
| 决策追踪怎么查 | `docs/subsystems/session-query.md`（只读了纲要） | #31 |

## 三 已经排除的做法

| 做法 | 为什么不做 | 出处 |
| --- | --- | --- |
| 用 `permission-presets` 砍工具 | 它只捆 sandbox + approval 两个旋钮，不决定有哪些工具 | `13` §7.1 |
| 用 sandbox 挡信息泄漏 | 只管写不管读，网络与进程可见性也在词汇表之外 | `13` §7.2 |
| 用 `workflow` 取代 `Orchestrator` | 是模型自己写编排脚本，与「财务数字必须可复现」冲突 | `13` §7.4 |
| 用 plan mode 当护栏 | soft guidance，什么都不强制 | `13` §7.5 |
| fork dsh | 版本全是预发布且明示会破坏性变更 | `CLAUDE.md` |
| Agent Teams | `packages/experimental/`，且四角色不需要互相说话 | `CLAUDE.md` |
