# 00 — 实测状态

> **本文是所有实测数字的唯一来源。** 其他文档一律**引用本文，不复写数字**。
>
> 之前每个数字被抄进三到五处，然后开始漂移：测试数量同时存在 19 和 21 两个版本，
> 样本行数同时存在 21 和 22，修复条数 47 与 48 并存。**而且两个版本往往都不对**——
> 实测样本是 18 行，22 是把 4 行表头也数进去了。
>
> 「每个数字都量过、可追溯」是这个项目对评委的核心叙事。评委抓到一处对不上，
> 整个叙事打折。所以：**改数字只改这一处。**

**最后更新：2026-09-06。** 更新时请附上复现命令。

---

## 跨操作链路复查（2026-09-06，当前结论）

**当前是能跑正常案例的功能原型，还不能按稳定的业务展示 MVP 验收。** 上一轮“通过”只覆盖对应测试路径；人工复核不重跑、端到端超时、重启与汇总失败恢复仍有实现缺口。完整归属链、已修与未修项见 [19 — 链路审计](19-chain-audit.md)。后文历史验收不能覆盖本节未完成项。

本轮同一浏览器连续操作两个批次，修复前 **4 项全部失败**，修复后 **4 项全部通过**。错误为继承旧报告 ID、刷新清除手选批次、跨批次派活数混用、错误链接留下旧内容。新增本次研判不能继承旧报告的投影测试；启动器检查旧构建与子进程退出；错误字典由泛化 500 改为明确配置 503。最终 `acceptance.json` 与计量文件分开，不能以 report_status 代替整轮验收。

| 本轮检查 | 结果 / 复现 |
| --- | --- |
| Python | **253 passed**；`pytest -q backend/tests`，含启动器与无效字典回归 |
| TS | **12 passed**；`pnpm --dir plugins test` |
| 静态与产物 | `pnpm --dir plugins typecheck` / `build`、`ruff check backend scripts` 通过 |
| 连续业务操作 | `pnpm --dir plugins smoke:business` 通过，默认加入跨批次回归；[明细](evidence/business-mvp/chain-regression/chain-audit.json) / [最终结果](evidence/business-mvp/chain-regression/acceptance.json) |
| Partial 路径 | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` 通过；只证明意见提交与脚本对应路径，不证明宿主禁止重跑 |
| 原生审批 / Web | `pnpm --dir plugins smoke:web` 通过；allowed-once / rejected / cancelled 与理由通道，无 JS 异常 |
| 证据 | chain-regression 独立场景保留修复前后 **2** 轮；未覆盖已有真实模型证据，未清理真机会话 |

本轮浏览器全部使用离线模型适配器，**没有新增付费模型调用**。正常链路 `/tmp/bridgeflow-web-e2e-3OztvL`；故障链路 `/tmp/bridgeflow-web-e2e-cBguAe`；审批 `/tmp/bridgeflow-web-e2e-YgANpT`。另一次最终浏览器复验 `/tmp/bridgeflow-web-e2e-XcxABD` 通过，增加了错误链接不得残留“批次已保存”提示的断言；该轮未重复导出截图。最终配置异常调整另跑相关 Python **22 项**通过。同批次再次研判的旧报告问题由投影测试覆盖，重启等故障场景尚未实测。

---

## 原生队长与业务状态页验收（2026-09-06，上一轮）

已实现「对话｜轨迹｜**业务状态**」独立页签，右上角提供部门文件轻量侧栏；复用官方槽位，无 DSH fork。详情见 [18](18-native-captain-and-state.md)，一站式入口见 [demo-walkthrough](../demo-walkthrough/README.md)。本节覆盖下面上一轮的 UI 与编排状态，领域标准答案不变。

| 检查 | 实测结果 | 复现 |
| --- | --- | --- |
| Python | **247 passed**，2 条依赖弃用警告 | `pytest -q backend/tests` |
| Ruff | backend 与 scripts 全部通过 | `ruff check backend scripts` |
| TS / Client / 锁文件 | typecheck、build、frozen-lockfile 通过 | `pnpm --dir plugins typecheck` / `build` / `install --frozen-lockfile` |
| ToolRuntime 与状态投影 | **11 passed**；终局 Spawn guard、审批 ID/备注关联、空状态与跨审查计数 | `pnpm --dir plugins test` |
| 原生队长 | 父模型同一响应 **4 次**官方 subagent；顶栏 **4**；四子运行重叠；首个实际请求即含 structured_output，正常流程无嵌套工具错误 | `pnpm --dir plugins smoke:business` |
| UI | 中英文、深色、状态页在轨迹后、文件栏、报告刷新重开、冷启动父子链接通过，无 JS 错误 | 同上，`BRIDGEFLOW_CASE=balanced` |
| Partial + HITL | 财务连续 **3 步**错误后停止，其余 **3/4**保留；人工意见进入原队长会话，孩子总数仍 **4** | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 默认审批 | allowed-once / rejected / cancelled，拒绝理由原样回传；**5s**测试 / **300s**生产配置在界面显示 | `pnpm --dir plugins smoke:web`，真实模型加 `BRIDGEFLOW_LIVE=1` |
| 证据治理 | 每场景最近 **2** 轮；审计仅对应 parent + 4 children；测试目录隔离；真机会话只提供手动 prune | `pytest -q backend/tests/test_session_retention.py` |

### 本轮真实模型与费用基线

官方 DSH 0.1.2-rc.1，模型 deepseek-official / deepseek-v4-flash。子代理 low reasoning、每次请求输出上限 **4000 tokens**、最多 **3 步**，子调用组合取消信号设为 **180s**；不是整名子代理累计 token 预算，也不是覆盖父模型等待的端到端期限。父模型沿用环境配置。按原生日志模型响应统计，包含父编排和最终回复。

| 运行 | 端到端 | 模型响应 | 未缓存输入 / 缓存 / 输出 | totalTokens |
| --- | ---: | ---: | ---: | ---: |
| [风险组](evidence/business-mvp/risk/measurement.json) | **21.901s** | **9** | **16825 / 16000 / 3945** | **36770** |
| [正常组](evidence/business-mvp/balanced/measurement.json) | **36.805s** | **8** | **16725 / 14080 / 6130** | **36935** |
| [原生审批](evidence/business-mvp/approval/measurement.json) | 未记录端到端 | **6** | **3300 / 16256 / 916** | **20472** |

风险组相对上一轮 host 直接编排基线 **26203 tokens / 19.792s**：增加 **10567 tokens（40.3%）/ 2.109s**。这是本次请求样本，不是稳定延迟或货币账单；inputTokens 与 cacheReadTokens 分开、reasoning 已计入 output，不重复求和。

本轮共 **4 次真实模型运行**，落盘的 **30 次响应 / 122877 totalTokens**；包括最初失败，不只算成功。首轮在父回复进行时结束测试，因此该累计是已记录量，不声称涵盖未落盘流的全部账单。[本轮完整迭代清单](evidence/business-mvp/captain-live-iterations.json) 与上一轮清单分开。

正常组真实研判、四部门校验、状态页与中英文截图通过；该次新加的冷启动孩子链接断言随后暴露客户端地址缓存误用。现改从官方目录取地址，修复由离线完整浏览器 `/tmp/bridgeflow-web-e2e-jQrtzm` 验证，不伪称付费模型在修复后又跑了一遍。最终 UI 变更不涉及模型、领域计算或报告内容。

### 新发现的实质错误

- pre-step 发生在 request assembly **之后**；在该 hook 才注册结果工具，真实模型的首请求没有工具。现移到 agent/created，并保留 pre-step 的角色票据验证及步骤上限。
- 原离线适配器无 schema 时会误调父工具；原断言读取 `data.error`，漏掉 `message.content[].isError`。已改为首请求 schema + 嵌套错误的真实检查。
- DSH `subagentAddress` 是曾打开地址的缓存。首次从报告跳孩子必须读取官方 catalog，不能假定缓存已存在。
- 原生聊天宽度拖柄在自定义宽页面上拦截点击。状态页以自己的交互层与自适应网格解决，不修改基座布局。

[浅色新页](evidence/business-mvp/risk/business-state.png) · [深色](evidence/business-mvp/risk/business-state-dark.png) · [英文](evidence/business-mvp/risk/business-state-en.png) · [文件侧栏](evidence/business-mvp/risk/department-files.png) · [四次原生派活](evidence/business-mvp/risk/native-spawn.png)。所有场景证据根目录链接始终指向最近运行，历史数字以对应迭代清单为依据。SSO/角色/租户、字段向导、隔离放行与正式签发仍属后续企业试点范围，不在本次新增 UI 上冒充已实现。

---

## 业务 MVP sprint 验收（2026-09-06，上一轮基线）

本节记录上一轮 host 直接 spawn 编排的基线，最新的父模型原生派活与 UI 以本文上节为准。当时已完成可见合成案例上的真实模型闭环。演示操作及模拟业务负责人验收见 [17](17-business-mvp-acceptance.md)。这不是实际企业负责人签字，也不是留出集或生产上线验收。

| 检查 | 当前结果 | 复现命令 |
| --- | --- | --- |
| Python 回归 | **241 passed，11.23s**；2 条依赖弃用警告 | `cd backend && pytest -q` |
| 静态检查 | 通过 | `ruff check backend scripts/start_web.py scripts/make_business_case.py scripts/collect_demo_evidence.py` |
| TS 类型 / Client 构建 / 锁文件 | 通过 | `pnpm --dir plugins run typecheck`、`run build`、`install --frozen-lockfile` |
| 官方 ToolRuntime 契约 | **7 passed**；含终局 deny、跨会话备注票据、子代理越权拒绝、一次性回执 | `cd plugins && pnpm test` |
| 正常浏览器链路 | 目录、聚合、官方 spawn、报告落盘、刷新重开、可见四部门卡通过，无 JS 或工具协议错误 | `pnpm run smoke:business` |
| 故障浏览器链路 | 财务连续 **3 步**无效结构后停止；报告 **partial**，财务 **0** 条有效判断，其余部门保留 | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm run smoke:business` |
| 默认原生审批 | 批准 / 拒绝附理由 / 无人应答超时均通过；**3 对** asked/decided 按 id 配对，结果 allowed-once / rejected / cancelled | `pnpm run smoke:web`；真实模型加 `BRIDGEFLOW_LIVE=1` |
| 数据拒绝 | 缺价、币种不符、负成本违反声明、零分母、歧义日期、重复行交易身份不明均拒绝业务总额 | `backend/tests/test_business_mvp.py` |
| 引用与批次 | 原文件行列可追溯；空记录、去重、隔离不重排引用；旧批次不受新导入与字典变更影响 | 同上及 `test_enterprise_web.py` |

生成测试组每种场景 **12 行**：生产 4、采购 4、财务 2、市场 2；不与下方历史样本混计。标准答案来自独立显式算术，**未送入模型**。全部计算使用输入全集；每项公式最多展示 **5 条**来源，`source_count` 是公式引用输入单元格的次数，重复使用按次数计，不宣称唯一单元格数。

| 部门 / 检查 | 风险组标准答案 | 正常组标准答案 |
| --- | ---: | ---: |
| 生产：负荷 / 余量 | **110% / −10 hours** | **80% / 20 hours** |
| 采购：支出 / 同数量预算价格偏差 | **760 SGD / 8.5714%** | **700 SGD / 0%** |
| 财务：毛利 / 余额加权账期 | **−10% / 47.1429 days** | **33.3333% / 30 days** |
| 市场：订单减产出 / 数量加权请求账期 | **30 units / 50 days** | **−20 units / 30 days** |

辅助口径：两组产出均 **150 units**、采购同数量预算均 **700 SGD**、销售均 **3000 SGD**；风险组正数成本 **3300 SGD**，正常组 **2000 SGD**。这些是生成案例的声明，不能套用到旧 GL 或未知 OA 表。

### 最终真实模型复测

使用官方 DSH `0.1.2-rc.1`、官方 `spawn` 与配置模型 `deepseek-official / deepseek-v4-flash`。每个业务用例均有 **4 个独立子会话**，原生日志的生命周期证明四者实际重叠；每部门 **2 项**判断，合计 **8 项**，与标准答案一致。每次子运行最多 **3 步**、输出预算 **4000 tokens**，整体研判时限 **180 秒**；不调用横向通信工具，不获得父会话历史或原始工作簿。

| 最终运行 | 端到端耗时（含协调者回复） | 模型响应数 | 未缓存输入 / 缓存读取 / 输出 tokens | API totalTokens |
| --- | ---: | ---: | ---: | ---: |
| [风险组基线](evidence/business-mvp/live-iterations.json) | **19.792s** | **7** | **16234 / 5760 / 4209** | **26203** |
| [正常组基线](evidence/business-mvp/live-iterations.json) | **24.695s** | **7** | **16308 / 5248 / 5121** | **26677** |
| [原生批准、拒绝与超时基线](evidence/business-mvp/live-iterations.json) | 未记录端到端总耗时 | **6** | **3072 / 14208 / 877** | **18157** |

以上是单次实测，不是延迟 SLA。`request/header` 只在请求头变化时记录，因此不能用其事件数充当模型调用数；表中按 `assistant/message` 模型响应计数。该适配器缓存读取与 inputTokens 分开，reasoningTokens 已包含在 outputTokens 中，不重复累加。账单货币金额未核对。

审查和修复中共完成 **9 轮真实模型运行 / 59 次模型响应**，API 报告累计 **237042 totalTokens**（含最终运行）。[完整迭代用量与问题记录](evidence/business-mvp/live-iterations.json) 保留先前不合格的业务措辞和目录契约错误，不能只报告最后一次成功的费用。所有离线协议运行均不调用付费模型。

真实拒绝叙述已包含：**“客户编码未核实，请销售负责人确认后再提交。”** 同时说明未执行、未写入、下月仍可能询问。审批拒绝不是保存 `accepted=false`，后者仍是必须另获批准的写操作。无人应答测试 **5 秒**后结束，部署默认 **300 秒**。备注最多 **240 字符**，只绑定当前 session/call 的有效临时票据，不授予权限；旧票据与跨会话请求被拒绝。

证据：[风险报告](evidence/business-mvp/risk/report.json)、[正常报告](evidence/business-mvp/balanced/report.json)、[父子与调用审计](evidence/business-mvp/risk/session-audit.json)、[原生拒绝审计](evidence/business-mvp/approval/approval-events.json)、[故障报告](evidence/business-mvp/step-limit/report.json)、[报告界面](evidence/business-mvp/risk/business-review.png)、[拒绝理由界面](evidence/business-mvp/approval/rejection-note.png)。证据导出脚本只保留合成报告、公开回复和精选审计字段，不复制凭证、完整提示或推理过程。

Rubric 证据已从“能收表”推进到官方四角色、真实判断、人工拒绝理由与可复演故障路径；仍不宣称全项达标。待完成的是实际企业口径、员工 SSO/角色/租户隔离、字段向导、隔离处置及报表签发；普通聊天的开放文字不是已校验财务结论。

---

## 原生 Web 重构复测（2026-09-06）

此节保留本 sprint 开始前的原生 Web 基线。当前结果以上方业务 MVP 验收为准。下方原 pipeline / 控制台的耗时与评分属于历史实验，
不表示新 Web 当前能力；旧样本中的歧义日期现在会被隔离，旧总额不能直接沿用。

| 检查 | 结果 | 复现命令 |
| --- | --- | --- |
| Python 回归 | **221 passed，9.07s**，2 条依赖弃用警告 | `cd backend && pytest -q` |
| 静态检查 | 通过 | `ruff check src tests ../scripts/start_web.py` |
| TS 类型与 Client 构建 | 通过 | `cd plugins && pnpm run typecheck && pnpm run build` |
| 官方 ToolRuntime 派发与回执契约 | **5 passed** | `cd plugins && pnpm test` |
| 原生 Web / Chromium | 上传、主表、原生工作区/对话、批准/拒绝/无人应答超时与文件结果、代理鉴权、禁写路由通过；无页面 JavaScript 错误 | `cd plugins && pnpm run smoke:web` |
| 模型调用费用 | **0**；浏览器审批使用只在测试加载的离线适配器 | `plugins/tests/fixtures/scripted-model` |
| 上传数据是否真的决定答案 | 两个独立批次分别返回 **17 / 29**；改变当前字典后旧批仍返回 **17** | `test_enterprise_web.py` |
| 歧义日期 | 原样进入隔离区；新批次总额 **409 拒绝** | `test_ambiguous_date_is_preserved_in_quarantine_and_blocks_partial_total` |
| 看板只读快照 | **63 项：Done 36 / Backlog 26 / Ready 1；开放 issue 27** | `gh project item-list 1 --owner EricWang1358 --limit 100 --format json` |

浏览器脚本还核对原生 JSONL 中 **3 组** `approval/asked` / `approval/decided` 的 id，
结果依次为 `allowed-once`、`rejected`、`cancelled`；并展开 **3 张**领域工具卡片。
无人应答测试等待 **5 秒**后拒绝，生产默认期限 **300 秒**。
批准写入共享会话授权标识，拒绝后记忆文件逐字不变。截图见
[导入与主表](evidence/native-web/data-workspace.png)、[原生工具与审批结果](evidence/native-web/native-approval.png)。

`conftest.py` 现在强制隔离测试 provider、字典和临时输出；普通 pytest 不再继承开发者的
付费模型配置。该基线阶段没有重跑真实模型判断评测或留出验收集。浏览器离线脚本只证明
运行时、审批与 I/O 链路，不证明模型会遵守拒绝叙述或产出正确 Finding。

该基线当时尚缺官方四角色、真实业务判断和来源验收；本 sprint 已补可见案例证据。员工身份、隔离处置和真实 OA 验收仍未完成。逐项条件和看板修订建议见 [16](16-dsh-web-review.md)。

---

## 一 样本数据

| | 值 | 怎么量的 |
| --- | --- | --- |
| 部门文件数 | 4 | `data/samples/*.csv` |
| **数据行（不含表头）** | **18** | production 6 · procurement 4 · finance 4 · marketing 4 |
| 文件总行数（含表头） | 22 | `cat data/samples/*.csv \| wc -l` |
| 覆盖月份 | **1**（2025-11） | 所以跨月记忆无法验证 |

```bash
for f in data/samples/*.csv; do echo "$(basename $f): $(awk 'NR>1 && $0 !~ /^,*$/' $f | wc -l)"; done
```

> ⚠️ **文档里出现的「21 行」「22 行」都是错的。** 22 数进了表头，21 来源不明。

## 二 Sanitizer 产出（隔离修复前的历史记录）

| | 值 |
| --- | --- |
| 修复条数 | **48** |
| 进入 quarantine 的行 | **0** |
| 产量列是否被毁 | **否**（PR #53 之前：整列变成 `1970-01-01`） |
| 每条修复都带规则与置信度 | 是 |

```bash
cd backend && python - <<'PY'
import asyncio, pandas as pd
from pathlib import Path
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
S=Path("../data/samples")
async def m():
    a=DataSanitizerAgent(); c=q=0
    for d in ("production","procurement","finance","marketing"):
        t=await a.run(SanitizerInput(d,"2025-11",pd.read_csv(S/f"{d}_2025-11.csv")))
        c+=len(t.corrections); q+=len(t.quarantine)
    print(f"corrections={c} quarantine={q}")
asyncio.run(m())
PY
```

> ⚠️ **`docs/04` 的 demo 脚本说「47 fixes, 3 rows quarantined」，两个数都不对。**
> 实际是 48 条修复、**0 行隔离**——台上那句话现在讲不出来。

## 三 测试（原 pipeline 历史记录）

| | 值 |
| --- | --- |
| 测试数量 | **210**（`pytest --collect-only -q`，2026-09-06；#91 指标口径 8、#93 合并口径 8、#94 拒绝叙述 9） |
| 打真实模型的 | `test_resolver.py`（9 个） |
| 其余 | mock provider，只证明代码不崩 |
| 离线全绿 | **210 passed / 7.9s**（`LLM_PROVIDER=mock LLM_PROVIDER_RESOLVER=mock pytest -q`，不计费） |

原实验复现曾继承本机 provider 并计费；当前测试隔离配置，见本文最新复测节。

## 四 耗时与 token

resolver 一整轮（PR #70 前后）：

| | 调用数 | 耗时 | 提示词 |
| --- | --- | --- | --- |
| 一条候选一次调用 | 6 | 129.7s | 587 字符 |
| **按关系类型批量（#4）** | **2** | **80.2s** | 1,283–1,469 字符 |

整条 pipeline：10 次调用 / 310.6s → **6 次 / 60.0s**（evaluator 改吃指标而非原始行，#13）。

**⚠️ 这个 60.0s 复现不出来。** 2026-09-06 在同一组 2025-11 样本上重测 `POST /analyze`，
墙上时间 **144.8s**。两个数字都不删——差异本身是待查的：60.0s 是改造 evaluator 当天量的，
中间落了 #29 记忆、#12/#18 月度轴、#65 指标规则。**重测之前不要引用其中任何一个当作现状。**

一次 `/analyze` 里工具端的实际调用（读服务日志，非推测）：

| 端点 | 次数 | 结果 |
| --- | --- | --- |
| `/tools/list-metrics` | 4 | 全部 200 |
| `/tools/aggregate-metric` | 14 | **全部 409**（原记 13，按日志重数） |

**13 次全拒。** 拒绝本身是对的——模型在问 `used_capacity`、`remaining_headroom`、
`order_quantity` 这些字段字典没有声明的指标，而它此前已经调过 4 次 `list_metrics`。
所以 rubric 第 3、5 项的证据成立（不猜、只拒），代价是时间和钱。见 #89。

> ⚠️ 日志里 aggregate-metric 还有 **4 次 200，但那不属于本次运行**：它们排在
> `/analyze` 返回**之后**，是演示时手工 curl 的。别读成「模型试到第 18 次终于问对了」。
> 运行内 14 次 aggregate 全被拒，这个结论成立。

### 指标口径修正：material_spend 加的是单价列（PR #91）

`field-dictionary.yaml` 把 `unit_price` 声明成了 `purchase_amount`，于是 `material_spend`
照声明把一整列单价加起来当支出报了出去。**它引用的每个单元格都是真的**——三个价、
一次加总、可回溯——而数字是错的。「结论必须带证据」保证的是数字来自表格，不保证公式有意义。

| | 值 |
| --- | --- |
| 修正前报出 | 13,540.0 ＝ 4,850 + 5,200 + 3,490（一列单价之和） |
| 三张填了价的 PO 实际 | **117,250.0** ＝ 4,850×12 + 5,200×8 + 3,490×5 |
| 第四张（11-23，RM-Alu-6061） | 4 件、**单价空着**，所以这个月没有可辩护的总支出 |
| 修正后 | `material_spend` **拒绝**，并点名 `procurement row 3 states no amount` |

拒绝而不是只加填全的那几行：少算一行就把「至少花了 117,250」报成「花了 117,250」。
这与 `compute` 早已遵守的「加得动的行才加，加不动就整条拒绝」是同一条规则。
两条路线，优先级写死：**表里自己写了金额列就直接读它**（客户写下的数才是能签字的数），
没写才派生。派生式住在字典的 `derived` 段而不是代码里——「哪两列相乘等于金额」属于客户的
表结构，还在协商中（`CLAUDE.md` 第八条硬约束）。缺价行同时离开分子和分母，见下。

`material_price_change` 建在同一个错误声明上，一并修，口径也变了：

| | 值 |
| --- | --- |
| 修正前 | Σ「purchase_amount」（其实是单价）÷ Σ数量，分子分母不是同一批行 |
| 修正后 | 数量加权：只取单价与数量齐全的行，Σ金额 ÷ Σ数量 |
| 2025-10 → 2025-11 实测 | **+17.66%**（3,986.16 → 4,690.00） |
| `docs/04` Beat 5 的台词 | 「Alu-6061 +18%」——**这句话现在是算出来的，不是稿子写的** |

分母不能带上缺价的行：只加有价的金额、却把缺价行的数量算进分母，会得出一个低于实际成交
价的价格。所以缺价行必须同时离开分子与分母——这也解释了为什么它对 `material_spend` 是
致命的（求和会少算），对 `material_price_change` 只是缩样（比率仍然成立，公式里写明覆盖几行）。

同一次 `/analyze` 的产出：

| | 值 |
| --- | --- |
| 清洗修正 | 33（production 7 / procurement 8 / finance 9 / marketing 9） |
| 隔离行 | **0** —— 这条路径从没被真正走过（#88） |
| 实体 / 已确认关系 / 待裁决 | 15 / 1 / 6 |
| Master Table | **9 行（修复前的运行）**，期间 `['2025-03', '2025-11']` —— **那个 2025-03 是 #79**：`03/11/2025` 被读成 3 月 11 日。#93 之后行数会变少（同一实体不再分裂），需重跑取新数 |
| 同一 SKU 两行（**PR #93 已修**） | `SKU-A1`（1200/180h）与 `sku-a1`（1100/175h）曾各占一行。`EntityGraph` 早就把它们并成了 `sku:sku-a1` 带两个 alias，但旧代码用**原始单元格字符串**当 join 键、没查图——resolver 的产物在演示会展示的那一步被丢掉。现在按 `(实体类型, 写法) → 实体` 归一，行里带 `entity_id` |
| 静默覆盖（**PR #93 已修**） | 多条源行落进同一格时曾是后写覆盖前写：`RM-Alu-6061` 三张 PO 只剩 `qty 4 / unit_price None / 11-23`。现在按字典 `rollups` 声明折叠（`sum`/`average`/`period_end`），**没声明又真撞上多行就拒绝整张表**并点名度量；属性分歧保留成列表。该行现为 `qty 24 / 均价 5,025`，`source_rows: 3` |
| ⚠️ 平均会抹平月内涨价 | 单价按 `average` 折叠后，4,850→5,200 那一轮在表里看不见了。要讲涨价得用 `material_price_change`（月对月，数量加权），或把口径改成别的策略——这是策略选择的后果，不是 bug |
| ⚠️ 跨科目求和仍然可疑 | 财务部同一客户有两行：`4000-Sales/A1 +88,400` 与 `5000-COGS/A1 −91,200`，按 `revenue_amount: sum` 折叠后表里是 **−2,800**——一个「净发生额」，不是任何人以为的「收入」。`metrics.py` 早就为这个开了 `sales`/`cost_of_sales` 两个带科目标记的指标，所以**发现层是对的**，只有表里这一格是净值。要修得把科目标记搬进字典（那里本就是 TODO）。见 #92 |
| 表格与指标对账 | 修复后 `Σ 表格里的 production.output_qty == total_output == 4030`（`test_master_rollup.py` 钉住）。此前表格那一侧报 1,100，指标报 4,030，同一屏互相打脸 |
| 发现 / 张力 / 卡片 | 6 / 8 / 1 |

一次映射裁决（同一个问题，三种配置）：

| 配置 | 耗时 | 工具调用 | 灌回模型的工具输出 |
| --- | --- | --- | --- |
| dsh，带 bash | 12–212s | 3–12 次 | 28,431 字符 ≈ 7,100 token |
| dsh，`dsh/no-shell.patch.yml` | **5.9s** | **0** | **0** |
| DeepSeek 直连 | **3.6s** | — | 707 token 总计 |

全套测试：

| 时点 | 结果 |
| --- | --- |
| resolver 在 dsh 上 | 739.6s，3 failed / 16 passed |
| resolver 改直连（PR #34） | 587.0s，21 passed |
| 加 no-shell 补丁（PR #50） | **447.8s，26 passed** |
| 方案 B 落地（PR #53） | **419.6s，38 passed / 1 failed**，重跑即过 |

**那次失败是间歇的，而且暴露了一个真缺陷**：`test_resolver.py` 的结果取决于本机有没有
`data/mappings/field-dictionary.yaml`——那是 gitignored 的真实数据文件。
跟「测试跟着 `.env` 走」是同一类问题：**测试结果取决于一个不在版本库里的文件**。
新增的 `test_tool_endpoints.py` 用 fixture 显式钉住字典，resolver 测试还没有。

补丁省下的 139 秒全部来自 evaluator——它不再跑 bash 了，但仍然整表进提示词（#13）。

> ⚠️ **文档里的「627 秒」是历史值，且当时的归因是错的**——它被记成「整表塞进提示词所致」，
> 实际是 dsh 每次调用自发跑十几步 bash。见 `docs/13` §7.2 与 issue #25。

## 四之二 验收套件

| | 值 |
| --- | --- |
| 结果 | **24/24 passed** |
| 覆盖 | 三个行业 × 载入 / 指标 / 五类质量缺陷 / 注入识别 |

```bash
cd backend && python -m bridgeflow.eval
```

**验收集是留出的**：`data/acceptance/` 在开发期间不读。到货时是 14/24，
每条红都挂着 issue 或带着解释——见 `data/README.md` 的红线。

## 五 rubric 计分（迁移前历史自评，不代表当前验收）

| # | 项 | 状态 |
| --- | --- | --- |
| 1 | Goal & Scope | ✅ |
| 2 | Architecture & Reasoning Loop | ❌ |
| 3 | Tool Use & Integration | ❌ |
| 4 | Autonomy & HITL | ✅ 拒绝与批准**两条路径都在真实运行时上跑通**（见下） |
| 5 | Safety & Guardrails | ❌ |
| 6 | Observability & Eval | ⚠️ |
| 7 | Platform & Tooling | ❌ |

**7 项中 2 项达标。** 逐条比对见 `docs/13` 第六节。

### 人在环内：旧控制台历史实测（#30，2026-09-06）

以下测量发生在旧 `/console` 与旧 answerer 路径，当时启用了旧控制台。它不证明原生默认面板当时能够传理由；该缺口由本 sprint 的官方 slot 备注接入修复，当前复演见本页顶部。

| 操作者点了 | 到达控制台 | turn 结束 | `data/outputs/mappings.json` |
| --- | --- | --- | --- |
| 允许一次 | 3.1s | 4.0s `completed` | **写入**，含 `authorised_by: eric` |
| 拒绝 | 2.6s | 3.6s `completed` | **不存在** |
| 无人应答（#39 实测） | — | 报错 | **不存在** |
| 拒绝 + 理由（#86 修后复测） | 4.2s | `completed`，**叙述里引用了理由** | **无新增** |

第三行是 #39 已经证明的那条：
`tool "confirm_mapping" requires approval, but no approval channel is available`。
它现在是**四条路径里的一条**，而不是唯一一条——这才是「分级自主权」与「无人能介入」的差别。

这组旧耗时保留作历史记录，不提供已失效的默认 `/console` 启动命令。当前原生路径复演：

```bash
source env.sh
BRIDGEFLOW_LIVE=1 node plugins/tests/web-smoke.mjs
```

**#86 已修（PR #94）。原来为什么会说 `done`**：拒绝路径下模型收到的是框架的固定句

    Error: the user rejected tool "confirm_mapping"

里面**没有地方放理由**——框架不认识操作者想说什么。于是拒绝与被批准在叙述里长得一样。

现在 gate 自己通过 `ctx.approval.request()` 发问，因此**拒绝的话由我们写**。审计事件对、
fail-closed、`never` 策略（CI 仍然无人被问就拒）全部保留。实测：

模型收到 → `confirm_mapping did NOT run: a person reviewed it and refused. The reviewer said: "evidence is stale - use the October BOM, not this one". Nothing was written, …`

模型说出 → "The record was not written: the confirm_mapping call was refused by a human reviewer because the evidence is stale — they said to use the October BOM, not that evidence — and so no mapping decision was stored."

`unavailable` 与 `cancelled` **不会**被写成「有人拒绝」：没人被问到时说「没人能决定」，
答前撤回时说「撤回后才拒」。编一个决策者出来，比这个 bug 本身更糟。

## 六 dsh 事实

| | 值 |
| --- | --- |
| 版本 | `deepseek-harness-sdk==0.1.2rc1`（锁死） |
| 运行时启动（WSL 文件系统内） | 0.6s |
| 运行时启动（`/mnt/d`） | 3.6s |
| 无工具 turn | 0.6s |
| `sdk-minimal` 的工具册 | `persistent-bash` · `persistent-pwsh` · `str-replace-editor` |
| approval 插件 | **未加载**——所以 bash 没有闸门 |
| 可用 model id | `deepseek-v4-flash` · `deepseek-v4-pro` · `deepseek-v4-flash-vision-exp` |

工具册复现：

```bash
$RUNTIME --profile sdk-minimal --dump-config | grep '^- id:'
```
