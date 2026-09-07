# 18 — 原生队长、业务状态页与会话治理

> 连续操作与故障恢复的最新限制见 [19 — 链路审计](19-chain-audit.md)。这一篇讲接口与设计，
> 不替代完整交付验收。

交互入口是「对话｜轨迹｜业务状态」。业务状态是官方 `conversation.view` 的独立页签，排在轨迹之后；
右侧辅助空间用于选部门文件。`ui-workflow-run` 没有启用，状态图也没有被包装成可执行工作流。

## DSH 复用的边界

| 需求 | 复用的入口 | BridgeFlow 自己负责的部分 |
| --- | --- | --- |
| 四人派活与顶栏计数 | 官方 `dsh-subagent` + `spawn-in-process` + `dsh-tool-subagent` | 冻结业务包、约束四部门、校验真实返回 |
| 对话与轨迹右边的新页 | `conversation.view`，id `bridgeflow-state`，order 20（官方轨迹 order 10） | 静态规则图、实际高亮、点击筛选与来源跳转 |
| 文件辅助栏 | `conversation.session.header.utilities` + `shell.overlay` | 四个 CSV/XLSX 输入、月份、限额预检，同一批次上传接口 |
| 报告卡 | `tool.call.toolview` | 风险置顶、职责与负责人、公式与来源、部分失败的人工复核 |
| 拒绝理由 | `conversation.composer` | 输入框与「会话 + 调用」绑定的备注；仍调用官方 `pending.answer` |
| 跳父子会话 | 官方 `sessions` 目录与 `openSubagent` | URL 只带 parent/child ID，先查官方目录验证直接父子关系 |

交互参考了 [DSH-better-sidebar](https://github.com/omdsh-dev/DSH-better-sidebar) v0.18.0
（参考 checkout `a5c52b3f1bc450b04578bd9252f67b7d79c98502`）的轻量入口与面板交互。
它完整的实现还包含终端、编辑器与布局适配；本项目只用现有官方槽位做到了所需的文件选择，
没有安装整套插件、复制源码或建远端 fork。文件栏用浏览器本地选择，不暴露服务器文件树，
也没有新增文件读写或命令执行权限。

业务状态页按当前可用宽度换行，它自己的交互层避开原生聊天宽度拖柄的命中区。
原生聊天拖柄之所以会挡点击，是因为它按父容器宽度定位；解决办法是在自己的层里处理，
不改基座布局、不查原生 DOM 改布局。工具原始详情照旧保留。

## 真正的队长调用链

`review_context` 只做两件事：读取受限业务包，签出四个一次性派活提示。之后由队长模型在同一条
assistant 响应里调用四次官方 `subagent`，description 分别是 production / procurement / finance / marketing，
最后调 `review_finalize`。工具 dispatch 上的终局 guard 检查角色集合、会话、票据、防重复与背景模式，
后加的 allow listener 绕不过去。

子代理侧：`toolFilter.allow: []` 隔离继承来的工具，创建时只在子作用域注册 `structured_output`，
终局 guard 拒绝其它工具。注册时机放在 `agent/created`，它早于首次请求组装，所以模型第一个请求就能看到
结构化 schema。`agent/pre-step` 验证一次性角色身份、用宿主冻结包替换派活提示，并执行三步上限。
四个部门互相看不到父会话历史与原始工作簿。一次性 provider、深度与 token / 时间上限见配置与
[实测状态](00-status.md)。

`review_finalize` 只从宿主记录的真实子 session 与 result 收集，父模型不能上传自己写的四份判断冒充子代理。
Python 重核值、单位、状态、动作与解释约束，补回来源与责任。缺部门、失败或内容错误会让该部门 unvalidated，
整单 partial。队长取消或未汇总时，尝试持久化 partial，而不是造一份成功报告。
没有 shell、pwsh、编辑器与代码运行工具。

这轮真实复演揪出过一个生命周期错误：工具在 pre-step 才注册，于是首个请求不带工具。
更早的离线适配器还在没看到 schema 时误调父工具，而原测试读的是 `tool/result.data.error`，
漏掉了嵌套的 `message.content[].isError`。现在正常用例要求「第一次请求含 schema」且「所有真实
tool-result 均无错误」，最终报告通过不再等于协议全过程通过。

## 状态含义与人工责任

导入状态可能是 `needs_configuration` / `needs_review` / `ready` / `empty`。`needs_review` 指的是有待确认关系，
不自动等于业务计算被禁止：本案例按声明的列直接计算，不消费未确认映射，所以在 needs_review 下也能出
validated 报告。旧批次的关系快照不会因为后来批准而被改写。

报告的 `validated` 只代表四部门判断按字典校验过；`attention` 表示触及关注阈值。
两者都不表示系统已经执行了业务操作。部分失败页面可以把人工复核意见通过官方 session prompt 发给原队长，
要求只记录缺口、不重跑；报告仍是 partial，一条意见不能替代缺失部门的签核。

审批图按当前已加载原生事件的 asked/decided ID 与 callId 关联备注，显示 allowed-once / rejected / cancelled，
超时算 cancelled。事件窗口没加载齐时页面明确提示，并支持加载更早的记录；未知状态不伪装成成功。
页面请求仍经过 `connection.requestRejection`，读的是已有批次、报告与原生审计，
没有另起一个 Python 状态机后端。

深链只用无凭证的 ID：

- `#bridgeflow?batch=<batch_id>&view=master`
- `#bridgeflow?batch=<batch_id>&view=review&report=<report_id>`，服务端限定该报告属于该批次
- `#bridgeflow?parent=<session_id>&child=<child_id>`，官方目录验证后打开只读的一次性子会话

界面操作标签跟随 DSH 的中英文设置。字典里的责任条文、业务动作与模型原文保留原始语言，
不为了界面统一临时翻译业务口径。

## 证据与会话保留

```bash
# 导出精简证据，每个场景保留最近两次完整运行
python3 scripts/collect_demo_evidence.py /tmp/bridgeflow-web-e2e-EXAMPLE docs/evidence/business-mvp/risk --keep 2
python3 scripts/build_demo_walkthrough.py

# 真机治理：先停 DSH，手动预览；确认范围后由操作者执行同一命令去掉 --dry-run
pnpm --dir plugins sessions:prune --root "$PWD/.dsh-bridgeflow/sessions" --keep 2 --dry-run
```

真实会话以「父会话及其全部子代」为一个保留单元，按族内最新 mtime 排序。没有开机自动清理，
本轮实现也没有去动用户的真机目录。测试继续用 mkdtemp 隔离，并且每次都严格核对对应四个孩子。
导出时只读取报告所指的父子日志全文，其它日志仅发现头部 ID；拒绝跨父会话拼接。

证据目录里 `runs/` 只保留最近两轮的物理文件，场景根目录是指向最新轮次的相对链接。
`demo-walkthrough/` 引用的是同一份证据，所以重复生成说明页不会多复制一份截图。
完整入口见 [一站式 Demo](../demo-walkthrough/README.md)。

## 对远端规划的意见

沿用 [16 的 issue 与看板审查](16-dsh-web-review.md)，本地实现状态与远端卡片状态分开谈。
#38 的评审材料应当是「父模型四次官方工具调用、子作用域首请求的工具白名单、四条实际血缘、运行重叠、
partial 路径」，不是四张 UI 卡片。#86 的拒绝安全性质与默认面板的理由回传分别核对。
SSO 与租户、字段向导、隔离处置、签发与版本差异留在后续企业试点范围。本轮不修改远端 issue、看板或发布状态。
