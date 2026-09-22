# 36 — #245 实施计划：导入问题的 agent 可读明细与受控单元格读取 / Implementation plan for #245

2026-09-22 制定。前提：[#245](https://github.com/EricWang1358/BridgeFlow-AI/issues/245) 需求已被业务负责人确认（五个待确认问题有了答案），且字典起草分支（`feature/usability-20260921`，#205）已合并。本计划是依赖顺序与验收口径，不是工期承诺。

## 目标

一句话：`needs_review` 批次处置从「人读屏、人动手」变成「队长列清单、读行、提议，人批准」。三个既有闭环（业务研判、字典优化、总表生成）的前一步由此打通。

不做的事（#245 已写明）：批量原始行进上下文；agent 自主写入；通用查询面；新权限模型。

## 设计判定（D1–D8）

PRD 留了五个待确认问题。下面是开发侧按既有约束推定的默认答案，负责人可逐条推翻；推翻哪条，哪个阶段回炉。

| # | 判定 | 依据 |
| --- | --- | --- |
| D1 | cell 读取**免逐次审批**，走 read + 审计；写决定仍走 `quarantine_decide` 既有审批 | 引导一条隔离行要读一次、提议要引用、人批一次；读取再审批一次等于每行两次审批，引导体验被淹死。与 #205「草案是读、发布是批」同构 |
| D2 | 审计为独立按日 JSONL：`data/outputs/cell-access/`（config 键 `cell_access_log_path`），字段：at / actor / batch_id / department / index / 列名集合 / 关联待办 id / trace | 复用 `journal.py` 的按日文件模式，不塞进 HTTP 形状的 `journal.entry`。读取事件是领域事实，不是请求日志 |
| D3 | corrections 进 `monthly_inbox` 成为新 kind `intake_correction`，条目按 **部门 × 列聚合**（subject=列名，detail=条数+代表规则）；明细只在 `batch_issues` | 逐条修正进清单会把清单淹没（一个批次几十条）；聚合后清单仍是索引，明细仍是文档，与 inbox「投影不决定」定位一致 |
| D4 | 首期**不做**按角色脱敏；可见性沿用部门粒度（`Scope`） | 现有批次可见性就到部门粒度；脱敏需业务先给遮蔽规则（PRD 问题 4），规则没来不猜 |
| D5 | 封顶：一次一行、行内全列、每格 4KB、响应总 64KB；超限截断并**列名点名**，不静默 | #245 验收第 3 条要求超限拒绝并说明；静默截断违反「跑不动比静默出错好」 |
| D6 | `quarantine_row` 只按 待办（department + index）定位，不做任意行号读取；不可见部门 404（复用 `_visible`） | 「与待办绑定」是边界修订的本体（#245 约束表）；任意行号读取就是通用查询面，明确不做 |
| D7 | `Fix` 增加可选 `proposed_by` 与 `evidence`；`quarantine_decide` 语义不变——人提交的值仍为准，标注只是留痕 | #88 修订只放开「提议」，不放开「决定」；revalidate 链路一行不动 |
| D8 | `batch_issues` 与浏览器右侧栏同一事实源：corrections 读 `clean_tables[].corrections`，intake 读 `intake_checks`，隔离读 `quarantine.entries`，不建第二套口径 | 两套口径必然漂移；漂移了 agent 说的和人看的对不上，比没有更糟 |

## 分阶段计划

### Phase 0 — 前置（外部输入）

- [ ] #205 字典分支合并进 main（本地已全绿，待实例验证 → PR）。
- [ ] #245 五个待确认问题拿到负责人答案；与本表 D1–D8 不一致的，先改本计划再动工。

### Phase 1 — 后端读取面（核心）

新建 `backend/src/bridgeflow/api/issues.py`（router `/tools`）：

- [ ] `POST /tools/batch_issues {batch_id}`（read）：一个批次的全部问题投影——
  corrections（部门、列、before/after、rule、reason、source 出处）、隔离行（复用 `quarantine.entries`：检查名、可释放性、移位建议、已有决定）、intake 失败（`intake_checks` 里的拒因/警告）、`dropped_columns`、`stale_matches`、`column_questions` 计数。每条带 `next_step` 指到能解决它的工具名。
- [ ] `POST /tools/quarantine-row {batch_id, department, index}`（read）：该行值 + `original_columns` 原始表头 + 出处（filename、sheet、source_row）。D5 封顶；D6 可见性与定位；D2 审计落账。
- [ ] `monthly/inbox.py` SOURCES 增 `"corrections"` 源，产出 D3 的聚合条目；`api/checklist.py` 无需新端点（`monthly-inbox` 工具自动带出）。
- [ ] `config.py` 增 `cell_access_log_path`；conftest 隔离到 tmp。

验收：#245 AC-1/2/3/5（同一事实源、无关单元格零泄漏沿用字节检索法、封顶与 404、审计有行）。

### Phase 2 — 提议链路

- [ ] `quarantine.Fix` 加 `proposed_by: str = ""`、`evidence: str = ""`；`DecideRequest` 透传；决定账本与派生批次照旧携带（D7）。
- [ ] 审批卡（插件层 approval detail）展示：行原文（来自 `quarantine_row`）+ 提议值 + 证据。人在卡上可改写；改写后以改写为准。

验收：#245 AC-4（未批不落账；卡上同行原文与提议；人改写生效）。

### Phase 3 — 工具注册与编排

- [ ] `plugins/src/tools/issues.ts`：`batch_issues`、`quarantine_row`（均 read），注册进 catalogue；pinned catalogue 测试更新；client toolview 键补齐。
- [ ] `agent.cordis.yml` persona 增编排段：`needs_review` 时先调 `batch_issues`，向人复述「几类问题、各几条、卡在哪」，逐项带走——读行（`quarantine_row`）→ 讲规则 → 提议 fixes（`quarantine_decide`，证据同呈）→ `quarantine_apply` 派生新批次；字典类问题衔接 #205 起草流；待办清零后 `review_context`。红线照旧：不自行决定、被拒不重试、不谎称已处置。
- [ ] `ui.ts` 的 `next_needs_review` 文案补「让队长逐项带你处理」。

验收：#245 AC-6 前半（复述与指引）。

### Phase 4 — 测试与彩排

- [ ] 后端行为测试 `backend/tests/test_agent_issues.py`，对照 #245 六条 AC；含：越权 404、封顶拒绝、审计断言、corrections 聚合、Fix 提议标注与人改写优先。
- [ ] 彩排脚本 `scripts/rehearse_issue_walkthrough.py`（照 `rehearse_dictionary_draft.py` 模式）：构造含 隔离行 + 清洗修正 + 列问题 的批次 → 队长全链「清单 → 读行 → 提议 → 人批 → apply 派生 → 待办消失 → 新批次就绪」。mock 模型，验证流程不验证提议质量。
- [ ] 插件 runtime 测试 + typecheck；全量回归。

验收：#245 AC-6 全条。

### Phase 5 — 文档与上线

- [ ] `docs/requirements/`：E04（intake 质量）补 corrections 可读 UC；E09（安全审批）补受控单元格读取 UC 与 #88 修订记录；E14-UC05 登记 corrections kind；traceability 表更新。
- [ ] CLAUDE.md：边界修订记录（「原始数据行绝不进上下文」→「不批量进上下文；待办绑定的有界读取 + 审计」，照 #205 修订的写法）；README 双语「导入后」段落更新。
- [ ] 上线顺序照 [[verify-before-push-workflow]]：本地全绿 → Lightsail 实例验证（真实批次走一遍引导链）→ commit → PR 流水线。

## 风险与回退

| 风险 | 缓解 |
| --- | --- |
| cell 值进上下文扩大泄漏面 | D5 封顶 + D6 待办绑定 + D2 审计 + 字节检索测试；泄漏即回退读取面，写链路不受影响 |
| 提议质量差，人全在拒绝 | 提议带证据（行原文+规则+跨行一致性）；真实模型运行留痕评估；mock 不作质量证据（项目惯例） |
| corrections 聚合条目仍太多 | D3 按 部门×列 聚合已压一层；仍多则 inbox 只显示计数、明细全走 `batch_issues`（一行配置的事） |
| 两个事实源漂移 | D8 同源实现；测试断言 `batch_issues` 与浏览器视图逐字段一致 |

## 依赖顺序一览

Phase 0 → 1 → 2 → 3 → 4 → 5。其中 1 与 2 可并行（读取面不依赖提议链路）；3 依赖 1+2；4 依赖 3；5 收尾。
