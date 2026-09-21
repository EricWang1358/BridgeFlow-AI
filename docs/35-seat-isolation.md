# 35 · 按人隔离的席位化实施（7 席位静态方案）

状态：已实施（2026-09-20，本机验证；实例侧部署见 §5 M3/M5 与 [`22`](22-lightsail-deploy.md) 席位小节）。
M0 spike 数字在 [`00`](00-status.md)；门户行为有测试（`portal/tests/test_portal.py` 席位一节，39 项全绿）。
前置讨论：#229（控制台门禁）、#231（读取归属）、#230（按人隔离评估——本文取代其「评估」，直接给落地）、
[`34`](34-web-refactor-plan.md)（Web 化收口与拍板）。

## 0 · 已拍板的前提（本文不再讨论）

| 拍板 | 出处 |
| --- | --- |
| 一人一个**常驻** dsh 实例，静态供给，不做按需拉起/空闲回收 | 本轮讨论，2026-09-20 |
| 席位数 7；服务器 4GB（Lightsail，Ubuntu 24.04） | 本轮讨论 |
| **先到先得（2026-09-20 追加拍板）**：席位是固定容量的通用实例（seat-1…seat-7），配置文件里**不出现任何人名**；有 `console_access` 的登录者第一个进入即认领、认领即长期绑定。释放是运维动作（`provision_seat.sh --release`） | 本轮讨论 |
| 认领状态不做规范 ID 间接层；飞书/Lark 是两个工作区，同一人跨平台=两个主体=两次认领 | 「飞书/Lark 是两个工作区」拍板 |
| `access-control.yaml` 仍是角色/操作唯一事实来源；**能否认领席位由 `console_access` 决定**，先到先得只在获授权者之间进行 | 沿用 #229 |
| 不做：跨实例审批总线、会话 DB 审计层（后续叠加）、多节点 | docs/34 拍板延续 |

## 1 · 目标与非目标

**目标**：7 个席位，每人一个物理隔离的工作区（自己的 `DSH_HOME`、自己的 dsh web 进程、
自己的子域名），按门户凭证正确路由与拒止；重启不丢历史；内存有硬围栏，OOM 只死一个席位。

**非目标**：弹性伸缩（触发条件：席位 >8 或实测闲时 RSS >300MB，届时先升配 8GB 再谈）、
跨席位会话可见性、员工侧轻量问答端点（角色分层的后续项）、Lark 双主体合并。

## 2 · 现状事实（实施的接缝）

1. **`scripts/start_web.py` 同时监管两个子进程**：backend uvicorn（127.0.0.1:8000）+
   dsh web（`--port` 指定，默认 3080）。它由 `deploy/bridgeflow.service` 经 `run.sh` 拉起，
   是今天唯一的生产单元。**直接复制 7 份会起 7 个 backend 端口冲突——运行时必须先拆分。**
2. launch token 已经按 `DSH_HOME` 落盘：`start_web.py` 把 dsh web 启动行里的 token 写进
   `$DSH_HOME/.web-launch-token`，门户 `PORTAL_DSH_TOKEN_FILE` 指向同一文件（start_web.py
   顶部注释）。**per-seat token 文件机制现成，缺的只是门户按注册表取对应那份。**
3. 门户 `/enter`（portal_app/main.py:284）现在从**一份全局** token 文件读值，交接给**唯一**
   的 dsh web；`/verify` 是 Caddy `forward_auth` 的目标（#229 门禁，`PORTAL_CONSOLE_CHECK_URL`）。
4. Caddy 模板按 `__DOMAIN__` 渲染主站 + `portal.__DOMAIN__` 两块；`reverse_proxy` 默认保留
   原始 Host——`/verify` 可以读到 `alice.console.example.com`，这是席位绑定校验的载体。
5. `DSH_HOME` 由 `env.sh` 导出（gitignored），内容含 profiles/credentials/sessions；
   一个全新 home 的初始化清单**未验证**——进 §5 M0 spike，不猜。
6. 内存：全仓无实测数字。规划假设：单实例闲时 ~250MB、研判峰值 ~400MB（subagent 为同进程
   子会话，docs/13），backend 闲 ~350MB + 摄取尖峰至 ~1GB（#228 的内存放大），OS 地板 ~850MB。

## 3 · 目标架构

```text
浏览器 ── https://<seat>.console.<domain>          （7 个显式子域名，不申请泛域名证书）
            │
          Caddy（每席位一块：forward_auth → 门户 /verify；reverse_proxy → 127.0.0.1:310x）
            │
          /verify：① 会话有效 ② console_access ③ Host 席位的认领人 == 登录人 sub   ← 新增③
            │
   ┌────────┴──────────────────────────────────────────┐
   │ bridgeflow.service（改后端专用）: uvicorn :8000    │  全局唯一 backend
   │ bridgeflow-portal.service: uvicorn :8100           │
   │ bridgeflow-dsh@<seat>.service × 7:                 │  systemd 模板单元
   │     DSH_HOME=data/homes/<seat>/   dsh web :310x    │  Slice=bridgeflow-dsh.slice
   └───────────────────────────────────────────────────┘
```

**两份席位文件，纪律不同**：

- **`data/mappings/seats.yaml` = 容量声明**（随 git 走 PR，与 access-control.yaml 同纪律）。
  只写席位本身，**不出现任何人名**：
  ```yaml
  seats:
    - {name: seat-1, port: 3101, home: "<repo>/data/homes/seat-1"}
    # … seat-2 … seat-7
  ```
- **`data/seats-assigned.json` = 认领状态**（untracked 实例状态，`git reset --hard` 天然不碰，
  deploy 也不需要任何保护逻辑）。门户是唯一写入方，每次认领原子重写：
  ```json
  {"oun_xxx…": "seat-1"}
  ```

**认领语义**：`/enter` 时按请求重读认领文件——已有认领 → 复用（会话历史跟着席位走）；
无认领且门禁通过 → 认领第一个空位；满员 → 403「席位已满」。门禁（#229 `console_access`）
在**首次认领前**检查：无授权者不消耗容量。运维释放（`--release <sub>`：除名 + home 归档 +
新 home + 重启单元）在下一个请求即生效，无需重启门户。

**校验链**（谁也绕不过去的三层）：进子域名 → Caddy forward_auth 问 `/verify` →
门户查会话 + console_access + 该席位认领人 == 登录人（未认领的席位对所有人 403）；直连
他人端口不可达（dsh web 只绑 127.0.0.1）；拿到子域名但无对方 launch token/session cookie →
dsh 自身凭据栅栏拒绝。

**这条链必须对 WebSocket 同样成立，而且是「放行」而不是「拦掉」。** 控制台有一半跑在
`wss://<seat>.console.<domain>/api/remote.mux` 上：dsh 所有 Typert Remote **流**共用这一条
socket，工作区投影只订 `workspace.follow`、没有 unary 回退。`forward_auth` 会把原请求的
`Connection`/`Upgrade` 头一并带进 `/verify` 子请求，装了 `websockets` 的 uvicorn 于是把它当
握手处理、匹配不到 ws 路由回 403，整条升级被认证层吃掉——席位打开后没有工作区、
`watchNavigation` 静默不建会话、输入框写着「choose a workspace to start」，而目录选择器
按企业策略禁用，连「添加」都没有（2026-09-21 线上现象）。两侧各堵一次：Caddy 每个站点块
`header_up -Connection` / `-Upgrade`（[`22`](22-lightsail-deploy.md) §7），门户单元
`--ws none`（§9b）。不要改成「WS 跳过 forward_auth」——那等于让 WS 不过席位绑定校验，
是本节校验链的倒退。preflight 逐席位查判别式：无 cookie 的升级握手 **401 = 好**（dsh 在拒，
说明穿过了认证层），**403 = 坏**（forward_auth 在拒，根本没到 dsh）。

**内存预算（4GB）**：地板 ~850MB + backend ~350MB（尖峰预留 1.2GB，靠 `MemoryMax` 兜住）
+ 7 席位 × 250MB ≈ 1.75GB 常驻；并发研判 ≤3 个的峰值 ≈ 2.2GB；2GB swap 吸收闲置页。
**超线即触发 §0 的升配条件，不硬撑。**

## 4 · 改动清单（逐文件）

| # | 文件 | 改动 |
| --- | --- | --- |
| 1 | `scripts/start_web.py` | 加 `--backend-only` / `--web-only` 两模式。默认行为不变（开发机单进程流照旧）；生产两个单元分别用两个模式 |
| 2 | `deploy/bridgeflow.service` | `ExecStart` 改 `--backend-only`；加 `MemoryHigh=1G`、`MemoryMax=1.3G`（摄取尖峰伤不到席位） |
| 3 | `deploy/bridgeflow-dsh@.service`（新增） | 模板单元：`EnvironmentFile=data/homes/%i/seat.env`（`DSH_SEAT_PORT`），`ExecStart=bash -c 'source env.sh && export DSH_HOME=<repo>/data/homes/%i && python scripts/start_web.py --web-only --host 127.0.0.1 --port $DSH_SEAT_PORT --trusted-host %i.console.<domain>'`；`Slice=bridgeflow-dsh.slice`、`MemoryMax=512M`、`Restart=on-failure` |
| 4 | `deploy/bridgeflow-dsh.slice`（新增） | `MemoryHigh=1.6G`、`MemoryMax=2.0G` |
| 5 | `data/mappings/seats.yaml`（新增） | §3 的容量声明（无任何个人信息）；`--init N` 生成，PR 只 review 容量 |
| 6 | `portal/src/portal_app/seats.py`（新增） | `Seats`（容量加载与校验）+ `Assignments`（认领状态：读/幂等认领/原子写） |
| 7 | `portal/src/portal_app/main.py` | ① `/enter`：已有认领→复用；无认领→门禁（#229）通过后认领第一个空位，满员 403「席位已满」；认领文件按请求重读（运维释放即时生效）。② `/verify`：席位绑定校验——该席位的认领人 == 登录人，未认领席位对所有人 403。③ `/health` 上报 `seats`/`seats_assigned`。无 `PORTAL_SEATS_PATH` 时行为与从前完全一致 |
| 8 | `portal/` 配置 | 新增 `PORTAL_SEATS_PATH`、`PORTAL_SEAT_BASE_DOMAIN`、`PORTAL_SEAT_ASSIGNMENTS`（三项一起生效，缺认领路径 fail-fast）；`PORTAL_COOKIE_DOMAIN` 必须是父域（`.example.com`），覆盖席位子域名 |
| 9 | `deploy/bootstrap.sh` | 渲染 Caddy 时按 seats.yaml 生成每席位站点块（显式子域名，逐个自动 HTTPS）；新增 2GB swapfile + `vm.swappiness=10` 持久化 |
| 10 | `scripts/provision_seat.sh`（新增） | `--init N`：生成容量文件 + 各席位 home/seat.env + 单元 + Caddy + env.sh 三项导出（有认领时禁止缩容）；`--release <sub>`：除名 + home 归档（客户资产，#232 保留纪律）+ 新 home + 重启单元；`--status`：席位/认领/单元一览 |
| 11 | `deploy/preflight.sh` | 席位模式开启时新增检查：容量可解析、认领文件与舰队一致（指向存在、不重复、不超容）、门户上报数与两份文件一致、席位数 ≤7（MemoryMax 是**封顶不是预留**，封顶之和可超 slice，设计如此）、slice 围栏生效、每席位单元 active / token 非空 / 端口在听 / 子域名无 cookie 访问 401 / 无 cookie 的 WebSocket 升级握手也到得了 dsh（401 而不是 forward_auth 的 403，§3）、swap ≥2G。无注册表时全部静默跳过 |
| 12 | `portal/tests/` | 认领/复用/满员/绑定/未认领 403/门禁拦截不耗容量/运维释放即时生效/坏配置 fail-fast（12 项） |
| 13 | `deploy/deploy.sh` | 部署后顺带重启全部席位单元（否则席位继续跑旧插件代码）；web 活性按部署形态分流（`--backend-only` 查席位单元，无席位则跳过并告警）；认领文件 untracked 天然幸存，无需暂存逻辑 |
| 14 | 文档 | 本文档 + [`00`](00-status.md)（spike 数字）、[`22`](22-lightsail-deploy.md)（单元/Caddy/swap 小节）、[`27`](27-login-portal.md)（/enter 认领、/verify 第三层校验）、[`34`](34-web-refactor-plan.md)（#230 条目指向本文）、`../HANDOFF.md` 同步 |

不动的：`access-control.yaml` 语义、backend 全部 API、`plugins/src/actor.ts`（#231 一人一
进程后归属自动无歧义，零改动）、审批面（原生审批留在本人控制台，跨人审批走 backend 队列）。

## 5 · 实施里程碑（顺序执行，M0 是门）

| 里程碑 | 内容 | 估时 | 退出条件 |
| --- | --- | --- | --- |
| **M0 spike（门，不可跳过）** | 在目标机起 1–2 个 `--web-only` 实例：测闲时 RSS、研判峰值 RSS、冷启动耗时；**定稿全新 `DSH_HOME` 的初始化清单**（模板复制 vs 首启自建，逐项列文件） | 0.5–1d | 数字落 [`00`](00-status.md)；闲时 RSS ≤300MB 过门，>300MB 停下走升配拍板 |
| M1 运行时拆分 | 改动 #1–#4：两模式 + 三份 systemd 文件；开发机验证默认流不回归 | 0.5–1d | 同机 backend×1 + web×2 共存，`systemctl show` 围栏生效 |
| M2 门户路由与校验 | 改动 #5–#7、#11：注册表、/enter 席位路由、/verify 绑定校验 + 单测 | 1d | 单测绿；本地 hosts 模拟两席位，A 的浏览器到 B 子域名收 403 |
| M3 Caddy 与端到端 | 改动 #8：按注册表渲染；实例上配 DNS、开两个真席位端到端 | 0.5–1d | 真浏览器×2 各进各的；直连他人端口不可达；重启席位历史在 |
| M4 加固与预检 | 改动 #10 + swap（#8 内）：preflight 全绿 | 0.5d | preflight 在实例通过 |
| M5 全量开通与演练 | 7 席位开通（#9）；双人排练：会话互不可见、`x-bridgeflow-user` 归属正确、`journalctl -u bridgeflow-dsh@x` 可查 | 0.5–1d | 验收清单 §6 全勾；文档 #12 同步 |

总计约 3.5–5 天。M0 失败的回退：升配 8GB 后重跑 M0；仍失败才重开方案讨论。

## 6 · 验收清单

1. 7 席位在线；两个已授权者先后进入，各认领各的席位、只被送进自己的子域名；手输他人
   或未认领的子域名收 403（/verify 绑定校验）。
2. 任意两席位：会话、笔记本、待审批互不可见（物理隔离，非过滤）。
3. 席位单元 `systemctl restart` 后历史会话仍在（home 在盘上）；再次进入复用同一席位。
4. 第 8 个获授权者进入收 403「席位已满」，不消耗任何容量；`--release` 后下一个进入者
   认领该席位，且得到的是全新空 home。
5. 归属：单席位内模型触发的读取带正确的 `x-bridgeflow-user`（#231 无歧义）。
6. `bridgeflow-dsh.slice` 2.0G、单元 512M、backend 1.3G 围栏在 `systemctl show` 可见；swap 2G 激活。
7. `deploy/preflight.sh` 在实例全绿；spike 数字在 [`00`](00-status.md)。
8. 开发机 `start_web.py` 默认单进程流行为不变（回归项）。
9. 对外口径更新：「控制台按人隔离、席位先到先得」可以讲；「席位成本封顶」仍不可讲
   （静态方案无弹性）。

## 7 · 风险与对策

| 风险 | 对策 |
| --- | --- |
| 实测 RSS 超规划（>300MB 闲时） | M0 是门；先垂直升配 8GB，不硬塞 4GB |
| Caddy `forward_auth` 未按预期透传 Host | M3 首项验证；不行改用 `X-Forwarded-Host`（Caddy 显式 `header_up`），属小改 |
| 全新 `DSH_HOME` 初始化踩坑 | M0 已定稿：零仓库内容、dsh 首启自建（[`00`](00-status.md)） |
| 先到先得被「占坑」：早到的低频用户长期占席位 | 接受（拍板）；需要腾位时 `--release` 是显式运维动作，home 归档不丢数据 |
| 月尖峰：多单上传 + 多人研判叠加 | backend `MemoryMax` 优先保 backend；并发重研判 ≤3 写进运维手册；swap 兜闲置页 |
| 7 席位 ×512M 触 slice 上限被杀 | 这就是设计：OOM 只死一个席位，preflight 提示扩容/升配 |
| `env.sh` 内 `DSH_HOME` 导出与席位覆盖打架 | 席位单元 `source env.sh` 后**再** `export DSH_HOME=...` 覆盖，写进模板注释与测试 |
| 认领文件被手工改坏 | 逐请求重读时 fail-fast（明确报错，不猜测）；preflight 有一致性检查 |

## 8 · 运维手册（上线后常态操作）

- **建舰队**（一次性）：`BRIDGEFLOW_DOMAIN=<domain> scripts/provision_seat.sh --init 7` →
  每席位一条 DNS A 记录 → 获授权者自然先到先得。有认领时禁止缩容，先 `--release`。
- **看状态**：`scripts/provision_seat.sh --status`（舰队、认领、单元）；门户 `/health` 的
  `seats` / `seats_assigned` 同口径。
- **腾出席位**：`scripts/provision_seat.sh --release <union_id>`——除名、home 归档进
  `_archive/`（客户资产，#232 保留纪律）、新 home、重启单元；原主人下一次请求即被
  /verify 拒绝，下一个进入者认领到全新席位。
- **升级**：`deploy.sh` 照旧（会顺带重启全部席位单元）；全停 30 秒窗口，单租户可接受，
  写进 SLA 预期。
- **排障**：`journalctl -u bridgeflow-dsh@<seat>`；跨席位问题先看 `/verify` 的 403 日志；
  认领对不上看 `data/seats-assigned.json`。
