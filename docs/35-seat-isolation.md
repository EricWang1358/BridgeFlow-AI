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
| 注册表按门户 `sub`（union_id）直接键路由，**不做**规范 ID 间接层 | 「飞书/Lark 是两个工作区」拍板 |
| `access-control.yaml` 仍是角色/操作唯一事实来源；席位持有者必须有 `console_access` | 沿用 #229 |
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
          /verify：① 会话有效 ② console_access ③ Host 的席位 == 登录人 sub   ← 新增③
            │
   ┌────────┴──────────────────────────────────────────┐
   │ bridgeflow.service（改后端专用）: uvicorn :8000    │  全局唯一 backend
   │ bridgeflow-portal.service: uvicorn :8100           │
   │ bridgeflow-dsh@<seat>.service × 7:                 │  systemd 模板单元
   │     DSH_HOME=data/homes/<seat>/   dsh web :310x    │  Slice=bridgeflow-dsh.slice
   └───────────────────────────────────────────────────┘
```

**席位注册表 `data/mappings/seats.yaml`**（随 git 走 PR，与 access-control.yaml 同纪律）：

```yaml
seats:
  - name: gm1            # 子域名标签 + 单元实例名 + home 目录名
    sub: "oun_xxxxxxxx"  # 门户 subject（飞书 union_id）
    port: 3101           # 3101–3107
```

**校验链**（谁也绕不过去的三层）：进子域名 → Caddy forward_auth 问 `/verify` →
门户查会话 + console_access + `Host`↔`sub` 绑定；直连他人端口不可达（dsh web 只绑
127.0.0.1）；拿到子域名但无对方 launch token/session cookie → dsh 自身凭据栅栏拒绝。

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
| 5 | `data/mappings/seats.yaml`（新增） | §3 的注册表；`console_access` 与席位的对应关系在 PR review 时人工核对 |
| 6 | `portal/src/portal_app/main.py` | ① `/enter`：加载 seats.yaml，按会话 `sub` 查席位 → 目标 `https://<seat>.console.<domain>/`、token 文件取 `data/homes/<seat>/.web-launch-token`；无注册表时保持现有单实例行为（开发机兼容）。② `/verify`：新增席位绑定校验——`Host` 匹配 `*.console.<domain>` 时，要求 `session.sub == 该席位.sub`，否则 403；非席位 Host 走现有逻辑 |
| 7 | `portal/` 配置 | 新增 `PORTAL_SEAT_BASE_DOMAIN`、`PORTAL_SEATS_PATH`（缺省沿用旧行为）；`PORTAL_COOKIE_DOMAIN` 必须是父域（`.example.com`），覆盖席位子域名 |
| 8 | `deploy/bootstrap.sh` | 渲染 Caddy 时按 seats.yaml 生成每席位站点块（显式子域名，逐个自动 HTTPS）；新增 2GB swapfile + `vm.swappiness=10` 持久化 |
| 9 | `scripts/provision_seat.sh`（新增） | 开通一个席位：按 M0 定稿的初始化清单建 `data/homes/<seat>/` → 写 `seat.env` → 追加 seats.yaml → 渲染 Caddy 并 reload → `systemctl enable --now bridgeflow-dsh@<seat>`。撤销为其逆操作（停单元、home 归档到备份、注册表移除、Caddy 重渲） |
| 10 | `deploy/preflight.sh` | 席位模式开启时新增检查：注册表可解析、席位数 ≤7（容量口径。注意 MemoryMax 是**封顶不是预留**，各席位封顶之和可超 slice，这是设计而非错误）、门户上报的席位数与注册表一致、slice 围栏生效（MemoryMax=2147483648）、每席位单元 active / token 文件非空 / 回环端口在听 / 子域名无 cookie 访问收 401、swap ≥2G。无注册表时全部静默跳过 |
| 11 | `portal/tests/` | `/verify` 绑定校验单测（sub↔Host 三种组合）；`/enter` 按注册表路由的单测 |
| 12 | 文档 | 本文档 + [`00`](00-status.md)（spike 数字）、[`22`](22-lightsail-deploy.md)（单元/Caddy/swap 小节）、[`27`](27-login-portal.md)（/enter 席位路由、/verify 第三层校验）、[`34`](34-web-refactor-plan.md)（#230 条目指向本文）、`../HANDOFF.md` 同步 |

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

1. 7 席位在线；每人经门户只被送进自己的子域名；手输他人子域名收 403（/verify 绑定校验）。
2. 任意两席位：会话、笔记本、待审批互不可见（物理隔离，非过滤）。
3. 席位单元 `systemctl restart` 后历史会话仍在（home 在盘上）。
4. 归属：单席位内模型触发的读取带正确的 `x-bridgeflow-user`（#231 无歧义）。
5. `bridgeflow-dsh.slice` 2.0G、单元 512M、backend 1.3G 围栏在 `systemctl show` 可见；swap 2G 激活。
6. `deploy/preflight.sh` 在实例全绿；spike 数字在 [`00`](00-status.md)。
7. 开发机 `start_web.py` 默认单进程流行为不变（回归项）。
8. 对外口径更新：「控制台按人隔离」可以讲；「席位成本封顶」仍不可讲（静态方案无弹性）。

## 7 · 风险与对策

| 风险 | 对策 |
| --- | --- |
| 实测 RSS 超规划（>300MB 闲时） | M0 是门；先垂直升配 8GB，不硬塞 4GB |
| Caddy `forward_auth` 未按预期透传 Host | M3 首项验证；不行改用 `X-Forwarded-Host`（Caddy 显式 `header_up`），属小改 |
| 全新 `DSH_HOME` 初始化踩坑（profiles/credentials 缺失） | M0 定稿清单前不开工；供给脚本逐项复制模板内容并校验 |
| 月尖峰：多单上传 + 多人研判叠加 | backend `MemoryMax` 优先保 backend；并发重研判 ≤3 写进运维手册；swap 兜闲置页 |
| 7 席位 ×512M 触 slice 上限被杀 | 这就是设计：OOM 只死一个席位，preflight 提示扩容/升配 |
| `env.sh` 内 `DSH_HOME` 导出与席位覆盖打架 | 席位单元 `source env.sh` 后**再** `export DSH_HOME=...` 覆盖，写进模板注释与测试 |

## 8 · 运维手册（上线后常态操作）

- **开通席位**：`scripts/provision_seat.sh <name> <sub>` → 核对该 `sub` 的角色已声明
  `console_access` → 交付子域名地址。
- **撤销席位**：逆操作 + home 归档进备份（home 是客户资产，与 #232 的保留策略合并执行）。
- **升级**：`deploy.sh` 照旧；重启顺序 backend → 席位单元（全停 30 秒窗口，单租户可接受，
  写进 SLA 预期）。
- **排障**：`journalctl -u bridgeflow-dsh@<seat>`；跨席位问题先看 `/verify` 的 403 日志。
