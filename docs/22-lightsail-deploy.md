# 22 — AWS Lightsail 部署（GitHub Actions 自动部署）

目标：合并到 `main` 即自动测试并部署到 Lightsail 实例；公网经 Caddy
（自动 HTTPS）进入，身份由统一登录门户（飞书 OAuth，[`27`](27-login-portal.md)）
承担，**不用 Docker**。

流水线在 `.github/workflows/deploy.yml`（本仓库唯一 CI 文件），
实例侧脚本 `deploy/deploy.sh`，systemd 单元 `deploy/bridgeflow.service`。

**每一步都有验证命令。验证不过不要往下走。**

§2–§8 已写成可重复执行的 `deploy/bootstrap.sh <domain>`（不写任何密钥），§12 的机器可查部分写成只读的
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
必须在门户进程起来之前就位也行，Caddy 会各自签证书：

```caddyfile
<domain> {
    reverse_proxy 127.0.0.1:3080
}

portal.<domain> {
    reverse_proxy 127.0.0.1:8100
}
```

```bash
sudo systemctl reload caddy
```

Caddy 反代默认透传 `Host`、原生支持 WebSocket 升级、无请求体大小上限
（约 26 MiB 的上传路径不受阻）。

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
export PORTAL_APPS_PATH="$HOME/Hackathon2026/portal-apps.yaml"
# 后端验签与 dsh web 代理下发门户地址共用这一个变量；必须与上面一致
# （验签时 iss 按它逐字节比对）：
export PORTAL_BASE_URL="https://portal.<domain>"
```

`~/Hackathon2026/portal-apps.yaml`（实例文件，不进仓库；仓库里的
`portal/apps.yaml` 保留给本地开发）：

```yaml
apps:
  bridgeflow:
    audience: bridgeflow
    redirect_uri: "https://<domain>/"
    origins:
      - "https://<domain>"
```

```bash
sudo cp deploy/portal.service /etc/systemd/system/bridgeflow-portal.service
sudo systemctl daemon-reload
sudo systemctl enable --now bridgeflow-portal
```

**验证（按顺序，不过就停）**

```bash
curl -fsS http://127.0.0.1:8100/health                    # feishu 与 signer 均为 true
curl -fsS https://portal.<domain>/health                  # 同上，证明 Caddy 站点与证书就位
curl -sI 'https://portal.<domain>/login?app=bridgeflow'   # 期望 302 到 open.feishu.cn
```

### 9c 后端开身份层 + 首登拿 union_id

```bash
sudo systemctl restart bridgeflow   # 后端与 web 代理拿到 PORTAL_BASE_URL
```

浏览器打开主站：数据路由 401 → 界面出现「飞书登录」入口 → 完成 OAuth →
浏览器直接访问 `https://portal.<domain>/me` 拿到自己的 union_id →
写 `data/mappings/access-control.yaml`（格式见同目录 `.example`；gitignored，
部署不动它）→ 再 `sudo systemctl restart bridgeflow`。

文件缺失时数据面是 503「未配置」，这是设计的中间态（fail-closed），不是故障。

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
6. 演示前排练一次回滚：`bash deploy/deploy.sh <prev-sha>`，确认字典、
   uploads 与 `access-control.yaml` 存活（实例 `git status` 干净）
