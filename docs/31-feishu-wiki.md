# 31 — 飞书知识库（wiki）读写（实施文档）

2026-09-17 定范围：按当前登录飞书角色的权限，**读**我有权的知识库（个人文档库／团队知识库）中的文件节点，
并支持**上传本地文件／报告**进知识库指定位置。
本期明确不做：wiki 内在线表格（sheet）与多维表格（bitable）节点的解析导入、docx 正文抽取、
wiki 权限镜像、知识库的创建与设置管理。

前置：[`30-feishu-user-docs.md`](30-feishu-user-docs.md) 的 user token 管线（加密 Cookie、
`/feishu/user-token`、用户态端点形态）已全部就位，本篇只做增量，不重复。
实测数字进 [`00`](00-status.md)，外部输入清单进 [`27`](27-external-inputs.md)。

## 范围与理由

docs/30 上线后的实测结论：`drive/v1/files` 够不着 wiki — 用户的测试文档建在「我的文档库」
（个人知识库）里，根目录列表为空。而分部门知识库（生产／物资／财务／市场各一库）正是
业务方的真实组织方式：部门文件归部门库，与 `access-control.yaml` 的部门模型天然对齐。

本期把 Sources 面板的浏览范围从「我的空间」扩展到「我有权的全部知识库」，
导入与写回动作复用既有管线。

## 飞书 wiki 的两级寻址（核心机制）

```
wiki space（知识库，space_id）
  └─ node（wiki_token，树形，父子分页）
       └─ obj_token + obj_type（真实文件身份：file / docx / sheet / bitable）
```

- `wiki_token` 只用于**浏览**（列子节点）与**挂载**（写回时指定父节点）；
- `obj_token` 才是文件本体，**下载直接走 `drive/v1/files/{obj_token}/download`** —
  与 docs/30 的导入路径同一接口，`obj_type=file` 时无需任何转换；
- 界面与后端都必须同时携带两个 token 的含义，禁止混用（见关键决策 1）。

## 架构

```
浏览器 ──► portal /feishu/user-token          （复用，零改动）
   │
   ├──► backend /tools/feishu-wiki-spaces      （列我有权的知识库）
   ├──► backend /tools/feishu-wiki-list        （列节点，懒加载分页）
   ├──► backend /tools/feishu-import-user      （复用：file_token 传 obj_token）
   ├──► backend /tools/feishu-wiki-upload      （本地文件 → 知识库节点）
   └──► backend /tools/feishu-upload-user      （报告写回：folder_token 之外
                                                 接受 wiki 目标，见决策 4）
```

- **portal**：零改动。wiki scope 加进飞书应用后，重登签发的 user token 自动带权。
- **backend**：`FeishuDrive` 增 `list_wiki_spaces()` / `list_wiki_nodes()` / `move_to_wiki()`；
  三个新端点（spaces、list、wiki-upload）从头取 `X-Feishu-User-Token`，与 docs/30 三端点同形态：
  不缓存、不落盘、不写日志、不注册为模型工具。
- **插件**：Sources 面板「从飞书选择」顶层变为两入口：**我的空间**（现有 Browser 原样）与
  **知识库**（空间列表 → 节点树浏览器，面包屑与分页组件复用）。上传入口加「到知识库」选项。

## 关键决策

### 1. wiki_token 与 obj_token 双轨，不互相猜

浏览状态记 `wiki_token` 链（面包屑），选中导入时提交 `obj_token`。
后端 `/tools/feishu-import-user` 不改签名 — 它收到的 file_token 本来就是 opaque 字符串，
飞书下载接口对 obj_token 直接放行。**代价**：返回值里必须带 `obj_type`，
UI 只允许 `obj_type=file`（且后缀 csv/xlsx）的节点可导入，其余灰显并说明，不静默跳过。

### 2. 知识库写回 = 先落 Drive 再挂载，不直写 wiki

飞书没有「直接上传文件进知识库」的接口。标准两步：

1. `drive/v1/files/upload_all` 把文件传进用户我的空间（临时落点，根目录）；
2. `POST /wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki` 把它挂到指定父节点下
   （`obj_type=file`，指定 `parent_wiki_token`）。

文件从我的空间「移动」进 wiki，不留副本。两步任一失败：第一步成功第二步失败时
文件留在我的空间根目录 — 可接受（用户自己的空间，看得见、可手动处理），
错误信息里明说文件已在我的空间，不做自动清理（清理动作本身也可能失败，徒增状态）。

### 3. 报告写回复用同一条路

`feishu-upload-user` 现为「报告 → Drive 文件夹」。本期扩展为可选 wiki 目标：
请求体加可选 `wiki_space_id` + `parent_wiki_token`，存在时走「传 Drive → 挂载」两步，
不存在时行为不变。一个端点两种落点，不开第四个上传端点。

### 4. 审批语义与权限分层不变

浏览器点击 + 门户会话 + user token = 批准（docs/30 已拍板），新端点同样不注册为模型工具、
不走 `consume_approval`。文件级权限飞书 enforce（非库成员列不出、无写权限挂载被拒），
部门批次级 `access-control.yaml` enforce，两层照旧互不替代。
wiki 返回值照旧只有元数据（节点 token、名称、obj_type、是否有子节点），分页封顶。

### 5. 知识库列表不做缓存，不做全盘扫描

spaces 与 nodes 都是实时调用、按页取。知识库可能很大（企业级库上万节点），
只浏览不扫描；UI 懒加载，进一层取一层。与 docs/30「不递归遍历整棵目录树」同一原则。

## 飞书 API 对应表（用户身份，新增）

| 动作 | 接口 | 所需用户态 scope |
| --- | --- | --- |
| 列我有权的知识库 | `GET /open-apis/wiki/v2/spaces` | `wiki:wiki:readonly` |
| 列库内子节点 | `GET /open-apis/wiki/v2/spaces/{space_id}/nodes?parent_node_token=…&page_token=…` | 同上 |
| 下载文件本体 | `GET /open-apis/drive/v1/files/{obj_token}/download`（复用） | `drive:drive:readonly` |
| 临时落点上传 | `POST /open-apis/drive/v1/files/upload_all`（复用） | `drive:drive` |
| 挂载进知识库 | `POST /open-apis/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki` | `wiki:wiki` |

scope 准确名称与免费版可用性**待实测**，同 docs/30 的纪律：被拒则原样记录 code 与 msg 进
[`00`](00-status.md)，不绕过。

## 实施步骤

按依赖排序，每步独立可验。沿用当前分支 `feature/feishu-user-docs-20260916`，单独 commit。

**第 1 步 — 飞书应用配置（外部依赖，先行）**
管理员加用户态 `wiki:wiki:readonly` 与 `wiki:wiki` → **创建版本并发布** → 全员重新登录。
不发布不生效（docs/30 实测踩过：scope 加了没发版，99991672）。

**第 2 步 — backend：wiki 客户端方法与新端点**
- `FeishuDrive`：`list_wiki_spaces(page_token)`、`list_wiki_nodes(space_id, parent, page_token)`
  （返回元数据 + obj_type + has_child）、`move_to_wiki(space_id, parent_wiki_token, obj_token)`；
- `POST /tools/feishu-wiki-spaces`、`POST /tools/feishu-wiki-list`：缺头 401，分页封顶，只回元数据；
- `POST /tools/feishu-wiki-upload`：multipart 本地文件 → upload_all → move_to_wiki 两步，
  返回 {wiki_token, name}；`_check_upload_scope` 不适用（目标不是部门批次），但保留
  user token 门与日志打码；
- `feishu-upload-user` 扩展可选 wiki 目标（决策 4）；
- 测试：transport 注入假飞书，验 401／403 透传、两步调用顺序、第二步失败时的错误语义、
  返回值无单元格内容、token 不进日志。

**第 3 步 — 插件：知识库浏览与上传**
- `feishu-picker.tsx`：`WikiBrowser`（空间列表 → 节点树，复用面包屑/分页/灰显逻辑）；
  import 流程选中节点提交 `obj_token`，走现有 `feishu-import-user`；
- 上传对话框加「到知识库」模式：选库 → 选父节点 → 本地文件 input 或当前报告；
- i18n 标签补齐；路由白名单加 `feishu-wiki-(spaces|list|upload)`，`x-feishu-user-token` 转发照旧；
- Playwright smoke 用假 portal + 假 backend 覆盖浏览与两步上传。

**第 4 步 — 真实联调**
真实凭据：登录 → 列出知识库（至少含个人文档库 + 一个团队库）→ 从 wiki 导入 xlsx 成批次 →
上传报告进 wiki 指定节点 → 飞书界面肉眼确认文件在位。
两个权限不同的账号互验：B 非成员的库不出现在 B 的 spaces 列表。结果与耗时记 [`00`](00-status.md)。

## 明确不做（本期）

- wiki 内在线表格／多维表格节点解析导入（与 docs/30 同一条边界）；
- docx 节点正文抽取；
- 知识库创建、成员管理、设置变更；
- wiki 权限镜像到 `access-control.yaml`；
- 节点移动、重命名、删除（只增不改）；
- 全盘扫描与搜索（只浏览）。

## 需要人工操作与输入（阻塞项）

| # | 事项 | 谁 | 说明 |
| --- | --- | --- | --- |
| 1 | 应用加用户态 `wiki:wiki:readonly`、`wiki:wiki` 并**发布版本** | 飞书管理员 | 不加则全部 wiki 调用 99991672 |
| 2 | 全员重新登录 | 所有用户 | 新 scope 要重新授权 |
| 3 | 确认免费版 wiki API 额度 | 飞书管理员 | 被拒则记录，不绕过 |
| 4 | 测试用团队知识库 + 非成员对照账号 | 团队 | 验「读取范围不超出操作者权限」 |
| 5 | 确认目标库允许成员添加节点 | 库管理员 | 写回被拒的第一嫌疑 |

## 风险

- **两步写入的中间态**：upload 成功 move 失败 → 文件留在我的空间根目录。已定为可接受，
  错误信息必须说清（决策 2），不许静默。
- **库的写权限设置**：知识库可设「仅管理员可添加内容」，user token 也会被拒 — 属预期行为，
  报错透传，提示联系库管理员。
- **节点树深度**：懒加载下深层路径要点多次，UI 体验以面包屑补救，不做搜索（本期）。
- **免费版额度**：wiki nodes 分页每页封顶 50，大库首屏可能多页，实测后如需调页大小再议。
