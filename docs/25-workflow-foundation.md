# 25 — 工作流基座：三个 Agent 共用的底层（#143 / #144 / #145）

> 设计记录。代码在 `backend/src/bridgeflow/workflow/`，接口在 `backend/src/bridgeflow/api/workflow.py`，
> 合成示例声明在 `data/workflow_demo/catalogue.yaml`（#147 的生产部 → 市场部交接）。
> 测试与数字见 [`00`](00-status.md)。本篇只讲结构和理由。

## 一句话

三个 Agent 做的事不同，但读写的是同一份东西：**人批准的声明**、**按声明形成的数据**、**数据发生过什么**。
基座把这三样做成可靠的底层，Agent 只在上面做提议、补问和解释，状态与算术由确定性代码负责。

## 分层

依赖只向内：API → service → 领域模块。每个模块只有一个会让它改动的理由。

| 模块 | 负责 | 服务哪个 Agent |
| --- | --- | --- |
| `catalogue` | 人批准的声明：模板、阶段、字段血缘、路由、MVP 决定；整体校验后才可用 | 1（产出）、2/3（读取） |
| `normalise` | 按声明类型把写法变成规范值，或说明为什么不能 | 2 |
| `intake` | 观测值 → 草稿：每个值带出处，每个缺口带问题 | 2 |
| `lifecycle` | 状态机；唯一允许改状态的地方 | 2 |
| `store` | 追加式事件日志、事务性发件箱 | 全部 |
| `ports` | 数据写到哪、怎么通知人：协议 + 适配器 | 2 |
| `service` | 用例编排；API 只调它 | 全部 |
| `board` | 从事件投影出的状态看板 | 2、3 |
| `adoption` | 从事件日志找出流程卡在哪 | 3 |
| `materials` | 上传的工作簿是什么结构（表头、标题、有无数据） | 1 |

## 用到的模式，以及为什么是它

| 模式 | 在哪 | 解决什么 |
| --- | --- | --- |
| 声明式配置 + 整体校验 | `catalogue` | 字段名不进代码（`CLAUDE.md` 硬约束）；路由指向不存在的阶段这类错误在加载时暴露，而不是在员工提交时 |
| Strategy + Registry | `normalise.REGISTRY` | 新增一种类型是加一个函数，不改流水线；每个策略要么给规范值，要么给问题，不给猜测 |
| Pipeline（纯函数） | `intake.evaluate` | 同样的输入永远得到同样的草稿；草稿摘要（digest）就是复核人批准的对象 |
| State Machine（转移表） | `lifecycle` | 「文件已收到 ≠ 数据已就绪 ≠ 已通知 ≠ 下游已完成」（#144 状态表）写成三台独立的机器；非法历史存不进去 |
| Event Sourcing | `store.events` + `service` 回放 | 状态只由事件回放得到，任一状态都能追到哪次操作；Agent 3 直接读事件，不需要另建埋点 |
| 乐观并发 | `store.commit(expected)` | 两个人同时补同一份草稿，后到的被拒，不会交错写入 |
| Transactional Outbox | `store.outbox` + `service.dispatch` | 「数据就绪」事件和它要发的通知同一事务写入；通知独立重试，按去重键不重复发送 |
| 幂等键 | `service.submit` → `RecordSink.submit(key)` | 键 = 产物 + 版本 + 复核摘要；写入后进程崩溃，再次提交拿回同一张回执，不产生第二条记录 |
| Ports & Adapters | `ports` | 公司数据平台和通知渠道都没定（#140 / #144）。本地 SQLite 与本地发件箱让全流程可跑；「未配置」适配器明确报缺失，不假装成功；飞书适配器是加一个类 |
| CQRS 读模型 | `board.project` | 看板从事件投影，不能被直接改写；部分输入显示为「部分」，不会误报「已就绪」 |
| Specification / Rule 对象 | `adoption.RULES` | 每条信号是独立规则，输出「事实 + 证据 + 假设 + 该谁决定」；分类决定处置路径 |

## 三个 Agent 怎么用它

**Agent 1（#143）** 的交付物就是 `catalogue.yaml`：阶段与部门、输入输出模板、字段定义与别名、
跨阶段血缘（每条边带 `confirmed / inferred / missing / conflict`）、下游路由与负责角色、MVP 决定及其记录出处。
`materials.inspect` 先回答「这份文件是什么」——四份只有表头的模板会被识别为无数据，不会凭空生成关联。
`GET /workflow/lineage/{template}/{field}` 双向追溯字段血缘。
**未批准的模板可以查看，不能收数据**（`Catalogue.runnable`）。

**Agent 2（#144）** 走 intake → lifecycle：

```text
material_received ─► needs_input ──answer_provided──► ready_for_review ──reviewed（需审批回执）──► reviewed
                                                                                            │
                          submit_failed ◄──submission_failed── submitting ◄──submission_started┘
                                │                                   │
                                └───────────（可重试）───────────────┘──submission_succeeded──► data_ready
data_ready ──answer_provided（修订）──► 版本 +1，重新复核；下游交接标记为 stale
```

交接只在下一阶段**所有**声明输入都就绪时打开，并同时入队通知；否则看板显示「已收到部分输入，仍待……」。
通知内容只有部门、模板、版本和业务键，不带数据明细。

**Agent 3（#145）** 读 `GET /workflow/adoption`。当前六条规则：

| 规则 | 分类 | 交给谁 |
| --- | --- | --- |
| 写入目标系统失败 | technical | 运维（#135），不是培训问题 |
| 通知发送失败 | technical | 运维；数据本身不受影响 |
| 同一模板补问轮次超过声明上限 | template | Agent 2 模板负责人，先和填写者确认 |
| 出现未声明的字段写法 | template | Agent 2；别名需批准后才生效 |
| 交接被退回 | flow | Agent 1 流程负责人 |
| 交接等待超过约定时限 | resource | 该阶段负责角色；没约定时限就不报 |

所有结论的范围只到阶段、部门、模板或渠道，**不针对个人、不打分**，也不自动执行任何建议。

## 和 #148 演示的关系

#148 是队友交付的独立演示，字段、别名、路由直接写在代码里，用来给开发看流程，定位是对的。
基座把同一个故事做成声明驱动：同一份 #147 案例在 `data/workflow_demo/catalogue.yaml` 里，
测试 `test_the_147_story_end_to_end` 逐步复现（缺实际量 → 补问 → 未复核拒提交 → 入库回执 → 交接 → 通知 → 仍待市场部处理）。
#148 的界面可以直接改为调用 `/workflow/*`。

## 硬约束如何保持

- **字段名不进代码**：测试解析 `workflow/` 与 `api/workflow.py` 的可执行代码，出现示例声明中的任何字段标签或键即失败。
- **原始行不进模型上下文**：`materials` 只返回结构；给模型的工具层（下一步）只返回问题、状态与引用。
- **不猜**：无单位的数、两种解析的日期、没有自带依据的数量、互相矛盾的来源，全部变成问题。
- **状态以真实结果为准**：没有写入回执不算就绪；通知发出不等于已读或已完成。

## DSH 工具层（Agent 2 的对话入口）

插件 `plugins/src/tools/workflow.ts`，主机端 `backend/src/bridgeflow/api/workflow_tools.py`：

| 工具 | 类型 | 作用 |
| --- | --- | --- |
| `workflow_catalogue` | 读 | 已批准模板、字段（必填、单位、是否需依据）、接收阶段 |
| `workflow_draft` | 读 | 一份草稿的状态、未解决问题、该记录的值与核对、下一步 |
| `workflow_board` | 读 | 看板摘要，最多 30 行 |
| `workflow_record` | 审批 | 转述对方说的话：新建草稿或回答问题。审批卡逐项列出每个值，由本人确认模型没听错 |
| `workflow_approve_submit` | 审批 | 复核人批准当前值（按 digest 绑定）并提交；值变了即拒绝 |

两条主机侧保证：模型提交的值**出处一律记为本次对话**（`reply` / `dsh-call:<调用 id>`），模型无法声称它来自某个文件；
写入需要与请求逐字节绑定的一次性审批回执，部署时可用 `allowWorkflowWrite` 关闭写工具而保留读工具。
captain 提示词要求逐个问 `open_questions`、只转述不代填、不跨字段抄值、不计算，只有结果为 `data_ready` 才说数据就绪。

## 还没做

- Web 界面（草稿、看板、落地信号的可视化）；真实模型下的连续对话验收。
- 图片 / OCR / 模型抽取：目前观测值由调用方提供，抽取路径需先定是否允许外发原件。
- 飞书或公司平台的 `RecordSink` / `Notifier` 适配器（#140 当前只到上传下载）。
- MVP 投票记录的录入界面：现在只能在声明里写 `decision_record` 出处。
- 事件回放是全量的，适合演示规模；数据量上来后需要物化投影表。
