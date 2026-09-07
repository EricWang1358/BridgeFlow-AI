# docs/images — 指引用截图

这些是 [`../README.md`](../README.md) 与 [`README.zh.md`](../README.zh.md) 里嵌的截图。
它们是从 `docs/evidence/` 的浏览器复演证据里**复制**出来的稳定副本：证据目录按 `--keep 2`
轮换，直接引用 `runs/<id>/` 会在下一轮复演后失效。

| 文件 | 内容 | 来源运行 | 界面外壳版本 |
| --- | --- | --- | --- |
| `01-notebook-empty.png` | 空笔记本：三栏工作面与顶栏按钮 | `quotation-ui/runs/1788723465966` | 2026-09-07 三栏 |
| `02-sample-sources.png` | 示例笔记本：四份来源、批次号、主表产物与原件预览 | 同上 | 2026-09-07 三栏 |
| `03-source-provenance.png` | 「文件来源信息」：上传文件、批次、工作表、SHA-256 | 同上 | 2026-09-07 三栏 |
| `04-batch-master-table.png` | 批次弹窗：主表、清洗记录、待确认映射、隔离行、发起研判 | 同上 | 2026-09-07 三栏 |
| `05-report-preview.png` | 四部门报告预览：公式、关注阈值、责任、解释与原始来源 | `quotation-ui/runs/1788722008993` | 2026-09-07 三栏（窄栏裁切） |
| `06-trajectory-four-spawns.png` | 轨迹：`review_context` → 四次 `subagent` → `review_finalize` | `business-mvp/risk/runs/1788698431615141529` | **2026-09-06 外壳**（对话｜轨迹｜业务状态） |
| `07-business-state-page.png` | 业务状态页与节点筛选 | `business-mvp/chain-regression/runs/1788700374221311054` | **2026-09-06 外壳** |
| `08-approval-rejection-note.png` | 原生审批面板：参数、拒绝理由、期限、拒绝 / 允许一次 | `business-mvp/approval/runs/1788698590713111342` | **2026-09-06 外壳** |
| `09-save-notebook.png` | 离开前保存对话框：保存 / 不保存 / 取消 | `quotation-ui/runs/1788723465966` | 2026-09-07 三栏 |
| `10-notebooks-list.png` | 笔记本列表与历史恢复 | 同上 | 2026-09-07 三栏 |
| `11-quotation-workspace-en.png` | 报价工作区（英文界面）：声明模板与待补依据 | 同上 | 2026-09-07 三栏 |

两点必须说清楚：

1. 后三张是 2026-09-06 那一轮拍的，外壳还是「对话｜轨迹｜业务状态」两栏加右上角文件栏；
   09-07 换成三栏笔记本之后没有重拍。卡片内容、审批面板与轨迹语义至今一致，
   但外框按钮位置不同，跟着截图找按钮的人会困惑，所以这里逐张标了外壳版本。
2. 截图来自离线模型适配器的浏览器复演，界面里的数字是合成案例的声明值，
   不是客户账目。费用与实测数字一律看 [`docs/00-status.md`](../00-status.md)。

重新生成：`cd plugins && pnpm run smoke:quotation`（或 `shots` 对真实 `DSH_HOME` 手工看），
证据落在 `/tmp/bridgeflow-web-e2e-*`，再用 `python3 scripts/collect_demo_evidence.py` 采集，
最后把要用的几张复制到这里并更新上表。
