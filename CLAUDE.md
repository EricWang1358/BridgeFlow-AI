# BridgeFlow AI

把生产、物资、财务、市场四个部门的月度表格合成一张对齐的 Master Table，产出风险预警与动态报价。
参赛项目（Show Me Your Agents Hackathon, NUS ISS）。

动手之前先读 [`docs/13-golden-standard.md`](docs/13-golden-standard.md)：它是架构决策的唯一权威，
与其他文档冲突时以它为准。当前进度、待验证问题与下一步建议见 [`HANDOFF.md`](HANDOFF.md)
（这份会过期，情况变了就更新它）。

---

## 硬性约束

下面每一条都是踩过坑之后定下的。违反它们等于重复已经犯过的错误。

### dsh 是基座，不是 provider

DeepSeek Harness 拥有工作流编排、工具执行、审批、护栏与子代理。不要把它包进 `LLMProvider` 协议：
那个抽象是给可互换的模型后端用的，把 dsh 塞进去等于丢掉选它的全部理由。

`bridgeflow/llm/providers/dsh.py` 与 `pipeline/orchestrator.py` 是这个错误的产物，属于遗留路径
（默认关闭，保留供迁移对照），不是范例。

resolver 已经从这个位置上撤下来了（#25、PR #34），纯判断类调用走 `deepseek` 直连。实测代价值得记住：
同一次裁决在 dsh 上要 12–212 秒、光工具输出就 7,100 token，因为它会自发跑十几步 bash 把整个仓库读一遍；
直连是 3.6 秒、707 token。这段说明针对遗留 Python provider 路径；当前默认入口与尚未迁移的部分以 HANDOFF 为准。

### 只用官方内置插件

目的是消除输出错误、幻觉、子代理越权与未定义行为的来源。`packages/experimental/` 下的一律不用，
包括 `agent-team` 全家与 `code-runtime-python`。

四角色研判用官方 `packages/subagent` 的 fan-out，不用 Agent Teams。理由是语义而不是版本状态：
四个角色读同一份数据、各自出结论、从不需要互相说话；给它们一条协商通道，正是「子代理越权」的来源。

### 不 fork dsh

用 `dsh plugin --profile sdk-minimal add file:<绝对路径>` 装本地 bundle，插件源码留在本仓库
`plugins/` 下。所有版本都是预发布且明示会破坏性变更，版本锁死 `deepseek-harness-sdk==0.1.2rc1`。

### 引导变量绝不进 `.env`

`DSH_*` 与 `DEEPSEEK_BASE_URL` 只能由启动 shell export（放 `env.sh`，已 gitignore）。
dsh 会扫描 cwd 下的 `.env` 并拒绝这些变量，这是安全边界：如果这类变量能从项目携带的文件里设置，
clone 一个恶意仓库就足以重定向代码加载与网络出口。不要绕过它（例如改 dsh 的 cwd）。
一个空行 `DEEPSEEK_BASE_URL=` 也算「已设置」。

### 原始数据行绝不进上下文

任何代理都不行：captain、四个角色子代理、任何一个。PRD 第十二章要求单批次支持 20 万行，
20 万行进不了任何上下文窗口，而在 fan-out 里每个子代理还要各付一遍。

三个层次，缺一不可：

| 层 | 状态 |
| --- | --- |
| 模型不能自己去读文件 | 已做到：`dsh/no-shell.patch.yml` 在 profile 层关掉 bash / pwsh / editor |
| 提示词里不能塞原始行 | 已做到：evaluator 改吃算好的指标（#13） |
| 工具返回值里也不能有原始行 | 已做到：封顶样本加真实计数（#58） |

第三层最容易漏：它把行挡在提示词外面，然后又从返回值里漏回去。

每个新工具的 review 都要回答一句：这个返回值在 20 万行时有多大？可追溯性靠引用
（部门、行号、列名）加总数，不靠把每个单元格寄回来。

### 字段名绝不写进代码

真实 XLS 的字段构成尚未确定，仍在与公司协商。所以列名、实体类型、关系一律只能来自
`data/mappings/field-dictionary.yaml`：谈成什么样，改 YAML，不改 Python。

当初列出的三处违规，两处已经改掉，一处还在：

- 已修（PR #60，#44）：`agents/sop_flow.py` 猜不到主键时曾直接 `return names[0]`，拿第一列去 join
  四张表、静默出错。现在只认字典声明的可连接列，没声明就不合并并说明原因。
- 已修（PR #60，#45）：`schemas/__init__.py` 的 `EntityKind` 曾是封闭 `Literal`，多一类实体就得改代码。
  现在是开放类型加一份「已知种类」清单，校验从「词汇表封闭」移到了「字典必须声明」。
- 仍在（#32）：`agents/semantic_resolver.py` 的 `_COLUMN_HINTS` 全是英文列名，而真实导出大概率是中文字段。
  它只是字典缺席时的退路，但这条退路本身就是猜测。

字典缺席时应当明确报「未配置」，不许退回猜测。跑不动比静默出错好。这与「无证据的结论被拒绝，
而不是降级显示」是同一条原则。

反过来说，这不是权宜之计：[`docs/01`](docs/01-problem-and-hmw.md) 说客户「没有数据团队，每家的表都不一样」，
所以字段映射本身就是产品的一部分（#46 的字段映射向导）。

### 字典：模型起草，人逐条审核，发布才生效

2026-09-07 业务方定的边界如下，**2026-09-18 已被业务负责人显式修订一处**（见本节末尾）。

> 设定标准格式和初始字典是纯人工。字典是需要人工事先预设好的。这个东西没有知识库，LLM 做不出来的。
>
> 是上传 excel 后，agent 根据我们设定好的标准格式的 excel 和字典，先自动清洗上传的 excel
> 并自动做字段匹配。

| 事项 | 谁做 |
| --- | --- |
| 标准格式 excel 模板 | 人，事先 |
| 初始字典的**起草** | 模型提议（只吃列画像统计），每条带证据 |
| 初始字典的**审核与发布** | 人，逐条接受 / 修改 / 拒绝，全部有决定才可发布 |
| 上传件的清洗 | 系统，自动 |
| 上传件的列匹配到已声明字段 | 模型提议，人审核 |

匹配不是创造。匹配的候选集是封闭的，只能来自标准字典里已经声明的字段，所以每条候选都能附上证据、
让人做一道选择题。创造是开放的，而没有知识库它立不住。

这条约束改变的是动作，不是上一条：字段名仍然绝不写进代码，字典仍然是唯一事实来源。

**2026-09-18 的修订（#205，需求见 [E05-UC07/UC08](docs/requirements/05-mapping.md)）**：
初始字典的起草从「纯人工」变为「模型起草 + 人逐条审核」。四部门上传后由总经办聚合，模型**只吃列画像
统计**（`profile_batch`：唯一度、填充率、跨部门值重合度，全部不含单元格内容）与可选的模板表头，
起草出带证据的字典草案；人逐条接受 / 修改 / 拒绝，全部条目有决定后才发布为新版本，发布只影响之后的导入。

修订的只有这一条。以下全部保留，实现时不得回退：**未经人审核的草案绝不自动生效**，
**匹配的候选集仍然只能来自已声明字段**（匹配不是创造：候选封闭才能附证据、让人做选择题），
**原始数据行绝不进上下文**，**跨部门关系不靠字符串相似度**。首期起草不含跨部门 relations。

`data/mock_business/demo/dictionary.yaml` 这类示例字典是既定案例的例子（演示与测试用），
不是「客户必须先手写一份字典」的前提——[docs/01](docs/01-problem-and-hmw.md) 说客户没有数据团队、
每家的表都不一样，字段映射本身就是产品的一部分。

**2026-09-22 已实现**（`backend/src/bridgeflow/dictionary_draft.py`、`api/dictionary_tools.py`、
插件工具 `dictionary_import / dictionary_draft / dictionary_decide / dictionary_publish`）。起草有两条路：
业务带来 OA 字典表（六列标准格式）走 `dictionary_import` **确定性转写**，不花钱不调模型；没有表才走
`dictionary_draft` 按列画像统计起草（计费留痕，宿主丢弃无证据条目）。两条路汇进同一道逐条决定与发布闸：
全部条目有决定、每个度量有 rollup、合并结果通过导入侧同级校验（含可连接列），才写
`versions/field-dictionary--*.yaml` 新版本并更新当前指针；旧批次的冻结快照不受影响。校验先于审批回执消耗。
同期修了两个被真实字典暴露的词表/编码残留，都不是放宽猜测：其一，`sop_flow._primary_key_column`
的可连接判定放开为「字典声明过的任意实体 kind」（已知 kind 仅作优先序；多 kind 时按**字典声明序**选，
绝不按上传列序——否则财务按 项目编号 连、生产没有该列落到 项目名称，主表静默错位）；`kind_for`
对非空字典仍然完全尊重声明、绝不回退列名猜测。其二，`semantic_resolver._slug` 原来只保留 ASCII，
所有中文实体标签被折叠成同一个空 slug、主表只剩一行；现保留 Unicode 词字符（CJK 原样），空 slug
回退原文。两个都由 `scripts/rehearse_dictionary_draft.py`（真实 OA 字典表全链路彩排）抓出。

### 跨部门映射不靠字符串相似度

`SKU-A1` 与 `RM-Alu-6061` 是产品与其原料，本来就不该字符相似（实测相似度 35.3）。
映射来源按可信度降序：OA 字段字典声明 → 行内共现 → 模型裁决残余。字符串相似度只用于同一实体的
别名归并，已有测试锁死此约束。

### 结论必须带证据

`Finding` 在 schema 层强制 `evidence` 非空：无证据的结论被拒绝，不是降级显示。
不要为了让流程跑通而放宽这条。

### 不要扩大范围

Docker、compose、AWS 章节、CI、自建 Next.js 前端都是未经要求自行添加的，是明确的错误。
前端复用 dsh web 深度定制（Client 插件注册进 `tool.call.toolview` 键槽），不自建。

---

## 评分标准优先于 PRD 完整度

评审考的是 Agent 工程能力。PRD 剩余的大部分缺口（批次版本、XLSX 导出、RBAC、季度年度表、
币种归一）不计分，已关闭。

逐项验收条件见 [`docs/16`](docs/16-dsh-web-review.md) 的 rubric 表，逐条比对见
[`docs/13` 第六节](docs/13-golden-standard.md)，实测状态与数字见 [`docs/00`](docs/00-status.md)。

不达标各项的根因当初是同一个：dsh 位置放错，其原生的编排、工具、审批、护栏、多代理能力全部闲置。
修正架构一次性修正五项，这件事的优先级高于按 PRD 补功能。

---

## 环境

搭建见 [`docs/14-wsl-setup.md`](docs/14-wsl-setup.md)。要点：

```text
~/Hackathon2026/
├── BridgeFlow-AI/     仓库（源码）
├── .venv/             虚拟环境（仓库外）
└── .dsh-bridgeflow/   DSH_HOME（仓库外，与日常用的 dsh 隔离）
```

绝不放在 `/mnt`：inotify 失效、权限位丢失、IO 慢一个量级（同一运行时放在 `/mnt` 与放在 ext4 上的
启动差异，数字只在 [`docs/00`](docs/00-status.md) 记一次）。

常用命令：

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh

cd backend && ruff check src tests
pytest -q                               # conftest 隔离 provider，离线回归
python ../scripts/smoke_dsh.py          # 同样会计费，别随手跑
```

测试配置由 `backend/tests/conftest.py` 隔离，普通 pytest 不得继承开发者的真实 provider、输出或记忆。
离线回归只证明规则与契约成立；真实判断质量需要显式运行模型评测，记录费用与局限，
不能把 mock 输出当作真实研判的证据。

---

## 本文只管硬约束

其余各归其位，不在这里复述。重复的内容一旦过期，就是三处互相矛盾的事实。

| 你要找 | 去哪 |
| --- | --- |
| 当前进度、已知缺陷、下一步、待验证问题 | [`HANDOFF.md`](HANDOFF.md) |
| 任何一个实测数字 | [`docs/00-status.md`](docs/00-status.md)，唯一来源 |
| 架构决策与官方能力边界 | [`docs/13-golden-standard.md`](docs/13-golden-standard.md) |
| 插件形态的设计结论 | [`docs/15-plugin-design.md`](docs/15-plugin-design.md) |
| 该读哪篇文档、写作约定 | [`docs/README.md`](docs/README.md) |

Issue 与看板：<https://github.com/users/EricWang1358/projects/1>
