# 30 — 飞书用户态云文档读写（实施文档）

2026-09-16 定范围：按当前登录飞书角色的权限，读／写飞书云文档中的**普通文件**（xlsx、csv 等 Drive 附件）。
本期明确不做：docx 正文抽取、飞书 ACL 镜像。
（在线表格与多维表格的读取后由 [`32`](32-feishu-sheets-bitable-read.md) 立项，按同一 user token 管线覆盖。）

这篇是实施计划，先于代码写定。实测数字进 [`00`](00-status.md)，外部输入清单进 [`27`](27-external-inputs.md)。

## 范围与理由

现状的两个洞（背景见 [`27-login-portal.md`](27-login-portal.md) 与 [`24`](24-meeting-2026-09-13.md)）：

1. 导入飞书文件要用户手抄 file_token 贴进界面；
2. tenant_access_token 只能看到共享给应用的文件夹，用户自己有权但未共享给应用的文件够不着。

本期把 Drive 读写从应用身份（tenant token）扩展到用户身份（user token）：
用户在界面里浏览自己有权的文件、选作来源导入；结果写回时落到用户指定的文件夹。
飞书侧按用户权限过滤与放行，我们不复制它的 ACL —「能看什么」由飞书 enforce，
「能看哪些部门批次」仍由 `access-control.yaml` enforce，两层互不替代。

这落实了 [`24`](24-meeting-2026-09-13.md) 留下的远景：「Agent 的读取范围不超出操作者权限」（rubric 第 5 项 least-privilege）。
不是重建数据平台，仍是快捷调用。

## 架构

```
浏览器 ──► portal /feishu/user-token（会话 Cookie + 加密存储的 refresh token）
   │            │
   │            ▼ 需要时用 refresh token 向飞书换新 access token
   │◄─── 当前用户的 user_access_token（飞书原生 TTL，约 2 小时）
   │
   ├──► backend /tools/feishu-list     （X-Feishu-User-Token 头，只回元数据）
   └──► backend /tools/feishu-import-user / feishu-upload-user
                                       （同头传入，用完即弃）
```

- **门户（`portal/`）**：OAuth 换码后保留 refresh token，加密存进会话 Cookie；
  新增 `/feishu/user-token` 端点，校验会话后用 refresh token 换当前 user access token 返回。
  门户仍无数据库。
- **后端（`backend/`）**：`FeishuDrive` 增加 user token 模式；新端点从头取 token，
  每次请求独立，不缓存、不落盘、不写日志。
- **审批语义**：三个用户态端点**不注册为模型工具**，只由浏览器点击触发。
  人的点击 + 门户会话 + user token 本身就是批准（与现有 `/batches` 浏览器上传同级），
  因此不走 `consume_approval` — 那套收据只有模型工具链能产出。
  既有 tenant token 的 `feishu-import` / `feishu-upload-report` 是模型工具，审批闸门照旧，不动。
- **插件（dsh web）**：Sources 面板加「从飞书选择」：先向 portal 换 user token，
  再调 backend 列目录；选中文件后走既有导入流程。浏览器只见到自己本就有权的文件的元数据。

## 关键决策

### 1. user token 存哪：加密进现有会话 Cookie，不开服务端存储

门户架构是无状态签名 Cookie（docs/27-login-portal）。但现有 `seal()` 是 HMAC 签名、
**不加密**（`portal/src/portal_app/tokens.py`）：payload 只是 base64，浏览器可读。
飞书 refresh token 明文放 Cookie 不可接受。

做法：给 token 字段单独加一层 AEAD 加密（XChaCha20-Poly1305，经 PyNaCl 调 libsodium；
密钥由 `PORTAL_SESSION_SECRET` 加域分隔符派生，不新增环境变量），
Cookie 里其余身份字段保持签名明文。轮换密钥 = 全员重新登录，与现有会话失效语义一致。
不开 Redis、不加数据库 — 那会同时破坏「门户无状态」和部署简单性。

### 2. user token 经浏览器中转，是用户自己的令牌

user access token 从 portal 到浏览器再到 backend，走 TLS + 内存持有，不写 localStorage。
这是 SPA 标准形态：令牌本来就是发给这个用户的，他能从飞书官方客户端拿到同样的东西。
风险面不在传输而在落地：禁止写日志（backend 日志中间件要对该头打码）、
禁止进模型上下文（见下）、禁止持久化。

### 3. 模型永远见不到 user token 与原始行

模型路径继续走主机共享令牌（docs/27-login-portal「工具/模型路径不受身份层影响」）。
user token 只存在于浏览器数据面的请求头，不进任何工具参数、不进返回值、不进轨迹。
`feishu-list` 返回值只有元数据：文件 token、名称、类型、大小、修改时间 — 
沿用「原始数据行绝不进上下文」第三层：这个列表在 20 万行文件库里的体积有界（分页 + 每页封顶）。

### 4. 权限校验责任分清，不重复 enforce

- 文件级：飞书按 user token 放行或拒绝（用户无权的文件，列不出来、下载 403）。
- 部门批次级：导入后 `access-control.yaml` 照旧过滤 — 用户拿自己有权的文件导入了自己无权看的部门，
  批次对他 fail-closed。两层各管各的，不互相猜。

### 5. 写回也走用户身份

`feishu-upload-user`：用户指定目标文件夹 token（由浏览界面从列表里选），
用 user token 上传，飞书侧按用户对该文件夹的写权限放行。
现有 tenant token 的 `feishu-upload-report` 保留不动 — 两条路并存，
tenant 路径供无登录的旧部署形态使用。

## 飞书 API 对应表（用户身份）

| 动作 | 接口 | 所需用户态 scope |
| --- | --- | --- |
| 列文件夹内容 | `GET /open-apis/drive/v1/files?folder_token=…` | `drive:drive:readonly` |
| 我的空间根目录 | 同上，folder_token 为空 | 同上 |
| 下载文件 | `GET /open-apis/drive/v1/files/{token}/download` | 同上 |
| 上传文件 | `POST /open-apis/drive/v1/files/upload_all` | `drive:drive` |
| 刷新令牌 | `POST /open-apis/authen/v1/oidc/refresh_access_token` | `offline_access` |

scope 的准确名称与免费版可用性**待实测**：管理员配置后跑 `scripts/feishu_live_check.py` 的 user-token 分支验证。

## 实施步骤

按依赖排序，每步独立可验。分支 → PR → merge，不直接提交 main。

**第 1 步 — 飞书应用配置（外部依赖，先行）**
管理员给自建应用加上表的用户态权限并重新发布版本；确认免费版接口额度。
详见下节「需要人工操作与输入」。

**第 2 步 — portal：持有与换发 user token**
- OAuth `fetch_user` 保留 refresh token，AEAD 加密后并入会话 Cookie；
- 新增 `GET /feishu/user-token`：校验会话 → 必要时刷新 → 返回 access token 与剩余 TTL；
- 刷新失败 → 401，前端引导重新登录，不静默续期；
- 测试：无凭据 503「未配置」；篡改 Cookie 401；refresh token 不出现在任何响应体与日志。

**第 3 步 — backend：用户态 Drive 客户端与端点**
- `FeishuDrive` 支持以 user token 构造（与 tenant 模式并列，`from_user_token`）；
- `POST /tools/feishu-list`：列指定文件夹，分页，每页封顶，只回元数据；
- `POST /tools/feishu-import-user`：下载选中文件 → 复用 `_import_batch`（浏览器触发，不走模型审批，见「审批语义」）；
- `POST /tools/feishu-upload-user`：上传报告到指定文件夹（同上）；
- 三个端点从头 `X-Feishu-User-Token` 取令牌，缺头 401；日志对该头打码；
- 测试：transport 注入假飞书，验 401／403 透传、返回值无单元格内容、token 不进日志。

**第 4 步 — 插件：Sources 面板「从飞书选择」**
- 左栏 Sources 加入口：换 token → 文件夹浏览（面包屑 + 分页）→ 按部门选文件 → 导入；
- 导入后走既有批次检查与映射流程，界面不变；
- 写回入口放在报告区，选目标文件夹后上传；
- Playwright smoke 用假 portal + 假 backend 覆盖浏览与导入路径。

**第 5 步 — 真实联调**
真实凭据下跑通：登录 → 列出文件 → 导入成批次 → 写回报告。
两个权限不同的测试账号互验：A 能看到、B 看不到的文件，B 的列表与下载都被飞书拒绝。
结果与耗时记 [`00`](00-status.md)。

## 明确不做（本期）

- 在线表格、多维表格读取已单独立项（[`32`](32-feishu-sheets-bitable-read.md)），不再是本条边界；
- docx 正文抽取（报价路径将来另议）；
- 飞书文档 ACL 镜像（「能看哪个文件」永远由飞书 enforce，不复制）；
- token 服务端持久化、踢人黑名单；
- 递归遍历整棵目录树（只浏览，不扫描）。

注：成员关系层面的飞书化是另一件事，已由 #204 落地（只读解析知识库成员决定角色），
见 [`27`](27-login-portal.md)；本条边界（文件级 ACL 不镜像）不变。

## 需要人工操作与输入（阻塞项）

| # | 事项 | 谁 | 说明 |
| --- | --- | --- | --- |
| 1 | 自建应用加用户态 scope 并**重新发布版本** | 飞书管理员 | 上表五个接口对应的权限；不加则 user token 调 Drive 全部被拒 |
| 2 | 确认免费版接口额度 | 飞书管理员 | user token 的 Drive 接口频率与配额，不够则记为限制 |
| 3 | 两个权限不同的测试账号 | 团队 | 验证「读取范围不超出操作者权限」需要对照 |
| 4 | 重新登录一次 | 所有用户 | 新 scope 需要重新授权，旧会话没有 refresh token |

凭据交付纪律不变：App ID / Secret 只进启动 shell 环境变量，见 [`27`](27-external-inputs.md)。

## 风险

- **Cookie 体积**：加密 refresh token 后 Cookie 增大，仍在数 KB 内，无虞；但不再适合塞更多东西。
- **refresh token 失效语义**：飞书侧用户改密、管理员撤销授权都会让它失效，表现是 401 → 重新登录。这是特性不是缺陷。
- **免费版额度**：未实测。若 Drive 接口被拒，原样记录 code 与 msg 进 [`00`](00-status.md)，不绕过。
- **录制主线冲突**：HANDOFF 的 P0 是收口录制。**已拍板（2026-09-16）：本支线排在录制主线之后动**，两条线的证据不混用。
