# 33 — 飞书在线表格 / 多维表格读取（实施计划）

2026-09-17。需求规格见 [`32`](32-feishu-sheets-bitable-read.md)，本篇是它的落地计划：每一步改哪个文件、
跑什么测试、验收什么。范围、FR 定义、明确不做都在 `32`，本篇不复述，冲突以 `32` 为准。

**结论在前：五步，前两步是纯代码可离线验证，第三步插件，第四步联调；阻塞项是
`32` 第六节的人工前置（scope 发版 + 全员重登），没做完联调全挂 99991672。**

实施状态（2026-09-17）：第 1–3 步已落地，后端 595 测试全绿（其中本篇新增 10 个）、
插件 typecheck/build 过。第 4 步联调等人工前置。与计划的出入：每条 files 项的表头字段名
用单数 `header_row`（与 `Layout.header_row` 对齐）；bitable meta 按拍板改为两段
（不带 `table_id` 返表清单，带 `table_id` 返该表字段定义）。

## 〇、现状锚点（复用面）

计划建立在以下既有件上，不重写：

| 既有件 | 位置 | 本篇怎么用 |
| --- | --- | --- |
| user token 管线（`for_user`、头部传 token、不落盘） | `backend/src/bridgeflow/feishu.py:56`、`api/feishu_tools.py:40` | 新端点全部走 `_user_client` |
| 批次导入主路径（字节上限、行数上限 413、quarantine、字典匹配） | `api/batches.py:438` `_import_batch` | sheet/bitable 物化成 CSV 后原样进 |
| 表头行/工作表选择的 `Layout` | `api/batches.py:220` | sheet 的 header_row 直接复用 |
| 浏览面与灰显节点 | `plugins/src/client/feishu-picker.tsx:169`（`importableNode`） | 放开 sheet/bitable，加二级选择 |
| 无泄漏探针（`secret_cell`） | `backend/tests/test_feishu.py:25` | 新端点沿用同一模式 |

## 一、设计决策（review 重点）

**决策 1 — 导入路径：分页读 → 物化 CSV 字节 → `UploadFile` → `_import_batch`。**
不新增 DataFrame 通道，不改 `_import_batch`。理由：行数/字节上限、清洗、quarantine、字典匹配
全部白拿；`_parse_department_file` 只认字节，CSV 物化是零侵入的适配层。CSV 用 `csv` 模块写，
逗号/换行/引号天然转义。

**决策 2 — sheet 的表头在物化时切片，不进 `Layout`。**
按用户选的 `header_row` 从第 N 行开始物化，物化后的 CSV 表头恒为第 1 行。
sheet 公式取飞书算好的值（`valueRenderOption=FormattedValue`，`32` 第五节已定不重算）。

**决策 3 — 超限在分页侧提前拒，不依赖 `_import_batch` 兜底。**
边分页边累计行数，超过 `bridgeflow_max_batch_rows` 立即 413，报「已读行数 / 上限」，
不物化、不建批次（FR-6：截断 = 静默出错）。`_import_batch` 的 413 仍在，双保险。

**决策 4 — 本期 sheet/bitable 只在 user 端点启用。**
tenant 路径（模型工具 + 审批的 `/tools/feishu-import`）传 `kind=sheet|bitable` 直接 422。
理由：`32` 接口面全标用户身份；tenant scope 是否加、加了是什么权限语义，本期不拍。

**决策 5 — 剔除列不进 quarantine 行级处置，进批次摘要新字段。**
quarantine 语义是「行被拦下待人工处置」，塞列级事实会把两种语义混在一起。
`BatchSummary` 加 `dropped_columns: [{department, column, field_type, reason}]`，
批次详情页照实显示。这是对现有 schema 的唯一扩展，FR-5 的「有据」落在这里。
*（若 review 认为应复用 quarantine，改动集中在 `_import_batch` 的 summary 组装，代价相当，取此案因语义干净。）*

**决策 6 — 分页重试有界。**
429 / 频控 code（如 99991400）指数退避，最多 3 次；仍失败则 502 透传飞书 code/msg。
不无限重试，不吞错。单次 range 读的行块大小定 5000，联调按实测配额调（`32` 风险表）。

## 二、实施步骤

分支沿用 `feature/feishu-user-docs-20260916`。三个 commit：backend → 插件 → 联调记录。
每步验收独立可跑。

### 第 0 步 — 人工前置（阻塞联调，不阻塞代码）

`32` 第六节四项。代码与离线测试不等它，真实联调等。

### 第 1 步 — backend：飞书客户端（`feishu.py`）

`FeishuDrive` 加五个方法，全部走既有 `_headers` / `_json`，错误原样带飞书 code/msg：

| 方法 | 接口 | 返回 |
| --- | --- | --- |
| `sheet_meta(token)` | `GET /sheets/v3/spreadsheets/{token}/sheets/query` | `[{sheet_id, title, rows, cols}]`（rows/cols 取 `grid_properties`） |
| `sheet_values(token, sheet_id)` | `GET /sheets/v2/spreadsheets/{token}/values/{range}`，`valueRenderOption=FormattedValue` | 异步生成器，按 5000 行一块 yield 行列表 |
| `bitable_tables(app_token)` | `GET /bitable/v1/apps/{token}/tables` | `[{table_id, name}]` |
| `bitable_fields(app_token, table_id)` | `GET /bitable/v1/apps/{token}/tables/{id}/fields` | `[{name, type}]` |
| `bitable_records(app_token, table_id)` | `GET /bitable/v1/apps/{token}/tables/{id}/records`，`page_size=500` | 异步生成器，逐页 yield |

分页生成器内含决策 6 的退避；`has_more` / `page_token` 协议与既有 `list_files` 一致。
生成器而非整表返回：20 万行不整体驻留内存两次（飞书 JSON 一份、DataFrame 一份已经够了）。

**单元测试**（`tests/test_feishu.py` 的假 transport 模式）：

- 多页 records（3 页）拼全且顺序对；中途 429 一次重试成功；重试耗尽透传 code/msg。
- `sheet_meta` / `bitable_tables` / `bitable_fields` 返回值只含元数据，假 payload 里埋
  `secret_cell`，断言响应 JSON 无泄漏。

### 第 2 步 — backend：物化与端点（`api/feishu_tools.py`）

**物化函数**（新文件 `bridgeflow/feishu_tabular.py`，保持 `feishu.py` 纯客户端）：

- `materialize_sheet(drive, token, sheet_id, header_row) -> tuple[str, bytes, list[dict]]`：
  读 meta 取行列数 → 按 `header_row` 切片分页 → CSV 字节。文件名为
  `feishu-sheet-{token 前 8 位}-{标签页名}.csv`（清洗/summary 里可见来源）。
  第三个返回值是 `dropped_columns`，sheet 不剔列、恒为空表，形状与 `materialize_bitable` 一致。
- `materialize_bitable(drive, token, table_id) -> tuple[str, bytes, list[dict]]`：
  取 fields → 逐字段归一化（FR-5）→ 字段名作 CSV 第 1 行 → 分页写记录。
  返回第三个值是 `dropped_columns` 清单。
- 两个物化函数内含决策 3 的行数上限检查。
- bitable 字段归一化表：

| 字段类型（`ui_type`） | 取值 |
| --- | --- |
| Text / Number / DateTime / SingleSelect / MultiSelect / Checkbox | 直接取标量（日期转 ISO 文本；多选取显示文本逗号连接） |
| User / Link / Attachment / Formula / CreatedTime 等 | 取飞书返回的显示文本 |
| 无任何可取表示 | 整列剔除，进 `dropped_columns` |

**端点**（全部 user 身份、浏览器点击即审批、不注册为模型工具，同 docs/30 契约）：

- `POST /tools/feishu-sheet-meta`：入参 `{token}`，出参 `[{sheet_id, title, rows, cols}]`。
- `POST /tools/feishu-bitable-meta`：入参 `{token}` 返 `{tables: [{table_id, name}]}`；
  带 `table_id` 返 `{table_id, fields: [{name, ui_type}]}`（两段式，见拍板 2）。
- `ImportFile` 扩展：`kind: Literal["file", "sheet", "bitable"] = "file"`，
  `sheet_id`、`table_id`、`header_row: int | None`。validator：
  `file` 不得带三个新字段；`sheet` 必须有 `sheet_id` + `header_row ≥ 1`；`bitable` 必须有 `table_id`。
  违反一律 422，不带默认值猜（字典缺席报「未配置」的同一条原则）。
- `_import_with` 按 `kind` 分流：`file` 走既有 `download`；`sheet`/`bitable` 走物化。
  分流后殊途同归进 `_import_batch`，`dropped_columns` 并入 summary（决策 5）。
  tenant 端点入口按决策 4 拒 `kind != "file"`。

**单元测试**：

- sheet 导入：假飞书出两页 values → 导入成正常批次，行数与假数据一致；
  `header_row=3` 时列名来自第 3 行。
- bitable 导入：含 User / Attachment / Formula / 不可表示四类字段，断言标量取值、
  复杂字段取显示文本、不可表示列剔除且 `dropped_columns` 有据。
- 超限：假数据行数 > 上限 → 413，报已读行数与上限；断言无批次落盘。
- 无泄漏：meta 与 import 两个端点的完整响应 JSON 断言无 `secret_cell`（单元格内容）。
- 权限：假 transport 对 meta 调用回 403 → 端点 403 透传飞书 code/msg（用户授权失败保持 403，
  与 `32` FR-7 一致；502 保留给后端/上游失败）。
- kind 校验六个组合（缺 sheet_id、缺 header_row、file 带 table_id 等）全部 422。

回归：`cd backend && ruff check src tests && pytest -q`。

### 第 3 步 — 插件（`plugins/src/client/feishu-picker.tsx`）

- `importableNode` 放开 `obj_type ∈ {sheet, bitable}`；Drive 列表侧放开 `type ∈ {sheet, bitable}`。
  其余类型维持灰显。
- 选中 sheet/bitable 节点 → 调对应 meta 端点 → 二级选择：
  sheet 选标签页 + 表头行号输入（复用本地导入 `sheetLayout`/`headerRow` 的既有 UI 模式与校验）；
  bitable 选数据表（字段名清单只读展示，帮助用户认表）。
- 提交扩展后的 `feishu-import-user` 请求体；413/502 报错原文上屏（含已读行数）。
- i18n：`ui.ts` 文案表加新键；`feishuPickHelp` / `feishuWikiHelp` 去掉「暂不支持导入」，
  改为「在线表格与多维表格以显示值导入，复杂字段取显示文本」。
- 批次详情页显示 `dropped_columns`（若有）。

**测试**：`plugins/tests/` 加 picker 二级选择的 smoke（假 meta 响应 → 选择 → 断言请求体
带 `kind`/`sheet_id`/`header_row`）；`pnpm build` 通过；既有 web-smoke 回归不红。

### 第 4 步 — 真实联调与记录

- 两账号互验：A 的表 B 无权 → meta 调用即 403 透传（验收 3）。
- 大表分页压测：实测行数 / 耗时 / 调用次数 / 是否撞频控，记 `docs/00`（验收 5）。
- 免费版配额结论（`32` 阻塞项 4）记 `docs/00`，撞限就如实记为限制，不绕过。
- `docs/README.md` 索引加本篇；`HANDOFF.md` 更新进度。

## 三、验收对照（`32` 第三节）

| `32` 验收 | 落在哪一步 | 判据 |
| --- | --- | --- |
| 1 在线表格选中→导入，行数一致 | 4 | 真实账号端到端 |
| 2 bitable 复杂字段按 FR-5，摘要有据 | 2（单测）+ 4 | `dropped_columns` 非空且准确 |
| 3 无权账号 403 | 2（假 403 单测）+ 4（真实两账号） | meta 调用即拒 |
| 4 返回值无单元格/记录内容 | 1、2 的 `secret_cell` 探针 | 断言无泄漏 |
| 5 行数-耗时-调用数记 `00` | 4 | 数字入库 |

## 四、拍板结果（2026-09-17）

1. 剔除列进 `BatchSummary.dropped_columns` 新字段（决策 5），不复用 quarantine 行级语义。
2. bitable meta 两段式：前端选中数据表后再二次调用取字段定义。
3. sheet range 单块 5000 行，联调按实测配额调。
4. 无 tenant 读在线表格场景：tenant 路径拒 `kind != file`（决策 4）成立。
