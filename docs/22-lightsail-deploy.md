# 22 — AWS Lightsail 部署（GitHub Actions 自动部署）

目标：合并到 `main` 即自动测试并部署到 Lightsail 实例；公网经 Caddy
（自动 HTTPS）进入，身份由统一登录门户（飞书 OAuth，[`27`](27-login-portal.md)）
承担，**不用 Docker**。

流水线在 `.github/workflows/deploy.yml`（本仓库唯一 CI 文件），
实例侧脚本 `deploy/deploy.sh`，systemd 单元 `deploy/bridgeflow.service`。

**每一步都有验证命令。验证不过不要往下走。**

§2–§8 已写成可重复执行的 `deploy/bootstrap.sh <domain>`（不写任何密钥），§13 的机器可查部分写成只读的
`deploy/preflight.sh <domain>`；下文保留逐步命令，便于排查某一步。deploy job 默认关闭，设仓库变量 `DEPLOY_ENABLED=true` 才会部署。

本文只管一次性引导和已知坑；日常部署是自动的，回滚一行：

```bash
ssh <user>@<host> 'bash -s -- <previous-sha>' < deploy/deploy.sh
```

---

## 0 部署拓扑

```
浏览器 ──HTTPS──▶ Caddy (:443/:80, 唯一公网监听)
                    │ reverse_proxy, 透传 Host
                    ├─ <domain>        → dsh web (127.0.0.1:3080)
                    │                      │ 宿主侧 Node 代理，带
                    │                      │ BRIDGEFLOW_SERVICE_TOKEN
                    │                      │ 与浏览器的门户令牌
                    │                      ▼
                    │                   后端 uvicorn (127.0.0.1:8000，JWKS 验签)
                    └─ portal.<domain> → 登录门户 uvicorn (127.0.0.1:8100)
```

浏览器只与 dsh web 同源通信（客户端插件全部请求同源 `/bridgeflow/*`）；
对后端的 fetch 发生在 dsh web 宿主进程内，`DEEPSEEK_API_KEY` 与服务
凭证不出实例。因此 `dsh/enterprise.patch.yml` 的
`backendUrl: http://127.0.0.1:8000` **保持原样**，无 CORS 改动。

主站不套 basic auth：dsh web 自身的会话凭证栅栏仍在，门户签发的短期
JWT 守所有浏览器数据路由（见 [`27`](27-login-portal.md)）。门户站点不能
加任何前置密码——飞书 OAuth 回调要直达。

启动链复用本地开发原样：`run.sh` → source `env.sh` →
`scripts/start_web.py` → uvicorn + `dsh web`。systemd 只是把这条链
变成常驻服务（SIGTERM 时 start_web.py 会干净停掉两个子进程）。

---

## 1 实例与网络

- Lightsail 实例：**Ubuntu 24.04 LTS, x86_64**，≥ 2 GB RAM（dsh 运行时 + pandas；4 GB 更宽裕）
- 绑定**静态 IP**
- Lightsail 防火墙：只开 **80 / 443**。SSH 限源 IP，或干脆走 Lightsail 浏览器终端
- 一个指向静态 IP 的域名 A 记录（自动 HTTPS 需要真域名）

**验证**

```bash
curl -sI http://<domain>/     # 期望 301/308（Caddy 跳 HTTPS）或 401
```

---

## 2 系统基础

```bash
sudo apt update && sudo apt install -y git curl ca-certificates
```

**验证**

```bash
lsb_release -d    # 期望 Ubuntu 24.04
```

glibc ≥ 2.28（`deepseek_harness_runtime_bin` 的 `manylinux_2_28` wheel 要求），24.04 满足。

---

## 3 Node 22 + pnpm + uv + dsh

```bash
# Node 22 (NodeSource)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# pnpm 版本由 plugins/package.json 的 packageManager 声明；部署用 corepack 解析
sudo corepack enable

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh   # 装到 ~/.local/bin

# dsh，版本与 Python SDK 双向锁死，只在这里装
sudo npm install -g @deepseek-ai/dsh@0.1.2-rc.1
```

**验证**

```bash
node -v                 # v22.x
corepack --version      # 部署时从插件目录解析项目声明的 pnpm
~/.local/bin/uv -V      # uv 版本号
dsh --version           # 0.1.2-rc.1
```

---

## 4 代码与虚拟环境（目录照抄开发约定）

```bash
# 实例生成只读 deploy key，公钥加到 GitHub 仓库 Settings → Deploy keys
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

git clone git@github.com:EricWang1358/BridgeFlow-AI.git ~/Hackathon2026/BridgeFlow-AI

cd ~/Hackathon2026/BridgeFlow-AI
uv venv --python 3.13 ~/Hackathon2026/.venv
uv pip install -e "backend[dsh,dev]" --python ~/Hackathon2026/.venv/bin/python

# DSH_HOME 必须绝对路径、必须在仓库外（CLAUDE.md 硬约束）
mkdir -p ~/Hackathon2026/.dsh-bridgeflow
```

**验证**

```bash
~/Hackathon2026/.venv/bin/python -c "import bridgeflow; print('ok')"
```

---

## 5 env.sh 与生产字典

```bash
cd ~/Hackathon2026/BridgeFlow-AI
cp env.sh.example env.sh
chmod 600 env.sh
```

编辑 `env.sh`：

- `DSH_HOME=/home/ubuntu/Hackathon2026/.dsh-bridgeflow`
- `DEEPSEEK_API_KEY=<生产 key>`（建议低额度档 + 控制台消费上限）
- **追加 `export BRIDGEFLOW_DSH=$(command -v dsh)`** —— systemd 的 PATH
  极简，没有它可能找不到全局 npm 装的 dsh
- `DSH_*` 与 `DEEPSEEK_BASE_URL` **只能在这里**。绝不写进 `.env`、
  绝不写进 systemd 单元 —— dsh 会扫描 cwd 的 `.env` 并拒启，这是安全边界

生产字段字典放 `data/mappings/field-dictionary.yaml`（gitignored，
部署永不触碰；见 CLAUDE.md「字段名绝不写进代码」）。

**验证**

```bash
source env.sh && [ -n "$DEEPSEEK_API_KEY" ] && [ -d "$DSH_HOME" ] && echo ok
```

### 5b 两份配置各走各的通道

改配置都不需要 SSH 上机器，但两份文件的路径不同，因为敏感度不同。

**`access-control.yaml` 随代码走 git。** 它只声明知识库 space_id 与角色策略，
没有任何凭证；space_id 对组织外的人无意义，对组织内没权限的人也打不开对应知识库。
而它恰恰是最该被评审的文件，所以改权限策略 = 提 PR = 有 diff、有评审、有回滚。
`deploy.sh` 的 `git reset --hard` 直接把它带上实例，`backend/tests/test_access_resolver.py`
里有一条守卫：仓库里这份文件非法，PR 就红，而不是上线后数据面 503。

一个后果要知道：**回滚到旧 commit，这个文件会跟着回到那个 commit 的版本**；
实例上同路径的手改文件会被 `git reset --hard` 静默覆盖。两者都是想要的行为。

**`field-dictionary.yaml` 走流水线密文通道。** 它是真实业务数据，不入库：内容存为
`production` 环境的 GitHub secret `FIELD_DICTIONARY_YAML`，部署时 base64 经 SSH 管道
送到实例，由 `deploy/config-put.sh` 先用导入侧自己的 `_load_dictionary` 校验再原子替换。
**非法配置让部署失败，而不是到达运行时**；内容没变就不写；被替换的旧文件保留为
`*.bak` 一代。secret 留空则跳过，实例上已有文件继续生效。

> 顺序要求：同步步骤必须排在 `deploy.sh` **之后**。`config-put.sh` 用产品自己的加载器
> 校验，那就必须是**被部署的那个 commit** 的加载器。2026-09-19 的部署把同步排在前面，
> 校验撞上旧代码里还不存在的模块（`ImportError: cannot import name 'access_resolver'`），
> 文件一个字节没落地，而 `ssh-action` v1 取最后一条命令的退出码，整步报成 ✅。
> 现在 deploy.yml 的同步脚本首行有 `set -eo pipefail`（v1 删掉了 `script_stop`，
> 官方替代写法就是它）。配置落地后**不需要重启**：两个加载器都每次调用重读文件。

env.sh 里的真凭证（`DEEPSEEK_API_KEY`、`FEISHU_APP_SECRET`、`PORTAL_*`）**两条通道都不走**，
维持「凭证只住实例」的既有决策（deploy.yml 文件头）。

---

## 6 客户端 bundle 与首次冒烟

```bash
cd ~/Hackathon2026/BridgeFlow-AI
(cd plugins && corepack pnpm install --frozen-lockfile && corepack pnpm run build)
# dist/ 是 gitignored，必须在实例上构建
./run.sh --host 127.0.0.1 --port 3080
```

**验证**

```bash
curl -fsS http://127.0.0.1:8000/health          # 在另一个终端
ss -tlnp | grep -E '3080|8000'                  # 两者都应只在 127.0.0.1
```

`dist/client.js` 的新鲜度门在 `scripts/start_web.py` 启动时检查
（比 `plugins/src/client/**` 等源文件新即可）；`deploy.sh` 每次部署
都重新构建，天然满足。Ctrl-C 停掉。

---

## 7 Caddy（反代 + 自动 HTTPS）

```bash
# 官方 apt 源安装，见 https://caddyserver.com/docs/install#debian-ubuntu
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`（实例文件，**不进仓库**）——两个站点，门户站点
必须在门户进程起来之前就位也行，Caddy 会各自签证书。主站带
`forward_auth`：每个请求先问门户 `/verify`，没有登录会话的浏览器拿到
401 引导页，被送去门户登录——AI 对话页面本身也在门后。开了控制台门禁（§9d）之后
这一跳还会答 403（已登录但无授权）与 503（授权无法确认），Caddyfile 本身不用改：

```caddyfile
<domain> {
    forward_auth 127.0.0.1:8100 {
        uri /verify
        header_up -Connection
        header_up -Upgrade
    }
    reverse_proxy 127.0.0.1:3080
}

portal.<domain> {
    reverse_proxy 127.0.0.1:8100
}
```

与 `deploy/Caddyfile.template` 一致；`bootstrap.sh` 与 `deploy.sh` 渲染的就是它
（`deploy.sh` 每次部署按 diff 重渲并 reload，单元文件同理——改了没人装是 2026-09-20
与 09-21 各摔一次的同一个坑）。

```bash
sudo systemctl reload caddy
```

Caddy 反代默认透传 `Host`、原生支持 WebSocket 升级、无请求体大小上限
（约 26 MiB 的上传路径不受阻）。

**那两行 `header_up -` 是功能性的，不是整洁。** `forward_auth` 的子请求会原样带上
原请求的头，包括 `Connection: Upgrade` / `Upgrade: websocket`；门户是装了 `websockets`
的 uvicorn，于是它把这个 `GET /verify` 交给 WebSocket 协议处理，`/verify` 没有 ws 路由
→ **403**，`forward_auth` 据此拒掉整条升级。被拒的正是 `wss://<host>/api/remote.mux`：
dsh 所有 Typert Remote **流**都跑在这一条 socket 上，而工作区投影**没有 unary 回退**
（`dsh-api-workspace-controller` 客户端只订 `workspace.follow`）。于是控制台打开后没有
工作区、原生落地策略（`watchNavigation` 要求 `workspace.phase === 'ready'`）静默不建会话、
输入框显示「choose a workspace to start」——而目录选择器按企业策略禁用，菜单里连「添加」
都没有。2026-09-21 线上就是这个现象；剥掉两个 hop-by-hop 头后 `/verify` 恢复成普通 GET，
原请求照常升级，三层校验一层不少。门户侧另有一道 `--ws none`（§9）。

判别式（数字见 [`00`](00-status.md)）：无 cookie 的升级握手，**401 = 好**（dsh 自己在拒
未登录浏览器，说明升级穿过了认证层），**403 = 坏**（`forward_auth` 拒的，请求根本没到
dsh）。`preflight.sh` 按席位逐个查这一条。

**验证**

```bash
curl -sI https://<domain>/          # dsh web 未起时 502——502 也证明反代与证书活着
curl -sI https://portal.<domain>/   # 同上（门户进程在 §9 才起）
```

---

## 8 systemd 常驻

```bash
cd ~/Hackathon2026/BridgeFlow-AI
sudo cp deploy/bridgeflow.service /etc/systemd/system/bridgeflow.service
sudoedit /etc/systemd/system/bridgeflow.service   # 把 <domain> 换成真域名
sudo systemctl daemon-reload
sudo systemctl enable --now bridgeflow
```

**验证**

```bash
systemctl status bridgeflow            # active (running)
journalctl -u bridgeflow -n 50 --no-pager   # 见字典路径与 dsh web 带凭证 URL
ss -tlnp                                # 公网监听仅 sshd 与 caddy
```

---

## 8b 席位化多用户隔离（2026-09-20，docs/35）

主单元 `bridgeflow.service` 在席位部署里只起**共享 backend**（`--backend-only`）；
每个授权者一个 `bridgeflow-dsh@<seat>.service` 实例（`--web-only`，各自 `DSH_HOME`
在 `data/homes/<seat>/`，回环端口 3101+），全部归入 `bridgeflow-dsh.slice`
（MemoryHigh=1.6G / MemoryMax=2.0G；单实例 MemoryMax=512M）。拆分模式下
`BRIDGEFLOW_SERVICE_TOKEN` 必须在 env.sh 显式设置并由 backend 与所有席位共享
（审批回执 HMAC 也以它为钥）。

```bash
# bootstrap.sh 已自动装单元/slice/swap(2G, swappiness=10)并按 seats.yaml 渲染 Caddy；
# 建 7 席位舰队（一次性，通用席位、先到先得认领，配置里没有任何人名）：
BRIDGEFLOW_DOMAIN=<domain> scripts/provision_seat.sh --init 7
# 状态 / 腾位：
BRIDGEFLOW_DOMAIN=<domain> scripts/provision_seat.sh --status
BRIDGEFLOW_DOMAIN=<domain> scripts/provision_seat.sh --release <union_id>
```

Caddy 由 `deploy/render_caddy.py` 从 `data/mappings/seats.yaml` 渲染：无容量文件时与
§7 旧形态逐字节相同（apex 即控制台）；有容量时 apex 永久重定向到门户，每个席位一个
显式子域名站点块（`<seat>.console.<domain>`，forward_auth → 门户 /verify，
reverse_proxy → 127.0.0.1:<port>）。**每个席位需要一条 DNS A 记录**；Caddy 对显式
主机名各自取证书，7 席位不需要泛域名。认领状态在 `data/seats-assigned.json`（untracked，
每次部署天然幸存）；部署会顺带重启全部席位单元。

每个席位块同样带 §7 那两行 `header_up -Connection` / `-Upgrade`：没有它们，
`wss://<seat>.console.<domain>/api/remote.mux` 被 `forward_auth` 403 掉，席位打开后
没有工作区、发不起对话（2026-09-21）。

席位模式检查已进 `preflight.sh`（单元/token/端口/子域名 401/**升级握手到 dsh 是 401 而不是
forward_auth 的 403**/slice 围栏/swap/席位数 ≤7），未配置注册表时全部静默。
运行手册（开通、撤销归档、升级重启顺序）见 [`35`](35-seat-isolation.md) §8。

---

## 9 登录门户（飞书 OAuth）

门户是第二个常驻进程（`portal/`，127.0.0.1:8100），与主服务同机部署。
设计与边界见 [`27`](27-login-portal.md)；这里只记实例侧装配。顺序有讲究：
**门户验证通过之后再让后端开身份层**，否则数据面会在门户就绪前全体 401。

### 9a 飞书后台（一次性，人工）

复用 #140 的自建应用即可（凭据同一对，权限范围不同）：

1. 添加「网页应用」能力；
2. 安全设置 → 重定向 URL 填 `https://portal.<domain>/callback`；
3. 权限：开通获取用户 user_id 的通讯录只读权限（否则 user_info 没有
   union_id，门户会报错而不是猜）；
4. 创建版本并发布。

App ID / Secret 只进实例 `env.sh`，不进仓库、不进 GitHub。

### 9b 实例装配

```bash
cd ~/Hackathon2026/BridgeFlow-AI
uv pip install -e portal --python ~/Hackathon2026/.venv/bin/python
# 签名私钥放仓库外，绝不入库：
~/Hackathon2026/.venv/bin/python -m portal_app.keygen ~/Hackathon2026/.portal-key.pem
```

`env.sh` 追加（`PORTAL_SESSION_SECRET` 用 `openssl rand -hex 32` 生成一次、
粘贴**字面值**——每次启动重算会让所有已登录会话作废）：

```bash
export PORTAL_FEISHU_APP_ID=<app id>
export PORTAL_FEISHU_APP_SECRET=<app secret>
export PORTAL_KEY_PATH="$HOME/Hackathon2026/.portal-key.pem"
export PORTAL_SESSION_SECRET=<32+ 随机字符>
export PORTAL_EXTERNAL_BASE_URL="https://portal.<domain>"
export PORTAL_COOKIE_SECURE=true
# 主站的 forward_auth 也要读会话 cookie → 共享到父域（点前缀，两个站点都吃）：
export PORTAL_COOKIE_DOMAIN=".<domain>"
export PORTAL_APPS_PATH="$HOME/Hackathon2026/portal-apps.yaml"
# 后端验签与 dsh web 代理下发门户地址共用这一个变量；必须与上面一致
# （验签时 iss 按它逐字节比对）：
export PORTAL_BASE_URL="https://portal.<domain>"
```

`BRIDGEFLOW_SERVICE_TOKEN`（拆分模式必填）必须是**粘贴的字面量**，绝不能写
`$(python …)` 之类的命令替换——每次 source 都会重新生成，各单元在不同时刻
source 就各拿一个值，席位对后端全线 401（2026-09-20 事故即是此行）。生成
一次贴进来：`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`。
preflight 的「stable service token / backend accepts / 进程持有」三检查盯住
这一类漂移。

`~/Hackathon2026/portal-apps.yaml`（实例文件，不进仓库；仓库里的
`portal/apps.yaml` 保留给本地开发）：

```yaml
apps:
  bridgeflow:
    audience: bridgeflow
    # 登录成功后先落 /enter：dsh web 的原生会话只认它启动时打印一次的
    # launch token（每次重启轮换，无配置入口），/enter 读出当次值再放行。
    # 走主站的 /__enter（Caddy 把它反代到门户的 /enter），这样交接页与主站同源；
    # 没配这条 Caddy 路由时退回 "https://portal.<domain>/enter"，同站也够用。
    redirect_uri: "https://<domain>/__enter"
    # /enter 的最终目的地；token 以 ?token= 附在这个地址上进主站。
    app_uri: "https://<domain>/"
    origins:
      - "https://<domain>"
```

席位模式下 redirect_uri 填 `https://portal.<domain>/enter`；`*.console.<domain>`
各席位源**不用**写进 `origins`——门户按 seats.yaml 在启动时自动并入 CORS 白名单
（席位页面跨域换取 app token 必须带 cookie）。

token 文件不需要配置：`start_web.py` 从 dsh web 的 stdout 捕获当次 token
写到 `$DSH_HOME/.web-launch-token`（0600），门户默认读同一路径
（`PORTAL_DSH_TOKEN_FILE` 可覆盖）。dsh 会话 cookie 跨重启有效（签名密钥
持久化在 dsh credentials store），所以 /enter 只在新浏览器首次进入时绕一次。
捕获失败时 /enter 不再 503：照样把浏览器送到主站，只是不带 token——手里已有
cookie 的浏览器不该被拦；`start_web.py` 会在控制台 WARNING，preflight 也查。

**/enter 回的是一张页面，不是 302**。dsh 的会话 cookie 是 `SameSite=Strict`，
而整条登录导航从 `open.feishu.cn` 起跳属于跨站链，再多一跳 302 会让浏览器在
最后一跳不带 cookie，dsh 直接 401（现象：登录后停在
「dsh web authentication required」，手动再访问一次才进得去）。交接页把链打断，
之后那一跳由页面自己发起，同站/同源，cookie 才跟得上。改这里时别把
`Location` 加回来，`portal/tests/test_portal.py` 有断言守着。

```bash
sudo cp deploy/portal.service /etc/systemd/system/bridgeflow-portal.service
sudo systemctl daemon-reload
sudo systemctl enable --now bridgeflow-portal
```

单元里的 `--ws none` 别删。门户没有任何 WebSocket 路由，而装了 `websockets` 的 uvicorn
会把**任何**带 `Connection: Upgrade` 的请求交给 WebSocket 协议处理、匹配不到 ws 路由就
403。`forward_auth` 的子请求恰好会带着这两个头到 `/verify`，于是一个本该答 200 的授权
问询变成了拒绝，把席位的 `/api/remote.mux` 一起带走（2026-09-21）。§7 的 `header_up -`
从 Caddy 侧堵住同一个洞，两边都做：这一行说的是「本进程只答 HTTP，永远不升级」。

**验证（按顺序，不过就停）**

```bash
curl -fsS http://127.0.0.1:8100/health                    # feishu 与 signer 均为 true
curl -fsS https://portal.<domain>/health                  # 同上，证明 Caddy 站点与证书就位
curl -sI 'https://portal.<domain>/login'                  # 期望 302 到 open.feishu.cn（app 缺省即 bridgeflow）
curl -sI https://portal.<domain>/verify                   # 无会话期望 401
curl -sI https://<domain>/                                # 主站过 forward_auth：无会话同样期望 401
journalctl -u bridgeflow-portal -n 5 --no-pager           # 启动日志打印 registry（app → redirect_uri），配置错这里现形
```

### 9c 后端开身份层 + 配置结构映射（#204）

```bash
sudo systemctl restart bridgeflow   # 后端与 web 代理拿到 PORTAL_BASE_URL
```

浏览器打开主站：forward_auth 401 → 引导页送去门户 → 飞书 OAuth →
回调落门户 `/enter` → 带当次 launch token 进主站，dsh web 签出原生会话
cookie（此后直到 cookie 过期都直达，重启不影响）。

授权不再登记逐人名单：五个知识库（四部门 + 总经办）的 space_id 与角色策略写在
`data/mappings/access-control.yaml`。这份文件**跟踪在仓库里**（理由与通道见 §5b），
部署自动带上，实例侧不需要手动创建，改它走 PR 而不是 SSH。飞书侧前提：应用已发版带
`wiki:member:retrieve`，且应用本体已加为每个知识库成员。

### 9d 开启控制台门禁（#229，可选但建议）

默认关闭时任何已登录员工都能到达代理控制台，而控制台是共用的一个 dsh 身份。开启前先在
`access-control.yaml` 里给该进控制台的角色加上 `console_access` 操作（本仓库的示例配置只给了
`master_office_admin`），**顺序不能反**：先开门禁后加授权会把所有人锁在门外。

`env.sh` 追加，然后重启门户：

```bash
export PORTAL_CONSOLE_CHECK_URL="http://127.0.0.1:8000/identity/console-access"
```

**验证（按顺序）**

```bash
curl -fsS http://127.0.0.1:8100/health                    # console_gate 为 true
curl -sI https://<domain>/                                # 无会话仍是 401（登录问题先答）
# 带一个有授权的会话 cookie 访问 → 200；换一个没有 console_access 的账号 → 403
# 停掉后端再访问 → 503，页面写「暂时无法确认你的访问范围 … 这不是拒绝」
sudo systemctl restart bridgeflow                         # 恢复后回到 200
```

403 与 503 都经由 Caddy `forward_auth` 透传给浏览器（§7 的配置不用改）；这一跳的真实形态
尚未在实例上验过（[`00`](00-status.md) 记为未验），放行前自己点一遍。

`deploy/preflight.sh` 会挡住上面那个顺序错误：门禁已开而没有任何角色声明 `console_access` 时
它报 FAIL。门禁关闭时这条检查沉默——关闭是受支持的默认值，不是待办。

文件缺失时数据面是 503「未配置」，这是设计的中间态（fail-closed），不是故障。
放行前跑侦察脚本确认五个库的成员可读——脚本只认 shell 导出的凭据，先 `source env.sh`
（其中必须有 `FEISHU_APP_ID` 与 `FEISHU_APP_SECRET`，缺了脚本会报 `not_configured`）：

```bash
source env.sh   # 导出 FEISHU_APP_ID / FEISHU_APP_SECRET
python scripts/feishu_membership_check.py
```

---

## 10 GitHub 仓库侧配置

| 项 | 位置 | 值 |
| --- | --- | --- |
| `SSH_HOST` | Actions secrets | 实例静态 IP |
| `SSH_USER` | Actions secrets | `ubuntu`（或专用 deploy 用户，见 §11） |
| `SSH_PRIVATE_KEY` | Actions secrets | CI 部署私钥（公钥进实例 `authorized_keys`） |
| `PUBLIC_DOMAIN` | Actions **variables** | 域名（公开信息，不必做 secret） |

`DEEPSEEK_API_KEY` **不进 GitHub**，只住实例 `env.sh`。

**验证**：推送一个 trivial commit 到 `main`，Actions 全绿，实例
`git log -1` 与 main 一致。

---

## 11 已知坑

- **`--trusted-host` 匹配形态未验证**：fence 按 host 还是 `host:port`
  匹配待实测。flag 可重复；第一种形态 403/拒绝时，两个都传：
  `--trusted-host <domain> --trusted-host <domain>:443`
- **首次访问**：`journalctl -u bridgeflow` 里 dsh web 打印的带凭证 URL
  是 `127.0.0.1:3080/...`，浏览器里改写成 `https://<domain>/...` 打开，
  种下会话 cookie；此后直接访问 `https://<domain>/`（basic auth →
  会话 cookie 两道门）
- **绝不 `git clean`**：`env.sh`、生产字典、`data/uploads|outputs`、
  `plugins/dist` 全靠 gitignore 存活。`deploy.sh` 只 `git reset --hard`
- **版本门**：`start_web.py` 每次启动校验 `deepseek-harness-sdk==0.1.2rc1`
  与 dsh CLI `0.1.2-rc.1`；dsh 全局包升级只能手动做（本表与
  `pyproject.toml`、CI 均需同步改）
- **零停机不做**：`systemctl restart` 有数秒空窗，hackathon 演示可接受

---

## 12 可选加固：专用 deploy 用户

CI 的 SSH key 若指向 `ubuntu`（免密 sudo）即等价 root。更严做法：

```bash
sudo useradd -m -s /bin/bash deploy
# deploy 用户的 authorized_keys 放 CI 公钥
echo 'deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart bridgeflow, /usr/bin/systemctl restart bridgeflow-portal, /usr/bin/systemctl is-active bridgeflow, /usr/bin/systemctl is-active bridgeflow-portal' \
  | sudo tee /etc/sudoers.d/deploy-bridgeflow
```

`deploy.sh` 中的 `sudo systemctl` 恰好只用到这四条。仓库读取权限
沿用 `~/Hackathon2026` 下的组可读或把 `deploy` 加进 `ubuntu` 组，按需调整。

---

## 13 验收清单（部署完成后逐条过）

1. `curl -sI https://<domain>/` → 200 且出 dsh web 页面；
   `curl -fsS https://portal.<domain>/health` → `feishu` 与 `signer` 均 true
2. 浏览器打开改写后的凭证 URL，`/api` 调用成功（`--trusted-host` 在此证明）
3. 点「飞书登录」完成 OAuth，数据路由带 JWT 通过；清掉会话后回到 401
   与登录入口
4. UI 走全链路：传演示月度表 → review 流程 → notebook 渲染
5. `sudo systemctl restart bridgeflow bridgeflow-portal` 自愈；
   `sudo reboot` 后两个单元自启
6. 演示前排练一次回滚：`bash deploy/deploy.sh <prev-sha>`，确认字典与 uploads
   存活（实例 `git status` 干净）。注意 `access-control.yaml` 现在跟踪在仓库里，
   **会跟着回到那个 commit 的版本**——回滚到 #204 之前的 sha，它会消失、数据面回到
   503「未配置」。这是配置与代码同版本的正确行为，别当故障（§5b）
