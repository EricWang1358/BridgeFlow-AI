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
| 测试数量 | **185**（`pytest --collect-only -q`，2026-09-06） |
| 打真实模型的 | `test_resolver.py`（9 个） |
| 其余 | mock provider，只证明代码不崩 |
| 离线全绿 | **185 passed / 6.9s**（`LLM_PROVIDER=mock LLM_PROVIDER_RESOLVER=mock pytest -q`，不计费） |

复现：`cd backend && pytest -q`（⚠️ **真实计费**）

## 四 耗时与 token

resolver 一整轮（PR #70 前后）：

| | 调用数 | 耗时 | 提示词 |
| --- | --- | --- | --- |
| 一条候选一次调用 | 6 | 129.7s | 587 字符 |
| **按关系类型批量（#4）** | **2** | **80.2s** | 1,283–1,469 字符 |

整条 pipeline：10 次调用 / 310.6s → **6 次 / 60.0s**（evaluator 改吃指标而非原始行，#13）。

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
