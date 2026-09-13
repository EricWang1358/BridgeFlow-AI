# 27 — 外部输入交接清单

剩下的 issue 都卡在开发侧给不了的东西上。本文逐项写清：要什么、以什么形式交、**怎么交才安全**、到手后跑哪条命令验收。
每项的工程侧准备已经做完，输入一到就能验收，不需要再改代码。数字与费用只记在 [`00`](00-status.md)。

| # | 输入 | 谁提供 | 到手后验收 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | 飞书自建应用凭据 + 测试文件夹（#140） | 飞书管理员 | `python scripts/feishu_live_check.py` | 未提供 |
| 2 | AWS Lightsail 实例、静态 IP、域名（#138） | 部署负责人 | `bash deploy/bootstrap.sh <domain>` → `bash deploy/preflight.sh <domain>` | 基建就绪，暂不连接 |
| 3 | 报价样板（#104、#7、#20、#40） | 市场部 + 报价负责人 | 见下 | 未提供；已用 `data/mock_business/quotation/` 模拟 |
| 4 | 真实月度导出 + 手填总表（#141） | 四部门 + 留出评测执行人 | `python scripts/integration_cases.py real <目录>` | 未提供；已用 `data/mock_business/monthly/` 模拟 |
| 5 | 口径确认（#23、#19） | 各部门负责人 | 改 `integration.yaml` / 字典，跑全量测试 | 已按通用做法补齐，待确认 |
| 6 | 复跑彩排的付费授权（#41） | 用户 | 录制版本冻结后 `BRIDGEFLOW_LIVE=1 pnpm --dir plugins smoke:business` 等 | 草案 [`28`](28-rehearsal-authorization.md)，待签署 |

---

## 1 飞书凭据（#140）

**要什么**：一个飞书自建应用的 App ID 与 App Secret，开通云文档 `drive:drive` 权限；一个与该应用共享的测试文件夹的 token。

**怎么交**：只在启动 shell 里 export，**不写进任何文件、issue、聊天记录或提交**。

```bash
export FEISHU_APP_ID=...  FEISHU_APP_SECRET=...  FEISHU_TEST_FOLDER=...
python scripts/feishu_live_check.py
```

脚本往测试文件夹传一个合成的小工作簿，再按返回的 token 下载回来，逐字节比对。输出只含状态、字节数与耗时，不打印任何凭据或 token。
`passed` 后在 Web 里各走一次「从飞书导入」与「报告传回飞书」（都要原生审批），把结果记到 `docs/00`。
免费版飞书的接口能力未验证：若 `refused`，原样记录飞书给出的 code 与 msg，放进限制说明，不绕过。

## 2 部署基建（#138）

AWS 尚未配置，本轮只搭基建、不连接。已就绪：

| 文件 | 作用 |
| --- | --- |
| `deploy/bootstrap.sh <domain>` | 在全新 Ubuntu 24.04 实例上自动完成 [`22`](22-lightsail-deploy.md) §2–§8；可重复执行。不写任何密钥：API key 手填进 `env.sh`，basic auth 密码从终端读入、只存 bcrypt |
| `deploy/preflight.sh <domain>` | 只读自检 §12：`env.sh` 权限、`.env` 无引导变量、`DSH_HOME` 在仓库外、dsh 版本、构建、单元状态、只有 22/80/443 对外、Caddy 401 |
| `deploy/Caddyfile.template` | Caddy 配置模板，端口与 systemd 单元一致（测试锁定） |
| `.github/workflows/deploy.yml` | deploy job 默认关闭，仓库变量 `DEPLOY_ENABLED=true` 才会部署 |
| `backend/tests/test_deploy_config.py` | 离线检查上述文件互相一致、健康检查路径真实存在、无提交的密钥 |

**到时的顺序**：建实例与静态 IP → 域名 A 记录 → 实例上 `bash deploy/bootstrap.sh <domain>` → `preflight` 全 ok →
GitHub 配 `SSH_HOST` / `SSH_USER` / `SSH_PRIVATE_KEY` secrets 与 `PUBLIC_DOMAIN` 变量 → 最后设 `DEPLOY_ENABLED=true`。

## 3 报价样板（#104、#7、#20、#40）

**要什么**（脱敏后即可，去掉公司抬头、真实客户名可替换）：

- 客户会话或询价记录 2–3 份，采购合同 1–2 份（PDF 或 Word 原件）；
- 人工做的标准报价单模板 1 份，并在上面标出每个数字来自哪份原件的哪个位置；
- 成本与产能依据：用料、单价、分摊方式；付款历史的权威来源；
- 定价政策：最低毛利、产能预留、信用与账期、交期条件，以及每条的例外由谁批准；
- 报价外发前由谁放行。

**到手后**：先确认抽取规范（每个事实绑定原件页／段），再实现抽取；样板不全的项继续拒绝出数。验收是业务负责人逐项核对标准答案。

## 4 真实月度导出与留出（#141）

**要什么**：同一个月四个部门按 v2 模板填好的真实表，外加一张业务方**手工**填好的跨部门总表（`master-v2.xlsx` 格式）作为标准答案。
需要两组：一组给开发调优，一组留出。

**留出的纪律**：留出那组只交给不参与开发的评测执行人，开发不看原件。执行人把五个文件放进同一目录
（部门文件名用「财务部」「市场部」「生产部」「物资部」开头即可，标准答案命名 `expected.xlsx`）：

```bash
python scripts/integration_cases.py real <目录>
```

输出只有计数、列名与待确认类型（匹配行、完整行、逐列一致行、有差异的列及次数），**不含任何单元格值**，可以直接转给开发。
合成调优与留出（`tuning`、`holdout`）已经跑通，见 `data/company_templates/README.md`。

## 5 口径确认（#23、#19）

已按通用做法补齐并在 `integration.yaml` 的 `assumptions` 里逐条标注：增值税 13%、缺口公式、合作状态诊断阈值、生产部按日汇总。
请各负责人逐条回复「确认」或给出自己的口径；改口径只改 YAML。仍需业务方回答、没有通用做法可代替的：

- 销售／成本科目分类与正负号（#92 已改为声明式，等真实科目表）；
- 产能上限的来源与维护者（#75）；
- 客户分级、信用与账期政策及负责人；
- 预警处置（#19）：谁能确认、驳回、指派、关闭，每一步是否需要审批。可参考的最小状态流是
  「待确认 → 已指派 → 处理中 → 已关闭／已驳回」，但责任人和审批要求必须由业务方定。

## 6 复跑彩排的付费授权（#41）

#167 已在当时的 main 上跑过一次连续彩排与对抗评测，调用次数与 token 见 `docs/00`。录制版本冻结后需要按同一组命令再跑一次，
才能说视频里的版本就是验收过的版本。授权时请说明：冻结的提交、跑哪几条（`smoke:business` risk / balanced / 投毒、`smoke:web` 真实审批、列匹配全流程）、预算上限。
与业务负责人逐项核对部门责任与 `manager_decision` 需要真人参加，不能用模型代替。
