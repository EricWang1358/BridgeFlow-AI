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

## 二 Sanitizer 产出

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

## 三 测试

| | 值 |
| --- | --- |
| 测试数量 | **201**（`pytest --collect-only -q`，2026-09-06；#91 加 8 条指标口径、#93 加 8 条合并口径） |
| 打真实模型的 | `test_resolver.py`（9 个） |
| 其余 | mock provider，只证明代码不崩 |
| 离线全绿 | **201 passed / 8.3s**（`LLM_PROVIDER=mock LLM_PROVIDER_RESOLVER=mock pytest -q`，不计费） |

复现：`cd backend && pytest -q`（⚠️ **真实计费**）

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

## 五 rubric 计分

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

### 人在环内：两条路径的实测（#30，2026-09-06）

一次真实 dsh turn，模型调用 `confirm_mapping`，`ctx.approval` 把问题送到控制台，
人点一下，决定回到那次还在等的工具调用：

| 操作者点了 | 到达控制台 | turn 结束 | `data/outputs/mappings.json` |
| --- | --- | --- | --- |
| 允许一次 | 3.1s | 4.0s `completed` | **写入**，含 `authorised_by: eric` |
| 拒绝 | 2.6s | 3.6s `completed` | **不存在** |
| 无人应答（#39 实测） | — | 报错 | **不存在** |

第三行是 #39 已经证明的那条：
`tool "confirm_mapping" requires approval, but no approval channel is available`。
它现在是**三条路径里的一条**，而不是唯一一条——这才是「分级自主权」与「无人能介入」的差别。

复现：

```bash
source env.sh && (cd backend && uvicorn bridgeflow.api.main:app --port 8000)
# 另开一个终端，浏览器打开 http://127.0.0.1:8000/console
```

**⚠️ 一处诚实的缺口**：拒绝之后模型仍回了 `done`。写没发生，话说错了——见 #86。

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
