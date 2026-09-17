# 32 — 飞书在线表格 / 多维表格读取（需求规格）

2026-09-17 定范围：agent 以**当前登录用户身份读取**在线表格（sheet）与多维表格（bitable），
导入为部门批次。**写回不做** — 编辑留在飞书里操作。
前置：[`30`](30-feishu-user-docs.md) 的 user token 管线与 [`31`](31-feishu-wiki.md) 的浏览面
（wiki/我的空间列表里这两类节点已可见、灰显）。本篇是需求规格，先于代码写定。

## 一、需求合理性分析

**结论：合理，且是主链路的必经补丁。**

1. **现实数据形态就是在线表格**。实测（2026-09-17）：飞书上传 xlsx 会被自动转换成
   在线表格/多维表格，用户日常维护的数据大概率本来就是这两类。只支持「文件附件」意味着
   真实数据几乎全部落在灰显区 — docs/30/31 的导入能力对真实场景名存实亡。
2. **读是导入的缺口，不是新能力**。浏览、选人、审批语义、权限分层都已就位；
   本篇只补「内容怎么进来」这一段管道，架构零推翻。
3. **写回不做是对的**。报告/总表写进在线表格或 bitable，要先定义「结果长什么样的表结构」，
   这是业务语义决定，不该替业务方拍。飞书内编辑体验也优于任何写回接口。
4. **与评分标准同向**：rubric 第 5 项 least-privilege —「读取范围不超出操作者权限」
   靠 user token 由飞书 enforce，本篇原样继承。

## 二、可行性分析

**结论：可行。sheet 低-中难度，bitable 中等。风险在配额与复杂字段类型，不在架构。**

### 接口面（全部用户身份）

| 动作 | 接口 | scope |
| --- | --- | --- |
| 列 sheet 标签页（名称、行列数） | `GET /sheets/v3/spreadsheets/{token}/sheets/query` | `sheets:spreadsheet:readonly` |
| 读单元格区域 | `GET /sheets/v2/spreadsheets/{token}/values/{range}` | 同上 |
| 列 bitable 数据表 | `GET /bitable/v1/apps/{token}/tables` | `bitable:app:readonly` |
| 列字段定义 | `GET /bitable/v1/apps/{token}/tables/{id}/fields` | 同上 |
| 读记录（分页 ≤500/页） | `GET /bitable/v1/apps/{token}/tables/{id}/records` | 同上 |

关键事实：浏览列表已返回 `obj_token` + `obj_type`（docs/31），对 sheet/bitable 节点
`obj_token` 直接就是 spreadsheet_token / app_token，**寻址零新增**。

### 风险与对策

| 风险 | 对策 |
| --- | --- |
| 20 万行 × 500/页 = 400 次分页调用，撞频率限制 | 后端流式分页落 DataFrame，页间自重试退避；超上限（FR-6）明确报错不截断静默 |
| 免费版 sheets/bitable 接口配额未实测 | 联调实测记录进 [`00`](00-status.md)，被拒原样记 code/msg，不绕过 |
| bitable 复杂字段（附件、人员、关联、公式） | FR-5：标量字段取值，复杂字段取显示文本；取不到的整列剔除并进 quarantine 说明，不猜 |
| sheet 的表头位置、多标签页语义 | 复用现有导入表单的 sheet 选择 + header_rows（本地 xlsx 导入已有此 UI） |

## 三、需求规格

### 功能项

**FR-1 可选中**：Sources 面板里 `obj_type=sheet` / `bitable` 的节点从灰显变为可选中，
选中后弹出二级选择 — sheet 选标签页 + 表头行数；bitable 选数据表。

**FR-2 sheet 导入**：`sheets/query` 取标签页元数据（名称、行列数）供选择；
按所选标签页与 header_rows，分页读 `values` 组装 DataFrame，复用 `_import_batch`。
列名只来自表头行；匹配走既有字典流程，模型不发明字段（硬约束不变）。

**FR-3 bitable 导入**：`tables` + `fields` 取表与字段元数据供选择；
分页读 `records` 组装 DataFrame，列名 = 字段名（飞书已结构化，无表头猜测）。
复用 `_import_batch`。

**FR-4 元数据先行**：二级选择的回答只有名称、行列数、字段名 — 原始记录行绝不进返回值，
更不先进模型上下文（三层纪律原样适用：读在模型外，返回值无行数据）。

**FR-5 复杂字段降级**：bitable 标量（文本、数字、日期、单选、复选、勾选）直接取值；
人员、关联、附件、公式取飞书返回的显示文本；无任何可取表示的列剔除，
在批次 quarantine 里记「列 X 类型 Y 不可导入」，不静默丢列。

**FR-6 上限明确**：单次导入上限 20 万行（与 PRD 一致）；超限 413/502 明确报错，
报已读行数与上限，**不返回截断的部分数据**（截断 = 静默出错）。

**FR-7 权限边界**：user token 一路到底；用户无权的表格，元数据调用即被飞书 403，
透传报错。部门批次级 `access-control.yaml` 照旧。端点不注册为模型工具，
浏览器点击 = 审批（docs/30 已拍板）。

### 端点增量（backend）

| 端点 | 入参 | 出参 |
| --- | --- | --- |
| `POST /tools/feishu-sheet-meta` | token | `[{sheet_id, title, rows, cols}]` |
| `POST /tools/feishu-bitable-meta` | token | `[{table_id, name}]` + 字段名清单 |
| `POST /tools/feishu-import-user`（扩展） | files 项加 `kind: file\|sheet\|bitable`、`sheet_id`/`table_id`、`header_rows` | 不变（batch summary） |

### 验收

1. 真实账号：从 wiki/我的空间选中在线表格 → 选标签页 → 导入成批次，行数与飞书一致；
2. bitable 同上，复杂字段列按 FR-5 处理，quarantine 有据；
3. 无权限账号 B 对 A 的表格：meta 调用即 403；
4. 全测试断言返回值无单元格/记录内容（沿用 secret_cell 探针模式）；
5. 实测行数-耗时-调用数记 [`00`](00-status.md)。

## 四、实施步骤

沿用分支 `feature/feishu-user-docs-20260916`，单独 commit。每步独立可验。

**第 1 步 — 飞书配置（人工，先行）**：加用户态 `sheets:spreadsheet:readonly`、
`bitable:app:readonly` → **发版** → 全员重登。

**第 2 步 — backend**：`FeishuDrive` 加 `sheet_meta` / `sheet_values`（分页生成器）/
`bitable_tables` / `bitable_fields` / `bitable_records`（分页生成器）；
`_import_with` 按 kind 分流，sheet/bitable 走「分页 → DataFrame → `_import_batch`」；
两个 meta 端点 + import 扩展。测试：假飞书分页、复杂字段降级、超限报错、无泄漏探针。

**第 3 步 — 插件**：sheet/bitable 节点可选中；选中弹二级选择（标签页/数据表 +
header_rows for sheet）；提交扩展后的 import 请求。i18n 补齐。

**第 4 步 — 真实联调**：两账号互验；大表压测分页路径；结果记 docs/00。

## 五、明确不做（本期）

- 在线表格 / bitable 的**写入**（编辑在飞书内进行）；
- docx 正文抽取；
- bitable 视图筛选、关联表展开导入、附件字段下载；
- sheet 公式求值（取飞书计算后的值，不重算）；
- 超过 20 万行的分片导入。

## 六、需要人工操作与输入（阻塞项）

| # | 事项 | 谁 | 说明 |
| --- | --- | --- | --- |
| 1 | 加 `sheets:spreadsheet:readonly`、`bitable:app:readonly` 用户态 scope 并**发版** | 飞书管理员 | 不加则全部 99991672 |
| 2 | 全员重新登录 | 所有用户 | 新 scope 要重新授权 |
| 3 | 各造一个测试用在线表格与多维表格 | 团队 | 含复杂字段列，验 FR-5 |
| 4 | 免费版接口配额确认 | 飞书管理员 | 大表分页撞限则记为限制 |
