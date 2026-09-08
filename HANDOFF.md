# 交接说明

更新于 2026-09-07。这份文档只放会过期的东西：现在跑到哪了、怎么跑起来、下一步做什么、已知哪些坑。
硬约束在 [`CLAUDE.md`](CLAUDE.md)，架构理由是 [`docs/13`](docs/13-golden-standard.md)，
所有实测数字在 [`docs/00`](docs/00-status.md)，业务演示与模拟负责人验收在 [`docs/17`](docs/17-business-mvp-acceptance.md)。
数字不要抄到这里来，它们会漂移。

## 现在的产品长什么样

默认入口是原生 DSH Web 上的三栏笔记本工作面：左栏 Sources 放实际上传的部门文件并可预览，
中栏是原生会话与轨迹（聊天、审批、会话管理都是 DSH 自己的前端），右栏 Studio 放工具入口、已保存产物和报价声明。
月度对账与报价是并列的两条路径，不是替换关系。实现走分支与 PR 合并；
远端看板的业务规划不能用界面验收代替。

2026-09-07 业务方定了一条影响后续所有设计的边界，原话与分工表在
[`CLAUDE.md`](CLAUDE.md)「字典由人预设，模型只做匹配」一节，一句话版本是：标准格式与初始字典由人事先写好，
模型只把上传件的列匹配到字典已声明的字段。两条直接后果：

1. [#102](https://github.com/EricWang1358/BridgeFlow-AI/issues/102) 的原始前提（让 captain 提一份字典）作废，
   已在该 issue 下更正。`profile_batch`（[#101](https://github.com/EricWang1358/BridgeFlow-AI/issues/101)）保留，
   用途改为把上传列匹配到已声明字段，候选集是封闭的。
2. 报价（[#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104)）是四部门月度对账旁边的第二条路径，
   任务书见 [`docs/20`](docs/20-quotation-brief.md)：分三步，第一步不依赖样板案例，现在就能做，
   做法是把报价单变成字典里的一份声明，而不是一段代码。
   [#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7)（价格带要有真实成本算术）因此从「演示砍掉的一拍」
   升级成这条路径的核心输出。

## 报价路径做到哪了

样板前阶段已实现，与月度对账并列；设计先于代码，记录在 [`docs/21`](docs/21-quotation-design.md)。
现在有的是：一个通用文档求值器（复用既有算术）、接受内部结构化事实与 SourceRef、产出 Decimal 成本草稿，
或者点名缺什么的聚合拒绝。示例政策只用于合成验证，业务字段与责任仍待样板案例确认。

界面上，空会话也能直接点右侧「报价工作区」，那里只显示当前人工配置的声明与待补的依据。
真实原件抽取和对外发送仍属于任务书的后续阶段。
不要把完整文件、也不要把浏览器自报的 JSON，当成可信的抽取结果。

笔记本本身支持命名、显式保存、退出时选择、历史恢复。「笔记本用途」控制它显示月度、报价还是综合状态；
栏间分隔线可拖动，聚焦后也能用方向键调整。左侧来源区和笔记本列表都有「打开示例笔记本」，
会导入一份合成月度案例并生成规则主表，这一步不调用模型。
给业务负责人看的连续操作说明在 [笔记本演示故事](demo-walkthrough/notebook.md)。

验证这两件事的命令：`pytest -q backend/tests/test_declared_documents.py`（声明与拒绝）、
`pnpm --dir plugins smoke:quotation`（原生工作台）。实测、费用、截图与验证边界统一记在
[`docs/00`](docs/00-status.md)。

## 怎么把它跑起来

带截图的逐步操作指引在仓库根 README（[`README.md`](README.md) / [`README.zh.md`](README.zh.md)，
顶部可切换语言），从装环境到完成一次研判每步都有图。下面是命令版。

在仓库根目录：

```bash
source ../.venv/bin/activate
source ./env.sh
npm install -g @deepseek-ai/dsh@0.1.2-rc.1
cd plugins
pnpm install --frozen-lockfile
pnpm run build
cd ..
python scripts/start_web.py
```

打开终端打印的带凭证 DSH Web 地址。启动器会检查锁定版本、选择官方 npm `dsh`、
只启动监听 localhost 的 Python 服务；服务凭证由启动器生成，不下发给浏览器。
后端用 8000 端口，Web 端口可以传 `--port 3082`。按 `Ctrl-C` 会停掉这次启动的两个进程。
`BRIDGEFLOW_DSH` 可以指定同版本 npm CLI 的完整路径，但不要指向 Python SDK 的打包二进制。

`DSH_*` 与 `DEEPSEEK_BASE_URL` 只能由 shell 导出，不能放进 `.env`（原因见 `CLAUDE.md`）。
从仓库根启动时不会读 `backend/.env`：领域配置要么导出到启动 shell，要么放仓库根的 `.env`（只放领域变量）。

生产字典由 `FIELD_DICTIONARY_PATH` 指定，缺失时界面明确显示「未配置」，系统不猜。
只在练习或演示这个合成案例时才显式设置：

```bash
export FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml
```

跑起来之后：新建笔记本会自动归入原生工作区 `BridgeFlow`（旧会话若仍提示选工作区，显式保存一次笔记本即可确认归属）。
点左侧 Sources 的「添加来源」→ 选月份与部门文件 →「导入并检查」→ 检查主表、隔离与映射 →
把分析请求复制进原生对话框。后续工具都带同一个 `batch_id`；`review_batch` 发起官方四部门子会话，
跑完在「四部门报告」里看建议、责任与来源。导入与规则计算不产生模型费用，
在对话里提交分析请求会调用配置的模型，可能计费。

映射写入走 `confirm_mapping` 与 DSH 原生审批面板。批准后主机为本次参数生成一次性回执，拒绝不写入。
原生审批支持可选的拒绝理由：理由先写进官方领域存储审计，再送回 agent，不依赖旧控制台。
要关掉写权限，得同时把 `dsh/enterprise.patch.yml` 的 `allowMappingWrite` 与环境变量
`BRIDGEFLOW_ALLOW_MAPPING_WRITE` 设为 `false`。

当前认证表示共享 DSH 会话，记录为 `dsh-authenticated-session`。员工 SSO、角色管理、租户隔离都没有实现。

## 复测

```bash
cd backend
pytest -q
ruff check src tests ../scripts/start_web.py
cd ../plugins
pnpm run typecheck
pnpm test
pnpm run build
pnpm exec playwright install chromium
pnpm run smoke:web
pnpm run smoke:business
BRIDGEFLOW_TEST_FAULT=step-limit pnpm run smoke:business
```

Python 测试由 `conftest.py` 隔离 provider、字典、输出与记忆。浏览器测试用临时 DSH_HOME、临时数据与
离线适配器，默认不访问付费模型；真实模型复演要显式加 `BRIDGEFLOW_LIVE=1`。`BRIDGEFLOW_PYTHON` 可以
指定 smoke 用哪个 Python，默认是仓库外的 `../.venv/bin/python`。

离线回归只证明规则与契约成立。判断质量要另外跑模型评测并记录费用与局限，
不能拿 mock 输出当真实研判的证据。

### 已知问题：三条浏览器 smoke 在开发机上是红的

`smoke:web` / `smoke:quotation` / `smoke:business` 三条都会失败，控制台同一句：

```text
client-modules: HTML did not preload @deepseek-ai/dsh-client-modules/client.js
```

这不是你弄坏的，也不是产品坏了。判别实验：同一份 `dsh/enterprise.patch.yml`、同一条 `dsh web` 命令，
换成指向已预装 web profile 的真实 `DSH_HOME` 的 harness（`pnpm --dir plugins shots`），该错误出现 0 次，
界面正常渲染。三条 smoke 各自 `mkdtemp` 建全新临时 DSH_HOME，差异指向那里；`dsh --dump-config` 显示
组合期 36 个官方客户端插件全在，所以问题在服务期。进展与已排除的假设见
[#97](https://github.com/EricWang1358/BridgeFlow-AI/issues/97)。

在它修好之前：浏览器行为只能靠 `shots` 手工看；`docs/00` 里那些「smoke 通过」的记录与本机复现不符，
引用前先自己跑一遍。

### 进行中：#110 中英切换默认英文（2026-09-08）

已落码（本分支，未合并）：无偏好新用户默认英文（客户端启动时等宿主设置文档加载后、确认无已存偏好，
才经官方 `setLocale` 写入一次 en，持久化仍由宿主负责）；审批卡正文改为结构化双语——新增
`/bridgeflow/approval-detail` 端点（`PendingDetails.peek`，只在决定悬而未决时存在），卡片渲染的是
issue #96 那份封顶摘要：标签译自我们自己声明的封闭参数名，值原文照显；日期/数字统一走
`formatDateTime/formatTime/formatNumber`（只改显示，不改领域值）；`workspace.tsx` 的 `' 条'` 与
`state.tsx` 的行内三元收进 labels 表。smoke 测试改为「先断言默认英文 → 原生设置里切中文 →
原流程」，并新增重载/宿主重启后语言保持、窄屏英文标签、审批卡结构化正文的断言
（`plugins/tests/locale.mjs` 是公共 helper）。

未验证：浏览器实测全部待跑——本机 Playwright chromium_headless_shell-1187 未装（官方源下载卡死），
且上一节 #97 的三条 smoke 红的问题可能仍在。跑之前先 `pnpm exec playwright install chromium`。
`plugins/tests/locale-probe.mjs` 是探针脚本，验证完 `locale.mjs` 的选择器后应删除，不进 PR。

## 仍需做什么

1. **真实企业口径。** 合成案例已有可复算的指标、字段与来源。真实 OA 科目、客户级规则、多 sheet 与合并表头
   仍须业务确认；本例那条正数成本约定不能直接套到混合符号的 GL 上。
2. **企业身份与交付流程。** 员工 SSO、角色与租户边界、版本 diff、正式签发都还没做。
3. **#46 / #61 / #88 人工修复。** 字段映射向导与隔离区的 release/discard 未实现。
   现阶段的做法是修正源文件后重新导入，原批次不改；未声明日期的歧义值拒绝参与总额。
4. **#38 / #40 / #87 远端评审。** 本地已接通官方 spawn、结构化校验、部分失败、原生报告卡与拒绝理由。
   要用复演证据去评审 issue 的范围，远端尚未改动；旧的 Python Orchestrator 不能当回退。
5. **扩大验证。** 目前是真实模型在可见合成案例上的验收，不是留出集，也不是真实客户验收；
   模型补充的文字仍需业务复核。大规模性能与更广泛的攻击评测未完成。

旧 `/analyze`、`/quote`、`/console` 与样本回退默认关闭。历史控制台测试与耗时记录留在 `docs/00`，
它们不代表新 Web 的员工身份或最新业务结果。新默认入口禁止回退到缺少策略的 runtime。

## 运行时与数据修复

**Web 与 Python SDK 必须用同一个运行时。** 两者共用 npm CLI 选择器（`bridgeflow.dsh_runtime.native_command`），
SDK 通过官方 `dsh_bin` 显式指定。原因是 Python 打包运行时会把同一 home 的模块入口改写到 `/snapshot`，
正在运行的 npm Web 随后动态挂载 preset 时导入不了。旧环境若已被污染，重启 `scripts/start_web.py`，
官方启动加载器会自愈；要直接试验打包 SDK，请另开独立 home（只换 profile 名称不隔离共享 fallback）。

**笔记本与审批元数据用官方 storage-domain**，不向原生日志写未知必需事件。研判状态从实际工具调用与结果恢复。
旧日志若因 `bridgeflow/review` 或 `bridgeflow/approval-note` 打不开：先停启动器，再跑
`python scripts/repair_session_metadata.py --root ../.dsh-bridgeflow/sessions` 检查，确需修复才加 `--apply`
（工具会保存原始备份）。不要改原生事件白名单，也不要让修复脚本和运行中的会话争写同一批文件。

## 接手约定

- 分支 → PR → merge，不直接提交 `main`。
- 所有实测数字只写进 [`docs/00`](docs/00-status.md)，别处引用它。数字被抄进三五处然后开始漂移，是这个项目犯过的错。
- 缺陷诊断到根因，不绕开、不记成「可接受成本」。异常是线索，不是预算项。
- 真实模型调用会计费：跑之前想清楚值不值，跑完把花销记进 `docs/00`。
- 硬约束在 [`CLAUDE.md`](CLAUDE.md)，架构权威在 [`docs/13`](docs/13-golden-standard.md)，冲突时以后者为准。
  报价功能的任务书是 [`docs/20`](docs/20-quotation-brief.md)。
- 写文档时看一眼 [`docs/README.md`](docs/README.md) 末尾的写作约定。