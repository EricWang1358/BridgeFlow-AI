# 36 — 线上演示为中心：免登录评委入口与模型额度防刷

状态：**P0 核心已实施**（分支 `feat/online-demo`，2026-09-25），实施状态与剩余项见 §13；服务器装配步骤在 [`22`](22-lightsail-deploy.md) §9e。
负责人拍板（2026-09-25）：演示相关功能放行（§10 的冲突按放行处理）；**先不设预算**，后续迭代；**主域名改为演示**。
数字只在 [`00`](00-status.md)；部署步骤落地后回写 [`22`](22-lightsail-deploy.md) §9e。

---

## 0 结论（一屏）

1. **不新建演示系统。** 访客实例（`start_web.py --guest`，docs/22 §9e）已具备：数据隔离、每晚重置、飞书剥离、
   上传拒收、AI 默认关。缺的只有三样：**公网免登录入口**、**评委首屏零点击**、**开 AI 后的额度闸门**。
2. **入口去门户化**：演示域名直达。dsh web 的启动令牌无法关闭（`start_web.py:34` 注释已实测），所以不是删掉令牌，
   而是 Caddy 在「无会话」时把浏览器转给一个**交接页**自动带令牌入站。浏览器看不到任何登录框。
3. **API key 防盗刷分五层**，核心一句话：**真 key 不进访客进程**。新增本机模型闸门 `llm-gate`
   （127.0.0.1:8300，OpenAI 兼容透传），访客的 dsh 与后端只拿到闸门地址和一个无价值的客户端令牌；
   闸门做模型白名单、`max_tokens` 封顶、请求体封顶、并发、速率、日预算、急停。
   外层再加**独立 DeepSeek 账号小额预充值**作物理硬上限。
4. **分期**：P0 只动部署与配置 + 闸门（约 1.5 天）；P1 访客席位池解决「评委互相看见会话」（约 2 天，交付后）。

---

## 1 现状（事实，均已核对代码）

| 项 | 现状 | 位置 |
| --- | --- | --- |
| 访客实例 | 独立后端 8001 + 控制台 3090，`data/guest/` 每次启动清空，03:30 定时重启重置 | `scripts/start_web.py:108` `guest_environment`；`deploy/bridgeflow-guest*.{service,timer}` |
| 凭据剥离 | 恒剥 `FEISHU_*` `PORTAL_*`；`BRIDGEFLOW_GUEST_LLM≠1` 时再剥所有模型 key，对话由固定回复插件代替 | `start_web.py:49-51,116`；`plugins/src/guest-model/index.ts` |
| **开 AI 时** | `BRIDGEFLOW_GUEST_LLM=1` → 运营方**真 key 原样进访客进程 env**，无预算、无速率、无模型限制 | `start_web.py:116-117` |
| 上传 | 六类用户文件入口访客 403，内置样例可载入 | `backend/src/bridgeflow/api/guest.py` |
| 入口 | 只能经门户 `/guest` → `handover` 页带 dsh 启动令牌跳转；门户首页须先配置 `PORTAL_GUEST_*` | `portal/src/portal_app/main.py:223,357` |
| Caddy | `guest.<domain>` 无 forward_auth，直接反代 3090；无 cookie 访问得 dsh 的 401 死页 | `deploy/render_caddy.py` `guest_site` |
| 公网 | 未装配：`/guest` 404，`guest.<domain>` 无 TLS | docs/00「公网访客入口」 |
| 共享 | 所有访客共用一个 dsh 身份：会话、审批卡互相可见 | docs/22 §9e 末段 |
| dsh 模型调用 | `${DEEPSEEK_BASE_URL}/chat/completions`，流式且带 `stream_options.include_usage`；另有 `/files`（图片卸载） | dsh `dsh-llm-deepseek/lib/index.js` |
| 后端直连 | resolver / evaluator / dictionary_draft 走 `deepseek_base_url or DEFAULT_BASE_URL` | `backend/src/bridgeflow/llm/providers/deepseek.py:30` |

结论：隔离与剥离已到位，**额度控制为零**，**入口依赖门户**。

---

## 2 目标 / 非目标

目标：

- 评委打开一个 URL → 5 秒内看到已载入样例数据的工作台，不注册、不登录、不点「打开示例」。
- 评委能完整体验 Agent 能力（队长对话、四角色研判、审批卡、证据追溯），**真模型**。
- 任何人拿到链接，能烧掉的钱有**确定上限**；真 key 泄露面为零。
- 额度耗尽时产品**降级可用**（浏览、样例、已录制的真实运行），不是白屏。

非目标：

- 不做访客注册、验证码之外的身份体系。
- 不改正式（飞书门户）部署的任何行为；门户继续服务正式用户。
- 不上传用户文件（维持现有 403）。
- 不做 Docker / CI 新流水线（CLAUDE.md「不要扩大范围」）。

---

## 3 拓扑

```
                        Caddy :443
 评委 ──https──► <domain>  ───────┬─ 有 dsh 会话 ──► 访客 dsh web :3090 ──► 访客后端 :8001
                                  │                       │ DEEPSEEK_BASE_URL=http://127.0.0.1:8300
                                  │                       │ DEEPSEEK_API_KEY=<gate 客户端令牌>
                                  └─ 无会话(GET /) ─► /__enter 交接页（带启动令牌跳回 /）
                                                          ▼
                                                    llm-gate :8300 ──(真 key)──► api.deepseek.com
                                                    （仅本机监听，访客进程之外）

 员工 ──https──► portal.<domain> → <seat>.console.<domain>   ← 正式部署，原样不动
```

域名：**主域名 `<domain>` 即演示**（2026-09-25 拍板）。
席位部署里主域名原本 301 到门户，现在只有启用访客单元后才改渲染为演示站点；员工入口是 `portal.<domain>`，
飞书回跳与席位子域名都不受影响。无席位的旧形态里，单一控制台随之挪到 `console.<domain>`（需同步门户 `apps.yaml`）。

---

## 4 入口：去掉门户拦截

### 4.1 为什么不能「直接反代」

dsh web 只认它每次启动打印一次的启动令牌来种会话 cookie，无配置可关（`start_web.py:34-36`）。
cookie 为 `SameSite=Strict`，所以交接必须是**页面**，不能 302（门户 `handover` 注释已说明）。

### 4.2 做法：交接页挪到演示域名自己身上

不再经过门户首页和按钮。Caddy 演示站点：

```caddy
demo.__DOMAIN__ {
    # 交接页：读访客实例本次启动的令牌，页面内跳转 /?token=...
    handle /__enter {
        rewrite * /guest
        reverse_proxy 127.0.0.1:__PORTAL_PORT__
    }
    handle {
        reverse_proxy 127.0.0.1:__GUEST_PORT__ {
            @unauth status 401
            handle_response @unauth {
                # 只有「浏览器打开首页」才转交接页；API / 资源 / WebSocket 的 401 原样返回，
                # 否则夜间重置后前端 XHR 会拿到一页 HTML
                @page {
                    method GET
                    path /
                    header Accept *text/html*
                    expression `{http.request.uri.query.token} == ""`
                }
                route {
                    redir @page /__enter 302
                    copy_response
                }
            }
        }
    }
}
```

实现要点（写进 `render_caddy.py` 的 `guest_site`，不手写 Caddyfile）：

- `/__enter` 复用门户已有 `/guest` + `handover()`，门户不签任何会话、不签身份令牌（现状即如此）。
  门户进程仍在跑，但**对访客只是一个令牌交接器，不是登录门户**。
- 防循环：`handover` 在令牌文件缺失时会带空令牌跳转 → 又 401 → 又交接。新增：访客交接时令牌缺失返回
  503 页「演示实例正在重启，约 30 秒后刷新」，不跳转。
- 仅 `GET /` 且 `Accept: text/html` 的 401 转交接；`/api/*`、`/bridgeflow/*`、WebSocket 保持 401。
  否则夜间重置后前端 XHR 会拿到一页 HTML。
- 每晚重置后旧 cookie 失效：用户刷新 `/` 即自动重新交接，无感。

替代方案（不推荐）：给 dsh web 加 `--no-auth`。需要 fork dsh，违反「不 fork dsh」。

### 4.3 令牌暴露评估

启动令牌出现在评委地址栏里。它只能进入**访客实例**控制台，访客实例本身就是公开的，
里面没有真 key（§6）、没有飞书凭据、没有真实数据、没有 shell（`dsh/no-shell.patch.yml`）。
所以令牌外泄 = 多一个人进公开演示，等价于链接本身，不构成新风险。

---

## 5 评委体验改造

按「打开 URL → 看懂 → 亲手跑一次 Agent → 追到证据」排。

| # | 改动 | 现状 | 做法 | 期 |
| --- | --- | --- | --- | --- |
| E1 | 首屏零点击 | 需点「打开示例笔记本」 | 访客启动时预导入默认案例（多问题并发样例）为批次并建好笔记本；首个会话自动打开它 | P0 |
| E2 | 自动导览 | 引导需手动开 | 访客首访自动启动 docs/29 的真实页面引导，可跳过；localStorage 记已看过 | P0 |
| E3 | 横幅说清规则 | 已有访客横幅 | 加三件事：示例数据、共享环境（P1 前）、**今日 AI 额度剩余 xx%**（读闸门 `/status`，经访客后端转发） | P0 |
| E4 | 录制的真实运行 | 无 | 把 2026-09-23 真实模型彩排的会话（docs/00 已有证据）复制进访客 `DSH_HOME` 种子，会话列表置顶「真实运行回放」。额度耗尽时评委仍能看到完整工具调用、审批、token | P0 |
| E5 | 额度耗尽降级 | 无 | 闸门 429 → dsh 显示闸门返回的可读消息：「今日演示 AI 额度已用完，示例、回放与所有页面仍可用，次日 00:00 恢复」。任务页「发起研判」按钮读同一状态禁用并说明 | P0 |
| E6 | 语言 | 界面跟随语言 | 演示默认英文（NUS ISS 评委），右上角切中文；对话请求随界面语言（#287 已做） | P0 |
| E7 | 飞书入口 | 显示「访客模式不可用」 | 保留并加一句「正式部署经飞书登录，见演示视频 01:20」，把死路变成指路 | P0 |
| E8 | 评委路线卡 | README 有三步路线 | 同一份文案进首屏引导卡（案例登记表同源，不另写一份） | P0 |
| E9 | 会话互不可见 | 共享 | 访客席位池 §7 | P1 |
| E10 | 一键重置 | 仅每晚 | 席位释放即重置（§7）；P0 只能靠每晚 | P1 |

E1 实现注意：预导入走现有「载入样例」同一条后端路径（`demo_case` 索引字段，HANDOFF 09-24 样例隔离），
不新增数据写入口；字段仍全部来自样例字典，不写死。

---

## 6 API key 防盗刷

### 6.1 威胁模型

| 编号 | 威胁 | 现状下后果 |
| --- | --- | --- |
| T1 | 有人写脚本/反复点研判，持续烧 token | 无上限，余额见底 |
| T2 | 真 key 外泄（进程 env、日志、模型被诱导输出） | key 被拿去别处用，损失不限于演示 |
| T3 | 切到贵模型（dsh 模型选择器开着，`enterprise.patch.yml:63-67`） | 单次成本放大 |
| T4 | 超长输入 / 超大 `max_tokens` | 单次请求成本放大 |
| T5 | 高并发打满内存 / 上游并发 | 演示对所有评委不可用 |
| T6 | 提示注入诱导队长连环调用工具 | 放大 T1；写操作仍要审批 |
| T7 | 访客互相干扰（共享控制台） | 体验问题，非计费问题 → §7 |

### 6.2 五层控制

| 层 | 控制 | 挡什么 | 期 |
| --- | --- | --- | --- |
| L0 供应商 | **独立 DeepSeek 账号**专供演示，预充值小额（例：¥50）；不开自动充值；赛后注销 key | 一切失控的**物理上限**；与正式 key 完全隔离 | P0 |
| L1 key 隔离 | 真 key 只在 `llm-gate` 进程；访客 dsh/后端只拿 `DEEPSEEK_BASE_URL=http://127.0.0.1:8300` + 客户端令牌 | T2 | P0 |
| L2 闸门策略 | 模型白名单、`max_tokens` 封顶、请求体封顶、并发、速率、日预算、急停 | T1 T3 T4 T5 | P0 |
| L3 应用层 | 访客模式下：同一批次研判冷却（例：10 分钟 1 次），队长单轮工具调用上限沿用 dsh 配置；关闭模型选择器 | T1 T6 | P0 |
| L4 观测 | 闸门逐请求记账；preflight 核对；额度 80% 时日志告警 | 事后可查、事前可见 | P0 |

L0 为什么必须有：L1–L3 都是自己写的代码，可能有 bug；预充值余额是唯一不依赖代码正确性的上限。
**待验证**：DeepSeek 控制台是否支持按 key 限额；若支持，L0 可退化为同账号独立 key + 限额。

### 6.3 `llm-gate` 设计

**位置**：`backend/src/bridgeflow/llm_gate/`（独立 ASGI app，`python -m bridgeflow.llm_gate`），
单元 `deploy/bridgeflow-llm-gate.service`，只听 `127.0.0.1:8300`。约 250 行 + 测试。
不是 `LLMProvider`，不碰 dsh 编排（CLAUDE.md「dsh 是基座」），dsh 只是被换了一个上游地址——
这正是 `DEEPSEEK_BASE_URL` 这个受信引导变量的用途。

**配置**：

- 真 key 与上游：闸门进程 source `env.sh`，默认用 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`（服务器现有路由，零新增秘密）；
  `LLM_GATE_UPSTREAM_KEY` / `LLM_GATE_UPSTREAM_URL` 可覆盖为演示专用 key。启动器剥离后逐值核对：
  任何运营方 `*_API_KEY` / `*_SECRET` / `LLM_GATE_UPSTREAM_KEY` 的值以任何变量名残留在访客 env 里，拒绝启动。
- 客户端令牌：闸门首次启动写 `data/gate/client-token`（gitignore，0600），此后保持不变；访客启动器读它，
  缺失则拒绝启动并提示先起闸门。P0 访客 dsh 与访客后端共用一枚；P1 每席位一枚。
- 策略：`data/mappings/llm-gate.yaml`（跟踪入库，无秘密，改 YAML 不改代码）：

实际入库版本见 `data/mappings/llm-gate.yaml`：`models: []`（= 启动器钉死的访客模型）、`paths: [/chat/completions]`、
`max_tokens_cap: 32768`、`max_request_bytes: 2000000`、`rpm: 60`、`concurrency: 6`、`daily_tokens: null`（按拍板暂不设）。
急停文件 `data/gate/OFF`。按客户端分预算留到 P1 席位池。

**请求处理顺序**（任何一步失败即返回 OpenAI 形错误体，dsh 能原样显示 `message`）：

1. `Authorization: Bearer <client token>` → 查表得 client；无 → 401
2. 急停文件存在 → 503 `demo_ai_paused`
3. 路径不在 `paths_allowed` → 403
4. 请求体 > `max_request_bytes` → 413
5. `model` 不在白名单 → 403 `model_not_allowed`
6. `max_tokens` 缺省或超上限 → 改写为上限；强制 `stream_options.include_usage=true`
7. 日预算（全局与 client）已用尽 → 429 `demo_budget_exhausted`，`message` 为 §5 E5 文案
8. 速率（令牌桶，按 client）→ 429 `rate_limited`，带 `Retry-After`
9. 并发信号量（按 client + 全局）→ 等最多 5 秒，否则 429
10. 替换 `Authorization` 为真 key，流式透传；从末帧 `usage` 记账。
    无 `usage`（上游中断）按请求+响应字节 / 3 估算记账，**宁多记不少记**。

**记账存储**：`data/gate/usage.sqlite`（untracked），表 `usage(day, client, requests, prompt_tokens,
cached_tokens, completion_tokens)`。按时区日切。不存请求体、不存响应体——
这同时满足「原始数据行不进上下文」的日志侧延伸：闸门日志只有计数。

**对外状态**：`GET /status`（仅本机）→ `{day, used_ratio, paused}`，访客后端代理成
`/bridgeflow/demo-quota` 给横幅与研判按钮用。只给比例，不给绝对金额。

**已知边界**：

- 闸门看不到「哪个评委」，只看到「哪个实例」。P0 单一共享实例时，一个人可以用光全部日预算 →
  L3 研判冷却与 rpm 缓解；彻底解决靠 P1 席位池（一席位一令牌一份子预算）。
- 预算按日重置，不按滚动窗口；演示期短，够用。

### 6.4 启动器改动（`start_web.py guest_environment`，已实施）

- 无论 AI 开关，**恒剥**所有模型 key 前缀（现在仅 AI 关时剥）。
- AI 开时只注入：`DEEPSEEK_BASE_URL=http://127.0.0.1:8300`、`DEEPSEEK_API_KEY=<guest-dsh 令牌>`；
  后端另注入 `<guest-backend 令牌>`（后端 `deepseek_base_url` 已支持，见 §1）。
- 断言：子进程 env 不含 `LLM_GATE_UPSTREAM_KEY`，且 `DEEPSEEK_BASE_URL` 必须是回环地址。否则拒绝启动。
- `DEEPSEEK_BASE_URL` 由启动器进程设置给子进程，仍属「启动 shell 导出」路径，不进 `.env`（CLAUDE.md 引导变量约束不破）。
- 访客 dsh 默认模型钉为 `deepseek-official/<访客模型>`，不再复制运营方 `settings.yaml` 的模型路由；设置页模型管理本来就关着（`enterprise.patch.yml` `ui-settings-models`），对话框里能选到的其他模型由闸门白名单 403。
- 后端 `LLM_PROVIDER*` 指向闸门够不到的供应商（anthropic 等）时改为 `deepseek`。

---

## 7 会话隔离：访客席位池（P1）

问题：共享 dsh 身份下评委 A 能看到 B 的对话、点 B 的审批卡。对评分体验伤害大于安全伤害。

复用 docs/35 席位机制，换一个认领键：

- 席位 = 一个访客 dsh web 进程（`bridgeflow-dsh@guest-N`），共用一个访客后端 8001。
  内存按 docs/35 规划 ~250MB/席位；池子 4 个 ≈ 1GB。**评审期把正式席位舰队缩到 1–2 个**换出内存。
- 门户新增 `/demo`：无会话 → 发签名 cookie `bf_demo`（随机访客 id，2 小时），认领空闲席位，
  交接到 `g<N>.demo.<domain>/?token=`；满员 → 落到共享大厅实例（即 P0 的单实例）并在横幅说明。
- 绑定校验：席位站点 `forward_auth` → 门户 `/verify` 比对 `bf_demo` 与席位认领人（与 docs/35 同一段逻辑，
  认领键从 union_id 换成访客 id）。
- 回收：30 分钟无请求 → 释放 → 以清空 home 重启该席位 = 重置。E10「一键重置」即主动释放。
- 预算：每席位一个闸门令牌 + 子预算 → 一个评委最多烧一席位的份额。
- 共用后端意味着批次、工作流记录跨席位可见。全是样例数据，可接受；横幅照写。
  若要彻底隔离需后端按席位分数据目录，不在本方案。
- DNS：4 条 `g1..g4.demo.<domain>` 显式记录，逐个自动 HTTPS，不要通配证书（与 docs/35 一致）。

---

## 8 硬约束对照（CLAUDE.md）

| 约束 | 本方案 |
| --- | --- |
| dsh 是基座，不是 provider | 闸门是上游 HTTP 代理，dsh 编排、工具、审批、子代理全不动 |
| 只用官方内置插件 | 不引入任何插件；访客模型插件沿用现有 |
| 不 fork dsh | 入口用交接页绕开令牌，不改 dsh 鉴权 |
| 引导变量绝不进 `.env` | `DEEPSEEK_BASE_URL` 由启动器 export 给子进程；闸门配置在 `env.sh` 与仓库外文件 |
| 原始数据行绝不进上下文 | 闸门不记请求体；预导入走既有载入路径 |
| 字段名绝不写进代码 | 预导入只选案例 id，字段全来自样例字典 |
| 结论必须带证据 | 额度耗尽时不降级出「无证据结论」，研判直接不可发起 |
| 不要扩大范围 | 无 Docker / CI / 自建前端；闸门一个进程、一个单元 |

---

## 9 实施清单

### P0（交付前可做，约 1.5 天）

| 步 | 内容 | 文件 | 测试 |
| --- | --- | --- | --- |
| 1 | `llm-gate` 应用 + 策略 YAML + 单元 | `backend/src/bridgeflow/llm_gate/`、`data/mappings/llm-gate.yaml`、`deploy/bridgeflow-llm-gate.service` | 离线：mock 上游，逐条覆盖 §6.3 十步；流式末帧记账；无 usage 估算；日切 |
| 2 | 启动器恒剥 key、注入闸门、断言 | `scripts/start_web.py` | 扩 `backend/tests/test_guest_mode.py`：AI 开时 env 无真 key、base url 为回环 |
| 3 | 演示站点 Caddy 渲染 + `/__enter` 交接 + 令牌缺失 503 | `deploy/render_caddy.py`、`portal/src/portal_app/main.py` | 门户测试：缺令牌不跳转；Caddy 渲染快照测试 |
| 4 | 首屏零点击：预导入默认案例、自动导览 | `start_web.py --guest` 启动后调用既有载入接口；`plugins/src/client/guest.tsx` | 访客浏览器旅程：首屏即有批次与案例说明 |
| 5 | 额度横幅 + 研判按钮联动 + 研判冷却 | `backend/.../api/guest.py`、`plugins/src/client/guest.tsx` | 闸门返回 exhausted 时按钮禁用、文案正确 |
| 6 | 真实运行回放种子 | `data/guest-seed/`（从彩排导出，脱敏检查） | 启动后会话列表含回放且可打开 |
| 7 | 关闭访客模型选择器 | 访客 web patch（启动器生成） | 界面无模型下拉 |
| 8 | preflight 扩检 | `deploy/preflight.sh` | 闸门 active、只听回环、访客进程 env 无真 key（读 `/proc/<pid>/environ`）、`/__enter` 200、匿名 API 401 |
| 9 | 文档回写 | docs/22 §9e、docs/00、HANDOFF | — |

服务器一次性装配（人工）：DNS `demo.<domain>`；新 DeepSeek 账号充值并把 key 写入 `env.sh` 的
`LLM_GATE_UPSTREAM_KEY`；`bootstrap.sh` 生成客户端令牌；启用 `bridgeflow-llm-gate`、`bridgeflow-guest`、重置定时器；
`BRIDGEFLOW_GUEST_LLM=1`。

### P1（交付后，约 2 天）

席位池 §7；每席位闸门令牌；E10 一键重置；满员大厅。

---

## 10 与 27 日收口的冲突

HANDOFF：「暂停新增功能…只修现有演示链路的阻断」。本方案中：

- **属于修阻断**：§4 入口（公网访客入口是演示闸门里未过的一项，docs/00）、§6.4 启动器恒剥 key、
  §5 E1/E5/E7。
- **属于新增**：`llm-gate`、E4 回放、E3 额度横幅。
- 若不批新增：P0 退化为「AI 关的公开演示 + 回放种子 + 独立账号 key 仅供现场演示人使用」，
  零盗刷风险；评委看回放与视频了解 Agent 能力。这是保底方案。

---

## 11 待验证 / 待拍板

| # | 事项 | 怎么验 |
| --- | --- | --- |
| V1 | dsh 对上游 429/503 的错误体是否原样展示 `message` | 本机起闸门，急停文件置位，发一句话看界面 |
| V2 | dsh 在 `/files` 被 403 时是否只影响图片 | 访客无图片输入，验一次普通对话与研判不走 `/files` |
| V3 | Caddy `handle_response` 能否按请求路径 + `Accept` 细分 401 | 渲染后 `caddy validate` + 本机 curl 三种请求 |
| V4 | 一次完整研判的真实 token 用量 | 取 docs/00 彩排数字，定 §6.3 预算 |
| V5 | DeepSeek 是否支持按 key 限额 | 控制台查；决定 L0 是否需要独立账号 |
| V6 | 回放会话是否含任何真实业务数据 | 种子只能来自样例批次的彩排；导出后 grep 真实字典字段值 |
| D1 | apex 是否改指演示 | 负责人拍板；涉及 `apps.yaml` 回跳 |
| D2 | 访客是否开 AI、日预算金额 | 负责人拍板；默认建议开，¥50 / 日预算 300 万 token 起 |
| D3 | 是否批准 §10 的新增项 | 负责人拍板 |

---

## 12 回滚

- 关 AI：`touch data/gate/OFF`（即时，全部 503）或 `env.sh` 去掉 `BRIDGEFLOW_GUEST_LLM=1` 后重启访客单元。
- 关演示：`sudo systemctl disable --now bridgeflow-guest bridgeflow-guest-reset.timer bridgeflow-llm-gate`，
  重跑 `deploy.sh` 去掉 Caddy 演示站点。
- key 泄露疑似：DeepSeek 控制台吊销演示 key，生成新 key 写回 `env.sh`，重启闸门。访客进程无需重启（它们从未持有真 key）。
- 正式部署全程不受影响：以上操作不触及 `bridgeflow`、`bridgeflow-portal`、席位单元。

---

## 13 实施状态（2026-09-25，分支 `feat/online-demo`）

已实施并验证：

| 项 | 位置 | 验证 |
| --- | --- | --- |
| 模型闸门 | `backend/src/bridgeflow/llm_gate/`、`data/mappings/llm-gate.yaml`、`deploy/bridgeflow-llm-gate.service` | `tests/test_llm_gate.py` 20 条：真 key 只发上游、令牌、模型/路径/体积拒绝不触达上游、速率 429、急停 503、可选预算、流式与非流式记账、无 usage 按字节估算、账本无请求内容 |
| 启动器 key 隔离 | `scripts/start_web.py` | `tests/test_guest_mode.py`：AI 开时 env 无任何运营方秘密、base url 为回环闸门、模型钉死、闸门未起拒绝启动、独立服务凭证 |
| 主域名演示 + `/__enter` | `deploy/render_caddy.py`、`deploy/bridgeflow-guest.service`、`deploy/deploy.sh` | `tests/test_deploy_config.py` 新增 4 条（含 `caddy validate`）；未启用访客时主域名仍跳门户 |
| 令牌缺失不循环 | `portal/src/portal_app/main.py`、`pages.py` | 门户测试 47 条 |
| 首屏零点击、员工登录链接 | `plugins/src/client/shell.tsx`、`guest.tsx`、`web.ts` | 类型检查、构建通过 |
| preflight | `deploy/preflight.sh` | `bash -n`；主域名三种应答、闸门只听回环、访客进程 env 无真 key |

本地端到端（假上游，不花钱）：假上游 → 闸门 → `run.sh --guest`（AI 开）→ 门户 → Caddy 主域名站点。
`curl`：无会话页面 302 到 `/__enter`、API 401、坏令牌 401 不循环、`/__enter` 带本次令牌；浏览器打开主域名直接落到
示例笔记本并弹引导，发一句话由假上游经闸门回复；上游收到的是闸门注入的运营方 key、钉死的模型、封顶的 `max_tokens`；
两个访客进程的 env 里都没有 `env.sh` 的真 key；急停后 dsh 重试 5 次，最终原样显示闸门的中英文说明（V1 通过）。

线上 preflight（2026-09-26）抓出一处漏洞：`run.sh` 先 source `env.sh` 再 exec 启动器，启动器进程启动时的环境里
带着真 key，`/proc/<pid>/environ` 读得到，而访客进程都是同一用户。本地端到端当时只查了 dsh 与后端两个子进程，漏了父进程。
修复：访客启动器先整理出剥离后的环境，再 `execve` 重新执行自己，同一 PID 的环境原件被整体替换。本地实测父进程与全部子进程均不含 key，
回归测试在 `test_guest_mode.py`。

未做（按拍板或留后）：

- E3 额度横幅、E5 额度耗尽联动：预算暂不设，无意义；闸门 `/status` 已给出 `used_ratio`，设预算时再接。
- E4 真实运行回放种子、E6 默认英文、E7 飞书入口指向视频、L3 研判冷却。
- §7 席位池（P1）。
- V4（真实研判 token 用量定预算）、V5（DeepSeek 按 key 限额）、V6。
- 真实模型经闸门的一次研判：需在服务器装配后用真 key 跑，会计费。
