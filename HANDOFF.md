# 开发交接 / Development handoff

更新：2026-09-17（按用户要求提交 PR、验证 CI/CD 并合并；功能开发仍暂停）。**用户已要求本阶段停止开发，整理交接后留给下一阶段。不要因旧实施计划或自动续跑继续增加功能。** 下列未完成项是后续任务，不代表本阶段已完成全项目目标。

## 接手先看

- 交付分支：`feat/14x-requirements-delivery`；基于 `main@4a38904`（合并 #186）。本轮代码、测试与需求文件纳入同一 PR；实际提交及合并状态以 Git/GitHub 为准。接手先看 `git status`，不要 reset 或 clean 尚未保存的工作。
- 全项目需求与逐 UC 状态：[requirements/README](docs/requirements/README.md)；一份双语 Markdown 对应一个 Epic，既有能力与历史延期范围也已纳入。14x 只是其中三个 Epic。实现顺序：[implementation-plan](docs/requirements/implementation-plan.md)；issue/PRD 对照：[traceability](docs/requirements/traceability.md)。
- 2026-09-17 需求复核（仅文档，未写代码）：按项目完整性、流程便民性、结论直观性与专业性三个视角补充 [00-foundations](docs/requirements/00-foundations.md)（角色目录、逐 UC 参与者与触发、非功能需求、结论呈现规范、优先级与 Given/When/Then 验收写法），新增 [E13 月度结论呈现与口径治理](docs/requirements/13-conclusions.md) 与 [E14 月度流程便民](docs/requirements/14-monthly-convenience.md) 共 12 个 UC，以及 [类设计](docs/requirements/class-design.md)；目录现为 14 个 Epic、85 个 UC。看板 Epic #189（E13）、#196（E14），每个 UC 一个子 issue。第一轮已实现 E13-UC01 一页结论主流程（#190）、E13-UC06 依据等级（#195）、E14-UC03 提交前自检（#199，离线完成），证据见 docs/00；下一轮建议 E13-UC05 口径确认与 E14-UC04 单部门补传。
- 测试数量、命令、截图及验收边界仅记录于 [docs/00](docs/00-status.md)。不要从“代码存在”“issue 已关闭”或离线通过推定企业验收。
- 必读硬约束：[CLAUDE.md](CLAUDE.md)、[架构权威 docs/13](docs/13-golden-standard.md)、[产品扩展契约 docs/23](docs/23-extension-contracts.md)。

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
- 门户开启后，ACL 需显式 `workflow_departments`（准确部门名）及 `operations`；省略不扩权。示例：[access-control.example.yaml](data/mappings/access-control.example.yaml)。真实门户接入见 [docs/27-login](docs/27-login-portal.md)。
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
