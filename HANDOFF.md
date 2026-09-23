# 开发交接 / Development handoff

更新：2026-09-23（界面说清楚一轮见首节，其下为同日夜间一轮）；此前 2026-09-21。**当前阶段是「全 Web 化 → Lark 接入」，顺序不可颠倒，见下面同名小节。** 该小节之外的内容属于此前已暂停的 14x 需求交付阶段，仍然有效但不是当前工作面；不要因那些旧实施计划或自动续跑继续增加功能。任何「已完成」都不代表企业验收。

## 2026-09-23 界面说清楚一轮（文案、布局、逻辑揭示、动效）

负责人评价页面「AI 机器味重、不够清晰、逻辑揭示不够、动效不美观、局部太紧凑」，拍板四件一起做、直接改代码、以英文为主打磨。
设计取舍与写作规范见 [docs/15 一之三](docs/15-plugin-design.md)，数字见 [docs/00](docs/00-status.md) 同日一节。要点：

- **文案**：77 条提示改写成「这是什么、下一步做什么」；讲机制的句子挪进每页的「How this works」（`explain.tsx`）。
  JSX 里硬编码的全角冒号和括号改由 `useUI()` 的 `colon` / `paren` / `list` 按语言输出。
- **布局**：打开工作室的某个去处时自动进入阅读布局（工作室约 46% 视口）；顶栏分成三组，主次分明。
- **逻辑揭示**：
  - 每个关注项写成「数值与阈值 → 谁决定」，下一行给出计算公式和出处单元格数（后端把公式投影到关注项上）。
  - 依据等级就地写出含义，例如 G2 formula。
  - 开始页常驻四步流程，每步标明由谁来做。
  - 记录页的风险处置显示关注项标题，不再显示内部编号。
- **动效**：切换去处时的进入与分层落位、数字计数、派活时的扫光、流程连线依次画出，全部尊重「减少动态效果」设置。

**后续可做**：README 截图仍是旧界面；讨论区（立项材料）页面的文案本轮没有逐条改写。

## 2026-09-23 夜间：非飞书部分的完整性与可用性（待负责人合并）

起点已固定为标签 `checkpoint/2026-09-23-start`（= `main@35c7843`），整晚的改动都在分支上，回退只需回到这个标签。
**已合并（2026-09-23）**：#246 与 #248 都已合进 main，两次部署流水线（test + deploy）都绿。main 上现在的状态：

1. **#246（已合并）**：落地 `feature/usability-20260921` 的前 4 个提交（#244 状态之后的下一步、#205 字典起草与审核发布），
   加 lint 修正与 E05-UC07/UC08 状态校正（只做过离线验证，改为 `IMPLEMENTED_OFFLINE`）。
2. **#248（已合并）**：见下。
3. **#247（草稿，待负责人拍板，已改指 main、可合并）**：同一分支的第 5 个提交（#245 队长可读导入问题与受控单元格读取）。
   它把「原始数据行绝不进上下文」改成「不批量进上下文」，docs/36 自己写着要先拿到负责人对 #245 五个问题的答复，
   issue 上没有记录，所以没合。`feature/usability-20260921` 分支因此保留，里面唯一没进 main 的就是这一个提交。

`fix/product-journeys` 修的是改版（#219/#225）之后没人发现的断裂——CI 不跑浏览器旅程，改版后 5 条离线旅程有 4 条是红的：

- **页面内引导第 2 步卡死**（真实用户可见）：打开示例笔记本后，会话元数据异步加载完又导航回默认落点，把引导刚打开的「数据」页冲掉，
  于是刚导入成功就提示「这一步暂时不可用」。引导现在在路由退回默认落点时重新打开本步页面（用户自己选的页面不动）。
- **关闭工作室预览会弹出全屏「批次数据表」**（真实用户可见）：关闭时导航成「带批次、不带 view」，恰好是打开该对话框的路由。现在回到工作室首页。
- 状态页的「导入与数据 ↗」其实打开的是批次数据表（导入早已搬到来源栏），改用对话框本名；两条不再渲染的死文案删除。
- 旅程改走唯一入口「＋ 添加来源」等新界面；演示文档（demo-walkthrough、docs/17 台本、README.zh）里的旧入口一并改掉。
- docs/19 的「还没收尾的链路」表写于 #111–#113 之前，逐条对照测试后改写：三条 P0 已收尾，仍开放的只有「跨步骤累计 token 预算」与「状态页 URL 与原生页签激活不是同一操作」。

数字与复现命令见 [docs/00](docs/00-status.md) 同日一节。

**留给负责人判断的（今晚没动）**

- CI 不跑浏览器旅程，这正是它们烂掉没人发现的原因。加进 CI 要装 Chromium 与 dsh 运行时；CLAUDE.md 把擅自加 CI 列为越界，所以只提议。
- 后端提示是英文原句（例：「No monthly close steps are declared…」「… template lacks: …」），中文界面里夹英文。记录页按「原话」排行拒绝是有意设计，
  要改就得全面改成「原因代码 + 前端翻译」，属于跨模块改动。
- README 14 张截图是 09-14 的旧界面（README 自己也写了「三张仍是旧外壳」）；`readme-shots.mjs` 与 `screenshots.mjs` 还指着旧入口。
- 真实模型端到端录证（rubric 第 2/4/6 项的唯一提分动作）仍需授权，今晚没有任何计费调用。

## 线上席位没有默认工作区 / 发不起对话（2026-09-21，已修待验证）

现象：登录进席位后工作区是空的、菜单里也选不了，只能从 BridgeFlow 顶栏切笔记本才能对话。
根因不在前端也不在 dsh：Caddy `forward_auth` 把原请求的 `Connection`/`Upgrade` 头带进了门户
`/verify` 子请求，装了 `websockets` 的 uvicorn 把它当 WebSocket 握手、没有 ws 路由回 403，
于是 `wss://<seat>.console.<domain>/api/remote.mux` 被认证层拒掉——dsh 所有 Remote **流**都在
这条 socket 上，工作区投影没有 unary 回退，`watchNavigation` 因此静默不建会话。
机理与判别式见 [docs/22](docs/22-lightsail-deploy.md) §7/§9b、[docs/35](docs/35-seat-isolation.md) §3，
实测对照见 [docs/00](docs/00-status.md) 首节。

改动：`deploy/{Caddyfile.template,render_caddy.py}` 每个站点块加 `header_up -Connection` /
`-Upgrade`；`deploy/portal.service` 加 `--ws none`；`deploy/preflight.sh` 新增逐席位的升级握手
检查（401 = 好，403 = 坏）；`deploy/deploy.sh` 每次部署按 diff 重渲 Caddyfile 并 reload
（此前只有 bootstrap/provision 会渲染，改了没人装）。开发机已端到端复现并验证修复。

**实例侧待人工**：部署后跑 `bash deploy/preflight.sh <domain>`，确认新检查为 401；
顺带确认同一条 socket 上的**会话流**也恢复了——原生侧边栏会话树是否列出会话、模型回复是否
流式出现（修复前这两项应同样是坏的，线上未逐项确认过）。

## 席位化隔离落地（2026-09-20，docs/35）

#230 从「推后的评估」升级为**已实施的 7 席位方案（先到先得）**：固定容量通用席位
（seat-1…7，各自 `DSH_HOME`、回环端口、子域名），获授权者先到先得认领、认领即绑定；
方案、拍板与运行手册全在 [docs/35](docs/35-seat-isolation.md)。
本机已验证：`start_web.py --backend-only/--web-only` 三模式、共享 token 探活、
全新 home 首启自建（闲时 RSS 224–289MB，过门线 300MB，**7 席位 ≈2.0GB 贴 slice 预算线**，
Linux 实测 >280MB 就减席位或升配）、门户 `/enter` 按人路由与 `/verify` 子域名绑定（39/39
测试绿）、Caddy 双形态渲染、默认单进程流回归。改动清单：`scripts/start_web.py`、
`deploy/{bridgeflow.service,bridgeflow-dsh@.service,bridgeflow-dsh.slice,bootstrap.sh,preflight.sh,render_caddy.py}`、
`portal/src/portal_app/{seats.py,main.py,config.py}`、`scripts/provision_seat.sh`、
`env.sh.example`；文档同步 00/22/27/34/35。

**实例侧待人工（部署时做，清单顺序即依赖顺序）**：① env.sh 写入共享 `BRIDGEFLOW_SERVICE_TOKEN`
（32+ 字符）；② 重跑 `bootstrap.sh`（装 slice/单元模板/swap/重渲 Caddy）；③
`BRIDGEFLOW_DOMAIN=<domain> scripts/provision_seat.sh --init 7` 建席位舰队（**先到先得**：
配置里没有人名，获 `console_access` 授权者第一个进入即认领）+ 每席位一条 DNS A 记录
（seat-1..seat-7.console.<域名>）；④ `preflight.sh` 全绿；⑤ 双人实测：各认领各的席位、
进错/未认领子域名收 403、会话互不可见、重启席位历史在、第 8 人收「席位已满」。
原「全 Web 化四件人做的事」（真人入库、开门禁、Caddy 透传、真实模型归属）仍要做——
席位化不替代门禁，两者叠加；门禁（`console_access`）是认领的前置。腾位用
`provision_seat.sh --release <union_id>`（home 归档、即时生效）。

**部署流水线已适配（合并前已改并本地全绿）**：`deploy.sh` 两处——每次部署顺带重启全部
`bridgeflow-dsh@*` 单元（席位加载的插件与 bundle 才会更新）；web 活性检查按部署形态分流
（`--backend-only` 时查席位单元，一个都没开通则跳过并告警，3080 只在旧形态检查）。
认领文件 `data/seats-assigned.json` 是 untracked 实例状态，`git reset --hard` 天然不碰。
CI test job 补装并跑 `portal/tests`（席位认领与绑定校验从此有门禁）。
**注意合并即切换**：主单元变 backend-only 后、席位开通前，公网控制台不可用且 CI 公开活性
检查会红（apex 仍指向已死的 3080）——这是预期的过渡窗口，开通完席位即恢复；不接受窗口就
拆两个 PR（先落机制保留旧单元，开通后再切换单元文件）。

## 评审 rubric 自评（2026-09-20）

按主办方七项打分，逐条写明**证据在哪**。自评不是宣传：能指到文件与实测数字的才给分，指不到的直接说没有。

| # | 项 | 分（/5） | 证据 | 明确的短板 |
| --- | --- | ---: | --- | --- |
| 1 | 目标与范围 | 4.5 | docs/01 的问题陈述；14 epic / 87 UC 与 traceability；`IMPLEMENTED_OFFLINE` 与 `IMPLEMENTED` 分列，明说不等于企业验收；Docker/CI/自建前端等越界项已撤 | 真实客户验收为 0；#23/#141 业务材料未到；20 万行是设计约束，未做规模实测 |
| 2 | 架构与推理循环 | 4.0 | dsh 作基座而非 provider（代价对比：12–212 s / 7,100 token vs 3.6 s / 707 token，docs/00）；队长 + 四角色 fan-out，角色间无协商通道；批次冻结、派生版本链、期间索引、追加日志、乐观并发、CQRS 投影 | 真实多步会话证据只有一次（4 步）；评委看的是跑起来的循环 |
| 3 | 工具与集成 | 4.5 | 35 个工具全部 `defineTool` 带 schema，读/审批两种 access kind；`test_tool_output_contracts` 逐字段比对插件 schema 与后端返回；工具目录被测试钉死；返回值封顶 + 真实计数 | 单队长 35 个工具偏多；工具选择本身无评测；`quarantine_list` 与 `monthly_inbox` 语义重叠 |
| 4 | 自主性与人在回路 | 4.5 | 每个写操作要原生审批回执（与请求体绑定、一次性）；员工许可 60 s / 单次 / 执行前重查；拒绝分类（no_base / declaration_changed / unknown）；系统不写「已结账」；口径替换不改写声明 | 自主性没有风险分级，只有 read / approval 两档；演示时容易显得保守 |
| 5 | 安全与护栏 | 4.5 | 三层挡原始行（profile 关 bash/editor、提示词、返回值）；注入用例中英双语且 TS 与 Python 共用同一份 JSON，在真实 dispatch 上验证；`access-control.yaml` 最小权限（`convention_decide` / `risk_disposition` 只给总表管理者）；不可见批次返回 404；凭据只从 shell 读 | 共享 DSH 会话 ≠ 企业身份（已在文档写明）；无第三方渗透测试 |
| 6 | 可观测与评测 | **3.0 → 4.6+**（两轮） | 见下 | 链路已覆盖 agent 循环；仍缺**真实计费模型**跑出来的那条运行（需授权） |
| 7 | 平台与框架 | 4.5 | 不 fork dsh，用 patch + 本地 bundle；官方 `packages/subagent` fan-out；UI 走 dsh web 插槽而非自建前端；版本锁死并写明理由 | — |

合计约 **31 / 35**（本轮之前 29.5）。

### 第 6 项这一轮做了什么

**决策日志（`backend/src/bridgeflow/journal.py` + `api/main.py` 中间件）**：写在一条缝上，不是四十处 logging。
理由与界限见 [13 第六节](docs/13-golden-standard.md#六-rubric-符合性)。要点：

- 每次请求一条：决定、耗时、结果（读取 / 写入 / 拒绝）、链路编号（同时回写响应头 `x-bridgeflow-trace`）；
- 拒绝按**它自己的原话**留存，因为每个拒绝本来就是带 `detail` 的 `HTTPException`；
- 只有编号、计数、版本与那句话，**没有数据行**（有测试逐个值比对，确认总表里的文本没出现在日志里）；
- 路径里的批次号与期间自动成为条目的主语，按批次筛选不需要任何 handler 配合；
- 有界：按天 JSONL、单条封顶、保留 14 天，实测单条约 271 字节。

**展现形式**：工作室「记录」页把它读回来——决策数 / 其中拒绝 / 其中写入 / 耗时中位与最慢，
「今天拒绝了什么」按原话排行，明细可按结果与批次筛选，每条带链路编号。
实测样本（11 次请求）：1 写入、6 读取、4 拒绝；中位 45.9 ms、最慢 2141.3 ms（示例批次导入）；
拒绝原话排行为「Complete the review before building the brief」×3、「A fresh DSH approval for this exact write is required」×1。

**评测**：`python -m bridgeflow.eval --json` 生成报告，界面只渲染生成物。
本轮把验收集扩成两半：正常路径 24 条（三行业留出月）+ 对抗与拒绝 7 条（植入指令、无基期、无声明来源、
未声明步骤、他月文件、单期趋势）。当前 **31/31 通过**，报告带生成时间与年龄，红行写明认领的 issue。
生成物副本：`docs/evidence/observability/acceptance-2026-09-20.{txt,json}`。

界面形态与设计稿（含可观测那块）一致，画板在 <https://claude.ai/artifact/MMeAdd9m4M6Eo4PdvfUZCx>，
说明见 [15 一之二](docs/15-plugin-design.md)。

### 第 6 项第二轮：链路接到模型侧

`exec.rootCallId` 就是「一次模型请求所拥有的整棵调用树」，也就是人说的「一次运行」。工具层把它连同
`call_id` / `agent` / `tool` 声明在 header 上（调用点每处只多一个词：`exec.signal` → `exec`，共 34 处），
后端那条缝仍然不解析任何 body；`batch_id` 与 `period` 是唯一被接受的主语键，别的 body 字段进不来（TS 测试锁死）。

- **一次运行一张图**：泳道 = 代理（队长 + 四部门子代理），标记 = 工具调用，宽度 = 该步在这次运行里的耗时占比，
  拒绝用虚线边框加 ✕ 标出（不靠颜色表意）；展开是逐步清单，每步带耗时、结果、拒绝原话与链路编号。
- 浏览器自己的读取没有根，因此不算运行——这张图回答「代理做了什么」。
- 实测：脚本化四角色研判一次运行 **7** 步、**5** 条泳道；截图 `docs/evidence/round1-e13-e14/agent-run.png`。

### 还剩什么能提分（按性价比）

1. **一次真实端到端并录证**（导入 → 队长四角色 fan-out → 结论 → 审批写入 → 导出），记步数、token、耗时与截图。
   这一件同时抬第 2、4、6 项，是唯一能改变名次的动作。**计费，需要你明确授权后才跑。**
2. **把 token 用量并进运行视图**：`usage` 现在只在研判报告里；按 `parent_session_id` 与运行对上之后，
   同一张图就能同时给出步数、耗时与 token。
3. **演示锚点**：七项各准备一个 30 秒画面（第 5 项就演「把提示注入写进单元格，工具在碰 Python 之前就拒」，
   第 6 项演「记录页的拒绝排行 + 生成的验收表」），别让评委自己在文档里找。


## 全 Web 化 → Lark 接入（当前阶段，2026-09-20）

形态决策见 issue #227，落地计划与逐步退出条件见 [docs/34](docs/34-web-refactor-plan.md)，
所有实测数字见 [docs/00](docs/00-status.md)。本小节只管「做到哪了、接下来怎么做」，不复述那三处。

### 为什么先 Web 化再 Lark

Lark（#234）要动的是门户的多提供方抽象、`/verify` 与 `apps.yaml`——正是 Web 化第 1 步刚改过的同一片代码。
先做 Lark 等于在一个还会变形的接缝上加第二个提供方，两次都要改同一处且冲突叠加。反过来，
Web 化收口之后，Lark 只是「再注册一个 provider」，判定与门禁不必再动。

顺序还有一条现实理由：Web 化剩下的是判断与验证（#230 只产结论，几项未验需要真人与真实租户），
而 Lark 是纯实现。把需要等外部条件的事排在前面，等待期正好用来写 Lark。

### 已完成（都在分支 `feature/web-based-refactor-20260920`，4 个提交，已推远端、**无 PR、CI 一次没跑过**）

流水线只在 push main 与针对 main 的 PR 上触发，所以推分支不触发任何检查：这 4 个提交至今只在开发机上验过。
上线路径是「开 PR（跑 test job）→ 合 main（触发 deploy job）→ 上实例改 `env.sh` 开门禁」，最后那步流水线做不了，
见下面「需要人去操作的」。

| | 内容 | 关键边界 |
| --- | --- | --- |
| 第 0 步 | 六项业务拍板 | 目标为评审（Web 化动机是「更新只需一处、用户不必手动升级」）；飞书不可达扣下整站；控制台 10 人以内；真实批次多在 10 MB 以内；本期不做本地部署；成本护栏与重启空窗留 TODO |
| 第 1 步 #229 | 控制台操作员角色门（`f7893c8`） | **默认关闭**，尚未在任何部署开启。开启后「无 `console_access` 授权」403、「授权无法确认」503，措辞分开——重登修不好缺授权，所以那一页不提供「重新登录」 |
| 第 3 步 #231 | 模型发起读取归属到人（`8ec17ce`） | `BRIDGEFLOW_SERVICE_TOKEN` 退回传输凭证；浏览器 `POST /bridgeflow/actor` 交出门户令牌，宿主经 `/identity/me` 验签后在模型触发的读取上原样转发，后端逐请求验签。有歧义就等于没有：两人同时绑定时不挂任何身份 |

两条必须一起记住的限制：**归属不是授权**——缺归属时读取照样执行，模型读取的授权仍是主机级；
第 1 步也不是按人隔离——控制台仍共用一个 dsh 身份，进去的人彼此可见。

### 后续工作流程（每一步都照这条流水走）

1. 读 [docs/34](docs/34-web-refactor-plan.md) 对应步骤的「退出条件」，不要从 issue 标题反推范围。
2. 写代码与测试。离线测试是本项目的默认验收形态，真实模型与真实租户另算。
3. 跑四条：`(cd backend && ../../.venv/bin/python -m pytest -q)`、`ruff check src tests`、
   `(cd portal && … pytest -q)`、`(cd plugins && corepack pnpm typecheck && corepack pnpm test && corepack pnpm build)`。
   插件套件里 `dsh-preflight.test.ts` 在 macOS 上因 `/private/var` 符号链接必然失败一条，与业务代码无关。
4. 数字只写进 [docs/00](docs/00-status.md)，并写明「未验」与「未做」；设计边界写进对应专题文档（门户身份进 docs/27）；
   进度写回本小节。三处不重复，冲突以 docs/34 为准。
5. 一步一提交，commit 标题带 issue 号。

### 已拍板推后（2026-09-20，不阻塞演示）

1. **模型读取缺归属时维持照读**，审计如实记 `host`；两人同时绑定时归属为空也维持现状。改成拒绝会让超过
   15 分钟与无人值守的运行在令牌过期后停住，而演示要走的正是这条路径。这是一条被知道的缺口：对外只能说
   「读取能归属到人」，不能说「无归属的读取进不来」。
2. **#230（按人隔离的评估）推后**，连判断也不在演示前产出——六问都需要真实并发数字才有意义。
   能力边界本身没等它：「dsh 没有内建的多用户归属」已记进 [docs/13 第四节](docs/13-golden-standard.md)。

两条都不产生代码动作，所以 **Web 化的代码面到此收口**（第 1、3 步落地并关闭，#232／#228／#233／#230 等演示后）。
剩下的只有下面「需要人去操作的」四件，做完就进 Lark（#234）。

### PR #235（门户改版）暂不合并 —— 2026-09-20 拍板

`feature/ui-refactor-20260919` 与 main 冲突较多，且不涉及核心功能重构，**MVP 演示完成后再考虑合并**。
在那之前它不影响本阶段：本分支基于 `origin/main`，第 1 步的 `console_blocked()` 用的正是 main 上现有的
`error-title`／`error-detail`／`again` 三个类，样式成立，无需改动。

合并那天有两件必须一起做的事，先记在这里免得丢：

1. **样式**：#235 把 `pages.py` 整篇换成 CDS 记号与 `.callout`，上面三个类一个不剩。`console_blocked()` 要改成
   `.callout` 形态，否则 403／503 两页掉样式（内容仍对）。
2. **冲突与增强**：`pages.py` 与 `portal/.../main.py` 必然冲突（两边都改了 `error()`、`/verify`、`create_app` 签名）。
   合并后顺手用 #235 带来的 `x-bridgeflow-reason` 把第 1 步的 503 细分成「不可达／未配置」——现在只能给一个 503。
   本分支 3 个提交是线性的、不含合并提交，普通 rebase 安全。

### 需要人去操作的（做不了代码替代）

- 真人加入飞书知识库 → 登录与角色判定端到端（各库现仍只有应用本体，见下文 #204 条目）
- 开启控制台门禁：`env.sh` 加 `PORTAL_CONSOLE_CHECK_URL`。**先在 ACL 给角色加 `console_access`，再开门禁**，顺序反了会把所有人锁在门外（docs/22 §9d）。开完跑一次 `bash deploy/preflight.sh <domain>`：它现在会在「门禁已开、无人有授权」时报 FAIL，这是唯一被脚本挡住的那个失误，其余三件仍得人自己点
- Caddy 对 403/503 的 `forward_auth` 透传实测（目前只有读码确认）
- 真实模型运行下的归属验证（本阶段未调用模型）

### 一处与下文记录不符

本分支基于 `origin/main`，不含 `feature/ui-refactor-20260919` 的门户改版（`failure.tsx`、`describeFailure`、
`x-bridgeflow-reason` 都不在这条线上，未丢失，现已进 PR #235）。下文 2026-09-19 的三条记录描述的是那条分支，
不是本分支的状态。

## 接手先看

- 交付分支：`feat/14x-requirements-delivery`；基于 `main@4a38904`（合并 #186）。本轮代码、测试与需求文件纳入同一 PR；实际提交及合并状态以 Git/GitHub 为准。接手先看 `git status`，不要 reset 或 clean 尚未保存的工作。
- 全项目需求与逐 UC 状态：[requirements/README](docs/requirements/README.md)；一份双语 Markdown 对应一个 Epic，既有能力与历史延期范围也已纳入。14x 只是其中三个 Epic。实现顺序：[implementation-plan](docs/requirements/implementation-plan.md)；issue/PRD 对照：[traceability](docs/requirements/traceability.md)。
- 2026-09-17 需求复核（仅文档，未写代码）：按项目完整性、流程便民性、结论直观性与专业性三个视角补充 [00-foundations](docs/requirements/00-foundations.md)（角色目录、逐 UC 参与者与触发、非功能需求、结论呈现规范、优先级与 Given/When/Then 验收写法），新增 [E13 月度结论呈现与口径治理](docs/requirements/13-conclusions.md) 与 [E14 月度流程便民](docs/requirements/14-monthly-convenience.md) 共 12 个 UC，以及 [类设计](docs/requirements/class-design.md)；目录现为 14 个 Epic、85 个 UC。看板 Epic #189（E13）、#196（E14），每个 UC 一个子 issue。第一轮实现 E13-UC01 一页结论主流程（#190）、E13-UC06 依据等级（#195）、E14-UC03 提交前自检（#199）；第二轮实现 E13-UC02 跨期对比与差异分解（#191，离线完成）；第三轮实现 E13-UC05 口径确认与替换（#194，离线完成）：逐条口径可带来源确认（依赖它的数字由 G3 升为 G2，数值不变）或申请替换（只记录决定并给出该改的声明行，系统不改写公式），写入走原生审批与版本冲突检查，`convention_decide` 只授予总表管理者。设计判定与依据记在 docs/requirements/13 的「本轮设计判定」（D8–D11）。第四轮实现 E14-UC04 单部门补传生成新版本（#200，离线完成）：只有出错的部门重传，其余部门沿用原批次的原件与清洗结果（摘要不变），派生新批次并给出总表差异；月份以文件自身的行判定，逐字节相同的文件不派生；冻结批次不被改写，版本链从索引正向查出。设计判定 D12–D15 记在 docs/requirements/14。第五轮实现 E14-UC01 月度对账进度清单（#197，离线完成）：步骤由字典声明，每步的状态直接读自负责它的模块，读不到就是「状态未知」而不是完成；「可结账」只是读数，系统不写「已结账」。设计判定 D16–D17 记在 docs/requirements/14。第六轮实现 E14-UC05 待确认事项收件箱（#201，离线完成）：跨模块聚合待办，每项只带「去哪处理」，不保存处理状态也不提供决定按钮；原模块处理完事项自动消失。设计判定 D18 记在 docs/requirements/14。第七轮实现 E13-UC03 指标可视化与下钻（#192，离线完成）：图表由字典声明，阈值线与结论判断取同一个数；缺失期间断线不插值；每张图配等价表格，状态不只靠颜色。设计判定 D19–D20 记在 docs/requirements/13。第八轮实现 E13-UC04 月度报告文档导出（#193，离线完成）：Word 文档由结论页生成，八章齐备，正文每个数字在附录有出处编号；结论页过期拒绝导出；只出 Word 不出 PDF，未新增依赖。设计判定 D21–D23 记在 docs/requirements/13。第九轮实现 E14-UC02 模板下载与上月预填（#198，离线完成）：沿用关系写在声明里，模板表头逐列复制批准模板（交回来的文件能被同一份声明导入），预填单元格带「预填自某月，请核对」批注，无上期批次就不填并写明原因。设计判定 D24–D25 记在 docs/requirements/14。证据见 docs/00；第十轮实现 E07-UC07 风险处置审批生命周期（#19，离线完成）：状态机由字典声明，字典没声明就拒绝；只能走声明允许的流转，要求理由的动作没有理由就拒；每次流转记审批人与时间，日志追加不覆盖；处置不改动报告与任何数字。第十一轮补齐 E13-UC01 与 E13-UC06 的剩余项（#190、#195，离线完成）：关注项列出出处引用（封顶 5 条 + 真实总数）、结论页作为派生产物进产物列表、图表数据点带依据等级、「出处缺失」进待办收件箱。#205「AI 辅助起草字典」已按仓库惯例补进需求目录（E05-UC07 聚合画像与起草、E05-UC08 逐条审核与发布，均为 DESIGNED，目录现为 87 个 UC）；issue 自身写明本期不实现，且起草是计费动作，需要你显式授权后再跑。能由开发侧定的 6 个设计问题已逐条判定（D28–D33，写在 docs/requirements/05-mapping.md），仍需业务方回答的 3 个问题也列在同一节。至此非飞书核心 UC 已全部清空。2026-09-20 做了一轮工作室 UI 重构（先出设计稿再落代码）：四个去处（本月任务 / 数据 / 结论 / 记录）取代并列的八个入口，进度清单与待确认收件箱合成一页并互相定位，导入面板拆成「数据」时间线（取模板与单部门补传落到部门自己那一行），结论页分三层，右栏只陈述事实；字体按中英双语定（拉丁 Source Serif 4 / Source Sans 3 在前，中文回落思源宋体 / 思源黑体）。详见 docs/00 与 docs/15-plugin-design.md。
- 测试数量、命令、截图及验收边界仅记录于 [docs/00](docs/00-status.md)。不要从“代码存在”“issue 已关闭”或离线通过推定企业验收。
- 2026-09-17 飞书在线表格/多维表格读取（分支 `feature/feishu-user-docs-20260916`）：规格 [docs/32](docs/32-feishu-sheets-bitable-read.md)，计划与实现 [docs/33](docs/33-feishu-sheets-bitable-impl.md)。代码与离线测试完成；第 4 步真实联调进行中：人工前置（scope 发版 + 全员重登）已生效，联调暴露的代理路由白名单与两处端上缺陷已修复。剩余：导入端到端与大表分页压测。测试数字与联调证据见 [docs/00](docs/00-status.md#飞书在线表格--多维表格读取联调docs32--docs332026-09-17)。
- 必读硬约束：[CLAUDE.md](CLAUDE.md)、[架构权威 docs/13](docs/13-golden-standard.md)、[产品扩展契约 docs/23](docs/23-extension-contracts.md)。
- 2026-09-19 部署配置通道修复（分支 `fix/deploy-config-sync`）：线上飞书导入报 503「Access control is not configured」而本地正常，根因链与证据记于 [docs/00 第一节](docs/00-status.md)。三处改动：`data/mappings/access-control.yaml` 改为**仓库跟踪**（改权限策略 = 提 PR，不再 SSH 上机器；`.example` 与它逐字节相同，已删）；deploy.yml 的配置同步移到 `deploy.sh` **之后**并只保留字段字典；同步脚本首行 `set -eo pipefail`（`ssh-action@v1` 删掉了 `script_stop`，失败会被吞成绿灯）。**待办**：合并后删除 production 环境里已作废的 secret `ACCESS_CONTROL_YAML`，并在线上实际点一次飞书导入验证——CI 的存活检查查不到数据路由的 503。
- 2026-09-18 #204 授权数据源迁移（分支 `feature/feishu-user-docs-20260916`，本条目所记代码未提交）：`access-control.yaml` 从逐人花名册改为「结构映射 + 角色策略」，成员关系运行时解析自飞书知识库成员（wiki-only 路径，不申请 contact 高敏权限；总经办也建知识库，其 admin = 总表管理者）。已拍板：fail-closed（映射缺失/飞书不可达均 503）、成员表 5 分钟缓存、飞书侧调岗无需改 BridgeFlow 文件。实现：`access_resolver.py` 新模块（同步 httpx、tenant token、`wiki/v2/spaces/{id}/members` 分页、429 有界重试），`access.py` 瘦身为门面（三函数签名不动，下游零改动），`identity.py` 记录 JWT 里的 open_id 桥（wiki 接口返回 open_id ≠ union_id）。后端 620 测试全绿（新增 test_access_resolver.py 25 项），ruff 过。人工前置（scope 发版 + 应用加为五库成员）已确认生效：2026-09-18 真实租户侦察五库全部可读，envelope 为 `data.members`、`ou_` 前缀；联调发现成员接口 page_size 上限 50（传 100 报 131002），已修复并记 docs/00。**剩余**：真人尚未加入任何知识库（各库现仅 1 名 admin，疑为应用本体），真人入库后做登录端到端与角色判定验证；群组/部门型成员不会被展开（人须直接加库）。本地配置：`data/mappings/access-control.yaml` + env.sh 导出 `FEISHU_APP_ID/_SECRET`（与门户同一应用）。另：`.gitignore` 当时补上了 `access-control.yaml`（docs/22 此前声称已忽略，实际没有）——**该决定已于 2026-09-19 反转**，见下一条。

## 当前交付范围

| 范围 | 本地已接通 | 主要剩余边界 |
| --- | --- | --- |
| 历史产品能力 | 导入清洗/隔离、列匹配与记忆、总表核对/XLSX、四角色研判、报价草稿、笔记本与引导 | 逐项看 E04–E12；本轮没有重新验收全部历史真实模型路径 |
| 读取与批准身份 | 总表/下载和工作流浏览器范围检查；JWT/JWKS 加固；验签员工、操作 ACL、精确请求一次性许可及执行前撤权检查 | 原生会话与模型读取的员工隔离、拒绝/取消的个人审计、完整多租户边界 |
| E01 材料与候选 | 暂存上传、配额、原生批准登记、版本原件/下载、来源位置校验、候选逐项编辑/修订、有界材料结构工具 | 自动语义抽取、音频/PDF/OCR、来源选择器、原件保留/清理策略及真实材料验收 |
| E01 流程草图 | 节点/关系编辑、四种依据状态、条件/返工、SVG 与依据详情、版本/来源保护及原生批准保存 | 图内原件跳转、自动生成、协同编辑及未批准草稿恢复 |
| E01 评分 | 人工量表配置、Decimal 坐标、评分表单、原生保存、四象限及依据查看；缺项/来源/政策变化不落点 | 真实量表签核、多项目政策管理、未批准编辑恢复 |
| E01 会议 | 候选快照、范围/风险/资源假设、阶段依赖与退出条件、会议准备/纪要版本；授权 API、原生审批、编辑/详情页面 | 自动会议摘要、多人共编、真实业务确认 |
| E01 MVP 决策 | 声明规则、本人投票、指定条件确认、明确批准/拒绝；领域/API/原生工具及决策页面；条件式决定、修订清票、过期撤下有效范围 | **Agent 2 模板治理消费端未接**；真实规则及企业验收、未批准编辑恢复 |
| E02/E03 首批运行能力 | 原生下游开始/退回/完成、修订确认与过期保护；按声明生成岗位指引 | 模板治理/试点、岗位页面、反馈处置与复盘、真实支持入口及通知渠道 |

浏览器目前可从“立项材料与候选”依次完成材料 → 候选 → 图 → 评分 → 会议 → 决策。编辑器生成请求后，用户复制到原生对话审批；复制不发送、不保存。未批准内容仅在当前页面，离开页面会丢失。

### 本阶段最后一次验证

决策浏览器连续旅程已通过：两个本地签名身份顺序投票 → 票数达标仍待决定 → 明确条件式决定 → 指定人确认来源 → 再次批准 → 显示当前批准范围 → 政策修订撤下范围。详细命令和产物见 [docs/00 的收尾记录](docs/00-status.md#阶段暂停前的决策浏览器验证2026-09-16)。

这是同一浏览器中顺序切换测试身份的离线验证，**不证明原生会话隔离、多人并发协作或真实飞书 SSO 验收**。模型为脚本化离线适配器，政策/数据为合成输入。没有据此调用付费模型、发送真实通知、部署或关闭远端 issue。

## 下一阶段从哪里接

按依赖顺序继续，详细 UC/退出条件见实施计划；不要只把状态标签变绿。

1. **Agent 2 消费有效 MVP 范围**（E01-UC06 → E02-UC01/02）。决策 `read()` 已投影 `agent2_handoff`，仅当前有效 approved 才有内容。实现接收与模板治理时，在同一事务检查决定序号、政策指纹、会议、候选和来源版本；禁止把读到过的批准 JSON 当成永久授权。定义接收身份/角色和接收回执，覆盖决定修订或来源变化与消费并发的拒绝路径。当前不创建执行目录、业务交接或通知。
2. **模板治理和试点**：模板/字典版本、批准发布、试点反馈、指标与修订；字段血缘图及版本一致性。catalogue YAML 不是已完成的治理界面。
3. **反馈、岗位支持与复盘**：反馈记录、分类/指派/关闭、措施效果、回流 Agent 1/2；真实责任人由业务声明。
4. **风险和报价闭环**：风险处置状态机、方案比较、可信抽取及精确版本签发；内部草稿不得被当作对外报价。
5. **通用数据缺口**：声明式单位/币种换算、补齐、实体有效期、分摊；季年汇总/PDF 不能从 XLSX 功能推定完成。
6. **真实接入及运维**：目标 API、通知路由、飞书文件往返、部署/保留调度及独立评测。凭据和真实业务输入缺失时保留待验收，不伪造成功。
7. **横向欠项**：员工会话/模型读取隔离、个人拒绝审计；未批准草稿恢复；来源跳转；整个新流程的导览和连续验收。E12 知识库曾明确排除，重启前需确认范围和资料授权。

## 核心实现位置与契约

- 领域：`backend/src/bridgeflow/workflow/discovery*.py`；持久化：`WorkflowStore` 追加事件和 `expected_seq` 并发保护；原件内容寻址存于 `RESULT_STORE_PATH/discovery-blobs`。
- 浏览器 API/原生写入口：`backend/src/bridgeflow/api/discovery.py`；个人授权：`write_authorization.py`、`api/write_identity.py`；原生回执仍不可省略。授权消费账本不等于业务写入成功。
- 原生工具：`plugins/src/tools/discovery*.ts`；页面：`plugins/src/client/discovery*.tsx`、`opportunity-editor.tsx`、`flow-graph.tsx`。审批完整显示有界内容，超限拒绝，不截断依据。
- 行为测试：`backend/tests/test_discovery*.py`、`test_employee_approval.py`；插件契约 `plugins/tests/runtime.test.ts`；连续浏览器脚本 `plugins/tests/web-smoke.mjs` 与离线 fixture。
- 决策动作：`discovery_decision_propose/vote/resolve/finalize`。ACL 操作许可与政策角色必须同时满足。角色取验签身份；提案修订清空票和条件确认；票数通过不自动批准；确认条件不自动释放。
- 模型不能读取原始表行/文本正文。来源位置存在只证明 locator 合法，不证明语义支持该陈述。图仍是草图；评分不是立项；会议参会名单不是身份验证或投票。

## 启动与配置

已有本地环境下，在仓库根执行：

```bash
source ../.venv/bin/activate
source ./env.sh
pnpm --dir plugins build
python scripts/start_web.py --demo
```

打开启动器打印的带凭证地址。安装与无演示模式见 [README.zh](README.zh.md)。使用锁定的官方 npm `@deepseek-ai/dsh@0.1.2-rc.1`；不要把 `BRIDGEFLOW_DSH` 指向 Python SDK 打包二进制。`Ctrl-C` 停止本次启动的服务。

- `DSH_*` 和 `DEEPSEEK_BASE_URL` 只由 shell 导出，不能进 `.env`。仓库根启动不读取 `backend/.env`。
- `FIELD_DICTIONARY_PATH` 指定人工字典；缺失拒绝猜测。`--demo` 使用合成样例声明，不会为新评分/决策自动配置真实政策。
- `DISCOVERY_SCORING_POLICY_PATH`、`DISCOVERY_DECISION_POLICY_PATH` 为人工 YAML/JSON，默认空；当前各支持一个项目文件。缺文件/非法政策返回 503，历史评分/决策详情也要求当前政策可读。不要把测试政策放入生产。
- 门户开启后，ACL 的角色需显式 `workflow_departments`（准确部门名）及 `operations`；省略不扩权。成员名单不登记在文件里，由飞书知识库成员实时解析（#204）。文件本身跟踪在仓库里：[access-control.yaml](data/mappings/access-control.yaml)（原 `.example` 与它逐字节相同，已删除以免漂移）。真实门户接入见 [docs/27-login](docs/27-login-portal.md)。
- 暂存支持 `DISCOVERY_UPLOAD_OWNER_COUNT/BYTES/TOTAL_BYTES` 配额。`scripts/cleanup_discovery_uploads.py` 默认预览，`--apply` 才删除过期暂存；使用服务相同 `RESULT_STORE_PATH`。未安装生产调度，不保证 SQLite 缩容/安全擦除；失败写入留下的无引用正式 blob 清理策略未定。

## 复测入口

```bash
# 从 backend 项目目录跑，避免误收集独立 portal 项目
(cd backend && ../../.venv/bin/pytest -q)
pnpm --dir plugins typecheck
pnpm --dir plugins test
pnpm --dir plugins build
BRIDGEFLOW_TEST_DISCOVERY=1 BRIDGEFLOW_TEST_EMPLOYEE=1 BRIDGEFLOW_LIVE=0 pnpm --dir plugins smoke:web
```

浏览器需要已安装 Chromium；smoke 默认使用 `../.venv/bin/python`，可用 `BRIDGEFLOW_PYTHON` 指定。脚本使用临时 DSH_HOME 和数据，结束自行清理启动的进程；截图和日志在 `/tmp/bridgeflow-web-e2e-*`，不是仓库长期资产。保存/迁移运行资料需同时考虑 `RESULT_STORE_PATH` 和真实 `DSH_HOME`；笔记本元数据不能替代源文件。

本阶段最后新增的决策政策响应提供服务端验签 `viewer.subject/actions`，供 UI 呈现权限；后端仍独立强制检查。测试证据的时间范围见 docs/00，不将前一次全量结果冒充最后每处改动的重新全量。

## 必须保留的历史边界

- 新业务总表走冻结 `integration_snapshot`，既有四角色研判走冻结字段字典及 `business_review` 声明；不得把两条独立成功路径剪成未验收的同一闭环。旧批次没有总表快照时保留原档并重新导入，不用当前政策补算历史。
- 原始表头行号、非有限值/不完整汇总拒绝、公式文本导出防护已有修复，不应回退。业务假设待确认；合成数据/手算答案不能证明真实泛化、多 Agent 优势或人工工时节省。
- 报价仍为声明驱动内部草稿；模拟原件与人工抽取记录在 `data/mock_business/quotation/`，设计见 [docs/21](docs/21-quotation-design.md)。
- 历史引导与笔记本已经存在，入口为帮助与引导、打开示例笔记本；演示说明 [demo-walkthrough/notebook](demo-walkthrough/notebook.md)。新的 E01 路径尚未补完整导览。
- 飞书 OAuth/JWKS、文件接入代码和部署脚本不等于真实企业接入通过。真实月度导出、人工总表、业务口径、调优/独立留出、评分/投票政策、试点角色、目标接口及密钥见 [外部输入清单](docs/27-external-inputs.md)。密钥只放运行环境/密钥管理，不写入文档或 issue。
- `docs/28-rehearsal-authorization.md` 是授权草案，不构成付费调用许可；真实模型验收需明确范围与预算。历史 #167 等验收不能自动外推到新页面。最终 PPT/视频/report 的外部状态仍需团队核对。

## 运行时故障与提交约定

Web 和 SDK 使用同一官方 npm 运行时选择器；Python 打包运行时污染共享 fallback 后，重启启动器由官方加载器自愈。直接测试打包 SDK 时使用独立 DSH_HOME，单换 profile 不隔离共享 fallback。

笔记本和审批元数据走官方 storage-domain，不向原生会话日志写未知事件。旧日志打不开时，先停相关服务，再运行 `scripts/repair_session_metadata.py --root <真实会话目录>` 预览；确认需要再 `--apply`（保留备份），不要改事件白名单或与运行进程争写。

后续开发继续使用分支和 PR；接手先 `git status` 审阅修改及未跟踪文件，不直接提交 main。每个 UC 完成后同时更新 Epic 索引、正文状态与实际证据。当前暂停不等于全项目完成，不应批量改为 IMPLEMENTED。
