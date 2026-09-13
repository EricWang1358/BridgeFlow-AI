# 28 — 录制版本复跑彩排：付费调用授权书（模拟草案，#41）

> **这是按实测数据预填的草案，本身不构成授权。** 付费模型调用只在用户于第五节签署（或在会话里明确回复「按 docs/28 授权」）后执行；
> 签署前开发侧不会运行任何带 `BRIDGEFLOW_LIVE=1` 的命令。所有 token 数字来自 [`00`](00-status.md)，费用以 DeepSeek 控制台当期单价为准。

## 一、目的

#167 的连续彩排跑在当时的 main 上。视频与报告要声称「录制的版本就是验收过的版本」，必须在**录制版本冻结后**，用同一组命令在该提交上再跑一次，
并把结果、调用次数与 token 记入 `docs/00`。

## 二、授权范围

| 项 | 预填值 | 说明 |
| --- | --- | --- |
| 冻结提交 | `＿＿＿＿＿＿`（录制版本冻结时填写；候选：当前 main） | 跑之前 `git status` 必须干净，`git rev-parse HEAD` 与此一致 |
| 运行时 | `deepseek-harness-sdk==0.1.2rc1`、dsh CLI `0.1.2-rc.1`、模型 `deepseek-v4-flash` | 与 `start_web.py` 版本门一致 |
| 数据 | `data/business_demo`（risk、balanced）、投毒单元格用例、列匹配改名批次 | 均为合成数据，不含客户数据 |
| 执行人 | 开发（Claude Code 会话），由用户监督 | |
| 时间窗 | 签署后 48 小时内 | 超时须重新授权 |

## 三、命令与预算

| # | 命令 | 验收什么 | #167 实测请求 / token |
| --- | --- | --- | --- |
| 1 | `BRIDGEFLOW_LIVE=1 pnpm --dir plugins smoke:business` | risk 案例 validated、与独立标准答案一致、冷重启 | 8 / 42,060 |
| 2 | `BRIDGEFLOW_LIVE=1 BRIDGEFLOW_CASE=balanced pnpm --dir plugins smoke:business` | balanced 案例 validated | 8 / 42,318 |
| 3 | `BRIDGEFLOW_LIVE=1 BRIDGEFLOW_POISON=1 pnpm --dir plugins smoke:business` | 注入文本不进入任何模型会话 | 8 / 42,542 |
| 4 | `BRIDGEFLOW_LIVE=1 pnpm --dir plugins smoke:web` | 真实审批允许 / 拒绝 / 超时 | 6 / 33,060 |
| 5 | 起演示服务后导入 finance 表头改名的批次，`node plugins/tests/column-match-live.mjs <带 token 的 Web 地址> <DSH_HOME> <批次 id> <输出目录>` | 列匹配提议 → 审批 → 重新导入 | 4 / 24,102 |
| | **一次全部通过的预计** | | **34 / 184,082** |

**硬上限**：模型请求 **50** 次、合计 **400,000** token（约为一次全过的 2.2 倍，覆盖一轮失败重试；#167 含失败共 388,902）。
另建议在 DeepSeek 控制台为本次使用的 key 设置消费上限。

**停止条件**（任一出现即停，不自动重试，先报告再等指示）：

- 累计请求或 token 触及硬上限的 80%；
- 同一条命令连续失败 2 次；
- 失败原因是产品缺陷而非网络抖动——按「不要绕过缺陷」先定位根因、修复并走 PR，修复后的复跑须重新确认冻结提交；
- 任何输出包含疑似真实凭据或客户数据。

## 四、交付物

- `docs/00` 新增一节：冻结提交、每条命令结果、请求数与 token（输入 / 输出 / 缓存读）、全部尝试含失败的合计；
- `docs/evidence/live-acceptance-<日期>/`：摘要与截图，不含原始会话；
- #41 评论：结论与证据链接。与业务负责人逐项核对部门责任和 `manager_decision` 需要真人参加，不在本授权内。

## 五、签署

| 角色 | 姓名 | 决定 | 日期 |
| --- | --- | --- | --- |
| 授权人（项目负责人） | | ☐ 同意　☐ 修改后同意（写明）　☐ 不同意 | |
| 预算上限（如修改） | | 请求 ＿＿ 次 / token ＿＿ / 金额 ＿＿ | |
