# BridgeFlow AI

把生产、物资、财务、市场四个部门的月度表格合成一张对齐的 Master Table，
产出风险预警与动态报价。参赛项目（Show Me Your Agents Hackathon, NUS ISS）。

**动手之前先读 [`docs/13-golden-standard.md`](docs/13-golden-standard.md)** ——
它是架构决策的唯一权威，与其他文档冲突时以它为准。

---

## 硬性约束

以下每一条都是踩过坑之后定下的。违反它们会重复已经犯过的错误。

### dsh 是基座，不是 provider

`DeepSeek Harness` 拥有工作流编排、工具执行、审批、护栏、子代理。
**不要把它包进 `LLMProvider` 协议**——那个抽象是给可互换的模型后端用的，
把 dsh 塞进去等于丢掉选它的全部理由。

现存的 `bridgeflow/llm/providers/dsh.py` 与 `pipeline/orchestrator.py` 是这个错误的产物，
**待重构，不是范例**。

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

当前 7 项 rubric **仅第 1 项达标**。第 2/3/4/5/7 项不达标的根因是同一个：
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

cd backend && pytest -q && ruff check src tests
python ../scripts/smoke_dsh.py          # 验证 dsh 运行时
```

`LLM_PROVIDER=mock` 是默认值，整条链路可离线跑通，测试与彩排都用它。

---

## 已知缺陷（不要当成能用的东西）

- **`evaluator.py` 把单元格内容原样拼进提示词** —— 真实注入漏洞，未修
- **21 行数据跑 627 秒** —— 整表塞进提示词所致，靠 tool 化解决
- **mock provider 输出是 `mock-justification-<hash>`** —— 能过测试，不可展示
- **只有 2025-11 一个月样本，共 22 行** —— 无法验证"跨月记忆"，也无法测规模
- **`quarantine` 是黑洞** —— 只写不读，没有出口
- **`/analyze` 同步返回、无进度无取消** —— 真实使用下不可用
- **19 个测试全在 mock 下跑** —— 验证代码不崩，不验证判断质量

---

## 文档索引

| | |
| --- | --- |
| `docs/13` | **架构权威**：决策、错误记录、官方能力边界、rubric 比对 |
| `docs/14` | WSL 环境搭建 |
| `docs/07` | 业务方 PRD（需求基线） |
| `docs/09` | rubric 自评（第 4 项评价已被 13 修正） |
| `docs/10/11` | 三周计划与复核（需按 13 重排） |
| `docs/12` | 提交表单内容 |
| `docs/02/06` | 部分内容已过时，顶部有标注 |

Issue 与看板：https://github.com/users/EricWang1358/projects/1
