# 15 — dsh 插件设计

> **骨架文档。** 读完官方文档得到的插件形态结论**落在这里**，不要再散进 `HANDOFF.md`——
> 那份声明自己会过期。已确认的事实进 [`13`](13-golden-standard.md) 第七节，
> **怎么落成插件**进本文。
>
> 当前状态：**`plugins/` 目录尚不存在，仓库零行 TypeScript。** 见 #40、#27。

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

## 二 待设计（读完剩余文档后填）

| 要设计的 | 依赖哪份文档 | issue |
| --- | --- | --- |
| 五个领域工具的签名与返回值形状 | `cookbook/adding-a-tool.md`（**未读**） | #27 |
| 三张 toolview 卡片怎么注册 | Client 插件机制（**未读**） | #40 |
| guard 插件拦注入的挂载点 | `cookbook/adding-a-tool.md` 的 policy hooks（**未读**） | #26 |
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
