# docs/images — 指引用截图

这些是 [`../README.md`](../README.md) 与 [`README.zh.md`](../README.zh.md) 里嵌的截图。
它们是从 `docs/evidence/` 的浏览器复演证据里**复制**出来的稳定副本：证据目录按 `--keep 2`
轮换，直接引用 `runs/<id>/` 会在下一轮复演后失效。

| 文件 | 内容 | 来源运行 | 界面外壳版本 |
| --- | --- | --- | --- |
| `01-notebook-empty.png` | 空笔记本：三栏工作面，开始页常驻四步流程 | `plugins/tests/readme-shots.mjs`（2026-09-25，离线） | 2026-09-25 页面质感改版 |
| `02-sample-sources.png` | 示例笔记本（模拟商砼 2024-07）：来源、批次、原件预览、「更多示例」 | 同上 | 同上 |
| `03-source-provenance.png` | 文件来源信息：上传文件、批次、工作表、SHA-256 | 同上 | 同上 |
| `04-batch-master-table.png` | 批次数据表：主表、清洗记录、待确认映射、列匹配、隔离行 | 同上 | 同上 |
| `05-report-preview.png` | 四部门报告预览：公式、关注阈值、责任、解释与原始来源 | `live-2026-09-25/risk`（**真实模型**） | 2026-09-25 页面质感改版 |
| `06-trajectory-four-spawns.png` | 轨迹：`review_context` → 四次 `subagent` → `review_finalize` | `live-2026-09-25/risk`（**真实模型**） | 同上 |
| `07-business-state-page.png` | 业务状态页：四部门报告、依据与归属 | `live-2026-09-25/risk`（**真实模型**） | 同上 |
| `08-approval-rejection-note.png` | 原生审批面板：要批准的草稿值、原话与换算、出处、被标出的检查、拒绝理由、拒绝 / 允许一次 | `live-2026-09-25/workflow`（**真实模型**） | 同上 |
| `09-save-notebook.png` | 离开前保存对话框：保存 / 不保存 / 取消 | `plugins/tests/quotation-smoke.mjs`（2026-09-25，离线） | 2026-09-25 页面质感改版 |
| `10-notebooks-list.png` | 笔记本列表与历史恢复 | 同上 | 同上 |
| `11-quotation-workspace-en.png` | 报价工作区（英文界面） | 同上 | 同上 |
| `12-cross-department-master.png` | 跨部门总表：完整行与待确认计数、口径假设、客户名称分歧、单元格出处 | `plugins/tests/readme-shots.mjs`（2026-09-25，离线） | 同上 |
| `13-workflow-handoff.png` | 填报与流转：七段流程条与两条示例记录（缺项 / 待审核），每条带下一步按钮 | 同上 | 同上 |
| `14-guided-tour.png` | 首次进入的引导欢迎卡 | 同上 | 同上 |
| `15-overview.png` | 总览：收口进度、待办、流转中的记录、代理运行与关键指标 | 同上 | 同上 |

两点必须说清楚：

1. 05–08 来自 2026-09-25 真实模型运行（`deepseek-official / deepseek/deepseek-v4.1-flash`），和其余截图同为改版后外观。
   05–07 是中文界面，08 是英文界面。
2. 截图来自离线模型适配器的浏览器复演，界面里的数字是合成案例的声明值，
   不是客户账目。费用与实测数字一律看 [`docs/00-status.md`](../00-status.md)。

01–04、12–15 重新生成：`source ../.venv/bin/activate && source env.sh && node plugins/tests/readme-shots.mjs`（隔离 DSH_HOME，离线，不调用模型，直接写入本目录）。其余几张的重新生成：`cd plugins && pnpm run smoke:quotation`（或 `shots` 对真实 `DSH_HOME` 手工看），
证据落在 `/tmp/bridgeflow-web-e2e-*`，再用 `python3 scripts/collect_demo_evidence.py` 采集，
最后把要用的几张复制到这里并更新上表。
