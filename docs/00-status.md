# 00 — 实测状态

本文是所有实测数字的唯一来源。其他文档一律链接到这里，不复写数字。

这条规矩是被逼出来的：同一个测试数曾经同时存在 19 和 21 两个版本，样本行数同时存在 21 和 22，
修复条数 47 与 48 并存，而且往往两个都不对（实测样本是 18 行，22 是把 4 行表头也数了进去）。
「每个数字都量过、可追溯」是本项目对评委的核心叙事，评委抓到一处对不上，整个叙事就打折。
所以改数字只改这一处。

最后更新：2026-09-24。新增一轮时照第三节的格式写，并附上复现命令。

---

## 当前评审 rubric 自评（2026-09-24）

按主办方七项、每项 5 分估算，**31.5 / 35**。这是已合入能力的技术 rubric 自评，不是评委分数、交付准备度或企业验收。27 日能否交付要看下面单列的演示闸门；功能在仓库中存在，不等于现场可用。

| # | 项 | 自评（/5） | 已验证的依据 | 尚未证明的部分 |
| --- | --- | ---: | --- | --- |
| 1 | Goal & Scope Definition | 4.5 | [问题与范围](01-problem-and-hmw.md)、[需求追溯](requirements/traceability.md)和明确的演示边界 | 真实客户材料、成功判据与企业签核仍待业务方 |
| 2 | Architecture & Reasoning Loop | 4.5 | 原生队长与四部门子代理的[真实模型研判](evidence/live-2026-09-23/risk/measurement.json)；立项范围接入、两跳流转的[真实模型运行](evidence/live-2026-09-24/workflow-two-hops/measurement.json) | 取消、恢复与正式签发状态机尚未完整验证 |
| 3 | Tool Use & Integration | 4.5 | 类型化工具在真实批次上执行；[工具选择原始结果](evidence/live-2026-09-24/tool-selection-rerun/tool-selection.json)为 18/18 | 用例经针对性修订，尚无独立新题；token 成本没有随正确率下降，真实企业文件适配待验 |
| 4 | Autonomy & Human-in-the-Loop | 4.5 | 两跳真实模型旅程经 8 次原生审批；写入回执与请求绑定、拒绝不写入 | 风险分级仍主要是读取/审批两档；多人真实并发的审批归属待验 |
| 5 | Safety, Security & Guardrails | 4.5 | [单元格注入真实模型运行](evidence/live-2026-09-23/poison/measurement.json)未把注入文本送入会话；原始行隔离、操作授权及独立访客实例已有实现 | 真实企业权限、共享访客会话、部署配置和外部安全检验尚未完成 |
| 6 | Observability & Evaluation | 4.5 | [决策日志](evidence/round1-e13-e14/decision-journal.png)、[代理泳道](evidence/round1-e13-e14/agent-run.png)及[正常/对抗验收记录](evidence/observability/acceptance-2026-09-20.txt)；真实模型旅程留有调用、审批、token 证据 | 已知生成案例和同套工具选择题不等于独立留出集；真实业务质量、长期费用待验 |
| 7 | Platform & Tooling Usage | 4.5 | 官方 Web、原生工具/审批/会话与子代理在真实模型旅程中使用；[架构边界](13-golden-standard.md#六-rubric-符合性)明确 | 框架升级契约与企业部署验收未完成 |

这次比 [09-20 自评](../HANDOFF.md#历史评审-rubric-自评2026-09-20)更有把握的部分是第 2、3、6 项：多步真实模型链路、全量工具选择评测及真实运行轨迹已经留证。第 3 项不因 18/18 直接给满分，第 6 项也不把脚本化回归当成模型质量证明。

## 27 日交付前的演示闸门（2026-09-24，`main@12b790c` 加 PR #263）

**当前仍是待验收，不把上面的技术自评当成交付分数。** 新功能和新需求先暂停，只处理演示主路径的故障、错误表述及其回归。

| 闸门 | 当前证据与结论 |
| --- | --- |
| 本地离线主路径 | 在私有 dsh 上复跑员工身份的材料→候选→图→评分→会议→决策浏览器旅程、工作流、月结、四部门研判、报价、三套样例、冷重启、笔记本恢复、部门故障和 README 截图旅程，均通过。员工旅程最初被过期的浏览器测试夹具挡住：它仍写旧的 `users` ACL，且按旧界面查找折叠内容和流程节点；修复测试夹具后通过。评分图第 51 个候选标题的 API 回归与引导四象限完整可见性检查已补上并通过。三本样例的待办固定在各自批次，回开第一本仍显示自己的 15 条；趋势图的当前月端点也固定为正在看的批次。左侧来源和任务页显示一致的案例问题，示例切换入口留在首屏，延迟批次响应时不会短暂显示旧批次来源，未就绪研判按钮及新笔记本创建时快速转向流转页也在浏览器中核对。复现：`BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`，以及 [交接文档中的其余命令](../HANDOFF.md)。测试模型是脚本化的，不能代替现场真实模型验收。 |
| 代码回归 | 本轮当前分支后端 743、插件 100 条全过，TypeScript 类型检查与相关 Ruff 通过。门户未改，46 条沿用上轮验证；CI 以 PR 当前提交为准。 |
| 负责人本机演示 | 3082 已重启到当前分支；8000 后端、8100 门户健康，3082 无会话的 401 符合身份围栏预期。新 Command Code 接口以极小请求得到 `OK`，原生 dsh 单题真实模型工具选择正确调用 `batch_summary`（55,625 token）。无飞书登录态的浏览器会被数据接口要求登录；负责人登录后仍需手工走查四样例与两条引导，不能把进程健康或单题模型调用当作走查完成。 |
| 公网访客入口 | 独立访客实例代码已合入；2026-09-24 只读探测：门户首页返回 200，却没有 `/guest` 入口，`guest.<domain>` TLS 仍不可用。[服务器装配步骤](22-lightsail-deploy.md)中的 DNS、环境变量、服务与重置定时器仍待执行和验收。当前分支的浏览器旅程验证了关闭 AI 时任务页、流转页的禁用与提示；另在临时隔离 worktree 启动真实 `--guest` 进程，从其令牌入站，干净样例与流转样例均可浏览、相应模型按钮禁用且无页面错误。部署 preflight 新增启用 guest 后的入口、令牌和 TLS 条件检查，尚未在服务器执行。该验证仍不等于公网验收。 |
| 真实业务输入 | 客户导出、业务口径及企业签核仍未到；[外部输入清单](27-external-inputs.md)未收齐。20 万行样例在现有上传/解压上限下导不进，实测见本文下方的 #228 记录。交付演示应使用已验证的合成样例并如实标明边界。 |

## 引导补流程线路、样例覆盖与私有 dsh（2026-09-24，分支 `feat/tour-workflow`）

| 项 | 结果 |
| --- | --- |
| 后端 / 门户 / 插件 | 739 / 46 / 100 passed |
| `tour-smoke`（含新的 9 步流程线路）、`workflow-journey` | 在私有 dsh（按 `scripts/dsh-cli/package-lock.json` 安装）上通过 |
| 不锁依赖的全新安装 | 50 个包比验证版本新，其中 cordis 4.0.4 让 `dsh web` 启动失败，除启动时不起 dsh 的两条外，其余旅程全部失败。按锁文件安装后，与全局那份逐包比对 0 差异 |
| 四个样例覆盖 | 见 README「Demo cases」下的覆盖矩阵。修了一个待办口径缺陷：改一列名字，待办却列出 20 列 |

## 试用反馈修复与权限收窄（2026-09-24，分支 `fix/workflow-record-card`）

| 项 | 结果 |
| --- | --- |
| 工作流全程（真实模型，`env.sh` 10:16 起改用 commandcode 端点，模型 `deepseek/deepseek-v4.1-flash`） | 通过：8 次原生审批，28 次模型请求，229 s，total 493,473 token |
| 同日第一次真实运行 | 失败：每轮都报「Model "deepseek-v4-flash" is not supported on this endpoint」。原因是旅程用一个全新的 DSH_HOME，没有 settings.yaml，就回落到 dsh 内置的默认模型名。现在真实旅程读 `DSH_PROVIDER` / `DSH_MODEL`（`tests/dsh.mjs` 的 `liveModelPatch`） |
| 后端 / 门户 / 插件 | 737 passed / 46 passed / 99 passed，typecheck 与 ruff 通过 |
| 离线浏览器旅程 | 10 条全部通过；web-smoke 抓出一处键盘顺序回归（技术细节插在理由框前面），已把技术细节挪到按钮之后 |

## 工具选择评测 18/18 与示例前两个月（2026-09-24，分支 `feat/eval-and-second-month`）

真实模型 `deepseek-v4-flash`，证据在 `docs/evidence/live-2026-09-24/tool-selection-rerun/`；上一轮的结果保留在同级 `tool-selection/`，便于对照。

| 项 | 上一轮 | 本轮 |
| --- | --- | --- |
| 选对第一个工具 | 15/18 | **18/18** |
| 每条中位步数 / token | 3 步 / 38,591 | 3 步 / 40,120 |
| 总 token（18 条） | 727,112 | 846,515 |

上一轮没选对的 3 条，都追到了工具或人设上，模型本身没有做错：
- **求和**：`aggregate_metric` 要求同时传批次号和月份，用户只给批次号时，模型只能先调 `batch_summary` 查月份。
  - 修法：带批次号时月份改为可选，默认取批次自己的月份；传了且不一致，照旧 409。
  - 参数说明不再引导模型「先调 list_metrics」。指标名未声明时，拒绝信息列出已声明的名字。
  - 代价：这条从 4 步、53,886 token 变成 5 步、69,912 token，因为模型先用「生产量」被拒，再按列出的名字重试。第一步选对了，但总成本没降。
- **陌生列**：`column_candidates` 的描述和人设都写着「批次需要配置时才调」，现在去掉了这个前提。
- **估个数**：人设规定只在用户给出的批次上工作，用户只说「七月」时，模型只能反问要批次号。
  - 同时发现 `monthly_checklist` 给模型的输出里没有批次号，模型按月份查到结果也接不上下一步计算。现在输出里带上了批次号（有 render 测试钉住）。
  - 人设补了两句：只给月份时用它查批次；被要求「别查了、估一个」也不估。
  - 用例的可接受名单加了 `monthly_checklist`，这符合用例自己写的「任何有依据的查询都算对」。本轮这条的第一步里还有 `list_metrics`，它本来就在原名单里，所以按原标准也是 18/18。

**示例前两个月**：`scripts/make_demo_cases.py` 新写出同一家供应商的 2024-05、2024-06 两个月（没有埋错），登记在 `cases.yaml` 的 `history` 下。`POST /batches/demo/history` 只导入调用者还看不到的月份，所以重复点击不会重复导入，也不会遮住别人自己导入的月份。只有示例批次的趋势图空着时，总览页和结论页才会出现「载入前两个月的示例」按钮；真实批次永远不会出现。README 的总览截图现在带上了趋势。

## 工作流补全：立项接上填报、第二跳、时效与时间线、总览页（2026-09-24，分支 `feat/workflow-story`）

真实模型为 `deepseek-v4-flash`，证据在 `docs/evidence/live-2026-09-24/workflow-two-hops/`。

| 运行 | 结果 |
| --- | --- |
| 工作流全程（真实模型，含接收立项范围与两跳） | 通过，共 76.9 s，8 次原生审批，28 次模型请求。token：输入 32,030、输出 6,132、缓存命中 445,440。各步耗时：接收范围 10.6 s、送审入库 11.8 s、市场部开始 4.3 s、结算依据入库 5.3 s、市场部完成 7.5 s、财务部开始 4.3 s、财务部完成 4.5 s、补问缺项 8.6 s |
| 同一旅程第一次真实运行 | 失败，但暴露了一个真缺陷：市场部环节能在它自己的产出（结算依据）还没审核时标为「完成」。真实模型拒绝了，离线脚本化模型照做了。已修在根因上：产出未按同一业务键入库时，后端拒绝完成 |
| 离线浏览器旅程 | tour、round1、web、business、business 部门故障（`step-limit`）、quotation、cases、workflow、cold-reload、notebook-walkthrough 全部通过 |
| 后端 | **731 passed**，`ruff` 无告警；新增立项范围 6 条、时效/时间线/产出未入库各 1 条 |
| 插件 | **95 passed**，typecheck 通过 |
| 总览页配色 | 标记色与超时色用 dataviz 校验脚本验过：浅色 `#2f6bd8/#9d271c` 全部通过；深色原文字色不在亮度带内，改用 `#4a86e8/#e0645a`，全部通过 |

## Issue 收尾：#252–#255 与 #228 规模实测（2026-09-24，分支 `feat/issues-252-255`）

**#253 队长过度探索**：根因有两处。
- 人设第 7 行要求「每个问题先调 `batch_summary`，再调 `list_metrics`」，现已改为只在需要时才调。
- `integration_summary` 与 `monthly_inbox` 的 render 只给模型计数，队长只能换参数反复重查。现在列出事项、口径和下一步（封顶并附真实总数）。

**#252 工具选择评测全量重跑**（真实模型，`docs/evidence/live-2026-09-24/tool-selection/`）：

| 项 | 修复前（09-23，跑到 13 条中止） | 修复后（09-24，18 条全部跑完） |
| --- | --- | --- |
| 选对第一个工具 | 9/13 | **15/18（83.3%）** |
| 每条中位模型步数 / token | 4 步 / 约 5.2 万 | **3 步 / 38,591** |
| 「这个月还有哪些事」 | `monthly_inbox` 连调 7 次 | 2 步、25,519 token |
| 卡住（未正常结束） | 2 条，各空等 150 s | 0 |
| 总 token（18 条） | — | 727,112 |

未选对的 3 条按运行前定的标准记为错，不事后改标准。三条的原因如下：
- **求和**：`aggregate_metric` 必须传入已声明的指标名，所以先调 `list_metrics` 是必要的一步。
- **陌生列**：人设把 `column_candidates` 设定为在 `batch_summary` 报告有待确认列之后才调，所以它先查了批次状态。
- **别查了，估个数**：队长没有调用工具，而是拒绝估算、说明理由，并要批次编号去按公式计算。这正是期望的行为；用例的 expect 写成「必须调一个工具」，定得有问题。

**审批卡**：「批准并提交」卡现在列出要批准的草稿值、原话与换算、出处和被标出的检查（此前只有编号和 digest）。卡片底部的提示改成通用写法，此前所有审批卡都显示的是列映射专用的提示。真实模型复跑工作流：通过，4 次审批，截图见 `docs/images/08-approval-rejection-note.png`。

**#228 20 万行规模**（`scripts/scale_probe.py`，离线，开发机）：

| 情形 | 结果 |
| --- | --- |
| 20 万行生产部 CSV | 34.1 MiB，被 25 MiB 上传上限拒绝 |
| 同样数据存为 XLSX | 13.6 MiB，能过上传上限；展开 176 MiB，被 100 MiB 防压缩炸弹上限拒绝 |
| 现有上限下能导入的行数（按比例折算） | CSV 约 14.6 万行，XLSX 约 11.3 万行 |
| 放宽字节上限后导入 CSV | 成功，199,988 行全部保留，状态可研判；耗时 80.9–85.8 s，进程内存峰值 1,164 MiB |
| 该批次上的工具（返回大小 / 耗时） | batch_summary 963 B / 2.0 s；integration_summary 2,712 B / 7.0 s；monthly_inbox 2,541 B / 9.3 s；quarantine_list 104 B / 1.7 s；review_context 36,890 B / 2.3 s；调用后内存峰值 1,623 MiB |

结论：返回值在 20 万行时仍有上限，「原始数据行不进上下文」这条约束在规模下成立。但按现有上限，20 万行用哪种格式都导不进来；而且总表摘要和待办清单每次调用都在重算，在这个规模下每次要 7–9 秒。是否放宽上限、服务器内存预算是否够，需要负责人拍板，未改。

## 收尾一轮：工作流、演示样例、真实模型验证（2026-09-23，分支 `feat/rubric-push`）

真实模型为 `deepseek-v4-flash`（env.sh 配置），证据在 `docs/evidence/live-2026-09-23/`。

| 运行 | 结果 |
| --- | --- |
| 四部门研判 · risk（真实模型） | 4/4 校验通过，17.6 s，9 次模型请求，total 86,453 token（缓存命中 53,632） |
| 四部门研判 · balanced（真实模型） | 4/4 校验通过，18.8 s，10 次请求，total 106,485 token |
| 四部门研判 · 单元格注入（真实模型） | 4/4 校验通过，12.3 s，8 次请求，total 71,686 token；注入文字未进入任何会话 |
| 工作流全程（真实模型） | 通过：送审提交 9.7 s、下游开始 6.5 s、完成 7.7 s、补问缺项 10.1 s；4 次原生审批，12 次模型请求，42.5 s |
| 工具选择评测（真实模型） | 跑到 13/18 条时中止：9/13 选对。未选对的 4 条模式相同：队长先调 `batch_summary` 再调目标工具。中止原因：评测脚本不回答提问卡片，遇到即空等 150 s。同时查出 `monthly_inbox` 的 render 只给计数不给事项，队长为一个问题连调 7 次（已修） |
| `business-smoke` 部门故障（离线，`BRIDGEFLOW_TEST_FAULT=step-limit`） | 通过：报告 partial，人工意见后会话数仍为 5 |
| 三套演示样例（离线，`cases-journey`） | core：需人工复核、1 行隔离；other：3 条研判阻碍、1 个待确认列；clean：可研判、零待办、10/10 检查在阈值内 |

未做：工具选择评测全量重跑、README 截图、立项材料页文案、20 万行规模实测（均已开 issue）。

## 界面说清楚一轮（2026-09-23，分支 `feat/ui-clarity`）

设计与写作规范见 [docs/15 一之三](15-plugin-design.md)。改动前后都用同一组离线旅程截图对照（`docs/evidence/round1-e13-e14/`、`docs/evidence/onboarding/`）。

| 项 | 改前 | 改后 |
| --- | --- | --- |
| `ui.ts` 中讲实现机制的中文提示（含「模块 / 读自 / 投影 / 声明 / 同一份」） | 28 条 | 移入「How this works」，提示句只说做什么 |
| 改写的提示 | — | 77 条（`ui.ts` 55、`tour/copy.ts` 22），`ui.ts` 中英同步 |
| 组件里硬编码的全角「：」「（）」「、」（英文界面会露出） | 6 个文件、22 行、28 处 | 0，由 `useUI()` 按语言输出 |
| 打开去处时工作室栏宽度（1440 视口） | 374px（26vw） | 662px（46%），来源栏 288px（20%） |
| 关注项的「为什么在这里」 | 阈值与负责人分散在两行，没有公式 | 一行链路 + 公式 + 出处单元格数 |

验证（最终代码，全部离线、脚本化模型，无计费调用）：

- 后端 **713 passed**，`ruff` 无告警；新增两条断言：关注项的公式等于关键指标行的公式；处置列表带标题。
- 插件 typecheck 通过，**86/86** 通过，构建成功。
- 浏览器旅程：`tour-smoke`、`round1-journey`、`web-smoke`、`quotation-smoke`，以及 `business-smoke` 的 risk / balanced / 注入三个变体，全部通过。（原文写的「部门故障」变体用了错误的开关 `=1`，实际没有进入故障路径；已在下一节用 `=step-limit` 补跑。）

未做：真实模型下的同一套旅程；README 截图未重拍；立项材料（discovery）各页的文案未逐条改写。

## 离线浏览器旅程在工作室改版后全部复绿（2026-09-23，分支 `fix/product-journeys`）

改版（#219/#225）后，5 条离线浏览器旅程只有按新界面写的 round1 还是绿的；CI 不跑它们，所以没人发现。
逐条定位后分成两类：两处真实界面缺陷（引导第 2 步被会话恢复冲回默认页；关闭预览弹出批次数据表），其余是旅程还指着已撤的入口。

在叠加 #246 之后的最终代码上实测（全部离线，脚本化模型，无计费调用）：

| 检查 | 结果 |
| --- | --- |
| 后端 `pytest -q` / `ruff check src tests` | **712 passed** / 无告警 |
| 插件 typecheck / `pnpm test` / build | 通过 / **86 passed**（含 #246 的 i18n key 定义=使用守卫）/ 通过 |
| `tour-smoke`（页面内引导） | 通过，12/12 步；修复前卡在 2/12 |
| `round1-journey` | 通过 |
| `web-smoke`（立项材料 → 候选 → 图 → 评分 → 会议 → 决策，上传上限） | 通过 |
| `business-smoke` risk / balanced | 通过：队长派四个官方子代理，报告 4/4 已校验，数字与独立答案一致；跨操作链路审计 5/5；冷重启无页面错误 |
| `business-smoke` 注入（`BRIDGEFLOW_POISON=1`） | 通过：写进单元格的注入文字不出现在任何模型会话 |
| `business-smoke` 故障（~~`BRIDGEFLOW_TEST_FAULT=1`~~） | **更正（2026-09-23）**：开关的正确写法是 `BRIDGEFLOW_TEST_FAULT=step-limit`，`=1` 实际跑的是正常路径，这一行当时不成立。已于同日用正确开关补跑并通过，见下一节 |
| `quotation-smoke`（含笔记本走查） | 通过：来源栏导入、报价工作区、笔记本保存/恢复/新建/退出、失败保存可重试、窄屏与英文界面 |

复现：`cd plugins && corepack pnpm build && BRIDGEFLOW_LIVE=0 node tests/<name>.mjs`（变体用上表的环境变量）。
未做：真实模型下的同一套旅程；`readme-shots.mjs` / `screenshots.mjs` 仍指着旧入口，README 截图未重拍。

## 席位默认工作区失踪：forward_auth 吃掉 WebSocket 升级（2026-09-21）

线上现象：登录进席位后没有 BridgeFlow 工作区、工作区菜单是空的（目录选择器按企业策略禁用，
连「添加」都没有）、输入框写着「choose a workspace to start」，发不起对话；从 BridgeFlow 顶栏
切笔记本就能用。开发机（macOS, arm64）用**线上同款 Caddy 配置 + 桩 `/verify`（FastAPI + uvicorn，
venv 内已装 `websockets`）+ dsh web** 逐层复现，四项结论：

- **带升级头的 `GET /verify` 被 uvicorn 当成握手**：普通 `GET /verify` → `200 OK`；
  加 `Connection: Upgrade` / `Upgrade: websocket` / `Sec-WebSocket-*` → **403**，
  日志为 `"WebSocket /verify" 403 connection rejected`。加 `--ws none` 后同一请求 → `200 OK`。
- **端到端判别式**（无 cookie 的升级握手打到 `/api/remote.mux`）：现网形态 → **403**，
  响应头 `Via: 1.1 Caddy`（请求没到 dsh）；`forward_auth` 加 `header_up -Connection` /
  `-Upgrade` 后 → **401**（dsh 自己在拒未登录浏览器，升级穿过了认证层）。preflight 查的就是这一条。
- **界面对照**（同一个 dsh web 实例，只换 Caddy 配置）：坏 → 浏览器 WS 探针 `error`，
  chip 显示「Choose workspace」、点开空菜单、输入框禁用、**无 `/api/session/create`**；
  好 → 探针 `open`，chip 回到「BridgeFlow」，输入框可用。
- **为什么本地从来不复现**：`run.sh` / `dev.sh` 直连 `127.0.0.1:<port>`，没有 Caddy、
  没有 forward_auth，WS 直通。

机理与两侧修法见 [`22`](22-lightsail-deploy.md) §7/§9b 与 [`35`](35-seat-isolation.md) §3。复现：

```bash
# 桩门户（装了 websockets 的 uvicorn，等价于 portal.service 改 --ws none 之前）
python -m uvicorn wsprobe:app --host 127.0.0.1 --port 8123
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8123/verify
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8123/verify \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Version: 13'

# 端到端：caddy run 起一个 forward_auth → 8123、reverse_proxy → dsh web 的站点，然后
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8099/api/remote.mux \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Version: 13'
```

未测：实例上的真实数字（合并后由 `preflight.sh` 的新检查回填）；同一条 socket 上的会话流
（侧边栏会话树、回合实时增量）在修复前应同样不通，线上未逐项确认。

---

## 席位化隔离 M0 spike：全新 DSH_HOME 与单实例内存（2026-09-20，#230 落地）

开发机（macOS, arm64）实测，方案与门槛见 [`35`](35-seat-isolation.md) §5 M0。三项结论：

- **全新 `DSH_HOME` 零仓库内容即可首启自建**。`dsh web --patch dsh/enterprise.patch.yml`
  启动时从仓库 cwd 注入全部接线（persona 走 `./dsh/presets`、插件走 `../plugins/src/index.ts`、
  backendUrl 固定 `127.0.0.1:8000`），首启在 home 内自建：`.credentials.yaml`、
  `profiles/{node_modules,web}`、`storages/workspace.json`；home 的用户 patch 层为空（`[]`）。
  席位供给脚本不需要复制任何模板内容，建目录即可。
- **单实例闲时 RSS ≈ 224MB 裸起 / ≈ 289MB 经 start_web.py 完整路径**（`ps -o rss`，node
  单进程、无子进程；macOS 数字，Linux 实例上由 preflight 复核）。均低于 300MB 过门线；
  按完整路径口径 7 席位 ≈ 2.0GB，**贴着 slice 2.0GB 预算线**——若 Linux 实测 RSS >280MB，
  先减为 6 席位或升配 8GB（docs/35 §7 风险表），不硬撑。
- **冷启动 ≈ 1s**（全新 home，从拉起到 launch token 行出现；1 秒粒度）。

未测：真实模型运行下的研判峰值 RSS（MemoryMax=512M 围栏兜底，上线后以 `systemctl status`
实测回填）。复现：

```bash
DSH_HOME=$(mktemp -d) dsh web --patch dsh/enterprise.patch.yml --no-open --host 127.0.0.1 --port 3091
ps -o rss= -p <pid>   # 等 30s 后读
```

---

## 全 Web 化第 3 步：模型发起的读取归属到人（2026-09-20，#231）

离线实现与验证，未调用模型、未接真实飞书租户。设计与边界见 [`27`](27-login-portal.md) 末节，计划见 [`34`](34-web-refactor-plan.md) 第 3 步。

`BRIDGEFLOW_SERVICE_TOKEN` 退回传输凭证；身份改由浏览器交出的门户令牌承担，宿主先经后端 `/identity/me` 验签一次才存，
之后模型触发的读取原样转发，后端逐请求验签。审计主体三种从此分得开：`user:<摘要>` / `host` / `anonymous`。

两条限制各有测试：过期绑定直接丢掉，不转发；同时有 **2** 个人绑定时什么都不挂（错的名字比没有名字更糟），
而同一个人在多个会话里仍算无歧义，另一个绑定过期后歧义自动解除。审批备注 `author` 有绑定时记人。

复现：

```bash
(cd backend && ../../.venv/bin/python -m pytest -q)        # 701 passed
(cd plugins && corepack pnpm exec node --test --experimental-strip-types tests/actor.test.ts)
(cd plugins && corepack pnpm typecheck && corepack pnpm build)
```

后端 **701 passed**（`test_identity.py` 再增 2 条，合计 36）；插件 **83 tests / 82 passed**，
唯一失败是 `dsh-preflight.test.ts` 的 macOS `/private/var` 符号链接断言，与本改动无关（该文件不涉及 actor/identity/portal）；
新增 `tests/actor.test.ts` **8** 条；typecheck 与 build 过。

**未验**：真实模型运行下的端到端归属（本轮没有调用模型，也没有浏览器旅程证据）；两人并发绑定只在单元测试里构造过，没有真实双人会话验证。
**未做**：无归属时拒绝读取——模型读取的授权仍是主机级，这一步只解决归属，不解决授权。

## 全 Web 化第 1 步：控制台操作员角色门（2026-09-20，#229）

离线实现与验证，未调用模型、未接真实飞书租户。计划见 [`34`](34-web-refactor-plan.md) 第 1 步。

门禁默认关闭：未设 `PORTAL_CONSOLE_CHECK_URL` 时 `/verify` 只答登录问题，行为与从前逐字节相同（有测试断言一次都没问过应用）。
开启后三种结局各有测试：有 `console_access` 授权放行 **200**；已登录但没有该授权 **403**（页面不出现「重新登录」——重登修不好缺授权）；
授权无法确认 **503**（页面写明「这不是拒绝」）。判定不在门户重写一份：门户用自己刚签的用户令牌问后端
`/identity/console-access`，后端按 JWKS 验签后走既有 `access_resolver`，角色规则仍只在 `access-control.yaml` 一处。

实现中定下的两处边界：① 答案缓存 **60** 秒、失败**不**缓存（否则一次故障会粘在会话上，有测试数调用次数：两次放行只问 **1** 次，两次失败问 **2** 次）；
② 应用回 503、回非布尔值、回空体一律读成「无法确认」而不是「已许可」（三种畸形答复各一条断言）。
`/identity/console-access` 是唯一不挂 `require_host` 的路由——门户不持有宿主凭证，也不该持有（理由写在 `api/console.py` 模块注释）。

复现：

```bash
(cd backend && ../../.venv/bin/python -m pytest -q)        # 699 passed
(cd portal  && ../../.venv/bin/python -m pytest -q)        # 32 passed
(cd backend && ../../.venv/bin/python -m ruff check src tests)
(cd portal  && ../../.venv/bin/python -m ruff check src tests)
```

Python 后端 **699 passed**（`test_identity.py` 新增 4 条）、门户 **32 passed**（新增 7 条），两处 ruff 全过。

收口时补了一条部署预检（`deploy/preflight.sh`）：门禁已开而没有任何角色声明 `console_access` 时报 FAIL——顺序反了会把所有人锁在门外（[`22`](22-lightsail-deploy.md) §9d）。
判定调 `access_resolver.structure()` 自己的加载器，不用 grep（YAML 注释里也写着这个词，grep 会误判）。两条分支各跑过一次：现行 `access-control.yaml` 只有
`master_office_admin` 一个角色声明它，退出码 **0**；抹掉那一处授权的副本退出码 **1**。门禁关闭时该检查沉默。

**未验**：真实飞书租户下的端到端（真人尚未加入知识库，见 HANDOFF）；Caddy `forward_auth` 对 403/503 的透传形态只读代码确认，没起真实 Caddy 跑过；
上面那条预检只在开发机上按两条分支验过逻辑，没在实例上完整跑过 `preflight.sh`（其余检查需要 systemd 与真实域名）；
本轮没有前端改动，也没有浏览器旅程证据。离线通过不等于部署可用。

## E13 第二轮：跨期对比与差异分解（2026-09-19，#191）

离线实现与验证，未调用模型。基期取该期间最新导入且可见的批次；两期可比性看字段声明而非版本字符串；只有声明为 `additive` 的 **16** 个字段跨项目求和。
以模拟商砼公司 2024-06 与 2024-07 两个批次实测：合计变化分解为新增、消失、持续三部分，**16** 个字段全部满足三者之和等于总变化（性质测试）；
声明阈值 −20% 下，第二实验学校扩建实际量环比 −40% 进入关注区并附两期出处；只有 7 月一个批次时状态为 `no_base`，不显示 0 或 −100%；
删掉基期批次的一个字段声明后状态转为 `declaration_changed` 并列出该字段；计划对比在无声明来源时状态为 `unavailable`。
实现中实测到两处问题并修正：① 总表主键含报表年月，保留它会让两期无一行对得上、每行都显示「新增」，改为按 `period_from` 识别并剔除期间维度；
② 比率指标（净利率 0.09% → −0.5%）的相对变化算出 −679%，改为按百分点给出、不给相对值。
反向验证 **2** 处（取消阈值判定、保留期间维度），均被测试抓到。
Python **629 passed**（新增 `test_comparison.py` 8 条）；TS typecheck、build、**71 passed**；浏览器旅程新增跨期对比一段并通过，截图 `docs/evidence/round1-e13-e14/brief-comparison.png`，页面错误 **0**。

## 可观测第二轮：把链路接到模型侧（2026-09-20）

第一轮只覆盖 HTTP 决策，这一轮把 agent 的循环接进来，自评由 4.5 升到 4.6+。

工具层把 `exec` 的上下文声明成 header（`x-bridgeflow-root` 取 `rootCallId`——dsh 里「这一次模型请求
所拥有的整棵调用树」），后端那条缝仍然不解析任何 body。调用点的改动是每处一个词（`exec.signal` → `exec`），
共 **34** 处；`callBackend` 只接受 `batch_id` 与 `period` 两个键作为主语 header，别的 body 字段进不来（TS 测试锁死）。

实测（浏览器旅程里的脚本化四角色研判）：一次运行 **7** 步、**5** 个代理泳道（队长 + 四部门），
逐步耗时与拒绝原话都在展开清单里；浏览器自己的读取没有根，不计入运行（有测试断言）。
展现形式为泳道时间线：泳道 = 代理，标记 = 工具调用，宽度 = 耗时占比，拒绝用虚线边框加 ✕ 标出，不靠颜色表意。
Python **695 passed**（`test_journal.py` 增至 12 条）；TS **74 passed**（新增 `backend-trace.test.ts` 3 条）；
浏览器旅程新增运行时间线一段并通过，截图 `docs/evidence/round1-e13-e14/agent-run.png`，页面错误 **0**。

## 可观测与评测：决策日志与两半验收（2026-09-20）

按评审 rubric 第 6 项补的一轮，自评由 3.0 升到 4.5（逐项自评写在 HANDOFF）。

**决策日志**写在中间件一条缝上（`journal.py` + `api/main.py`），不是四十处 logging：新端点自动被记，
拒绝按它自己的 `detail` 原话留存。实测 11 次请求：**1 写入、6 读取、4 拒绝**；耗时中位 **45.9 ms**、
最慢 **2141.3 ms**（示例批次导入）；路径里的批次号自动成为主语（11 条中 7 条带批次）；单条约 **271** 字节，
按天 JSONL、保留 14 天。日志不记录读取日志本身。
「日志里没有数据行」由测试逐个值比对总表文本确认；拒绝原话与调用方收到的 `detail` 逐字相同，也有测试锁死。

**验收评测**扩成两半：`python -m bridgeflow.eval --json` 输出正常路径 **24** 条（三行业留出月）
与对抗及拒绝 **7** 条（植入指令识别、无基期、计划无来源、无声明步骤、他月文件、单期趋势、无来源口径决定），
当前 **31 / 31 通过**；报告带生成时间与年龄，红行写明认领 issue；生成物副本存
`docs/evidence/observability/acceptance-2026-09-20.{txt,json}`。

**展现形式**在工作室「记录」页：决策数 / 拒绝 / 写入 / 耗时中位与最慢，「今天拒绝了什么」按原话排行，
明细可按结果与批次筛选，每条带链路编号（与响应头 `x-bridgeflow-trace` 同一个）。
Python **692 passed**（新增 `test_journal.py` 9 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增记录页一段并通过（截图 `docs/evidence/round1-e13-e14/decision-journal.png`），页面错误 **0**。
旅程同时修掉一处偶发：示例按钮在笔记本会话载入前是禁用的，点它不报错也不生效——改为等它可用再点。

## 工作室 UI 重构：四个去处与三层结论（2026-09-20）

先出设计稿再落代码（设计稿：Claude Design 画布，含中英双版结论页）。改动的是信息架构，不是配色：

1. **四个去处**取代原来并列的八个入口：本月任务 / 数据 / 结论 / 记录，其余为「其他工作区」。判据是「人在做什么」，不是模块边界。
2. **进度清单与待确认收件箱合成「本月任务」**：两者本来就读同一份事实（清单说「总表待确认 4 条」，收件箱把那 4 条列出来）。现在并排且互相定位——点某一步的「只看这几条」，右侧只留它在等的事项，总数不变。
3. **导入面板拆成「数据」一条时间线**：取模板 → 提交前自检 → 导入 → 修问题。四部门各占一行，取模板与单部门补传落到该部门自己那一行（此前混在新建批次弹窗里，而补传发生在提交之后）。
4. **结论页分三层**：一眼看完（结论＋四个数字）/ 数字（关键指标与关注项）/ 展开核对（跨期对比、图表默认折叠）。
5. **右栏只陈述事实**，不再放操作；版本链、口径、处置与产物归入「记录」，只读。

字体按双语定：拉丁 Source Serif 4（标题）/ Source Sans 3（正文）排在字体栈首位，中文回落思源宋体 / 思源黑体（同一超家族，混排不会一半粗一半细），数字 tabular。
实现中实测到一处缺陷并修正：新页面渲染在宽度与视口无关的侧栏里，原先按 `@media (max-width)` 排版会在窄栏下重叠（浏览器旅程点不到补传按钮），改为按内容宽度换行。
导览锚点随之迁移：总表在「数据」里、发起研判在「本月任务」里，导览先打开对应去处再指向按钮。
TS typecheck、build、**71 passed**；Python **683 passed**；浏览器旅程全程通过（新增数据时间线、部门行取模板与补传、步骤↔事项联动、结论页折叠），页面错误 **0**，截图 `docs/evidence/round1-e13-e14/data-timeline.png` 等。

## E13 第十一轮：补齐结论页与依据等级的剩余项（2026-09-19，#190、#195）

离线实现与验证，未调用模型。四处缺口一次收掉：
① 关注项展开列出该数字引用的来源单元格（部门 · 文件 · 行 · 列），封顶 **5** 条并给出真实总数，只给引用不给数值，点击进该部门来源预览；
② 结论页作为派生产物出现在产物列表，与研判报告同版本绑定，不另存快照；
③ 图表每个数据点带依据等级——按项目条形的等级与总表该单元格**逐一相同**，趋势取声明指标的等级，把该指标挂上未确认口径后由 G2 变 G3；
④「出处缺失」成为待办收件箱的第五类来源，按字段一条，写明涉及多少单元格与断链原因；实测示例批次里正是跨部门不一致导致留空的那些字段，与总表视图里 `grade` 为 null 的字段集合**完全一致**。
确认口径只改等级、不会把断链变成有链（另有测试锁死）。
Python **683 passed**（新增 6 条）；TS typecheck、build、**71 passed**；浏览器旅程新增出处展开一段并通过，页面错误 **0**。

## E07 第十轮：风险处置审批生命周期（2026-09-19，#19）

离线实现与验证，未调用模型。状态机由字典声明（模拟公司示例：待确认 → 已确认 → 处理中 → 已关闭，另有已驳回；共 **5** 个动作），
字典没声明就明确拒绝，不给默认流程——业务方尚未确认责任与关闭规则，给一套看似合理的默认等于替他们做决定。
实测：研判后三条关注项均为「待确认」，可选动作为 confirm/reject；
从「待确认」直接 close 被拒（409，并列出当前可选动作）；无审批回执被拒（403）；
声明为「必须写理由」的 assign 无理由被拒（422）；带理由后走到「处理中」，再 close 进入终态。
以过期版本号提交被拒（409）且日志里只留下先前那一次；追加日志逐条保留 from/to、审批人与时间。
报告里没有的 check 404。处置不改动报告与任何数字。
Python **677 passed**（新增 `test_dispositions.py` 6 条）；TS typecheck、build、**71 passed**；浏览器旅程通过，页面错误 **0**。

## E14 第九轮：模板下载与上月预填（2026-09-19，#198）

离线实现与验证，未调用模型。沿用关系写在声明里（`carry_over`：生产部「上月实际量」续上期「生产_实际量」），schema 校验该字段确由该部门提供。
实测：导入 2024-06 后下载生产部 2024-07 模板，表头与批准模板 `production-v2.xlsx` **逐列一致**，文件名含声明版本；
预填的「上月实际量」与 6 月总表该项目的「实际量」**逐一相同**，每个预填单元格带「预填自 2024-06，请核对」批注；
没有 6 月批次时一行都不预填，说明页写明「没有 2024-06 的批次」；财务部没有沿用声明，照常可下载但不预填，说明页写明原因；未声明部门 404。
额外验证：生成的工作簿交给 E14-UC03 自检可以读取（交回来的文件必须能被同一份声明导入，D25）。
Python **670 passed**（新增 `test_templates.py` 6 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增模板下载一段，实际下载到 `生产部-2024-07-*.xlsx`，页面错误 **0**。

## E13 第八轮：月度报告文档导出（2026-09-19，#193）

离线实现与验证，未调用模型。报告完全由结论页生成，所以文档说不出页面没说的话。
实测：示例批次导出的 .docx 含八个章节，正文出现的每个 `[Sn]` 在附录都能查到（公式、来源单元格数、依据等级），
文件名为 `月度经营结论-2024-07-<报告号前 8 位>.docx`；
确认「增值税税率」后重新导出，口径章节状态由「未确认」变为「业务方已确认」并写明依据来源，**数值一个都没变**；
用旧报告号导出被拒（409，提示重新生成），不导出旧内容；
财务部研判失败的 partial 报告在封面标「部分完成」并列出缺失部门。
文档按 Office Open XML 直接写出，未新增依赖（D21）；本轮不出 PDF（D22）。
Python **665 passed**（新增 `test_report.py` 5 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增一键导出一段，实际下载到 `月度经营结论-2024-07-*.docx`，页面错误 **0**。

## E13 第七轮：指标可视化与下钻（2026-09-19，#192）

离线实现与验证，未调用模型。图表由字典声明（本轮声明 **4** 张：两条趋势、一张差异瀑布、一组按项目条形），没有声明就只给表格。
实测：导入 2024-05、2024-06 与示例 2024-07 三期后，签收率趋势有 **3** 个点（期间依次为 05/06/07），阈值线为声明值 **97%**，
每个点带批次号且该批次可直接打开；只有一期时不画单点线，而是「至少需要两期」；
删掉 6 月只留 5 月与 7 月时，6 月为断点（value 为 null、无批次），线分两段，不插值也不补零。
差异瀑布四段（基期 + 新增 + 消失 + 持续）之和等于当期值，误差 < 1e-6；
按项目条形按绝对值降序、上限 8 条，超阈值实体标记为 PRJ2023098，且条形数值与总表该行的字段值**逐一相同**。
表格视图与图同源（同一组点），状态不只靠颜色（▲ 标记加表格文字）。
Python **660 passed**（新增 `test_charts.py` 7 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增图表一段（断言表格里既有测得值也有断点），截图 `docs/evidence/round1-e13-e14/metric-charts.png`，页面错误 **0**。

## E14 第六轮：待确认事项收件箱（2026-09-19，#201）

离线实现与验证，未调用模型。四类来源聚合：总表各类问题、隔离行、待匹配上传列、研判落在已更正数据上。
实测：把生产部客户单位写成简称后导入，跨部门不一致 **2** 条；按 E14-UC04 补传正确文件后刷新收件箱，降为 **1** 条——
收件箱没有被任何人通知，它本来就不保存处理状态（D18）。
部门筛选只缩小列表、不改变总数；作用域测试中，不可见事项既不显示也不计入（`total` 从 3 降为 1）。
每项只有「打开处理」，返回结构里没有任何批准/拒绝字段（AC-4 由结构保证）。
研判保存后再补传，新批次自己没有报告而同月旧批次有，收件箱给出一条「研判基于已更正的数据」。
Python **653 passed**（新增 `test_inbox.py` 6 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增收件箱一段（断言每项只有一个按钮），截图 `docs/evidence/round1-e13-e14/open-items.png`，页面错误 **0**。

## E14 第五轮：月度对账进度清单（2026-09-19，#197）

离线实现与验证，未调用模型。步骤由字典 `monthly_close.steps` 声明（本轮在模拟公司字典里声明 **6** 步），字典没声明就整张清单拒绝，不给默认流程。
实测：只导入生产、物资、财务三个部门时，「四部门文件已提交」为 `blocked` 且 outstanding 列出 `marketing`，「四部门研判完成」为 `open`，整体不可结账；
示例批次导入后该步骤转 `done`，而「总表待确认事项清零」的计数与总表视图的 issues 条数**逐一相同**（同一来源，不会互相打架）；
把研判求值器换成抛 `TimeoutError` 后，该步骤为 `unknown`（理由里带异常类型），整体仍不显示「可结账」，其余步骤照常显示。
「可结账」只是读数，不写「已结账」记录，响应里带批次、报告与声明版本（D16）。
Python **647 passed**（新增 `test_checklist.py` 6 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增进度清单一段并通过，截图 `docs/evidence/round1-e13-e14/close-checklist.png`，页面错误 **0**。

## E14 第四轮：单部门补传生成新版本（2026-09-19，#200）

离线实现与验证，未调用模型。以模拟商砼公司 2024-07 示例批次实测：把生产部文件里的「示例建工第一分公司」改成简称后导入，
总表客户名称不一致比干净批次多 **1** 条；补传正确的生产部文件后派生新批次，这一条消失，
`issues_delta` 显示 `disagreement −1`，变化字段包含 `客户名称`；物资、财务、市场三部门的来源 **sha256 逐一相同**，生产部的不同。
原批次逐字节未变（比对批次文件与总表响应），其已保存报告仍可读；新批次没有自己的报告（必须重新研判）。
版本链由索引正向查出（`superseded_by`），冻结批次一个字节都没被改写。
拒绝路径实测：逐字节相同的文件 409「未变化」；上传 2024-06 的生产部文件但表单填 2024-07，仍按**文件自身的行**判出 2024-06 并拒绝；
表单月份不符 422；部门不在本批次 404。
Python **641 passed**（新增 `test_resupply.py` 5 条）；TS typecheck、build、**71 passed**；
浏览器旅程新增补传面板一段并通过（同文件补传被拒的提示），截图 `docs/evidence/round1-e13-e14/resupply-unchanged.png`，页面错误 **0**。

## E13 第三轮：口径确认与替换（2026-09-19，#194）

离线实现与验证，未调用模型。以模拟商砼公司 2024-07 批次实测：声明里 **4** 条按通用做法补的口径（增值税税率＝常数、市场_缺口＝公式、
生产_客户合作状态诊断＝判定规则、rollup.production＝汇总口径）逐条列出其种类与受影响字段。
附来源确认「增值税税率 13%」后，依赖它的 `物资_单方不含税毛利` 依据等级由 **G3 升为 G2**（依据链显示 `G2 增值税税率 (confirmed)`），
本月结论页的 `cells_G3` 随之下降、`cells_G2` 上升；数值一个都没变（D9）。
无来源的决定被拒（422），无审批回执被拒（403），以过期版本号提交被拒（409，不覆盖前一次决定）。
替换公式类口径返回 `replacement_requested` 与该改的声明行 `integration.yaml: derived.市场_缺口 ...`，系统不改写公式（D8）；
常数替换可干跑试算（13% → 6%），给队长的返回值只有变化单元格数、变化行数与字段名，单元格样例仅在浏览器端（D10）。
`convention_decide` 只授予总表管理者（D11）。
Python **636 passed**（新增 `test_conventions.py` 7 条）；TS typecheck、build、**71 passed**（工具目录清单同步新增 3 个工具）。

## 部署配置通道故障与修复（2026-09-19）

现象：线上飞书导入报 503「Access control is not configured」，本地同一操作正常。
实测根因链（证据来自 GitHub Actions run **35419647049**，main，2026-09-19T03:51）：

1. `access-control.yaml` 此前 gitignored，git 部署不携带，靠 deploy.yml 的 secret 通道下发。
2. 该通道的同步步骤排在 `deploy.sh` **之前**，`config-put.sh` 的校验因此跑在实例上
   **尚未更新**的代码上。`access_resolver.py` 恰是同一次 PR 新增的模块，于是校验失败：
   `ImportError: cannot import name 'access_resolver' from 'bridgeflow'`（03:51:38）。
3. `config-put.sh` 的 `set -e` 在校验处中止，**文件一个字节没写**。
4. `appleboy/ssh-action@v1` 已删除 `script_stop` 输入（实测 action.yml 无此 input，
   README 指明用 `set -e` 替代），整段脚本的退出码取自最后一条命令——那是
   field-dictionary 分支的 `echo`，返回 0。该步骤打印
   `✅ Successfully executed commands to all hosts.`，部署整体绿灯。
5. `deploy.sh` 随后把新代码装上，新代码要这个文件，`FileNotFoundError` → 503。
6. 存活检查看不见：它只查 `/`（接受 401）与 `portal/health`（200），
   503 只出现在带登录态的数据路由上。

修复：`access-control.yaml` 改为仓库跟踪（无凭证，space_id 对组织外无意义）；
secret 通道只留给 `field-dictionary.yaml` 并移到 `deploy.sh` 之后；同步脚本首行
`set -eo pipefail`；新增仓库内 ACL 合法性守卫测试。**后端 621 passed**
（基线 620 + 守卫 1），Ruff 通过。复现：`cd backend && pytest -q`（离线，无计费）。

## #204 授权数据源迁移到飞书知识库（2026-09-18）

离线实现与测试之外，**真实租户 Phase 0/3 侦察已完成**（2026-09-18，
`source env.sh && python scripts/feishu_membership_check.py`，env.sh 需含
`FEISHU_APP_ID` / `FEISHU_APP_SECRET`）：五个空间全部 `ok`，各 **1** 名成员
（admin，`ou_` 前缀），单库查询 **0.5–0.6 s**、总耗时 **2.65 s**。envelope
实测为 `data.members`（无 `items`），条目键 `member_id / member_perm /
member_role / member_type`。联调发现并修复一处真实缺陷：成员接口
`page_size` 上限为 **50**，传 100 被 **131002 param err** 拒绝（五个空间全部
复现），已改传 50，`test_access_resolver.py` 未断言该值故无需翻转。
`131006`（应用未加库）与 scope 未发版两种前置问题均已排除——当前各库唯一的
admin 成员疑为应用本体，**真人尚未加入任何知识库**，登录端到端与角色判定
待真人入库后验证。

- 后端 **620 passed**（基线 595 + 新增 `test_access_resolver.py` **25** 条：
  角色绑定、多空间并集、open_id 桥、TTL 缓存与失败不缓存、结构文件 7 类非法 → 503、
  429 重试后 503、HTTP 级分页与非人员成员过滤）。Ruff 通过。
  复现：`cd backend && pytest -q`（v0.1 离线，无计费）。
- 逐人花名册删除：共享身份夹具从「写 users 名单」翻转为「写 spaces+roles 映射 +
  假成员表」，7 个测试文件的授权助手改键路径不改结构。
- `employee_authorizations` 账本新增 `roles` 列（消费时刻角色快照，旧库 ALTER 原地迁移）。
- `.gitignore` 补上 `data/mappings/access-control.yaml`（docs/22 此前声称已忽略，实测未含）。
  **2026-09-19 已反转**：该忽略正是线上 503 的起点，文件改为仓库跟踪，见本文第一节。
- 已知边界：进程重启后 open_id 观察对为空，60 秒许可窗口内重启
  会导致消费端 403（fail-closed，瞬时）；成员表缓存 5 分钟，飞书侧调岗后
  最长延迟 5 分钟生效。

## 飞书在线表格 / 多维表格读取联调（docs/32 / docs/33，2026-09-17）

离线实现完成；第 4 步真实联调进行中，导入端到端与大表分页压测数字待补本节。

- 后端 **595 passed**（本篇新增 10 条），ruff 通过；插件 typecheck、build 通过。
  复现：`cd backend && pytest -q`、`pnpm --dir plugins typecheck && pnpm --dir plugins build`（离线，无计费）。
- 人工前置已生效：用户态 `sheets:spreadsheet:readonly` 与 `bitable:app:readonly` 发版并
  全员重登后，curl 直连 `sheets/v3/spreadsheets/{token}/sheets/query` 返回 `code: 0`。
- 联调暴露并已修复三处：
  1. dsh web 代理路由白名单（`plugins/src/web.ts` 的 `feishuUser` 正则）未含
     `sheet-meta`/`bitable-meta`，浏览器调用被 403「Route not authorized」拦在代理层；已补上并重新 build。
  2. 选中 sheet 后导入按钮不亮：`choose()` 未初始化 `header_row`，显示默认 1 与
     `ready()` 的 `?? 0` 不一致；已改为选中即置 1。
  3. `feishu-import-user` 报 503「Access control is not configured」：运行环境未按 docs/27
     创建 `data/mappings/access-control.yaml`；按示例声明后解除
     （当时为逐人名单格式；#204 起改为 spaces+roles 映射）。

## E13/E14 第一轮：一页结论、依据等级、提交前自检（2026-09-17，#190 / #195 / #199）

均为离线实现与验证，未调用模型，也没有真实员工或业务方验收。
**依据等级（E13-UC06）**：示例批次总表 **4** 行的已溯源单元格中，G1 **232**、G3 **71**、出处缺失 **1**（客户名称部门写法不一致而留空）。单方不含税毛利依赖未确认的增值税口径，判为 G3；各行一致即可的标识字段不计按日汇总口径，判为 G1。
**一页结论（E13-UC01）**：脚本化研判后，关注项按声明的严重度排为净利率、收款计划缺口、材料成本占收入 **3** 项，等级分别为 G2、G3、G2，建议动作均为 G4；财务部研判失败时财务部标为缺失，其指标不出现；较早的报告标为过期；无报告返回 409；生成过程替换全部模型入口后仍成功。
**提交前自检（E14-UC03）**：自检与导入共用 `CheckChain`。7 月模拟留出四部门文件，自检报告与导入存入批次的报告逐项相等，自检前后批次文件不变；v1 物资部模板报「表头不在第 1 行（疑似第 2 行）」；市场部「可争取」写文字时，报出声明核对的非数字与清洗器的错列隔离（第 2 行，引用清洗器原因）。
反向验证 **4** 处：去掉严重度排序、取消最弱等级传递、取消声明核对（2 条失败），均被测试抓到。
Python **574 passed**（新增 `test_conclusions.py` 9 条、`test_self_check.py` 5 条）；TS typecheck、build、**71 passed**；离线 `smoke:web`、`smoke:tour` 与新增 `plugins/tests/round1-journey.mjs` 通过，截图在 `docs/evidence/round1-e13-e14/`（本月结论、总表单元格等级、导入框自检），页面错误 **0**。

## PR 提交前完整回归（2026-09-17）

按用户要求发布本阶段改动并在远端检查通过后合并，未继续增加产品功能。

- 本地 Ruff（与 CI 相同范围）通过；后端 **560 passed**，2 项已有依赖弃用警告。
- 插件 TypeScript、构建通过，单元测试 **71 passed**；diff 检查通过。
- 连续离线浏览器证据沿用下节同一功能版本的验证，本次不声称新增真实企业验收。
- 远端以 `.github/workflows/deploy.yml` 的实际运行记录为准；PR 阶段执行测试，合并 main 后在 DEPLOY_ENABLED=true 时部署并检查公开服务存活。

## 阶段暂停前的决策浏览器验证（2026-09-16）

用户要求整理 handoff 后停止本阶段开发。本节记录当时已经启动的检查结果；后续 Agent 2 消费端和其他工作包留到下一阶段。

- 决策页面已接规则/验签身份与动作展示、提案/条件编辑、本人投票、指定条件确认及明确决定。政策 GET 响应新增服务端验签 viewer.subject/actions，后端授权依然独立检查。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。在既有材料/候选/图/评分/会议旅程后，两个签名测试身份顺序投票，核对非决定人没有批准按钮；达标仍 proposed，首次批准为 conditional，条件确认后仍无批准范围，再次批准才显示范围；政策修订撤下范围。
- 本轮 **17 次原生审批、34 次脚本化模型请求、浏览器错误 0**。产物 `/tmp/bridgeflow-web-e2e-iHxWZp`，已查看 `discovery-decision.png`。这是同一浏览器中切换签名身份的验证，不证明原生会话隔离、多人并发或真实企业 SSO。
- 最终 `pytest -q backend/tests/test_discovery_decisions_api.py`：**4 passed**；最终 TypeScript 检查和构建通过，diff 检查通过。此前完整后端/插件结果见下节；新增 UI 后没有再次重跑全部套件，不将前一次结果当作最终全量。
- 无真实模型计费、消息外发或部署。本地修改尚未提交/推送；完整交接与下阶段顺序已集中到 HANDOFF.md。E01-UC06 仍 PARTIAL，Agent 2 消费端未接。

## MVP 决策领域、授权与原生操作（2026-09-16）

新增人工声明决策政策、纪要版本提案、验签本人选票、指定条件确认、明确批准/拒绝和当前有效范围清单。政策无默认规则；原生四操作均需 ACL 权限及政策角色，批准前/执行前重查。满足票数不自动批准，条件满足也不自动释放；历史或来源/政策过期撤下 Agent 2 范围。

- 决策领域/API 定向 `pytest -q backend/tests/test_discovery_decisions.py backend/tests/test_discovery_decisions_api.py`：**15 passed**。覆盖阈值/弃权/反对规则、重投、角色和伪造 actor 拒绝、条件确认与再次批准、修订清票、历史批准不可用、会议/候选/来源/政策变化、事务并发、部门读取、审批后撤权及缺政策。
- 在 `backend/` 执行 `/home/eric/Hackathon2026/.venv/bin/pytest -q`：**560 passed**，2 项已有依赖弃用警告。
- 插件 `pnpm --dir plugins test`：**71 passed**，新验证四个原生操作完整批准展示、版本绑定、超长动作不截断及 allow 策略不能绕过原生审批。最终 typecheck、build、相关 Ruff 和 diff 检查通过。
- 本轮没有决策浏览器旅程，未声称多员工真实投票或企业验收。Agent 2 范围清单已由领域投影，模板治理尚未消费；不会创建执行交接或通知。真实政策、决定角色及业务签核仍为外部输入，测试全部为明确合成规则。

## 会议授权与浏览器旅程（2026-09-16）

会议清单/历史详情按员工部门过滤；discovery_meeting_save 通过原生审批保存准备或纪要，执行前重查操作权限和全部来源范围。工作室支持从候选准备会议、逐项编辑阶段/假设/依据、修订纪要并阅读结构化详情。

- 在 `backend/` 执行 `/home/eric/Hackathon2026/.venv/bin/pytest -q`：**545 passed**，2 项已有依赖弃用警告。会议 API 新增 4 项测试，覆盖原生批准缺失、验签记录人、读取范围/历史、越权来源、操作撤权、旧序号及审批后来源变化。首次从仓库根运行误收集 portal 测试，因独立 portal_app 未安装停止；更正为 backend 项目目录后全量通过，不将 portal 测试记为已跑。
- 插件完整 `pnpm --dir plugins test`：**70 passed**；最终 TypeScript 检查、构建、相关 Ruff 和 diff 检查通过。新测试检查完整会议批准展示、精确版本/内容绑定和 allow 策略不能绕过原生审批。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。连续材料/候选/图/评分后，从候选准备会议 v1，原生批准，再编辑为纪要 v2，批准并读取详情。**11 次原生审批、22 次脚本化模型请求，浏览器错误 0**。产物 `/tmp/bridgeflow-web-e2e-MG36xe`，会议截图 `discovery-meeting.png`，已查看最终截图。
- 浏览器验证发现修订表单的下拉框及非空 textarea 可访问名称包含内容，补明确 aria-label 后重跑通过。截图复核发现全局 form 样式覆盖 hidden 属性，补显式隐藏样式和非材料页不可见断言，最终重跑通过。
- 仅合成材料/离线模型。会议保存不是 MVP 决策或投票，未做真实业务签核、自动会议摘要、多人共编或未批准草稿持久恢复；E01-UC05 保持 PARTIAL。

## 评分浏览器旅程与会议领域（2026-09-16）

评分表单显示声明量表并准备原生审批请求；四象限显示当前政策下完整评分、可点击依据，缺项/版本变化不落点。材料上传表单限定在材料页，避免遮挡图表。

- `pnpm --dir plugins typecheck`、`build`、`test`：通过，插件 **69 passed**。
- `pytest -q backend/tests/test_discovery_scoring.py backend/tests/test_discovery_scoring_api.py`：**10 passed**，2 项已有依赖弃用警告。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。涵盖完整/缺项评分、原生审批、点击依据、政策修订后撤点，连续材料/候选/图旅程继续通过。**9 次原生审批、18 次脚本化模型请求，浏览器错误 0**。产物 `/tmp/bridgeflow-web-e2e-YHaACT`，已查看 `discovery-quadrants.png`。仅使用合成量表和离线模型。
- 首次评分 smoke 失败于测试等待内部 policy_revised 文案，而页面显示“量表已改变”；修正用户可见断言，并将其他未落点原因双语化，重跑通过。
- 新会议领域 `pytest -q backend/tests/test_discovery_meetings.py`：**6 passed**，覆盖冻结候选快照、会前/会后版本、陈述来源、假设、阶段依赖环、身份/范围、陈旧序号和候选/材料并发保护；相关 Ruff、diff 检查通过。会议尚无 API/原生工具/浏览器旅程，不据领域测试声明端到端完成。
- 本轮未重跑后端完整套件；先前完整结果保留在下节。真实量表、业务签核和会议决定规则仍待业务输入。

## 评分配置、授权与原生审批（2026-09-16）

接入 DISCOVERY_SCORING_POLICY_PATH、政策部门范围及指纹读取、评分授权列表/历史和 discovery_score_save 原生工具。保存同时要求员工操作权限和原生回执，执行时重查政策指纹。默认缺配置报 503，不发明量表。

- 后端完整 `pytest -q`：**535 passed**，2 项已有依赖弃用警告。新增政策/评分读取权限、验签评分人、审批后政策变化拒绝、缺文件、不完整评分不落点、撤权不修订覆盖。
- 插件完整 `test`：**69 passed**，包含完整评分展示、政策/候选/序号绑定及 allow 策略不能绕过原生审批。TypeScript 检查、构建、相关 Ruff 和 diff 检查通过。
- 此轮当时仅 API/工具；评分表单与浏览器证据现见上节。测试采用合成量表，真实尺度及企业签核仍待业务输入。

## 声明量表与评分领域（2026-09-16）

新增人工声明政策指纹/快照、候选版本评分、Decimal 坐标和显式分界点规则。不完整评分不落点，政策/候选/来源变更标为过期；不自动排序或批准立项。

`pytest -q backend/tests/test_discovery_scoring.py`：**7 passed**，覆盖边界相等归属、坐标、缺轴/依据不落点、越界/非有限数字拒绝、缺政策拒绝、政策/候选变更和来源并发保护。Ruff 和 diff 检查通过；无新增 API、原生审批或浏览器旅程证据，E01-UC04 仅更新为 PARTIAL。

## 流程图编辑与可视化浏览器旅程（2026-09-16）

候选清单可创建关联精确候选版本的流程草图；逐项编辑节点/来源、关系状态/条件/返工，经原生审批保存。图清单展示 SVG 和可键盘选择的节点/关系详情；缺失关系仍明确未知。

- 插件完整测试 **68 passed**，最终 TypeScript 检查、构建、diff 检查通过。后端未改领域行为，此轮未重复后端全量。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。连续材料登记/原件下载、候选 v1/v2 保存，再从候选 v2 建图、原生批准图 v1、打开 SVG、选择返工边/节点验证来源。
- 本轮共 **7 次原生审批、14 次脚本化模型请求**，浏览器脚本错误 **0**，另断言无客户端 slot 崩溃、无非法 HTML pattern。产物 `/tmp/bridgeflow-web-e2e-lmzi9P`，图截图 `discovery-flow-edit.png`、`discovery-flow.png`，已查看最终截图。
- 浏览器实测修复了候选→图切换时旧详情误渲染、下拉框可访问名称及标识 pattern 兼容问题，修复后重跑通过。
- 图形布局不推断业务顺序。真实业务共创、图内原件跳转、未批准编辑恢复/协作等边界仍在 E01/HANDOFF；不将离线旅程描述为企业验收。

## 流程图授权与原生审批（2026-09-16）

图列表/历史详情新增部门授权；原生 `discovery_graph_save` 校验图、候选及全部来源范围，员工操作授权及原生回执均不可省略。批准展示完整有界图；写入保持 draft，返回不复制节点/边正文。

- 后端完整 `pytest -q`：**525 passed**，2 项已有依赖弃用警告。新图 API 测试覆盖缺少审批、越权来源/读取、撤权、真实员工署名、历史、来源过期和旧版本冲突。
- 插件完整 `test`：**68 passed**，含完整审批展示、候选版本绑定、后续 allow 策略无法绕过批准。TypeScript 检查、构建、Ruff 及 diff 检查通过。
- 尚未运行图专用浏览器旅程；图形展示/编辑未接，不声称 E01-UC03 完成。

## 信息流与文件流草图领域（2026-09-16）

新增版本化图模型，保留节点角色/触发/输入输出、边的来源/确认状态/条件/返工，以及候选与材料版本。图不生成业务交接或通知。

`pytest -q backend/tests/test_discovery_graph.py`：**5 passed**，覆盖分支/环路/未知边、证据与确认要求、非法端点、历史恢复、来源过期、候选并发更新时事务拒绝、图版本及范围保护。相关 Ruff 和 diff 检查通过。没有新增 API/原生工具/浏览器验证，E01-UC03 仅从 DESIGNED 更新为 PARTIAL。

## 候选编辑与版本修订浏览器旅程（2026-09-16）

候选页面提供逐项陈述、多来源位置、推断标记、待确认问题及原生审批请求。修订读取当前版本并锁定标识/范围；不从页面直接执行业务写入。

- 插件 `typecheck`、构建、完整 `test` **67 passed**，diff 检查通过。此轮没有修改后端领域行为，未重复后端全量。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。在材料登记/下载旅程后，填写新候选、原生批准保存 v1、从页面载入并修订、再次批准保存 v2，详情验证 approval 为 not_decided。共 **6 次原生审批、12 次脚本化模型请求**；不是付费模型质量评测。
- 产物 `/tmp/bridgeflow-web-e2e-PuHCS8`，含 `discovery-opportunity.png` 和材料旅程截图；浏览器脚本错误 **0**。
- 尚无图形共创、语义自动抽取、源材料选择器或草稿跨页面保存；真实员工/企业验收另需样例与参与，UC 状态保持 PARTIAL。

## 暂存配额与独立清理（2026-09-16）

暂存增加可配置员工数量/字节及全局字节限额，检查与插入在同一 SQLite 写事务；拒绝返回 429。独立清理命令默认预览，仅 `--apply` 删除过期暂存，正式事件/原件不参与。

- 后端完整回归 **515 passed**；随后新增 HTTP 429 与 CLI 真实子进程测试，针对登记/配额模块再次验证 **9 passed**。这两个测试加入后没有重复全量运行，不把总数推算成一次完整跑数。
- 覆盖两并发上传争抢最后一个名额、员工/全局额度、删除后额度释放、清理预览无删除、apply 幂等、保留未过期材料。Ruff 和 diff 检查通过。
- CLI 测试仅操作临时目录；没有清理用户运行数据或安装调度。生产调度、SQLite 物理缩容/擦除及未引用正式 blob 的保留策略仍有边界，见 E01/HANDOFF。

## 工作室材料页与员工浏览器旅程（2026-09-16）

工作室新增材料上传表单、项目材料/候选分页清单、待登记请求复制、只读详情和授权版本原件下载。复制请求由人粘贴原生对话；不会自行发送或批准。原件下载在读取前校验范围，读取后校验摘要。

- 后端完整 `pytest -q`：**512 passed**，2 项已有依赖弃用警告。新测试覆盖原件身份/部门范围、精确历史版本、摘要损坏拒绝及文件缺失。
- 插件完整 `test`：**67 passed**；`typecheck`、构建通过。
- `BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**。页面上传 → 复制的登记请求进入原生对话 → 员工授权与原生批准 → 正式材料版本出现 → 下载字节一致；零浏览器脚本错误。保留原有映射批准/拒绝/超时、键盘拒绝和冷启动验证。
- 最终浏览器产物 `/tmp/bridgeflow-web-e2e-bcjdKs`，截图 `discovery-staged.png`、`discovery-registered.png`。截图检查后修复窄栏表单布局，并完成重跑。测量含新增登记审批，共 4 次审批；8 次脚本化离线模型请求，非真实模型用量。
- 真实 OAuth/企业材料/候选共创及全部生命周期未验收；暂存治理仍有独立任务。不能将上述材料旅程推广为整个 E01 已完成。

## 材料暂存与原生批准登记（2026-09-16）

新增受操作/部门权限和部署开关保护的 multipart 暂存 API，及 `discovery_register` 原生工具。上传不创建正式材料；批准精确绑定暂存 ID、摘要与元数据，登记后记录验签员工并消费暂存记录。暂存逻辑到期为 24 小时，清理为后续上传时惰性执行。

- 后端全量 `pytest -q`：**511 passed**，2 项已有依赖弃用警告。新增上传与登记分离、缺审批拒绝、操作/部门/开关约束、摘要/元数据篡改、过期、重复登记和版本冲突覆盖。
- 插件 `pnpm --dir plugins test`：**67 passed**，含登记内容完整展示、摘要绑定及后续 allow 策略无法绕过原生审批；TypeScript 检查、构建与相关 Ruff 通过。
- 未完成浏览器上传表单/送审批交互及连续旅程；没有使用真实企业材料或真实模型。暂存配额、独立清理与授权原件下载仍待实现。

## 原生材料结构检索（2026-09-16）

`discovery_materials` 原生只读工具提供项目材料及工作表分页、准确版本和物理位置；返回不包含原始行、表头标签、标题、来源描述或会议正文。声明与检测类型分别保留，结构不代表业务含义。

- 后端全量 `pytest -q`：**507 passed**，2 项已有依赖弃用警告。新增测试验证材料分页/总数、表格及文本内容排除、工作表总数/截断/继续翻页、非法项目/页长拒绝和主机认证。
- 插件 `pnpm --dir plugins test`：**66 passed**；`typecheck` 和相关 Ruff 检查通过。
- 本轮没有新增浏览器旅程证据。材料上传及批准登记仍未接产品入口；模型读取继续采用可信主机权限，不宣称员工会话隔离。

## 候选原生审批保存（2026-09-16）

新增 `discovery_propose` 原生工具、精确请求审批、门户员工许可/来源范围核查，以及不截断候选正文的有界审批展示。后端返回简短保存凭据，不复制完整材料或候选正文。

- 后端 `pytest -q`：**505 passed**，2 项已有依赖弃用警告；覆盖缺少原生/员工批准、操作拒绝、来源越权、权限撤销、员工署名、单次消费，既有领域测试覆盖来源/版本冲突。
- `pnpm --dir plugins test`：**66 passed**，包括工具目录、完整提案展示/容量拒绝及后续 allow 策略不能绕过审批。
- TypeScript 类型检查、插件构建通过。未运行此新工具的浏览器旅程，材料上传/模型检索/候选页面尚未接好；不宣称完整 UC 或真实业务验收。

## 来源位置与授权读取（2026-09-16）

在材料/候选领域基础上增加结构化来源位置检查、部门授权分页与历史读取 API。修复 WorkflowStore 流前缀查询将下划线/大小写视作 SQL LIKE 模式的问题，改为精确前缀，避免项目混查。

- `cd backend && ../../.venv/bin/pytest -q`：**503 passed**，2 项已有依赖弃用警告。
- 新增/扩展测试覆盖不存在的工作表、越界/非法行区间、文本与表格格式不匹配、空行位置、授权后计数和分页、历史版本权限、来源修订及项目前缀隔离。
- `pnpm --dir plugins typecheck`、相关 Python Ruff 与 `git diff --check` 通过。
- 尚未接审批写工具、材料上传产品入口和候选页面；本轮不是浏览器旅程验收，也未做真实模型或企业验收。

## 材料与候选领域存储（2026-09-16）

`../../.venv/bin/pytest -q tests/test_discovery.py`（backend 目录）针对性验证 **7 passed**：空模板与实际记录区分、历史版本跨服务恢复、原始数据不出投影、并发写拒绝、依据过期、解析失败/格式不支持、范围与项目约束、文本正文隔离、来源检查和提交之间的并发竞态。使用合成数据，尚未覆盖产品 API、原生工具或浏览器；这些入口仍待实现，不能当作完整 UC 验收。

## 员工授权与原生审批联通（2026-09-16）

批准写入新增验签员工许可：精确操作/请求绑定、60 秒有效、一次使用、执行前重查权限；仍须原生批准回执。上传、报告备注分别受独立操作权限约束。员工身份由后端验签取得，不信任模型填写姓名。访问配置迁移与剩余边界见 [登录门户](27-login-portal.md) 及 [E09-UC06](requirements/09-security-approval.md)。

本轮最终验证：

- `cd backend && ../../.venv/bin/pytest -q`：**484 passed**，2 项已有依赖弃用警告。包含过期、重放、请求篡改、跨操作、撤权、数据范围、上传/备注授权与非法导入部门。
- `pnpm --dir plugins test`：**65 passed**；`pnpm --dir plugins typecheck` 与后端 Ruff 检查通过。
- 构建后 `BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`：**passed**，原生 allowed-once / rejected / cancelled 均覆盖，映射持久记录为 `offline-employee`，并断言不存在共享会话身份回退。浏览器脚本错误 **0**。涵盖上传、总表、代理拒绝、审批详情重试、键盘拒绝、冷启动恢复。产物 `/tmp/bridgeflow-web-e2e-TnV8Gh`，包含 `data-workspace.png`、`native-approval.png`。
- 前次同改动本地模式冒烟：`BRIDGEFLOW_LIVE=0 PORTAL_BASE_URL='' pnpm --dir plugins smoke:web` 通过，产物 `/tmp/bridgeflow-web-e2e-4SLK3h`。

员工浏览器测试使用本地临时 JWKS 和签名 JWT、脚本化离线模型，不是飞书 OAuth 或真实模型验收。初次失败分别暴露旧共享身份断言、测试初始化脚本在无存储源文档读取 sessionStorage；已修复并完成上述重跑。授权消费账本不等于业务成功；拒绝/取消个人审计、原生会话和模型读取的员工隔离仍未完成，不宣称多租户隔离。

## 页面内引导与案例留档（2026-09-14）

基于已合并的 `b434ac6`（#175），在 `feat/product-tour-delivery` 实现。新增 React 页面内 Product Tour，
复用官方客户端插件与项目对话框；不新增依赖、不修改 DSH。案例原件、字典、模板／声明指纹与预期结果见
[`data/mock_business/demo`](../data/mock_business/demo/README.md)，实现边界见 [docs/29](29-interactive-onboarding.md)。

核心引导 **12 步**，实际完成导入与书签保存、总表读取、差异展开、单元格依据、对应部门原件、文件来源信息、
XLSX 下载请求、命名和明确保存。样例总表 **4 行，3 行完整，1 处客户名称分歧**；同批次研判上下文
**10 项检查，3 项 attention**（`collection_gap`、`material_cost`、`net_margin`）。它们是合成案例计算与契约结果，不是付费模型结论。

浏览器实测暴露并修复了现有缺口：笔记本的服务端导航白名单缺少 `integration` 和 `handoff`，
导致在新增总表页面保存失败。现已补齐合法目的地，并通过服务端解析测试与真实浏览器保存／刷新验证。
欢迎卡首次加载的会话切换、补充引导返回核心任务、替换样例批次清除旧操作完成标记，也已覆盖。

| 检查 | 结果 | 复现（仓库根） |
| --- | --- | --- |
| Python 全量 | **439 passed，2 warnings，56.69s**；依赖弃用警告 | `../.venv/bin/pytest -q -c backend/pyproject.toml backend/tests` |
| 样例与最终指纹复查 | **3 passed，2 warnings，2.98s** | `../.venv/bin/pytest -q -c backend/pyproject.toml backend/tests/test_sample_notebook.py` |
| Python 静态 | 通过 | `../.venv/bin/ruff check backend/src backend/tests scripts/start_web.py` |
| TypeScript 单测 | **61 passed，0 failed** | `pnpm --dir plugins test` |
| 类型／客户端构建 | 通过 | `pnpm --dir plugins typecheck`、`pnpm --dir plugins build` |
| 新手引导真实浏览器 | 通过，原生 DSH＋真实领域接口＋临时存储；引导 **0 次模型调用** | `pnpm --dir plugins smoke:tour` |
| 原生 Web 与审批 | 通过；离线适配器 **6 次请求**，批准／拒绝／超时、键盘拒绝、冷重启及代理权限 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web` |
| 既有业务链 | 通过，离线适配器 **8 次请求**、`validated`，四部门重叠执行、跨批次归属与刷新恢复 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:business` |
| 报价与笔记本交互 | 通过，**0 次模型请求**；含保存、重开、语言和既有响应式布局 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:quotation` |

引导浏览器断言覆盖首次欢迎、稍后再说和刷新、上一步、Escape 退出与继续、导入失败重试、
实际总表与原件、下载事件、持久化失败不完成、完成后刷新、重播不自动导入／保存、目标消失与超时恢复、
接口延迟、403 与重试、配置拒绝时无欢迎遮罩、**390×844** 布局、可视视口 **1.25 倍**缩放、内部滚动、
未保存修改对话框、补充模块和重置。纯状态回归覆盖不同笔记本、存储被禁用、过期／损坏记录和跨批次事件拒绝。

关键截图：[欢迎](evidence/onboarding/welcome.png)、[真实总表](evidence/onboarding/master.png)、
[单元格原件入口](evidence/onboarding/evidence.png)、[小屏](evidence/onboarding/mobile.png)、
[实际保存后的完成卡](evidence/onboarding/complete.png)。[断言记录](evidence/onboarding/checks.json) 由脚本生成。
已实际检查截图；它们不是静态教程的业务替身。

本轮付费调用 **0 次**。既有回归的 scripted adapter 请求不是 DeepSeek 真实研判证据；未验证新案例的付费四角色连续彩排、
真实企业账户、业务审批、飞书、部署或正式报告签发。未做 Safari／Firefox、真实移动设备、屏幕阅读器人工验收和跨安装迁移验收。
引导只保留标签页级导航状态；关闭标签页不保证恢复。原件／结果与 DSH 数据目录应独立备份。

既有报价／业务 smoke 首次冷重启后被新欢迎卡遮挡；已更新脚本从真实 **Maybe later** 操作关闭，而非强制穿过遮罩。
报价 smoke 会轮换其历史截图，本轮恢复了原有仓库截图，临时新图保留在 `/tmp/bridgeflow-tour-quotation-evidence-1789324413462`。
其他本机日志为 `/tmp/bridgeflow-tour-*.log`；临时数据会清理，可复现代码与上方引导截图在仓库长期保留。

## 新增进度复审与总表边界修复（2026-09-14）

基线 `4816e95`（#166–#173 之后），用户要求审查新增进度，并授权直接修复问题。
本轮修改在 `fix/integration-review-20260914` 分支，按 PR 流程提交审阅，合并状态以远端为准。

| 已复现问题 | 修复后的行为 | 验证入口 |
| --- | --- | --- |
| 新总表每次读取当前声明，修改政策会改变旧批次 | 导入保存 `integration_snapshot`；总表、摘要与 XLSX 共用冻结声明；旧批次无快照则 409，要求重新导入 | `test_old_master_and_download_do_not_change_when_declaration_changes`、`test_legacy_batch_cannot_silently_borrow_current_integration_policy` |
| 选择较后的表头后引用仍从原件第二行计数 | 保存原件 `header_row` / `row_numbers`，同步清洗后行号、修正日志、分页预览及 UI | `test_selected_header_keeps_original_locations_in_preview_and_master` |
| 总表工具摘要把含原始数值的冲突消息交给模型 | 模型只得到声明字段、类型、部门与固定指引；详细原值保留在浏览器 | `test_tool_summary_does_not_forward_numeric_conflict_values` |
| `NaN` / 正负无穷导致数值转换异常 | 记录 `invalid_number`，行不完整 | `test_nonfinite_numeric_cells_are_reported_not_crashed`（3 种输入） |
| 无法核对公式的行仍计完整；汇总跳过缺值行 | 未核对公式／分类计不完整；缺数值的按日汇总拒绝部分求和 | `test_unverified_formula_never_counts_as_a_complete_row`、`test_rollup_does_not_sum_only_the_rows_with_values` |
| 导出以等号开头的文本时会成为 XLSX 公式 | 总表、待确认与假设页的文本均按文字保存 | `test_download_preserves_untrusted_formula_shaped_text_as_text` |

以上 **10 条**新增回归集中在 `backend/tests/test_integration_boundaries.py`。
将同一测试文件放入 `git archive 4816e95` 的临时副本，指向副本 Python 源码执行，**10 failed**；
在修复后版本执行 **10 passed**。测试只使用已有的公开业务样例及人为变更，不读取新的业务留出。
测试隔离同时显式固定 `integration_spec_path`，不继承开发者的私有整合声明。

| 检查 | 本轮结果 | 复现（仓库根） |
| --- | --- | --- |
| 修复前 Python 全量 | **425 passed，2 warnings，15.19s** | `../.venv/bin/pytest -q -c backend/pyproject.toml backend/tests` |
| 修复后 Python 全量 | **435 passed，2 warnings，19.49s**；依赖弃用警告 | 同上 |
| 新增边界回归 | **10 passed，2.03s** | `../.venv/bin/pytest -q -c backend/pyproject.toml backend/tests/test_integration_boundaries.py` |
| Python 静态 | 通过 | `../.venv/bin/ruff check backend/src backend/tests scripts/start_web.py` |
| TS 单测 | 修复后 **55 passed，0 failed** | `pnpm --dir plugins test` |
| TS 类型与构建 | 修复后通过 | `pnpm --dir plugins typecheck`、`pnpm --dir plugins build` |
| 原生 Web 与审批 | 修复后通过，批准／拒绝／超时、冷重启、键盘操作 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web` |
| 正常业务链 | 修复后通过，`validated`，四部门并行和跨批次状态通过 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:business` |
| 故障业务链 | 修复后通过，财务无有效检查，报告 `partial` | `BRIDGEFLOW_LIVE=0 BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |

首次 TS 检查在沙箱中因 IPC `listen EPERM` 无法启动；受限环境内两次 Python 接口检查停住后被中断。
使用获准的测试执行环境完成上述检查，不能把环境阻塞当作产品失败。最终 TS 回归同样在获准环境通过。
本机日志 `/tmp/bridgeflow-review-0914-*.log`；修复后 Web、正常业务、故障业务临时产物分别位于
`/tmp/bridgeflow-web-e2e-C3GLHq`、`/tmp/bridgeflow-web-e2e-EZYTgm`、`/tmp/bridgeflow-web-e2e-CmbqZj`。
临时目录清理后不保证保留；仓库中的新增回归可复现关键缺陷。

本次付费模型调用 **0 次**。没有重跑随机合成留出、真实业务留出、真实飞书或部署；没有宣称已完成录制版本的真实模型验收。
本次浏览器回归覆盖既有路径，新总表的声明漂移、表头来源与导出边界由真实 HTTP 接口和工作簿读取回归验证；
仍需在冻结版本录制新总表的完整浏览器操作。新总表的通过不能替代四角色对同一业务数据的验收。

## 示例笔记本换成业务方 v2 模板案例；修复编码误合并与错用完工日期分月（2026-09-14）

「业务演示 · 月度对账」原来还是 2025-11 的英文合成 CSV。现改为模拟商砼公司 2024-07 四部门 v2 模板（`data/mock_business/demo/`）与对应字典和研判契约。
接入时发现并修复三个既有缺陷：① 实体别名合并只看字符串相似度，`PRJ2024011` 与 `PRJ2024017` 相似度过线被并成一个项目——现在数字序列不同的标签一律不合并；
② 主表按「第一个日期列」分月，市场部的「完工时间」把行分到 2024-12、2025-03——现在按字典 `period_columns` 分月，未声明且有多个日期列时不猜；
③ 跨部门总表的名称不一致按部门到达顺序报 1–3 条并保留先到部门的写法——现在每个字段只报一条、列出各部门写法、单元格留空。
结果：主表 **4** 行；研判 **10** 项检查 **3** 项关注（材料成本占收入 85.26%、净利率 −0.50%、收款计划缺口 942,897.50 元）；总表 **1** 条客户名称不一致。
Python **438 passed**，TS **55 passed**，离线 `smoke:web` 通过。真实模型调用 **0 次**。

## 统一登录门户与飞书 RBAC（代码就绪，待凭据联调）（2026-09-13）

新增 `portal/`：飞书网页登录（授权码流程）→ 门户会话 Cookie → 签发短期应用 JWT（Ed25519，15 分钟），JWKS 公钥发布；后端 `identity.py` 验签，`data/mappings/access-control.yaml` 人预设「union_id → 部门」，批次按「部门子集或导入人」过滤，不可见返回 404。门户模拟租户测试 **14 passed**（登录跳转、已登录跳过飞书直达应用、首页已登录自动跳转、state 防篡改、全流程签发验签、未注册应用/无凭据 fail-closed）；Python **380 passed**（新增 **8** 条：身份层关闭零回归、无令牌 401、伪造/错受众/空 sub 401、导入人可见、越权与未列出用户 404、上传限权、访问控制缺失 503）；TS `typecheck` 与 `build` 通过（`pnpm test` 有一条与本改动无关的既有环境断言失败：运行时路径期望）。**未连接真实飞书**：OAuth 登录回调与 union_id 尚未经真实租户验证。

## 模拟业务样板：月度导出、报价、彩排授权草案（2026-09-13，#141 / #104 / #7 / #20 / #41）

真实材料未到，按用户要求先用虚构样板顶上（`data/mock_business/`，全部虚构）。
**月度导出**：商砼公司 4 项目 × 3 月，四部门表与人工总表由 `scripts/make_mock_business.py` 按业务口径独立算出。`integration_cases.py real`：2024-05 **4/4** 行完整且逐列一致、0 条待确认；2024-06 报缺部门 **1**；2024-07 报名称不一致、跨部门生产量核对、非数字各 **1**，有差异的列恰为被篡改或因不一致而留空的 **4** 列。
为此修正一处核对口径：部门填写的派生值按其书写精度核对（半个末位单位），此前 4 位小数的比率会被误判为与公式不符。
**报价**：询价、合同范本、报价单模板、成本与产能依据、定价与信用政策、声明、抽取记录、手算答案。测试打开原件核对 **11** 条抽取；草稿底价 **419.77**、目标 **436.72**、争取 **448.02** 元/方、目标总额 **5,240,640.00** 元，与手算一致；期望价 415 低于底价标注总经理审批；付款比例、产能、C 级回款、交期 **4** 种违规均拒绝出草稿。抽取为人工核对，不代表自动抽取已实现。
**彩排授权**：`docs/28` 草案，未签署，未运行付费命令。Python **425 passed**。真实模型调用 **0 次**。

## 外部输入的收件准备：飞书实测、部署基建、真实导出评分（2026-09-13，#140 / #138 / #141，[`27`](27-external-inputs.md)）

未连接任何外部系统：飞书凭据未提供，AWS 未配置（用户要求本轮只搭基建），真实导出未提供。
`scripts/feishu_live_check.py` 上传合成工作簿再下载比对；无凭据时报 `not_configured` 退出 2（本机实跑），模拟租户下往返通过且输出不含凭据。
`deploy/bootstrap.sh`、`deploy/preflight.sh`、`deploy/Caddyfile.template` 通过 `bash -n`；**未在真实实例上运行**。一致性测试锁定：Caddy 与单元端口一致、健康检查路径是真实路由、deploy 需 `DEPLOY_ENABLED`、部署文件无密钥与引导变量。
`integration_cases.py real` 用业务方样例（文件按业务方命名习惯）对照总表模板：1 行匹配、逐列一致；改动标准答案一格后报出该列，报告不含单元格值。
Python **416 passed**。真实模型调用 **0 次**。

## XLSX 工作表与表头：声明或选择，不猜（2026-09-13，#47）

导入 XLSX 时，工作表与表头行来自字典的 `sheet_layout`（`{部门: {sheet, header_row}}`）或上传时逐文件的 `sheets` / `header_rows`（导入框「表格位置（可选）」），上传选择优先。都没有时：单工作表直接读；多工作表拒绝并列出全部表名；第 1 行至多一个非空单元格而下方有多列行（标题行、合并标题）则拒绝并指出疑似表头行，不自动跳过。
由程序写入、从未在表格软件里保存过的公式没有缓存结果，原先会被静默读成空值，现在拒绝并提示在 Excel/WPS 中打开保存。合并单元格仍只保留左上角值、不向下填充，空值走既有缺项与隔离规则。
测试用业务方真实的物资部 v1 模板（表头上方有合并标题行）：未声明时拒绝并指出第 2 行，选择或声明第 2 行后表头与原件逐列一致；非法声明报配置无效（503）。Python 新增 **6** 条，全量 **406 passed**；TS **55 passed**；离线 `smoke:web` 通过（含上传）。真实模型调用 **0 次**。

## 字典未写口径按通用做法补齐，带数据调优样例与留出生成（2026-09-13，#141 / #23）

业务方授权「按最佳实践处理」的五项写入 `integration.yaml`，每项在 `assumptions` 里写明做法与依据（见 `data/company_templates/README.md`）：增值税 13%、缺口 = 累计结算 − 收款计划合计、合作状态诊断规则表（签收率 95%、环比 ±5% / −20%）、生产部按日多行汇总（数量求和、厂站与备注去重拼接、比率与诊断用汇总数重算、其余字段须一致）。
业务方样例在新口径下 **76 列全部一致、0 条待确认**，缺口与诊断均核对通过；样例拆成按日两行汇总后仍逐列一致。依赖假设的单元格在出处里带上该条说明，xlsx 另有「口径假设」页，总控摘要列出假设。
`scripts/integration_cases.py` 按声明生成带数据样例并用独立的分数运算给出答案：调优两组（种子 1、2，各 **7** 个干净键、**8** 个故意错误）评分全过；留出 **30** 组（系统随机种子，不落盘）**30/30** 通过，干净键 **268/268** 逐列精确，7 类错误各 **30/30**（同键多行类 **60/60**），五种诊断各有覆盖（稳定增长 84、平稳合作 70、签收异常 50、需求下滑 45、合作萎缩 19）。
评分的反向验证：汇总只取首行、诊断恒为兜底、拼接只取首行、忽略按日多行冲突，**4** 处各被评分抓到。仍是合成数据，不代替真实导出的留出验收。
Python **400 passed**，TS **55 passed**，typecheck 通过。真实模型调用 **0 次**。

## 业务方模板与字典接入：四部门 → 跨部门业务整合总表（2026-09-13，#23 / #141 / #143 / #47 / #92）

> 以下为补齐口径之前的记录：当时「单方不含税毛利」未核对、同键多行一律拒绝。

业务方提供的字典 v2、四部门 v2 模板与总表模板收入 `data/company_templates/`，字典逐行转写为 `integration.yaml`（76 字段、9 条字典写明的公式、1 条跨部门核对）。
用总表里业务方自己的样例行拆回四部门模板后整合：**76 列全部与样例一致**，部门填写的 8 个派生值均按字典公式核对通过；「单方不含税毛利」因字典未声明增值税税率而标「未核对」（声明 0.13 后核对通过）。
拒绝猜测的场景各有测试：公式不符、跨部门生产量核对、名称不一致、缺部门、同键多行无汇总规则、v1 模板缺连接键。反向验证 **4** 处各有 **1** 条失败。
接入中发现并修复两个既有缺陷：① 清洗器表头规范化会删掉中文字符，业务模板里重复的「单价」「材料含量」被合并成同一列，导入直接报错；② 批次保留的原件预览按 pandas 默认精度写 JSON，数值被截成 10 位（改为无损序列化）。
Python **391 passed**，TS **55 passed**，离线三条浏览器 smoke 通过；本地浏览器截图核对总表视图与 xlsx 下载（76 列 + 待确认页）。真实模型调用 **0 次**。

## 真实模型连续彩排与对抗评测（2026-09-13，#41 / #69，**已计费**，用户授权）

四轮真实模型验收最终全部通过（证据 `docs/evidence/live-acceptance-2026-09-13/`，不含原始会话）：

| 运行 | 结果 | 模型请求 | token（输入 / 输出 / 缓存读 / 合计） |
| --- | --- | --- | --- |
| `smoke:business` risk | validated，与独立标准答案一致；跨操作链路与冷重启检查通过 | **8** | 20,966 / 4,198 / 16,896 / **42,060** |
| `smoke:business` balanced | validated，与独立标准答案一致；链路检查通过 | **8** | 20,547 / 4,875 / 16,896 / **42,318** |
| `smoke:business` risk + 投毒单元格 | validated；注入文本（中英指令式）未出现在任何模型会话中 | **8** | 20,819 / 4,827 / 16,896 / **42,542** |
| `smoke:web` 真实审批 | 允许 / 拒绝 / 超时三种结局；拒绝理由原样转述，未声称以后不再询问 | **6** | 5,743 / 821 / 26,496 / **33,060** |

本轮全部付费尝试（含失败与中途停止）共 **10** 次，合计 **388,902** token（输入 156,598、输出 31,984、缓存读 200,320）。
真实运行暴露并修复三个问题：① `batch_summary` 严格输出声明落后于宿主字段，真实 captain 第一步即失败（#166，已加跨语言契约测试）；
② 财务子代理在否定句中写出了声明禁用的话题词，被校验拒绝导致 partial——保留严格校验，指令改为「禁用词连否定也不写」；
③ `smoke:web` 的叙述检查两次误判模型正确的保留说法，改为逐句判断并识别否定/不确定表达。
局限：每个场景只跑一次，不是统计意义上的质量评估；用的是可见合成案例，不是留出集；业务负责人逐项核对与报价样板仍待业务方。

## 提交准备度复核（2026-09-13）

本地代码基线 `06cc1ab`（在下方 #166–#168 之前）；本次只做评估与文档更新，没有修改业务实现。之后的实测以本节以上的记录为准。普通测试使用隔离配置，浏览器显式设置
`BRIDGEFLOW_LIVE=0`。本次付费模型调用 **0 次**；未重跑真实模型、真实飞书、部署或新的留出验收。

| 检查 | 本次结果 | 复现命令（仓库根） |
| --- | --- | --- |
| Python 全量 | **372 passed，2 warnings，9.40s**；警告来自 Starlette/httpx 与 AnyIO 弃用 | `../.venv/bin/pytest -q -c backend/pyproject.toml backend/tests` |
| Python 静态 | 通过 | `../.venv/bin/ruff check backend/src backend/tests scripts/start_web.py` |
| TS 全量 | **54 passed，0 failed** | `pnpm --dir plugins test` |
| TS 类型／构建 | 均通过；本次未重新安装依赖 | `pnpm --dir plugins typecheck`、`pnpm --dir plugins build` |
| 原生 Web／审批 | 通过；允许、拒绝、无人应答，备注、重试、键盘操作及冷读取 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web` |
| 月度正常链 | 通过；**4** 个部门子会话，报告 `validated`，验证并行重叠与跨批次状态 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:business` |
| 月度故障链 | 通过；财务无有效检查，报告 `partial`，其他部门保留结果 | `BRIDGEFLOW_LIVE=0 BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 报价／Notebook | 通过 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:quotation` |

首次浏览器启动在沙箱内因 `listen EPERM: operation not permitted 127.0.0.1` 退出；在允许监听本地端口的环境
重跑上述浏览器套件后全部通过。这是执行权限边界，不能记为产品回归，也不能据此推断所有机器都能启动。
浏览器使用离线适配器：其请求数、合成 token 与亚秒级研判时间都不是付费模型效果或延迟证据。

本机临时日志在 `/tmp/bridgeflow-assessment-{web,business,partial,quotation}.log`；本次临时产物分别在
`/tmp/bridgeflow-web-e2e-PuFhnq`、`/tmp/bridgeflow-web-e2e-oe2sjN`、`/tmp/bridgeflow-web-e2e-bU3Gcz`、
`/tmp/bridgeflow-web-e2e-eDew9h`，清理 `/tmp` 后不保证保留。报价 smoke 自动轮换了仓库截图；本次已恢复原有归档，
新截图保存在临时目录，未把原始会话与凭证归档进仓库。提交建议见 [HANDOFF](../HANDOFF.md#提交准备度评估2026-09-14)。

## 真实 captain 列匹配全流程（2026-09-13，#102，**已计费**）

真实模型、演示服务、浏览器扮演操作者（`plugins/tests/column-match-live.mjs`）：finance 表头改名的四部门批次导入受阻（`needs_configuration`，主表 **0** 行）→ 数据工作区「让 captain 看这批数据」→ captain 依次调用 `column_candidates`、`lookup_field_dictionary` ×2、`confirm_column_match`，提议 `finance.project_code → project`（依据：类型相符、与 marketing.product 值重合 100%）→ 审批卡核对后批准 → 回合 `completed`，叙述写明当前批次冻结、需重新导入 → 重新导入主表 **4** 行、`matched_columns` 含该匹配；原批次仍为 `needs_configuration`。
模型用量（单个会话 **4** 步）：输入 **7,876** token、输出 **1,890** token、缓存读取 **14,336** token，合计 **24,102** token；只做了这一次真实调用。浏览器页面错误 **0**。证据：`docs/evidence/live-column-match/`（摘要与审批卡截图，不含原始会话）。
未做：本次没有在新批次上继续跑四部门研判（研判的真实模型验收见 `17`）。

## 飞书上传下载快捷调用（代码就绪，待凭据联调）（2026-09-13，#140）

新增 `feishu_import`（按文件 token 下载部门文件并导入为一个批次）与 `feishu_upload_report`（把已保存的研判报告传到指定文件夹），均需审批；凭据只从 shell 导出的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 读取，缺失时返回「未配置」。
协议用模拟租户测试（令牌复用、下载文件名取自飞书、拒绝原样上报、上传内容即保存的报告）：Python **372 passed**（新增 **4** 条），TS **54 passed**。**未连接真实飞书**：免费版接口能力与真实上传下载尚未验证。

## 科目分类改为字典声明（2026-09-13，#92）

`metrics.py` 里硬编码的科目关键词（sales / rev / 销售 / 收入、cogs / cos / cost / 成本）移到字典 `account_classes`；未声明时 `sales`、`cost_of_sales`、`gross_margin` 拒绝；声明了分类的部门，金额简单合计是净额，`revenue` 拒绝并提示改用 `sales` 与 `cost_of_sales`。测试解析源码确认代码里不再有科目关键词。
Python **368 passed**（新增 **3** 条）。真实 OA 科目表与独立标准答案仍待 #23，本卡保持外部阻塞。

## 错误出口与数值展示（2026-09-13，#110）

26 处直接显示原始异常的错误出口统一为「本地化说明：服务原文」，网络断开给出可操作提示；表格数字展示若因位数截断而不等于原值，标「≈」并保留完整值（悬停可见），不再静默四舍五入。
TS **53 passed**（新增 **2** 条），离线 `smoke:web`、`smoke:business`、`smoke:quotation` 通过。真实模型调用 **0 次**。

## 浏览器列匹配视图（2026-09-13，#46 / #61）

数据工作区新增「列匹配」标签页：每个字典不认识的上传列、它只能对应的本部门已声明候选、类型是否相符、跨部门值重合和决定状态（open / accepted / rejected / 需字典负责人），不含单元格；决定仍在对话中经审批做出，只对新导入生效。
本地演示服务上用改名表头的合成批次截图核对（页面错误 **0**）。Python **365 passed**，TS **51 passed**，离线 `smoke:business` 通过。真实模型调用 **0 次**。

## dsh 事实固化为测试；隔离行保留原始单元格与移位修复建议（2026-09-13，#55 / #77 / #63）

- 官方审批合约测试：不挂 answerer 时返回 `unavailable` 并写入审计对（含挂 answerer 的对照组）；产品工具目录快照 **18** 个工具。`docs/13` 第八节待实测清单逐条结清。
- **修复一个真实缺陷**：列错位的行进入隔离时，保存的是类型强转之后的值，日期和数量会变成空，原始数据丢失，而且这样的空行能通过重新校验。现在隔离行保留原始单元格。
- 隔离清单标出「整行左移或右移一格即可通过校验」的行（`shift_suggestion`），放行仍须人经审批选择移位方向，移位后的值由后端计算、不经模型。
- `data/README.md` 写明 `acceptance/` 的留出性质已用掉一次，新留出集按 #141 交付。
Python **364 passed**，TS **50 passed**。真实模型调用 **0 次**。

## 映射依据按事实比较、审批备注草稿与终稿（2026-09-13，#82 / #87）

映射记忆的依据改为比较规范化事实（标识、期间、行号、部门名；连接词与语序不计）：同一事实换说法沿用，任一事实增删改即重新询问，事实集合随决定落盘。
新增接口级连续验收：经宿主回执批准 → 再次导入不再询问 → 依据事实变化 → 再次导入重新询问。审批备注保存时为 `draft`，官方决定为拒绝才变 `final`，其他结局标 `unused`；离线 `smoke:web` 断言被拒调用的备注为 `final/rejected`。
Python **363 passed**（新增 **4** 条），TS **48 passed**。真实模型调用 **0 次**。

## 隔离行处置与声明式日期顺序（2026-09-13，#88 / #79）

字典可声明各部门 `date_order`（`day_first` / `month_first`）：斜杠日期严格按声明读取，与声明矛盾的值隔离（`date_conflicts_declared_order`），未声明时歧义日期照旧隔离；非法声明导入 503。
隔离行新增 `quarantine_list`（只列部门、序号、失败的检查，按列名，不含单元格）、`quarantine_decide`（审批；放行须按冻结字典重新校验，可附本人确认的更正值；丢弃须理由）、`quarantine_apply`（审批；生成**新批次**并记录 `derived_from`，原批次不变，重复应用返回同一新批次）。
Python **358 passed**（新增日期顺序 **4** 条、隔离处置 **3** 条），TS **47 passed**（攻击用例载体扩为 **5** 个工具 = **30** 次派发全部拒绝），离线 `smoke:business` 通过。真实模型调用 **0 次**。

## 失效会话链接可见（2026-09-13，#40）

打开不存在的父会话或不属于该父会话的子会话时，页面顶部出现可关闭的错误提示（独立 overlay，不受面板或弹窗状态影响）。
离线 `smoke:business` 新增并通过「父会话下打开伪造子会话链接 → 出现提示」；本地演示服务上另行核对了伪造父链接与伪造子链接两种。
`smoke:web`、`smoke:quotation` 通过，TS **46 passed**。已知边界：若当前正在查看某个子会话，笔记本书签逻辑会随即改写地址，这一路径未单独验证。

## 审批卡重试与键盘、图片出口（2026-09-13，#96 / #99 / #40）

离线 `smoke:web` 新增三项真实浏览器检查并通过：审批摘要接口首次返回 503 时卡片显示失败并可重试恢复；拒绝全程只用键盘
（焦点落到决定卡 → Tab 到理由 → 输入 → Tab 到「拒绝」→ Enter），备注审计照常；向输入框粘贴图片时出现「添加来源」出口。
所有审批写工具使用同一决定卡并按工具命名。`smoke:business`、`smoke:quotation` 通过（修复了 #151 引入的工作室按钮色调与报价 smoke 选择器冲突）。
TS **46 passed**。真实模型调用 **0 次**。本轮未提交 smoke 轮换的截图归档。

## 用量分阶段记账与攻击用例接入真实派发（2026-09-13，#31 / #38 / #69）

报告新增 `usage`：队长编排（只计研判窗口内的步数与 token）与每个部门分开记录，并写明每部门步数上限 **3**；报告出处可直接打开对应原件预览。
共享攻击用例 `untrusted-input.test-cases.json` 接入插件运行时：**6** 条必须拒绝 × **4** 个接收自由文本的工具 = **24** 次真实派发全部拒绝、后端请求 **0** 次；**9** 条普通业务文本不被误拒。
Python **351 passed**，TS **46 passed**，typecheck、build、ruff 通过；离线 `smoke:business` 通过。真实模型调用 **0 次**。

## 研判生命周期收尾（2026-09-13，#111 / #112 / #113）

研判开启即登记（`review_runs`，含统一期限）；汇总按 review_id 幂等；超时后迟到的成功不能覆盖超时终态；
宿主启动回收未结束的研判并落「host_restarted」报告；人工意见由宿主先落盘、带标记的回合被宿主 guard 拒绝研判与写工具。
Python **350 passed**（新增 `test_review_runs.py` **6** 条），TS **43 passed**（新增 **4** 条：意见回合 guard、派活前登记、父模型不派活到期由宿主结束、汇总失败可重试），typecheck、build、ruff 通过；
离线 `smoke:business` 正常与 `BRIDGEFLOW_TEST_FAULT=step-limit` 两种均通过（validated / partial）。真实模型调用 **0 次**。
后两条做过反向验证（去掉重试复位、去掉到期结束，各 1 条失败）。未做：浏览器层面的故障注入；最终叙述回复本身不受期限约束（报告终态已先落盘）；模型用量按阶段记账。

## 填报与流转界面（2026-09-13，#144 / #145）

工作室新增只读「填报与流转」视图。Python **344 passed**、TS **39 passed**，typecheck、build、ruff 通过。
在本机 3082 演示服务上用合成记录（一条已就绪、一条待补）经无头浏览器截图核对，页面错误 **0**；真实模型调用 **0 次**。

## 工作流 DSH 工具层（2026-09-13，#144）

新增 `workflow_catalogue` / `workflow_draft` / `workflow_board`（读）与 `workflow_record` / `workflow_approve_submit`（审批写）。
离线回归：Python **344 passed**（新增 `test_workflow_tools.py` **5** 条），TS **39 passed**，typecheck、build、ruff 通过；
离线 `smoke:business` 通过。真实模型调用 **0 次**，费用 **0**；真实 captain 带人填报的连续对话未验收。

## 工作流基座（2026-09-13，#143 / #144 / #145 / #147）

新增 `bridgeflow/workflow/` 与 `/workflow/*`，设计见 [`25`](25-workflow-foundation.md)。离线回归：Python **339 passed**
（含新增 `test_workflow_foundation.py` **29** 条），ruff 通过。四处关键行为做了反向验证：去掉依据检查、允许未复核提交、
部分输入即打开交接、在代码里写入字段标签，各有 **1** 条测试失败。
真实模型调用 **0 次**，费用 **0**；没有 DSH 工具层与界面，没有接入任何外部系统，通知只写本地发件箱。

## 上传列匹配闭环（2026-09-13，#102 / #46 / #61）

新增 `column_candidates`（读）与 `confirm_column_match`（原生审批写）。离线回归：Python **310 passed**
（含新增 `test_column_matches.py` **8** 条），TS **35 passed**，typecheck、build、ruff 通过。
三处关键行为各做一次反向验证：去掉改名、去掉形状比对、去掉封闭候选集检查，各有 **1** 条测试随之失败。
真实模型调用 **0 次**，费用 **0**；离线 `smoke:business` 通过；`smoke:web`、`smoke:quotation` 与真实 captain 连续验收本轮未跑，不能声称已完成。

## CI 工具链修复（2026-09-11）

主分支 Actions [run 34579999451](https://github.com/EricWang1358/BridgeFlow-AI/actions/runs/34579999451)
在前端依赖安装时失败：`packages field missing or empty`。CI 固定 pnpm 9，但工作区的
`allowBuilds` 配置使用当前开发工具链的格式；并非本轮领域逻辑测试失败。
插件清单现固定 `pnpm@11.25.0`，Actions 与部署脚本都从该声明解析版本。
同一 workflow 增加 PR 离线检查，部署仅允许 main；PR 不会取消进行中的生产部署。

本地 frozen-lockfile / typecheck / build 与 TS **30 passed**，部署脚本 `bash -n` 通过。
未改业务与浏览器代码，本轮不重复 UI smoke；远端结果以修复 PR 的 Actions 为准。
真实模型调用 **0 次**，费用 **0**。

## 浏览器启动链路复验（2026-09-11，PR #118）

浏览器启动与冷重启统一选择锁定的 npm DSH，跳过 venv 的 Python 包装器；显式指定不支持的版本直接拒绝。
候选文件只读 shebang 前缀；服务页诊断有总超时、重定向上限、同源 cookie 边界，HTTP 失败与缺客户端模块均明确拒绝。

新增真实进程／HTTP 回归后 TS **32 passed**，typecheck、build 通过；包括流式响应卡住后的超时退出。
在 venv 优先的 PATH 下运行 `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web`、
`smoke:business`、`smoke:quotation` 均通过。审批实际覆盖 allowed-once／rejected／cancelled、备注回传与冷读取；
月度 **4 个官方子会话**、**4/4 validated**、并行重叠与连续用途切换通过；报价／Notebook 完整旅程通过，浏览器无 JS 错误。
费用 **0**：业务／审批分别是离线适配器 **8／6 次**请求，不是付费模型；报价 **0 次**。
审计与截图复用 [business](evidence/product-patterns/business/manifest.json)、
[approval](evidence/product-patterns/approval/manifest.json) 的 keep-2 归档；
报价最新截图批次 **1789116709591**，保留此前 **1789114831177**，不提交原始会话或完整 prompt。

CI 修复 #137 的 PR 与 main 测试均通过，但部署停在 SSH 上传；已核对仓库及 production 环境均无
SSH_HOST／SSH_USER／SSH_PRIVATE_KEY 与 PUBLIC_DOMAIN。缺项追踪 [#138](https://github.com/EricWang1358/BridgeFlow-AI/issues/138)，
未运行服务器更新或公网检查，不能宣称部署成功。

## 一 当前结论

**可以对外说：**

- 月度对账可在原生 DSH Web 上完成导入、冻结字典的规则计算、官方四角色研判和保存后重开；映射写入另经原生审批。
- 列匹配已完成一次真实 captain 提议、人工批准与重新导入验收，详见上方对应记录；该次没有继续跑新批次研判。
- 研判期限、幂等汇总、重启回收、人工意见 guard、隔离处置与日期声明已有实现和对应回归。
- 业务模板总表已有整合、公式与跨部门核对、来源及 XLSX 导出；本轮补齐冻结与边界保护。报价模拟材料已通过人工抽取核对和手算比对，自动抽取未实现；飞书尚未真实联调。
- 本次离线完整复核通过，最新计数、命令与验证范围见 [新增进度复审与修复](#新增进度复审与总表边界修复2026-09-14)。

**还不能说：**

- 最终录制版本的真实模型连续彩排已经完成，或已证明稳定性 SLA。#167 的真实彩排跑在当时的 main 上，录制版本冻结后需要再跑一次；生命周期的浏览器超时／重启故障注入尚待补证据。
- 已通过真实企业验收：现有真实模型记录基于可见合成案例；新的业务留出集与人工效率基线仍缺。
- `validated` 意味着跨部门映射已全部确认或报表已正式签发；当前报告汇总声明列，不消费待确认关系。
- 已实现员工身份、角色、租户隔离或已部署上线。当前认证是共享 DSH 会话；部署由团队另行安排，本次没有外部验收结果。
- 多 Agent 比单 Agent／纯规则更准确或节省工时：本次未见支持该比较的效果实验。

---

## 二 历史运行环境差异与当前复验（#97）

本页下方多处记录 `smoke:web` / `smoke:quotation` / `smoke:business` 通过。2026-09-07 复核时，
在干净 `main`（`fd983fc`）、重建 `plugins/dist` 之后复跑，三条都失败，浏览器控制台同一句：

| 命令 | 退出码 | 控制台 |
| --- | --- | --- |
| `pnpm --dir plugins smoke:web` | 1 | `client-modules: HTML did not preload @deepseek-ai/dsh-client-modules/client.js` |
| `pnpm --dir plugins smoke:quotation` | 1 | 同上 |
| `pnpm --dir plugins smoke:business` | 1 | 同上 |

当时的判别实验：同一份补丁、同一条 `dsh web` 命令，改用指向已预装 web profile 的真实
`DSH_HOME` 的 harness（`pnpm --dir plugins shots`），该错误出现 **0 次**，界面正常渲染、可交互。
三条 smoke 各自用 `mkdtemp` 建全新临时 `DSH_HOME`，差异指向那里；`dsh --dump-config` 显示组合期
36 个官方客户端插件全在，所以问题出在服务期而不是组合期。

当前复验条件：本轮使用 PATH 中的 `/home/eric/.nvm/versions/node/v22.23.2/bin/dsh`（锁定 npm CLI），
浏览器各自创建临时 DSH_HOME、临时业务存储，明确设置 `BRIDGEFLOW_LIVE=0`；需要本地端口与 IPC 的验收在授权的沙箱外执行。
正常、报价、审批及 partial 均通过，见下方最新记录。没有复现此前 preload 报错，也没有修改共享用户 home 来绕过它。
因此历史失败不应继续被描述为当前所有环境的状态；本轮通过也不等于已定位其它运行时／环境中的根因。

---

## 三 各轮验收记录（新在上）

每轮固定四件事：做了什么、数字、复现命令、这轮不能证明什么。

### 2026-09-11 · 产品能力与工具策略重构

根因：`profile_batch` 已注册且诊断话术会调用它，却被独立执行白名单漏掉；笔记本用途在存储、选项、Studio 和状态页重复分支，报价状态的月度 hooks 仍执行。现在工具自带 `read`／`review`／`approval` 契约，注册目录驱动授权，审批策略注入 gate；用途共享声明，进度与完整页面按工作流组件组合。扩展步骤见 [产品扩展契约](23-extension-contracts.md)。未增加新业务写动作，未改变领域计算或 DSH 源码。

| 检查 | 本轮结果 | 复现 |
| --- | --- | --- |
| Python 全量 | **302 passed**，2 条依赖弃用提示；移除原有 2 条解析 TS 手工清单的断言，由实际 TS 契约测试接管 | `pytest -q -c backend/pyproject.toml backend/tests` |
| TS | **30 passed**，含注册缺项／重复／卸载撤权、扩展审批语义、实际派发诊断工具、用途持久化与非法输入 | `pnpm --dir plugins test` |
| 类型／构建／锁文件／静态 | typecheck、build、frozen-lockfile、ruff 通过 | `pnpm --dir plugins typecheck` / `build` / `install --frozen-lockfile`；`ruff check backend scripts` |
| Notebook 浏览器 | 默认英文、中英切换与持久化、用途、保存重开、来源分页、主表开关通过；**0 模型请求** | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:quotation` |
| 月度浏览器 | **4** 个官方子会话、角色 **4/4 validated**；连续操作 **5 项通过**，含报价状态换批无月度报告请求、月度／综合恢复 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:business` |
| Partial 浏览器 | **3/4** 角色保留、财务 unvalidated、人工意见可提交，未声称宿主已禁止重跑 | `BRIDGEFLOW_LIVE=0 BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 审批浏览器 | allowed-once／rejected／cancelled、双语结构化摘要、拒绝备注、一次性回执及冷读通过 | `BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web` |

最终证据：[月度验收](evidence/product-patterns/business/acceptance.json)、[连续功能检查](evidence/product-patterns/business/chain-audit.json)、[月度血缘](evidence/product-patterns/business/session-audit.json)、[审批审计](evidence/product-patterns/approval/session-audit.json)、[部分失败](evidence/product-patterns/partial/report.json)。Notebook 截图在 `evidence/quotation-ui/runs/1789114831177/`。来源临时目录分别为 `/tmp/bridgeflow-web-e2e-hbjJri`、`/tmp/bridgeflow-web-e2e-yFfZws`、`/tmp/bridgeflow-web-e2e-1upgJY`、`/tmp/bridgeflow-web-e2e-LvIqeA`。每个证据场景保留最近 **2** 轮，历史图片链接改为 Git 提交固定引用；用户真机会话未清理。

中间失败未计作通过：沙箱内 tsx 创建 IPC socket 被 EPERM 拒绝，Python 异步接口测试停住；清理该测试后，在获准的沙箱外跑隔离测试。合入主分支双语实现后，旧测试查找未渲染的「决定内容」、隔着数据模态点击设置，以及假设刷新后移动侧栏仍展开；分别改为核对实际结构化参数、关闭所属窗口后操作、断言点击前后状态与真实面板一致。没有放宽审批超时、跳过失败场景或使用强制点击。最终原生 Web 使用 PATH 中锁定 npm CLI，临时 DSH_HOME 未复现历史 preload 错误；不据此宣称已查明所有环境差异。

**费用：真实业务模型调用 0 次、计费 tokens 0、模型费用 0。** 浏览器的模拟请求与模拟 usage 只验证官方协议，不验证真实模型质量。真实合同抽取、企业政策、在途恢复、完整期限、partial 宿主限制和并发备注结算仍未完成。

### 2026-09-07 · 主表弹窗与来源预览补缺

用户复查指出上一轮验收漏了一件事：默认收起原生侧栏后，Studio 里的主表入口打开的是侧栏内部的 dialog。
隐藏祖先让弹窗边界成为 0 × 0，原生模态又把其余页面锁住，而控制台 **0 条 JS 异常**。
用「无异常」当判断标准本身就是错的。

现在侧栏只留按钮，数据弹窗改由官方 `shell.overlay` 独立承载，不改原生 DOM、不改 DSH。
来源区的问题类似：只放一个禁用的翻页按钮，用户不知道发生了什么；现在单页预览明确写「已显示全部数据，无需翻页」，
原先没有标签的批次编号与 SHA-256 改成「文件来源信息」，逐项说明上传文件、批次、工作表、文件指纹，
并注明指纹不是业务解释。

| 验证 | 结果 | 复现 |
| --- | --- | --- |
| TS、类型、构建 | **24 passed**，全部通过 | `pnpm --dir plugins test`、`typecheck`、`build` |
| Python 聚焦与静态 | **19 passed**，后端未修改 | `pytest -q -c backend/pyproject.toml backend/tests/test_enterprise_web.py`、`ruff check backend scripts` |
| 来源与笔记本 | 通过，`/tmp/bridgeflow-web-e2e-Rx7FT8` | `pnpm --dir plugins smoke:quotation` |
| 完整月度链路 | 通过，`/tmp/bridgeflow-web-e2e-VaraBn` | `pnpm --dir plugins smoke:business` |
| 原生审批 | 通过，`/tmp/bridgeflow-web-e2e-OliJw8` | `pnpm --dir plugins smoke:web` |
| 本机复验 | 原端口 **3082** 更新，保留 **12** 份已有会话；主表打开/关闭/继续操作与来源说明通过，**0 JS 异常、0 模型请求** | 手工 |

本轮验收看的是实际可见且可交互的结果：侧栏收起时，Studio 工具与产物区的 **2 个**主表入口都能打开有真实尺寸的表格，
关闭后还能继续打开报价，而不是只检查 `dialog.open` 或有没有 JS 错误。来源合成 **65 行**，验证 **50 → 15 → 50**
行前后分页与首末页禁用边界，展开预览也能双向翻页。原测试已有向后翻页的内容断言，漏掉的是返回、单页说明，
以及收起侧栏后从主表入口进来的组合。

证据：[主表可见且可关闭](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788723465966/master-modal.png) ·
[有标签的来源信息](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788723465966/source-provenance.png) ·
[功能检查](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788723465966/functional-check.json)。截图保留最近 **2** 轮。
本轮没有新增付费模型调用，费用 **0**。

> 上表三条 smoke 记的是「通过」，本机复跑为红，见第二节。

### 2026-09-07 · 报价声明与原生 Notebook 三栏工作面

[任务书](20-quotation-brief.md) 的样板前第一步完成：独立的 `quotation:` 人工声明示例，复用
`business.expression` 的通用文档求值器，结构化事实配文本 SourceRef，缺项聚合拒绝且不夹带价格。
月度管线保留。自由文本的边界先写进 [设计文档](21-quotation-design.md) 再实现；没有猜测客户原件的解析格式，也没有外发入口。

工作面按用户截图重做：左侧 Sources 是实际上传的文件，中间是原生 Chat／轨迹／审批，右侧 Studio 工具下方是
实际主表与已保存报告。来源与报告可就地预览或展开。报价工作区在空会话的 Studio 里直接可用，只展示配置声明，
不是已生成的交易报价。月度路径与业务状态页保留，此前错误的嵌套三栏和报价模态工作台移除。
DSH 的 AppFrame 与全部槽存储保留，布局走官方 `shell.overlay` 与公开 `data-slot` 样式锚点：
没有 fork DSH、没有复制私有组件、没有搬移原生 DOM、没有第二个 React 根。

| 验证 | 结果 | 复现 |
| --- | --- | --- |
| Python 全量 | **304 passed**，2 条依赖弃用提示；日志兼容与保留策略聚焦复验 **6 passed** | `pytest -q -c backend/pyproject.toml backend/tests` |
| 报价契约 | **28 passed** | `pytest -q -c backend/pyproject.toml backend/tests/test_declared_documents.py` |
| TS | **24 passed** | `pnpm --dir plugins test` |
| 类型 / 产物 / 锁文件 | 通过 | `pnpm --dir plugins typecheck` / `build` / `install --frozen-lockfile` |
| Python 静态 | 通过 | `ruff check backend scripts` |
| 报价浏览器 | 空会话 Studio 入口、原生 composer 不重挂、折叠实际状态、鼠标与键盘调整栏宽、窄屏、中英深浅色；来源上传/分页/展开/换批、命名保存/放弃/取消/失败重试/历史重开、样例与用途变体、完整宿主重启恢复；**0 JS 异常、0 模型请求** | `pnpm --dir plugins smoke:quotation` |
| 月度浏览器 | 完整研判、工具下方报告列表与预览展开、跨批次连续操作、父子链接；**4** 个实际原生子会话、**4/4** 校验 | `pnpm --dir plugins smoke:business` |
| Partial 回归 | **3/4** 保留、财务无有效判断、人工意见提交路径通过；仍不声称宿主已禁止重跑 | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 原生审批 | allowed-once / rejected / cancelled 与理由通道、官方存储审计、冷启动恢复 | `pnpm --dir plugins smoke:web` |
| 运行时聚焦单测 | **11 passed**（含 CLI 选择拒绝与 SDK 显式指定） | `pytest -q backend/tests/test_start_web.py backend/tests/test_dsh_runtime.py backend/tests/test_dsh_provider.py` |

**真机会话创建故障的收尾。** npm Web 启动后，共享 home 的模块 fallback 被 Python 打包运行时改写成 `/snapshot`
入口，后续 `bridgeflow` preset 的 persona 与 ask-user 挂载失败。现在项目的 SDK 入口通过官方 `dsh_bin` 与 Web
共用同一 npm CLI，SDK smoke 不再从 `.env` 读引导变量；模块由官方启动器自愈生成，未修改 DSH 源码。
恢复前已有的 **10** 份会话文件全部保留，没有剪裁或删除用户会话。真机 Web 在原端口 **3082** 重启后，
浏览器实际 `/api/session/create` 回执 `ok: true, agentPreset: bridgeflow`，空会话报价工作区可打开，
**0 JS 异常、0 session/prompt 请求**。空会话不一定持久化，不能拿新增日志文件数当成功回执。
`smoke:quotation` 额外播入失效的 `/snapshot` 代理以检验 npm 自愈；Web 运行期间真正初始化 SDK（不执行 run），
再核对新建会话回执与原生 symlink。直接试验 Python 打包运行时仍须另设独立 `DSH_HOME`，只换 profile 名称隔离不了共享模块。

**笔记本产品链路。** 新建与示例笔记本用官方 workspaceId 创建，保存时同步官方成员关系，原生输入框不再要求
额外选目录（浏览器检查真实 contenteditable 就绪）。名称、用途、来源与预览位置显式保存；有编辑才出现保存/放弃/取消，
失败后留在原页可重试。原生会话抽屉的直接切换保留宿主语义，未保存的编辑只在当前页面草稿里留着。
示例从界面直接导入真实合成文件并冻结示例字典，不改部署策略。用途支持月度、报价、综合；重复点击报价与业务状态
保持选中，来源/工作室按钮和原生折叠按钮状态一致；栏宽支持拖动、键盘、重置及刷新恢复。
完整用户故事见 [演示说明](../demo-walkthrough/notebook.md)。

**连续退出恢复**是本机复验额外发现的：保存退出后，当前会话从空状态重开会把默认状态页当作显式路由，漏恢复来源。
已修正恢复条件，并加了「保存后退出再重开」的连续浏览器回归。刷新或新建后的重开不能代替这条验收。

**冷启动根因。** 锁定的官方 `Session.append` 无法给下游自定义事件加 `ignorable`，旧的 `bridgeflow/review`
与 `bridgeflow/approval-note` 会被原生冷读拒绝。现在研判状态从原生工具事件投影，笔记本与备注写官方
storage-domain，原生标题与领域存储都确认落盘后才显示保存成功。正常与 partial 的 parent + **4** children、
以及拒绝备注，都通过了完整宿主重启读取。历史兼容工具默认只检查，显式应用才在保留原始字节备份后标记已知信息事件；
本机检查需修复 **0** 份，所以没有改写旧日志。

过程中失败的中间轮次没有计作通过：官方逐记录存储键拒绝 JSON 组合键（改身份摘要）；空会话没有原生页签是宿主行为
（验收改用实际可用的 Studio 入口）；恢复标题有独立读取过程（验收等元数据加载完成）；最初从仓库根跑无配置的 pytest
导致异步测试未被运行器接管（按 backend 配置完整复跑通过，未放宽测试）。

**本轮费用：真实模型调用 0 次、计费 tokens 0、模型费用 0。** 报价单测与报价 UI 不启动模型；月度与审批浏览器
用进程内离线适配器。这不验证真实合同抽取准确率，也不验证报价业务口径。

合成单测的独立标准答案：材料成本 **100 SGD/kg × 2 kg/unit**，加工成本 **0.5 hour/unit × 40 SGD/hour**，
合计 **220 SGD/unit**；声明目标毛利率 **10%**、备选毛利率 **20%**，按分向上舍入得底价 **220.00**、
目标价 **244.45**、备选价 **275.00 SGD/unit**；数量 **10** 的目标总额 **2444.50 SGD**。
把材料成本改成 **110 SGD/kg** 并更新对应合成出处后，底价变为 **240.00 SGD/unit**。
这些数字来自单测内部事实，不是客户合同实测，也不是 UI 已出具的报价。

边界：结构化事实最多 **64** 项，指标最多 **24** 项，每个输入最多 **4** 条出处，每片段最多 **480** 字符，
每个输出展示最多 **5** 条出处，真实引用次数照实保留。当前合成案例把每项出处与片段扩到封顶后，
序列化草稿通过「小于 **60000 bytes**」的断言；这不等于所有可能契约都是这个字节数。
计算不依赖展示截断，字段更名不修改 Python。

本轮定位并修掉的问题：旧版只在业务页里嵌套三栏，把声明字段当成 Sources、报告挤进 Chat；
原上传管线没保留清洗前的浏览器视图，所以新批次独立保留解析视图与 SHA-256，来源清单只读元数据，旧批次明确不可预览；
样式核验发现固定侧栏脱离 grid 后中栏占零宽、继承 height 导致顶栏遮挡，几何与 drawer 层级已修；
报告返回操作改为关闭所属 dialog，不再按全局第一个弹窗误关；DSH 原生「新建会话」会复用空会话，
顶栏「新建笔记本」因此显式调用官方 `sessions.create` 创建独立会话并清空当前批次选择。

目录：报价 `/tmp/bridgeflow-web-e2e-sEV0SF`；月度 `/tmp/bridgeflow-web-e2e-uFDJy7`；
partial `/tmp/bridgeflow-web-e2e-WFyjT5`；审批 `/tmp/bridgeflow-web-e2e-c8vP5T`。
截图按场景最多保留 **2** 轮，未清理用户真机会话。

证据：[保存与离开](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/notebook-save.png) ·
[笔记本历史](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/notebook-history.png) ·
[示例来源](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/notebook-sample.png) ·
[三栏空笔记本](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/notebook-empty.png) ·
[深色报价预览](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/quotation-dark.png) ·
[原件分页预览](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/source-preview.png) ·
[工具下方的产物及预览](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/artifact-preview.png) ·
[窄屏](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/quotation-narrow.png) ·
[英文](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/quotation-en.png) ·
[本机工作面](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/live-notebook.png) /
[检查记录](https://github.com/EricWang1358/BridgeFlow-AI/blob/4e885db/docs/evidence/quotation-ui/runs/1788722008993/live-check.json)。

本机最终入口：同一 Web 端口 **3082** 更新后保留 **12** 份已有会话文件，没有删除、剪裁或改写历史日志。
已保存「业务演示 · 月度对账」可直接展示，实际含 **4** 份可预览来源与规则主表；完整宿主重启、历史打开、
保存、退出、再次打开均通过，**0 JS 异常、0 session/prompt 请求**。此前空入口遗漏书签的失败已被连续用例复现并修复。
### 2026-09-06 · 跨操作链路复查

这一轮针对的是「页面都在、单次脚本能跑，但连续操作仍出错」。同一浏览器连续操作两个批次：修复前
**4 项全部失败**，修复后 **4 项全部通过**。四个失败分别是继承旧报告 ID、刷新清除手选批次、
跨批次派活数混用、错误链接留下旧内容。

同时补了三处防护：本次研判不能继承旧报告的投影测试、启动器检查旧构建与子进程退出、
错误字典由泛化 500 改为明确的配置 503。`acceptance.json` 与计量文件分开写，
不能拿 `report_status` 代替整轮验收。结论与未收尾项见 [19](19-chain-audit.md)。

| 检查 | 结果 | 复现 |
| --- | --- | --- |
| Python | **253 passed**（含启动器与无效字典回归） | `pytest -q backend/tests` |
| TS | **12 passed** | `pnpm --dir plugins test` |
| 静态与产物 | 通过 | `pnpm --dir plugins typecheck` / `build`、`ruff check backend scripts` |
| 连续业务操作 | 通过，默认已含跨批次回归 | `pnpm --dir plugins smoke:business`；[明细](evidence/business-mvp/chain-regression/chain-audit.json) / [最终结果](evidence/business-mvp/chain-regression/acceptance.json) |
| Partial 路径 | 通过；只证明意见提交与脚本对应路径，不证明宿主禁止重跑 | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 原生审批与 Web | 通过；allowed-once / rejected / cancelled 与理由通道，无 JS 异常 | `pnpm --dir plugins smoke:web` |
| 证据 | chain-regression 独立场景保留修复前后 **2** 轮；未覆盖已有真实模型证据，未清理真机会话 | — |

这轮浏览器全部用离线模型适配器，没有新增付费模型调用。正常链路 `/tmp/bridgeflow-web-e2e-3OztvL`、
故障链路 `-cBguAe`、审批 `-YgANpT`。另一次最终复验 `-XcxABD` 通过，新增了「错误链接不得残留批次已保存提示」
的断言，该轮未重复导出截图。配置异常的收尾调整另跑相关 Python **22 项**通过。
同批次再次研判时的旧报告问题由投影测试覆盖；重启等故障场景尚未实测。

### 2026-09-06 · 原生队长与业务状态页

实现「对话｜轨迹｜业务状态」独立页签，右上角是部门文件轻量侧栏，全部复用官方槽位，无 DSH fork。
设计与调用链见 [18](18-native-captain-and-state.md)，一站式入口见 [demo-walkthrough](../demo-walkthrough/README.md)。
这一轮覆盖上一轮的 UI 与编排状态，领域标准答案不变。

| 检查 | 结果 | 复现 |
| --- | --- | --- |
| Python | **247 passed**，2 条依赖弃用警告 | `pytest -q backend/tests` |
| Ruff | backend 与 scripts 全部通过 | `ruff check backend scripts` |
| TS / Client / 锁文件 | 通过 | `pnpm --dir plugins typecheck` / `build` / `install --frozen-lockfile` |
| ToolRuntime 与状态投影 | **11 passed**：终局 Spawn guard、审批 ID 与备注关联、空状态、跨审查计数 | `pnpm --dir plugins test` |
| 原生队长 | 父模型同一响应 **4 次**官方 subagent；顶栏 **4**；四子运行重叠；首个实际请求即含 structured_output，正常流程无嵌套工具错误 | `pnpm --dir plugins smoke:business` |
| UI | 中英文、深色、状态页在轨迹之后、文件栏、报告刷新重开、冷启动父子链接通过，无 JS 错误 | 同上，`BRIDGEFLOW_CASE=balanced` |
| Partial + 人工意见 | 财务连续 **3 步**错误后停止，其余 **3/4** 保留；人工意见进入原队长会话，孩子总数仍 **4** | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm --dir plugins smoke:business` |
| 默认审批 | allowed-once / rejected / cancelled，拒绝理由原样回传；界面显示 **5s** 测试与 **300s** 生产配置 | `pnpm --dir plugins smoke:web`，真实模型加 `BRIDGEFLOW_LIVE=1` |
| 证据治理 | 每场景最近 **2** 轮；审计只投影对应 parent + 4 children；测试目录隔离；真机会话只提供手动 prune | `pytest -q backend/tests/test_session_retention.py` |

**配置与费用口径。** 官方 DSH 0.1.2-rc.1，模型 deepseek-official / deepseek-v4-flash。子代理 low reasoning、
每次请求输出上限 **4000 tokens**、最多 **3 步**、子调用组合取消信号 **180s**。注意这三个数分别管单次请求、
步骤数与子调用，不是整名子代理的累计 token 预算，也不是覆盖父模型等待的端到端期限。父模型沿用环境配置。
下表按原生日志的模型响应统计，包含父编排与最终回复。

| 运行 | 端到端 | 模型响应 | 未缓存输入 / 缓存 / 输出 | totalTokens |
| --- | --- | --- | --- | --- |
| [风险组](evidence/business-mvp/risk/measurement.json) | **21.901s** | **9** | **16825 / 16000 / 3945** | **36770** |
| [正常组](evidence/business-mvp/balanced/measurement.json) | **36.805s** | **8** | **16725 / 14080 / 6130** | **36935** |
| [原生审批](evidence/business-mvp/approval/measurement.json) | 未记录端到端 | **6** | **3300 / 16256 / 916** | **20472** |

风险组相对上一轮 host 直接编排基线（**26203 tokens / 19.792s**）增加 **10567 tokens（40.3%）/ 2.109s**。
这是一次请求的样本，不是稳定延迟，也不是货币账单。inputTokens 与 cacheReadTokens 分开计，
reasoning 已计入 output，不再重复求和。

本轮共 **4 次**真实模型运行，落盘 **30 次响应 / 122877 totalTokens**，包括最初的失败，不只算成功的。
首轮在父回复进行时结束测试，所以这个累计是「已记录量」，不声称涵盖未落盘流的全部账单。
迭代清单：[captain-live-iterations.json](evidence/business-mvp/captain-live-iterations.json)（与上一轮的清单分开）。

正常组的真实研判、四部门校验、状态页与中英文截图都通过。那次新加的「冷启动从报告跳子会话」断言随后暴露了
客户端地址缓存误用，现改为从官方目录取地址；该修复由离线完整浏览器 `/tmp/bridgeflow-web-e2e-jQrtzm` 验证，
不伪称付费模型在修复后又跑了一遍。最终的 UI 变更不涉及模型、领域计算或报告内容。

**这轮挖出的四个真实错误：**

- pre-step 发生在 request assembly 之后。在该 hook 才注册结果工具，真实模型的首请求就没有工具。
  现已移到 `agent/created`，pre-step 保留角色票据验证与步骤上限。
- 原离线适配器在没有 schema 时会误调父工具；原断言读 `data.error`，漏掉 `message.content[].isError`。
  已改为首请求含 schema 加嵌套错误的真实检查。
- DSH 的 `subagentAddress` 是「曾经打开过的地址」缓存。首次从报告跳子会话必须读官方 catalog，
  不能假定缓存已在。
- 原生聊天宽度拖柄在自定义宽页面上会拦截点击。状态页用自己的交互层与自适应网格解决，没有改基座布局。

证据：[浅色新页](evidence/business-mvp/risk/business-state.png) ·
[深色](evidence/business-mvp/risk/business-state-dark.png) ·
[英文](evidence/business-mvp/risk/business-state-en.png) ·
[文件侧栏](evidence/business-mvp/risk/department-files.png) ·
[四次原生派活](evidence/business-mvp/risk/native-spawn.png)。
各场景证据根目录的链接始终指向最近一次运行，历史数字以对应迭代清单为依据。
SSO、角色、租户、字段向导、隔离放行与正式签发仍属后续企业试点范围，不在这次新增的 UI 上冒充已实现。

### 2026-09-06 · 业务 MVP sprint 基线

这一轮是 host 直接 spawn 编排的基线，之后被上一轮的父模型原生派活取代。当时完成的是可见合成案例上的
真实模型闭环：演示操作与模拟负责人验收见 [17](17-business-mvp-acceptance.md)。
那不是真实企业负责人签字，也不是留出集或生产上线验收。

| 检查 | 结果 | 复现 |
| --- | --- | --- |
| Python 回归 | **241 passed，11.23s**，2 条依赖弃用警告 | `cd backend && pytest -q` |
| 静态检查 | 通过 | `ruff check backend scripts/start_web.py scripts/make_business_case.py scripts/collect_demo_evidence.py` |
| TS 类型 / Client 构建 / 锁文件 | 通过 | `pnpm --dir plugins run typecheck`、`run build`、`install --frozen-lockfile` |
| 官方 ToolRuntime 契约 | **7 passed**：终局 deny、跨会话备注票据、子代理越权拒绝、一次性回执 | `cd plugins && pnpm test` |
| 正常浏览器链路 | 目录、聚合、官方 spawn、报告落盘、刷新重开、可见四部门卡通过，无 JS 或工具协议错误 | `pnpm run smoke:business` |
| 故障浏览器链路 | 财务连续 **3 步**无效结构后停止；报告 **partial**，财务 **0** 条有效判断，其余部门保留 | `BRIDGEFLOW_TEST_FAULT=step-limit pnpm run smoke:business` |
| 默认原生审批 | 批准、拒绝附理由、无人应答超时均通过；**3 对** asked/decided 按 id 配对，结果 allowed-once / rejected / cancelled | `pnpm run smoke:web`；真实模型加 `BRIDGEFLOW_LIVE=1` |
| 数据拒绝 | 缺价、币种不符、负成本违反声明、零分母、歧义日期、重复行交易身份不明，全部拒绝业务总额 | `backend/tests/test_business_mvp.py` |
| 引用与批次 | 原文件行列可追溯；空记录、去重、隔离不重排引用；旧批次不受新导入与字典变更影响 | 同上及 `test_enterprise_web.py` |

生成测试组每种场景 **12 行**：生产 4、采购 4、财务 2、市场 2，不与更早的历史样本混计。
标准答案由独立显式算术生成，未送入模型。全部计算使用输入全集；每项公式最多展示 **5 条**来源，
`source_count` 是公式引用输入单元格的次数，重复使用按次数计，不是唯一单元格数。

| 部门 / 指标 | 风险组标准答案 | 正常组标准答案 |
| --- | --- | --- |
| 生产：工时负荷 / 剩余工时 | **110% / −10 hours** | **80% / 20 hours** |
| 采购：支出 / 同数量预算价格偏差 | **760 SGD / 8.5714%** | **700 SGD / 0%** |
| 财务：毛利 / 余额加权账期 | **−10% / 47.1429 days** | **33.3333% / 30 days** |
| 市场：订单减产出 / 数量加权请求账期 | **30 units / 50 days** | **−20 units / 30 days** |

辅助口径：两组产出均 **150 units**、采购同数量预算均 **700 SGD**、销售均 **3000 SGD**；
风险组正数成本 **3300 SGD**，正常组 **2000 SGD**。这些是生成案例里的声明值，不能套到旧 GL 或未知 OA 表上。

**最终真实模型复测。** 官方 DSH `0.1.2-rc.1`、官方 `spawn`、模型 `deepseek-official / deepseek-v4-flash`。
每个业务用例都有 **4 个**独立子会话，原生日志的生命周期证明四者实际重叠；每部门 **2 项**判断，合计 **8 项**，
与标准答案一致。每次子运行最多 **3 步**、输出预算 **4000 tokens**，整体研判时限 **180 秒**；
不调用横向通信工具，也不给父会话历史或原始工作簿。

| 运行 | 端到端（含协调者回复） | 模型响应 | 未缓存输入 / 缓存读取 / 输出 | API totalTokens |
| --- | --- | --- | --- | --- |
| [风险组基线](evidence/business-mvp/live-iterations.json) | **19.792s** | **7** | **16234 / 5760 / 4209** | **26203** |
| [正常组基线](evidence/business-mvp/live-iterations.json) | **24.695s** | **7** | **16308 / 5248 / 5121** | **26677** |
| [批准、拒绝与超时基线](evidence/business-mvp/live-iterations.json) | 未记录端到端 | **6** | **3072 / 14208 / 877** | **18157** |

以上都是单次实测，不是延迟 SLA。`request/header` 只在请求头变化时记录，不能拿它的事件数当模型调用数，
表中按 `assistant/message` 响应计数。该适配器的缓存读取与 inputTokens 分开，reasoningTokens 已含在 outputTokens 里。
账单货币金额未核对。

审查与修复过程共完成 **9 轮**真实模型运行 / **59 次**模型响应，API 报告累计 **237042 totalTokens**（含最终运行）。
[完整迭代用量与问题记录](evidence/business-mvp/live-iterations.json) 保留了先前不合格的业务措辞和目录契约错误，
不能只报告最后一次成功的费用。所有离线协议运行都不调用付费模型。

真实拒绝叙述里已经出现：**"客户编码未核实，请销售负责人确认后再提交。"** 同时说明未执行、未写入、下月仍可能询问。
注意审批拒绝不等于保存 `accepted=false`，后者本身仍是一次需要另外批准的写操作。无人应答测试 **5 秒**后结束，
部署默认 **300 秒**。备注最多 **240 字符**，只绑定当前 session/call 的有效临时票据，不授予权限；
旧票据与跨会话请求会被拒绝。

证据：[风险报告](evidence/business-mvp/risk/report.json)、[正常报告](evidence/business-mvp/balanced/report.json)、
[父子与调用审计](evidence/business-mvp/risk/session-audit.json)、[原生拒绝审计](evidence/business-mvp/approval/approval-events.json)、
[故障报告](evidence/business-mvp/step-limit/report.json)、[报告界面](evidence/business-mvp/risk/business-review.png)、
[拒绝理由界面](evidence/business-mvp/approval/rejection-note.png)。
导出脚本只保留合成报告、公开回复与精选审计字段，不复制凭证、完整提示或推理过程。

Rubric 证据从「能收表」推进到官方四角色、真实判断、人工拒绝理由与可复演故障路径，仍不宣称全项达标。
待完成的是真实企业口径、员工 SSO 与角色/租户隔离、字段向导、隔离处置及报表签发；
普通聊天的开放文字不是已校验的财务结论。

### 2026-09-06 · 原生 Web 重构基线（本 sprint 之前）

本节保留 sprint 开始前的基线，当前结果看本文上方。下面的 pipeline 与控制台耗时属于历史实验，
不表示新 Web 现在的能力；旧样本里的歧义日期现在会被隔离，旧总额不能直接沿用。

| 检查 | 结果 | 复现 |
| --- | --- | --- |
| Python 回归 | **221 passed，9.07s**，2 条依赖弃用警告 | `cd backend && pytest -q` |
| 静态检查 | 通过 | `ruff check src tests ../scripts/start_web.py` |
| TS 类型与 Client 构建 | 通过 | `cd plugins && pnpm run typecheck && pnpm run build` |
| 官方 ToolRuntime 派发与回执契约 | **5 passed** | `cd plugins && pnpm test` |
| 原生 Web / Chromium | 上传、主表、原生工作区与对话、批准/拒绝/无人应答超时与文件结果、代理鉴权、禁写路由通过；无页面 JS 错误 | `cd plugins && pnpm run smoke:web` |
| 模型调用费用 | **0**；浏览器审批只加载测试用的离线适配器 | `plugins/tests/fixtures/scripted-model` |
| 上传数据是否真的决定答案 | 两个独立批次分别返回 **17 / 29**；中途改当前字典后，旧批仍返回 **17** | `test_enterprise_web.py` |
| 歧义日期 | 原样进隔离区；含隔离行的批次总额返回 **409 拒绝** | `test_ambiguous_date_is_preserved_in_quarantine_and_blocks_partial_total` |
| 看板只读快照 | **63 项：Done 36 / Backlog 26 / Ready 1；开放 issue 27** | `gh project item-list 1 --owner EricWang1358 --limit 100 --format json` |

浏览器脚本还核对了原生 JSONL 中 **3 组** `approval/asked` / `approval/decided` 的 id，
结果依次是 `allowed-once`、`rejected`、`cancelled`，并展开了 **3 张**领域工具卡片。
无人应答测试等 **5 秒**后拒绝，生产默认期限 **300 秒**。批准写入共享会话授权标识，拒绝后记忆文件逐字不变。
截图见[导入与主表](evidence/native-web/data-workspace.png)、[原生工具与审批结果](evidence/native-web/native-approval.png)。

`conftest.py` 从这时起强制隔离测试 provider、字典与临时输出，普通 pytest 不再继承开发者的付费模型配置。
该基线阶段没有重跑真实模型判断评测，也没有读留出验收集；浏览器离线脚本只证明运行时、审批与 I/O 链路，
不证明模型会遵守拒绝叙述或产出正确 Finding。当时尚缺官方四角色、真实业务判断与来源验收，本 sprint 已补上可见案例证据；
员工身份、隔离处置和真实 OA 验收仍未完成，逐项条件与看板修订建议见 [16](16-dsh-web-review.md)。

---

## 四 单一事实表

不挂在某一轮下面的长期事实。改这里的数时，说明是怎么量的。

### 样本数据（`data/samples/`）

| 项 | 值 | 怎么量的 |
| --- | --- | --- |
| 部门文件数 | 4 | `data/samples/*.csv` |
| 数据行（不含表头） | **18** | production 6 · procurement 4 · finance 4 · marketing 4 |
| 文件总行数（含表头） | 22 | `cat data/samples/*.csv \| wc -l` |
| 覆盖月份 | 1（2025-11） | 因此跨月记忆无法验证 |

```bash
for f in data/samples/*.csv; do echo "$(basename $f): $(awk 'NR>1 && $0 !~ /^,*$/' $f | wc -l)"; done
```

### Sanitizer 产出（隔离修复前的历史记录）

| 项 | 值 |
| --- | --- |
| 修复条数 | **48** |
| 进入 quarantine 的行 | **0** |
| 产量列是否被毁 | 否（PR #53 之前整列变成 `1970-01-01`） |
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

### 测试计数（原 pipeline 历史）

| 项 | 值 |
| --- | --- |
| 测试数量 | **210**（`pytest --collect-only -q`，2026-09-06；#91 指标口径 8、#93 合并口径 8、#94 拒绝叙述 9） |
| 打真实模型的 | `test_resolver.py`（9 个） |
| 其余 | mock provider，只证明代码不崩 |
| 离线全绿 | **210 passed / 7.9s**（`LLM_PROVIDER=mock LLM_PROVIDER_RESOLVER=mock pytest -q`，不计费） |

原实验复现曾继承本机 provider 并计费；现在的测试隔离见上方各轮。

### 耗时与 token（原 pipeline 历史）

resolver 一整轮（PR #70 前后）：

| 方式 | 调用数 | 耗时 | 提示词 |
| --- | --- | --- | --- |
| 一条候选一次调用 | 6 | 129.7s | 587 字符 |
| 按关系类型批量（#4） | **2** | **80.2s** | 1,283–1,469 字符 |

整条 pipeline：10 次调用 / 310.6s → **6 次 / 60.0s**（evaluator 改吃指标而不是原始行，#13）。
但这个 60.0s 复现不出来：2026-09-06 在同一组 2025-11 样本上重测 `POST /analyze`，墙上时间 **144.8s**。
两个数都留着，差异本身待查：60.0s 是改造 evaluator 当天量的，中间落了 #29 记忆、#12/#18 月度轴、#65 指标规则。
重测之前，两个数都不能当作现状引用。

一次 `/analyze` 里工具端的实际调用（读服务日志，不是推测）：

| 端点 | 次数 | 结果 |
| --- | --- | --- |
| `/tools/list-metrics` | 4 | 全部 200 |
| `/tools/aggregate-metric` | 14 | 全部 409（原记 13，按日志重数） |

**13 次全拒**（同一批，按日志实为 14 次）。拒绝本身是对的：模型在问 `used_capacity`、`remaining_headroom`、
`order_quantity` 这些字段字典没有声明的指标，而它此前已经调过 4 次 `list_metrics`。
所以 rubric 第 3、5 项的证据成立（不猜、只拒），代价是时间和钱。见 #89。
日志里 aggregate-metric 另有 4 次 200，但那不属于本次运行：它们排在 `/analyze` 返回之后，是演示时手工 curl 的，
不要读成「模型试到第 18 次终于问对了」。

一次映射裁决，同一个问题的三种配置：

| 配置 | 耗时 | 工具调用 | 灌回模型的工具输出 |
| --- | --- | --- | --- |
| dsh，带 bash | 12–212s | 3–12 次 | 28,431 字符 ≈ 7,100 token |
| dsh + `dsh/no-shell.patch.yml` | **5.9s** | **0** | **0** |
| DeepSeek 直连 | **3.6s** | — | 707 token 总计 |

全套测试的演变：

| 时点 | 结果 |
| --- | --- |
| resolver 在 dsh 上 | 739.6s，3 failed / 16 passed |
| resolver 改直连（PR #34） | 587.0s，21 passed |
| 加 no-shell 补丁（PR #50） | **447.8s，26 passed** |
| 方案 B 落地（PR #53） | **419.6s，38 passed / 1 failed**，重跑即过 |

那次失败是间歇的，而且暴露了一个真缺陷：`test_resolver.py` 的结果取决于本机有没有
`data/mappings/field-dictionary.yaml`（gitignored 的真实数据文件）。这跟「测试跟着 `.env` 走」是同一类问题：
测试结果取决于一个不在版本库里的文件。新增的 `test_tool_endpoints.py` 用 fixture 显式钉住字典，resolver 测试还没有。

补丁省下的 139 秒全部来自 evaluator：它不再跑 bash，但仍然整表进提示词（#13）。
早期文档里的「627 秒」是历史值，且当时的归因是错的（记成「整表塞进提示词所致」，
实际是 dsh 每次调用自发跑十几步 bash），见 [13 §7.2](13-golden-standard.md) 与 issue #25。

### 指标口径修正：material_spend 加的是单价列（PR #91）

`field-dictionary.yaml` 曾把 `unit_price` 声明成 `purchase_amount`，于是 `material_spend`
老老实实把一整列单价加起来当支出报了出去。它引用的每个单元格都是真的：三个价、一次加总、可回溯，
但数字是错的。「结论必须带证据」保证数字来自表格，不保证公式有意义。

| 项 | 值 |
| --- | --- |
| 修正前报出 | 13,540.0 ＝ 4,850 + 5,200 + 3,490（一列单价之和） |
| 三张填了价的 PO 实际 | **117,250.0** ＝ 4,850×12 + 5,200×8 + 3,490×5 |
| 第四张（11-23，RM-Alu-6061） | 4 件、单价空着，所以这个月没有可辩护的总支出 |
| 修正后 | `material_spend` 拒绝，并点名 `procurement row 3 states no amount` |

为什么拒绝而不是只加填全的那几行：少算一行就把「至少花了 117,250」报成「花了 117,250」。
这与 `compute` 早已遵守的规则是同一条：加得动的行才加，加不动就整条拒绝。
两条路线的优先级是写死的：表里自己写了金额列就直接读它（客户写下的数才是能签字的数），没写才派生。
派生式住在字典的 `derived` 段而不是代码里，因为「哪两列相乘等于金额」属于客户的表结构，还在协商中
（`CLAUDE.md` 第八条硬约束）。缺价行必须同时离开分子与分母，理由见下。

`material_price_change` 建在同一个错误声明上，一并修，口径也变了：

| 项 | 值 |
| --- | --- |
| 修正前 | Σ「purchase_amount」（其实是单价）÷ Σ数量，分子分母不是同一批行 |
| 修正后 | 数量加权：只取单价与数量齐全的行，Σ金额 ÷ Σ数量 |
| 2025-10 → 2025-11 实测 | **+17.66%**（3,986.16 → 4,690.00） |
| 遗留 Acme 叙事里的台词 | 「Alu-6061 +18%」。现在它是算出来的（+17.66%，四舍五入即 18%），不是稿子写的；但那一拍要走 `docs/04` 说明的遗留路径才跑得到 |

分母不能带上缺价的行：只加有价的金额、却把缺价行的数量算进分母，会得出一个低于实际成交价的价格。
所以缺价行同时离开分子与分母。这也解释了为什么它对 `material_spend` 是致命的（求和会少算），
对 `material_price_change` 只是缩样（比率仍成立，公式里写明覆盖几行）。

同一次 `/analyze` 的产出：

| 项 | 值 |
| --- | --- |
| 清洗修正 | 33（production 7 / procurement 8 / finance 9 / marketing 9） |
| 隔离行 | **0**，这条路径当时从没被真正走过（#88） |
| 实体 / 已确认关系 / 待裁决 | 15 / 1 / 6 |
| Master Table | 9 行（修复前的运行），期间 `['2025-03', '2025-11']`。那个 2025-03 是 #79：`03/11/2025` 被读成 3 月 11 日。#93 之后行数会变少（同一实体不再分裂），需重跑取新数 |
| 同一 SKU 两行（PR #93 已修） | `SKU-A1`（1200/180h）与 `sku-a1`（1100/175h）曾各占一行。`EntityGraph` 早就把它们并成 `sku:sku-a1` 带两个 alias，但旧代码用原始单元格字符串当 join 键、没查图，resolver 的产物在演示要展示的那一步被丢掉。现在按 `(实体类型, 写法) → 实体` 归一，行里带 `entity_id` |
| 静默覆盖（PR #93 已修） | 多条源行落进同一格时曾是后写覆盖前写：`RM-Alu-6061` 三张 PO 只剩 `qty 4 / unit_price None / 11-23`。现在按字典 `rollups` 声明折叠（`sum`/`average`/`period_end`），没声明又真撞上多行就拒绝整张表并点名度量；属性分歧保留成列表。该行现为 `qty 24 / 均价 5,025`，`source_rows: 3` |
| 平均会抹平月内涨价 | 单价按 `average` 折叠后，4,850 → 5,200 那一轮在表里看不见了。要讲涨价得用 `material_price_change`（月对月、数量加权），或改用别的折叠策略。这是策略选择的后果，不是 bug |
| 跨科目求和仍然可疑 | 财务部同一客户两行：`4000-Sales/A1 +88,400` 与 `5000-COGS/A1 −91,200`，按 `revenue_amount: sum` 折叠后表里是 **−2,800**，一个净发生额，不是任何人以为的「收入」。`metrics.py` 早就为此开了 `sales` / `cost_of_sales` 两个带科目标记的指标，所以发现层是对的，只有表里这一格是净值。要修得把科目标记搬进字典（那里本就是 TODO），见 #92 |
| 表格与指标对账 | 修复后 Σ 表格里的 `production.output_qty` ＝ `total_output` ＝ **4030**（`test_master_rollup.py` 钉住）。此前表格侧报 1,100、指标侧报 4,030，同一屏互相打脸 |
| 发现 / 张力 / 卡片 | 6 / 8 / 1 |

### 验收套件（留出）

| 项 | 值 |
| --- | --- |
| 结果 | **24/24 passed** |
| 覆盖 | 三个行业 × 载入 / 指标 / 五类质量缺陷 / 注入识别 |

```bash
cd backend && python -m bridgeflow.eval
```

验收集是留出的：`data/acceptance/` 在开发期间不读。到货时是 14/24，每条红都挂着 issue 或带着解释，
见 `data/README.md` 的红线。

### dsh 事实

| 项 | 值 |
| --- | --- |
| 版本 | `deepseek-harness-sdk==0.1.2rc1`（锁死） |
| 运行时启动（WSL 文件系统内） | 0.6s |
| 运行时启动（`/mnt/d`） | 3.6s |
| 无工具 turn | 0.6s |
| 早期一次简单 turn（`docs/11` §一 引用的即此值） | 0.7s |
| `sdk-minimal` 的工具册 | `persistent-bash` · `persistent-pwsh` · `str-replace-editor` |
| approval 插件 | 未加载，所以 bash 没有闸门 |
| 可用 model id | `deepseek-v4-flash` · `deepseek-v4-pro` · `deepseek-v4-flash-vision-exp` |

```bash
$RUNTIME --profile sdk-minimal --dump-config | grep '^- id:'
```

---

## 五 人在环内的历史实测（旧 `/console`，#30 / #39 / #86）

这些测量发生在旧 `/console` 与旧 answerer 路径上，当时启用了旧控制台。它不证明原生默认面板能传理由；
那个缺口由本 sprint 的官方 slot 备注接入修掉，当前复演见上方各轮。

| 操作者点了 | 到达控制台 | turn 结束 | `data/outputs/mappings.json` |
| --- | --- | --- | --- |
| 允许一次 | 3.1s | 4.0s `completed` | 写入，含 `authorised_by: eric` |
| 拒绝 | 2.6s | 3.6s `completed` | 不存在 |
| 无人应答（#39） | — | 报错 | 不存在 |
| 拒绝 + 理由（#86 修后复测） | 4.2s | `completed`，叙述里引用了理由 | 无新增 |

第三行是 #39 已经证明的那条：`tool "confirm_mapping" requires approval, but no approval channel is available`。
它现在是四条路径里的一条，而不是唯一一条。分级自主权与「无人能介入」的差别就在这四条里。
旧耗时保留作历史记录，不再提供已失效的 `/console` 启动命令。当前原生路径复演：

```bash
source env.sh
BRIDGEFLOW_LIVE=1 node plugins/tests/web-smoke.mjs
```

**#86（PR #94）之前为什么会说 `done`。** 拒绝路径下模型收到的是框架的固定句

    Error: the user rejected tool "confirm_mapping"

里面没有地方放理由，框架不认识操作者想说什么。于是「被拒绝」和「被批准」在叙述里长得一样。
现在 gate 自己通过 `ctx.approval.request()` 发问，拒绝的话由我们写。审计事件成对、fail-closed、
`never` 策略（CI 仍然无人被问就拒）全部保留。实测：

模型收到 → `confirm_mapping did NOT run: a person reviewed it and refused. The reviewer said: "evidence is stale - use the October BOM, not this one". Nothing was written, …`

模型说出 → "The record was not written: the confirm_mapping call was refused by a human reviewer because the evidence is stale — they said to use the October BOM, not that evidence — and so no mapping decision was stored."

`unavailable` 与 `cancelled` 不会被写成「有人拒绝」：没人被问到时说「没人能决定」，
答前撤回时说「撤回后才拒」。编一个决策者出来，比这个 bug 本身更糟。

---

## 六 rubric 计分（迁移前的历史自评）

保留是为了说明排期为什么那样走，不代表当前验收状态。逐条比对见 [13 第六节](13-golden-standard.md)，
当前逐项条件与远端 issue 建议见 [16](16-dsh-web-review.md)。

| # | 项 | 当时状态 |
| --- | --- | --- |
| 1 | Goal & Scope | 达标 |
| 2 | Architecture & Reasoning Loop | 不达标 |
| 3 | Tool Use & Integration | 不达标 |
| 4 | Autonomy & HITL | 达标（拒绝与批准两条路径都在真实运行时上跑通） |
| 5 | Safety & Guardrails | 不达标 |
| 6 | Observability & Eval | 部分 |
| 7 | Platform & Tooling | 不达标 |

**7 项中 2 项达标。**

---

## 七 别再直接引用的值

| 出现过的值 | 问题 | 现在该用什么 |
| --- | --- | --- |
| 「21 行」「22 行」样本 | 22 数进了表头，21 来源不明 | 数据行 **18**（见第四节） |
| 「47 fixes, 3 rows quarantined」 | 两个数都不对 | 48 条修复、0 行隔离（且那次运行没走过隔离路径）；台上不要说这两个数 |
| 「627 秒整条 pipeline」 | 历史值，且当时归因错误 | 见 #25 与第四节的三种配置对照 |
| 「60.0s」 | 复现不出来（重测 144.8s） | 两个数都不作为现状引用，待重测 |
| aggregate-metric「13 次」 | 按日志重数是 14 次 | 14 次全拒；日志里另有 4 次 200 属于手工 curl，不属于本次运行 |
| 旧样本的业务总额 | 歧义日期现在会被隔离，折叠规则也改了 | 重新跑，不要沿用 |
| 下方各轮的「smoke 通过」 | 本机复跑为红（#97） | 引用前先复跑，见第二节 |
## 14x 需求基线与下游工具（2026-09-16）

代码基线 `4a38904`；本轮工作分支 `feat/14x-requirements-delivery`。已只读核对 #127/#125/#140/#141/#143/#144/#145/#147 的正文与评论。
需求目录为 [requirements](requirements/README.md)，三个双语 epic、21 个 UC、八步工作包；E02-UC07/08 更新为离线实现，E03-UC01 为部分实现。

| 验证 | 命令（仓库根目录） | 结果 |
| --- | --- | --- |
| 针对性工作流行为 | `../.venv/bin/python -m pytest backend/tests/test_workflow_tools.py backend/tests/test_workflow_foundation.py -q` | 39 passed |
| 后端完整离线回归 | `../.venv/bin/python -m pytest backend/tests -q` | 453 passed；2 条依赖弃用警告 |
| 改动 Python 静态检查 | `../.venv/bin/ruff check backend/src/bridgeflow/api/workflow_tools.py backend/src/bridgeflow/workflow/service.py backend/src/bridgeflow/workflow/guidance.py backend/tests/test_workflow_tools.py backend/tests/test_workflow_foundation.py` | 通过 |
| 插件类型检查 | `pnpm --dir plugins typecheck` | 通过 |
| 插件完整回归 | `pnpm --dir plugins test` | 62 passed（随后新增的一项审批绕过测试由下一行验证） |
| 最终原生运行时测试 | `pnpm --dir plugins exec tsx --test tests/runtime.test.ts` | 32 passed，包含新增审批绕过拒绝测试 |
| 插件构建 | `pnpm --dir plugins build` | 通过 |

首次后端测试因拉取的新身份模块缺少已声明的 PyJWT 依赖而收集失败；执行 `../.venv/bin/python -m pip install -e 'backend[dev]'` 同步现有依赖后重跑通过，未修改依赖清单。

行为覆盖：没有审批不得改变下游状态；后来注册的 allow 策略不能绕过原生审批；审批绑定 ID、动作、seq 和原因；waiting 不可直接完成；过期 seq 拒绝；退回必须有原因；部署写开关生效；上游未重新就绪不可确认修订；stale 时不可开始/完成；确认新版本后可继续。岗位指引只使用声明，未知阶段 404，本地目标明确为 demo，未配置联系人不编造，读取不写业务事件。

边界：这些是离线行为与构建证据。没有新增浏览器截图、真实模型对话、飞书/目标系统调用、一线参与或业务签核。原生工具接入不代表完整岗位页面已验收，#143/#144/#145 仍有明确开发缺口；未对远端 issue 发评论或关闭。

## 全项目 UC 盘点补全（2026-09-16）

纠正上一轮只覆盖 14x 的范围遗漏：`docs/requirements/` 扩展到既有产品能力、新主线与历史延期范围，保留 E01–E03 编号。新增 E04–E12 双语 epic，分别覆盖导入清洗、字典映射、总表整合、四角色研判、报价、安全审批、原生工作室、运维评测及历史知识库范围。

本轮只修改需求与交接文档，没有新增运行时代码或模型调用。通过 GitHub CLI 读取所有 96 条 issue 的状态与正文，补读 #17/#22/#121/#128–135 的关闭评论，结合现有实现、测试和历史验收记录确定状态。#128–131 明确因本轮不做而关闭；#132–135 没有关闭说明，不从 CLOSED 推断已经交付。

盘点结果：12 个 epic、73 个唯一 UC。状态为 IMPLEMENTED 38、IMPLEMENTED_OFFLINE 2、PARTIAL 14、DESIGNED 11、DEFERRED 5、BLOCKED_EXTERNAL 3。这里的已实现状态是代码与验证资产盘点，不能作为真实公司签核比例。

文档校验通过：所有 UC 编号唯一、索引与正文状态一致、双语段落存在、本地引用目标存在；追溯矩阵覆盖 FR01–26 及全部 96 条 issue；`git diff --check` 通过。没有为这次纯文档补全重复运行产品测试，已有运行时变更的回归结果见上节。

## 未完成边界实施：浏览器读取授权（2026-09-16）

目标及后续顺序见 [implementation-plan](requirements/implementation-plan.md)。本轮实际补齐总表 JSON/XLSX 的门户身份及批次范围检查，工作流目录/血缘/看板/草稿/落地信号的显式部门范围检查；JWT 必需身份和有效期字段、无效 JWKS 配置拒绝也有覆盖。

验证：`../.venv/bin/python -m pytest backend/tests -q` → **473 passed**，2 条既有依赖弃用警告。针对身份、工作流与旧填报路径的中间检查通过；最终完整回归包含新增 JWKS 异常测试。改动文件 `ruff check` 通过，`git diff --check` 通过。

测试区分无 token/伪造 token（401）、已认证越权（404）、未授予工作流权限（空集合）、跨部门依赖隐藏、合法拥有者仍可读取/导出、错误授权配置（503）、缺少 JWT 必需字段（401）及无效 JWKS（503）。门户关闭的已有工作流行为仍通过回归。未新增真实门户/浏览器实测，不声称个人工具审批已经完成；下一工作包仍需将真实批准人身份贯穿原生审批、操作权限及审计。
