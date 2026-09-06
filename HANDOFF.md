# 交接说明

更新于 2026-09-06。当前默认产品入口已改为 **原生 DSH Web**：侧栏可导入 CSV / 单 sheet XLSX，查看主表、待确认映射、修正记录、隔离行和四部门研判报告；对话、会话、审批和轨迹使用 DSH 原有前端。

当前变更是本地实现，未提交或修改远端看板。架构原则见 [docs/13](docs/13-golden-standard.md)，业务演示与模拟负责人验收见 [docs/17](docs/17-business-mvp-acceptance.md)，本次审查与 issue 重排建议见 [docs/16](docs/16-dsh-web-review.md)，所有实测数字与验证边界见 [docs/00](docs/00-status.md#原生-web-重构复测2026-09-06)。

## 2026-09-07 业务方定的边界（影响后续所有设计）

**标准格式与初始字典由人事先预设，模型只做匹配，不做创造。** 原话与分工表见
[`CLAUDE.md`](CLAUDE.md) 的「字典由人预设，模型只做匹配」一节。

两条直接后果：

1. **不要再设计「让 captain 提出一份字典」。** [#102](https://github.com/EricWang1358/BridgeFlow-AI/issues/102)
   的原始前提已作废，已在该 issue 下更正。`profile_batch`（[#101](https://github.com/EricWang1358/BridgeFlow-AI/issues/101)）
   保留，用途改为**把上传列匹配到标准字典已声明的字段**——候选集是封闭的。
2. **多一个并列功能，不是转向。** 「客户会话 + 采购合同 → 报价单」（两个部门）是
   四部门月度对账**旁边**的第二条路径，两者共存
   （[#104](https://github.com/EricWang1358/BridgeFlow-AI/issues/104)）。任务书见
   [`docs/20`](docs/20-quotation-brief.md)：分三步，**第一步不依赖样板案例，现在就能做**
   ——把报价单变成字典里的一份声明，而不是一段代码。
   [#7](https://github.com/EricWang1358/BridgeFlow-AI/issues/7)（价格带要有真实成本算术）
   因此从「演示砍掉的一拍」升级为这条路径的核心输出。

## 怎么把它跑起来

在仓库根目录执行：

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

打开终端打印的带凭证 DSH Web 地址。启动器检查锁定版本，选择官方 npm `dsh`，并启动仅监听 localhost 的 Python 服务。共享服务凭证由启动器生成，浏览器不接收它。可通过 `BRIDGEFLOW_DSH` 指定同版本 npm CLI 的完整路径；不要指定 Python SDK 的打包二进制。后端使用端口 8000，Web 端口可传 `--port 3082`。`Ctrl-C` 会停止这次启动的两个进程。

`DSH_*` / `DEEPSEEK_BASE_URL` 仍只能由 shell 导出，不能放 `.env`。根目录启动时不会读取 `backend/.env`：将领域配置导出到启动 shell，或放根目录 `.env`（仅领域变量）。生产字典是 `FIELD_DICTIONARY_PATH`；缺失时界面明确显示未配置，不能猜测。仅练习时可显式设置：

```bash
export FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml
```

首次会话选择原生工作区 `BridgeFlow`。点击「导入与数据」→选择月份与部门文件→「导入并检查」→检查主表、隔离与映射→复制分析请求到原生对话框。后续工具都携带同一 `batch_id`；`review_batch` 发起官方四部门子会话，完成后在「四部门报告」查看建议、责任和来源。导入与规则计算不计模型费用；在原生对话中提交分析会使用配置模型，可能计费。

映射写入走 `confirm_mapping` 与 DSH 原生审批面板。批准后由主机为**本次参数**生成一次性回执；拒绝不会写入。原生审批现在支持可选拒绝理由，先记录会话审计再送回 agent，不依赖旧控制台。关闭写权限时应同时将 `dsh/enterprise.patch.yml` 的 `allowMappingWrite` 与 Python 环境的 `BRIDGEFLOW_ALLOW_MAPPING_WRITE` 设为 `false`。

当前认证表示共享 DSH 会话，记录为 `dsh-authenticated-session`，**没有实现员工 SSO、角色管理或租户隔离**。

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

Python 测试在 `conftest.py` 隔离 provider、字典、输出与记忆。浏览器测试用临时 DSH_HOME、临时数据与离线适配器，默认不访问付费模型；真实模型复演显式加 `BRIDGEFLOW_LIVE=1`。本次已完成真实模型及业务解释审读，范围与结果见 `docs/00` 和 `docs/17`，不代表未知数据集质量。`BRIDGEFLOW_PYTHON` 可指定 smoke 的 Python；默认使用仓库外 `../.venv/bin/python`。

## 仍需做什么

1. **真实企业口径**：合成案例已经有可复算指标、字段与来源，真实 OA 科目、客户级规则、多 sheet/合并表头仍须业务确认；不能将本例正数成本规则直接套到混合符号 GL。
2. **企业身份与交付流程**：员工 SSO、角色/租户边界、版本 diff、正式签发仍未实现。
3. **#46 / #61 / #88 人工修复**：字段向导与隔离 release/discard 未实现。现阶段修正源文件后重导，原批次不改；未声明日期的歧义值拒绝参与总额。
4. **#38 / #40 / #87 远端评审**：本地已接通官方 spawn、结构化校验、部分失败、原生报告卡和拒绝理由。以复演证据评审 issue 范围，远端尚未改动；旧 Python Orchestrator 不能作为回退。
5. **扩大验证**：目前是真实模型在可见合成案例上的验收，尚非留出集或真实客户验收；模型补充文字仍需业务复核。大规模性能和更广泛攻击评测未完成。

旧 `/analyze`、`/quote`、`/console` 和样本回退默认关闭。历史控制台测试及耗时记录保留在 `docs/00`，不代表新 Web 的员工身份认证或最新业务结果。新默认入口禁止回退到缺少策略的 runtime。
