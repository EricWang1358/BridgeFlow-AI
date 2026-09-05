# BridgeFlow AI

把生产、物资、财务、市场四个部门的月度表格合成一张对齐的 Master Table，
产出风险预警与动态报价。参赛项目（Show Me Your Agents Hackathon, NUS ISS）。

**动手之前先读 [`docs/13-golden-standard.md`](docs/13-golden-standard.md)** ——
它是架构决策的唯一权威，与其他文档冲突时以它为准。

当前进度、待验证问题、下一步建议见 [`HANDOFF.md`](HANDOFF.md)（会过期，情况变了就更新它）。

---

## 硬性约束

以下每一条都是踩过坑之后定下的。违反它们会重复已经犯过的错误。

### dsh 是基座，不是 provider

`DeepSeek Harness` 拥有工作流编排、工具执行、审批、护栏、子代理。
**不要把它包进 `LLMProvider` 协议**——那个抽象是给可互换的模型后端用的，
把 dsh 塞进去等于丢掉选它的全部理由。

现存的 `bridgeflow/llm/providers/dsh.py` 与 `pipeline/orchestrator.py` 是这个错误的产物，
**待重构，不是范例**。

resolver 已经撤出来了（#25、PR #34）——纯判断类调用走 `deepseek` 直连。
实测代价：同一次裁决在 dsh 上是 12–212 秒、光工具输出就 7,100 token，
因为它会自发跑十几步 bash 把整个仓库读一遍；直连是 3.6 秒、707 token。
**sanitizer 与 evaluator 仍在 dsh 上**，同样的账还欠着。

### 只用官方内置插件

目的是消除输出错误、幻觉、子代理越权、未定义行为的来源。
`packages/experimental/` 下的一律不用——包括 `agent-team` 全家与 `code-runtime-python`。

四角色研判用官方 `packages/subagent` 的 fan-out，**不用 Agent Teams**：
四个角色读同一份数据、各自出结论、从不需要互相说话；
给它们一条协商通道正是"子代理越权"的来源。

### 不 fork dsh

用 `dsh plugin --profile sdk-minimal add file:<绝对路径>` 装本地 bundle，
插件源码留在本仓库 `plugins/` 下。所有版本都是预发布且明示会破坏性变更，
版本锁死 `deepseek-harness-sdk==0.1.2rc1`。

### 引导变量绝不进 `.env`

`DSH_*` 与 `DEEPSEEK_BASE_URL` 只能由启动 shell export（放 `env.sh`，已 gitignore）。
dsh 会扫描 cwd 下的 `.env` 并拒绝这些变量——**这是安全边界**：
若可从项目携带的文件设置，clone 恶意仓库即可重定向代码加载与网络出口。
**不要绕过它**（例如改 dsh 的 cwd）。空行 `DEEPSEEK_BASE_URL=` 也算"已设置"。

### 字段名绝不写进代码

真实 XLS 的字段构成**尚未确定**，仍在与公司协商。所以列名、实体类型、关系
一律只能来自 `data/mappings/field-dictionary.yaml`——谈成什么样，**改 YAML，不改 Python**。

已知的三处违规（#32、#44、#45 在处理）：

- `sop_flow.py:98` 猜不到主键就 `return names[0]` —— 拿第一列 join 四张表，静默出错
- `semantic_resolver.py:23` `_COLUMN_HINTS` 全是英文，真实导出大概率是中文字段
- `schemas/__init__.py:12` `EntityKind` 是封闭 `Literal`，多一类实体就得改代码

**字典缺席时应当明确报「未配置」，不许退回猜测。** 跑不动比静默出错好——
这跟「无证据的结论被拒绝，不是降级显示」是同一条原则。

反过来讲，这不是权宜之计：`docs/01` 说客户「没有数据团队，每家的表都不一样」，
所以**字段映射本身就是产品的一部分**（#46 的字段映射向导）。

### 跨部门映射不靠字符串相似度

`SKU-A1` 与 `RM-Alu-6061` 是产品与其原料，**本来就不该字符相似**（实测相似度 35.3）。
映射来源按可信度降序：OA 字段字典声明 → 行内共现 → 模型裁决残余。
字符串相似度**只用于同一实体的别名归并**，已有测试锁死此约束。

### 结论必须带证据

`Finding` 在 schema 层强制 `evidence` 非空——无证据的结论**被拒绝，不是降级显示**。
不要为了让流程跑通而放宽这条。

### 不要扩大范围

Docker、compose、AWS 章节、CI、自建 Next.js 前端都是**未经要求自行添加的**，
是明确的错误。前端复用 dsh web 深度定制（Client 插件注册进 `tool.call.toolview` 键槽），
不自建。

---

## 评分标准优先于 PRD 完整度

评审考的是 Agent 工程能力。PRD 剩余的大部分缺口（批次版本、XLSX 导出、
RBAC、季度年度表、币种归一）**不计分**，已关闭。

当前计分见 [`docs/00-status.md`](docs/00-status.md) 第五节。不达标各项的根因是同一个：
dsh 位置错误，其原生的编排、工具、审批、护栏、多代理能力全部闲置。
**修正架构一次性修正五项**——优先级高于按 PRD 补功能。

逐条比对见 `docs/13` 第六节。

---

## 环境

搭建见 [`docs/14-wsl-setup.md`](docs/14-wsl-setup.md)。要点：

```
~/Hackathon2026/
├── BridgeFlow-AI/     仓库（源码）
├── .venv/             虚拟环境（仓库外）
└── .dsh-bridgeflow/   DSH_HOME（仓库外，与日常用的 dsh 隔离）
```

**绝不放在 `/mnt`**——inotify 失效、权限位丢失、IO 慢一个量级
（实测 dsh 启动 0.5s vs 3.6s）。

常用命令：

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh

cd backend && ruff check src tests
pytest -q                               # ⚠️ 慢，且**真的调用 API 计费**
python ../scripts/smoke_dsh.py          # 同样会计费，别随手跑
```

`.env.example` 里 `LLM_PROVIDER=mock` 仍是默认值，但**本机 `.env` 不是**：
`LLM_PROVIDER=dsh` + `LLM_PROVIDER_RESOLVER=deepseek`。所以本机跑测试会花钱。
跑之前想清楚值不值，跑完把花销告诉用户。耗时数字见
[`docs/00-status.md`](docs/00-status.md)。

---

## 本文只管硬约束

其余各归其位，**不在这里复述**——重复的内容一旦过期，就是三处互相矛盾的事实：

| 你要找 | 去哪 |
| --- | --- |
| 当前进度、已知缺陷、下一步、待验证问题 | [`HANDOFF.md`](HANDOFF.md) |
| 任何一个实测数字 | [`docs/00-status.md`](docs/00-status.md)，**唯一来源** |
| 架构决策与官方能力边界 | [`docs/13-golden-standard.md`](docs/13-golden-standard.md) |
| 插件形态的设计结论 | [`docs/15-plugin-design.md`](docs/15-plugin-design.md) |
| 该读哪篇文档 | [`docs/README.md`](docs/README.md) |

Issue 与看板：https://github.com/users/EricWang1358/projects/1
