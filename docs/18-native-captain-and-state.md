# 18 — 原生队长、业务状态页与会话治理

> 连续操作与故障恢复的最新限制见 [19 — 链路审计](19-chain-audit.md)。本页描述接口与设计，不替代完整交付验收。

当前交互入口是「**对话｜轨迹｜业务状态**」。业务状态是官方 `conversation.view` 的独立页签，排序在轨迹后面；右侧辅助空间用于“部门文件”选择。没有启用 `ui-workflow-run`，也没有把状态图包装成可执行工作流。

## DSH 复用边界

| 需求 | 复用入口 | BridgeFlow 负责 |
| --- | --- | --- |
| 四人派活与顶栏计数 | 官方 `dsh-subagent` + `spawn-in-process` + `dsh-tool-subagent` | 冻结业务包、约束四部门、校验真实返回 |
| 对话与轨迹右边的新页 | `conversation.view`，id `bridgeflow-state`，order 20；官方轨迹 order 10 | 静态规则图、实际高亮、点击筛选与来源跳转 |
| 文件辅助栏 | `conversation.session.header.utilities` + `shell.overlay` | 四个 CSV/XLSX 输入、月份、限额预检，同一批次上传接口 |
| 报告卡 | `tool.call.toolview` | 风险置顶、职责/负责人、公式与来源、部分失败人工复核 |
| 拒绝理由 | `conversation.composer` | 输入框与会话/调用绑定备注；仍调用官方 `pending.answer` |
| 跳父子会话 | 官方 `sessions` 的目录与 `openSubagent` | URL 只带 parent/child ID，先查官方目录验证直接父子关系 |

参考了 [DSH-better-sidebar](https://github.com/omdsh-dev/DSH-better-sidebar) v0.18.0（参考 checkout `a5c52b3f1bc450b04578bd9252f67b7d79c98502`）的轻量入口与面板交互。其完整实现还包含终端、编辑器及布局适配；本项目目前以现有官方槽位完成所需文件选择，**没有安装整套插件、复制源码或创建远端 fork**。文件栏使用浏览器本地选择，不暴露服务器文件树，未新增文件读写、命令执行权限。

业务状态页按当前可用宽度换行，其自身交互层避开原生聊天宽度拖柄的命中区；没有修改 DSH 的布局源码或查询原生 DOM 改布局。工具原始详情保留。

## 真正的队长调用链

`review_context` 只读取受限业务包并签出四个一次性派活提示。队长模型必须在同一条 assistant 响应里调用四次官方 `subagent`，description 分别为 production / procurement / finance / marketing；之后调用 `review_finalize`。工具 dispatch 的终局 guard 检查角色集合、会话、票据、防重复和背景模式；后加的 allow listener 不能绕过。

子代理 `toolFilter.allow: []` 隔离继承工具，创建时仅在子作用域注册 `structured_output`；终局 guard 拒绝其它工具。`agent/created` 早于首次请求组装，因此模型第一次请求就能看到结构化 schema。`agent/pre-step` 验证一次性角色身份并用宿主冻结包替换派活提示，执行三步上限；四部门互不读取父会话历史或原始工作簿。一次性 provider、深度与 token/时间上限见配置及 [实测状态](00-status.md)。

`review_finalize` 从宿主记录的真实子 session/result 收集，父模型不能上传自己的四份判断冒充子代理。Python 重核值、单位、状态、动作和解释约束，补回来源及责任。缺部门、失败或错误内容使该部门 unvalidated，整单 partial。队长取消/未汇总时尝试持久化 partial；不造成功报告。无 shell、pwsh、编辑器或代码运行工具。

此次真实复演发现并修正了“pre-step 才注册工具，首个请求不带工具”的生命周期错误。旧离线适配器还会在没看到 schema 时误调父工具，原测试误读 `tool/result.data.error`，漏掉了嵌套的 `message.content[].isError`。现在正常用例要求第一次请求含 schema、所有真实 tool-result 均无错误，不再把最终报告通过当作协议全过程通过。

## 状态与人工责任

导入可能是 needs_configuration / needs_review / ready / empty；needs_review 指待确认关系，并不自动等于业务计算被禁止。本案例按声明列直接计算，不消费未确认映射，因此可以在 needs_review 下形成 validated 报告；旧批次关系快照不会因后来批准而改写。

报告 validated 仅代表四部门判断按字典校验；attention 表示触及关注阈值，不能理解为系统已执行业务操作。部分失败页可将人工复核意见通过官方 session prompt 发给原队长，要求只记录缺口、不重跑；报告保持 partial，不能靠意见替代缺失部门签核。

审批图按当前已加载原生事件的 asked/decided ID 和 callId 关联备注，展示 allowed-once / rejected / cancelled。超时属于 cancelled。事件窗口未加载齐时明确提示，支持加载更早记录；未知状态不伪装成成功。页面请求仍经过 `connection.requestRejection`，读取已有批次/报告和原生审计，不新增 Python 状态机后端。

URL 示例（只用无凭证的 ID）：

- `#bridgeflow?batch=<batch_id>&view=master`
- `#bridgeflow?batch=<batch_id>&view=review&report=<report_id>`，服务端限定报告属于该批次。
- `#bridgeflow?parent=<session_id>&child=<child_id>`，官方目录验证后打开只读一次性子会话。

所有界面操作标签跟随 DSH 中英文设置；字典责任条文、业务动作与模型原文保留原始语言，不临时翻译业务口径。

## 保留最近两轮

```bash
# 导出精简证据，每场景保留最近两次完整运行
python3 scripts/collect_demo_evidence.py /tmp/bridgeflow-web-e2e-EXAMPLE docs/evidence/business-mvp/risk --keep 2
python3 scripts/build_demo_walkthrough.py

# 真机治理：先停止 DSH，手动预览；确认范围后由操作者执行同一命令去掉 --dry-run
pnpm --dir plugins sessions:prune --root "$PWD/.dsh-bridgeflow/sessions" --keep 2 --dry-run
```

真实会话按父会话及全部子代作为一个保留单元，使用族内最新 mtime 排序。没有自动启动清理，也未在本次实现中清理用户的真机目录。测试继续用 mkdtemp 隔离，每次严格核对对应四个孩子。导出时只读取报告所指父子日志全文，其他日志仅发现头部 ID；拒绝跨父会话拼接。

证据 `runs/` 只保留最近两轮物理文件，场景根目录是最新轮次的相对链接。`demo-walkthrough/` 也引用同一份证据，所以重复生成说明页不会多复制截图。完整入口见 [一站式 Demo](../demo-walkthrough/README.md)。

## 远端规划意见

继续沿用 [16 的 issue/kanban 审查](16-dsh-web-review.md)，本地实现与远端卡片状态分开。#38 的评审材料应以“父模型四次官方工具调用、子作用域首请求工具白名单、四条实际血缘、运行重叠、partial 路径”验收；不能只凭四张 UI 卡关卡。#86 的拒绝安全性质和默认面板理由回传分别核对。SSO/租户、字段向导、隔离处置及签发/版本差异保留后续企业试点范围。此轮不修改远端 issue、看板或发布状态。
