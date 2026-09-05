# 14 — WSL (Ubuntu 22.04) 开发环境搭建

目标：把仓库和 dsh 运行时完整放进 WSL 文件系统，与 Windows 上日常使用的 dsh **完全隔离**。

**每一步都有验证命令。验证不过不要往下走** —— 后面的坑会难查得多。

---

## 0 为什么不能放在 `/mnt/d`

不是"慢一点"的问题：

| 问题 | 后果 |
| --- | --- |
| 走 9p/drvfs 协议 | git、pnpm、pip 慢一个量级 |
| inotify 不工作 | dsh 的文件监听、任何 watch 模式**静默失效** |
| 权限位丢失 | 全部 777，可执行位没有语义 |
| 大小写敏感性不一致 | Linux 下能过的代码在这里行为不同 |

**规则：仓库、虚拟环境、`DSH_HOME`、`node_modules` 全部放在 `~` 下，一个都不放 `/mnt`。**

实测差距：dsh 运行时启动在 WSL 文件系统内 **0.5s**，在 Windows 上 **3.6s** ——
同一个运行时，七倍。

---

## 1 系统基础

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl wget git ca-certificates software-properties-common
```

**验证**

```bash
lsb_release -d && ldd --version | head -1
```

期望：`Ubuntu 22.04`，glibc `2.35`。
glibc ≥ 2.28 是 `deepseek_harness_runtime_bin` 的 `manylinux_2_28` wheel 的要求，2.35 满足。

---

## 2 Python 3.12

Ubuntu 22.04 自带 3.10，但本项目要求 ≥3.11（代码使用 `datetime.UTC`）。用 deadsnakes 装 3.12：

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

**不要动系统默认的 `python3`** —— Ubuntu 自身依赖 3.10，改默认会弄坏系统工具。我们只在项目虚拟环境里用 3.12。

**验证**

```bash
python3.12 -V          # 期望 Python 3.12.x
python3 -V             # 期望 Python 3.10.x —— 系统默认，不该被改
```

---

## 3 Node 与 pnpm

Python SDK 跑 dsh **不需要** Node（运行时是打包好的可执行文件）。
但我们要写 TS 插件，`dsh plugin add` 管理外部包时需要 pnpm。

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
sudo corepack enable
corepack prepare pnpm@latest --activate
```

**验证**

```bash
node -v && pnpm -v     # 期望 v22.x 和 pnpm 版本号
```

---

## 4 GitHub CLI 与认证

仓库是 private，需要认证才能 clone。

```bash
(type -p wget >/dev/null || sudo apt install wget -y) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
     | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
     | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update && sudo apt install gh -y
```

登录（会给一个网页 code，在 Windows 浏览器里完成）：

```bash
gh auth login -s project,read:project
```

**验证**

```bash
gh auth status         # 期望看到 EricWang1358，scopes 含 project
```

---

## 5 Clone 仓库

```bash
mkdir -p ~/Hackathon2026 && cd ~/Hackathon2026
gh repo clone EricWang1358/BridgeFlow-AI
cd ~/Hackathon2026/BridgeFlow-AI
```

仓库是 private，所以**必须先完成第 4 节的登录**，否则会报 404 或要求输入密码。
这是唯一的限制 —— 没有别的东西阻止 clone。

**验证**

```bash
pwd                    # 期望 /home/eric/Hackathon2026/BridgeFlow-AI，绝不能出现 /mnt
git log --oneline -1
```

### 目录布局

```
~/Hackathon2026/
├── BridgeFlow-AI/          ← git 仓库，唯一的源码事实来源
│   ├── backend/              Python 实现体
│   ├── plugins/              TS 插件源码（后续新增）
│   ├── scripts/ docs/ data/
├── .venv/                  ← Python 虚拟环境，在仓库之外
└── .dsh-bridgeflow/        ← DSH_HOME，在仓库之外
```

**`.venv` 与 `.dsh-bridgeflow` 都放在仓库外面**，这样它们不可能被误提交，
`git status` 也永远干净。分界线是：**源码进仓库，运行时状态不进**。

---

## 6 Python 环境与依赖

虚拟环境建在 `~/Hackathon2026/`（仓库外），依赖从 `backend/` 安装：

```bash
cd ~/Hackathon2026
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip

cd ~/Hackathon2026/BridgeFlow-AI/backend
pip install -e ".[dev]"
pip install --pre "deepseek-harness-sdk==0.1.2rc1"
```

`pip install -e` 必须在 `backend/` 下执行（`pyproject.toml` 在那里），
但装进的是 `~/Hackathon2026/.venv`。以后每开一个 shell，`source ~/Hackathon2026/.venv/bin/activate` 即可。

**验证**

```bash
python -c "import deepseek_harness, pandas, fastapi; print('imports ok')"
ruff check src tests && pytest -q
```

期望：`All checks passed!` 与 19 passed。

---

## 7 项目专属 DSH_HOME（与你日常那套隔离）

dsh 的 SDK **刻意不去发现 `~/.dsh`**，`DSH_HOME` 必填且无默认值 —— 这正是为隔离设计的。
我们指向一个项目专属目录，你 Windows 上日常使用的 dsh 完全不受影响。

```bash
mkdir -p ~/Hackathon2026/.dsh-bridgeflow
```

### 关键：引导变量必须 export，不能写进 `.env`

**dsh 会扫描它工作目录下的 `.env`，并拒绝从文件里读取引导类变量：**

```
dsh: .../backend/.env sets "DSH_HOME", which only the launching environment
may set (it decides how this process starts, where its code and instructions
load from, or how it reaches the network); export DSH_HOME instead of putting
it in a .env file
```

被拒绝的是 `DSH_*` 与 `DEEPSEEK_BASE_URL` —— 它们决定**代码从哪里加载**和
**网络去往哪里**。

**这是安全边界，不是麻烦。** 如果这类变量能从项目携带的文件里读取，那么
clone 一个恶意仓库就足以重定向运行时的代码加载路径和网络出口。
**不要试图绕过它**（比如改 dsh 的 cwd 让它扫不到 `.env`）。

> 一个空行 `DEEPSEEK_BASE_URL=` **也算"已设置"**，同样会被拒绝。
> 必须是整行不存在，而不是留空。

### 分成两个文件

| 文件 | 内容 | 读取者 |
| --- | --- | --- |
| `env.sh`（仓库根，需 `source`） | `DSH_*`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` | 启动 shell |
| `backend/.env` | `LLM_PROVIDER`、`API_HOST`、`CORS_ORIGINS`、阈值等应用配置 | pydantic-settings |

两个都在 `.gitignore` 里。

```bash
cd ~/Hackathon2026/BridgeFlow-AI
cp env.sh.example env.sh
# 编辑 env.sh 填入 DEEPSEEK_API_KEY
source env.sh

cd backend
cp .env.example .env
echo "LLM_PROVIDER=dsh" >> .env
```

每开一个新 shell 都要重新 `source ~/Hackathon2026/BridgeFlow-AI/env.sh`。
嫌麻烦可以加进 `~/.bashrc`，但那样就不是项目隔离了 —— 建议保持显式 source。

**验证**

```bash
echo "DSH_HOME=$DSH_HOME"
echo "KEY 长度=${#DEEPSEEK_API_KEY}"          # 不回显 key 本身
grep -E '^(DSH_|DEEPSEEK_BASE_URL)' backend/.env && echo "❌ 上面这些要从 .env 删掉" \
  || echo "✅ .env 里没有引导变量"
ls -la ~/Hackathon2026/.dsh-bridgeflow
```

---

## 8 冒烟测试：确认 dsh 真的跑得起来

```bash
source ~/Hackathon2026/.venv/bin/activate
source ~/Hackathon2026/BridgeFlow-AI/env.sh     # 引导变量必须来自启动环境
cd ~/Hackathon2026/BridgeFlow-AI/backend
python ../scripts/smoke_dsh.py
```

**期望输出**

```
--- 1. raw SDK: plain turn ---
  started in ~0.5s
  finish_reason = 'completed'
  final_response = 'ok'

--- 2. our DshProvider: structured output ---
  parsed = Verdict(confidence=..., justification='...')

=== SMOKE TEST PASSED ===
```

首次运行会初始化 profile，比后续慢。**这一步不过，后面所有 dsh 相关工作都无从谈起。**

**若报 `TransportClosedError: runtime stdout closed`**，看 stderr 尾部——
多半是某个引导变量还留在 `.env` 里。按上一节的验证命令逐个清掉。

---

## 8.5 插件放哪里：不 fork dsh

**不需要 fork `deepseek-harness`。** dsh 支持安装本地 bundle：

```bash
dsh plugin --profile sdk-minimal add file:$HOME/Hackathon2026/BridgeFlow-AI/plugins/bridgeflow-tools
```

`file:` 形式把本地 bundle 装进 profile 的包树，所以**插件源码留在我们自己的仓库里**，
dsh 那边只是安装目标。

**什么时候才需要 fork**：要改 dsh 核心行为、而所有 seam（`ctx.tools`、`tools/pre-execute`、
`ctx.approval`、`ctx.tools.guard()`）都覆盖不到的时候。目前的需求全在 seam 覆盖范围内。

而且 dsh **所有已发布版本都是预发布、且明示会有破坏性变更** —— fork 意味着三周里
持续处理 merge 冲突，与我们"版本固定 `==0.1.2rc1`"的决定直接矛盾。

### 开发循环的一个未验证点

`add file:` 是**拷贝**进 profile 包树，所以改完插件源码需要重新安装。
是否存在 link / watch 之类的开发模式尚未查证 —— 这会影响迭代速度，
是环境搭好后要第一批验证的事情。

---

## 9 在 WSL 里安装 Claude Code 并登录

目标环境就是 Linux，会话也该在这里 —— 路径、权限、工具链全部对齐。

```bash
sudo npm install -g @anthropic-ai/claude-code
claude --version
```

首次登录：

```bash
cd ~/Hackathon2026/BridgeFlow-AI
claude
```

它会打印一个登录 URL。WSL 里没有默认浏览器，两种处理方式：

- **推荐**：把 URL 复制到 Windows 浏览器打开，完成后把回调 code 粘回终端
- 或装一个转发器，让 `xdg-open` 直接调起 Windows 浏览器：
  ```bash
  sudo apt install -y wslu       # 提供 wslview
  echo 'export BROWSER=wslview' >> ~/.bashrc && source ~/.bashrc
  ```

用你自己的账户登录即可。凭据存在 WSL 侧的 `~/.claude`，与 Windows 那份**互不影响**。

在项目根目录启动会话，这样工作目录、git 仓库、项目配置都对得上。

---

## 10 端口转发：从 Windows 测试 WSL 里的服务

### 10.1 默认路径（优先试这个，通常够用）

WSL2 默认开启 `localhostForwarding`。只要服务监听在 **`0.0.0.0`**，
Windows 浏览器开 `localhost:<端口>` 就能访问。

后端：

```bash
cd ~/Hackathon2026/BridgeFlow-AI/backend
source ~/Hackathon2026/.venv/bin/activate
uvicorn bridgeflow.api.main:app --host 0.0.0.0 --port 8000 --reload
```

dsh web（端口以它自己打印的为准）：

```bash
DSH_HOME=$HOME/Hackathon2026/.dsh-bridgeflow <运行时路径>/dsh web
```

**验证 —— 先在 WSL 内确认监听地址，这是最常见的失败点**

```bash
ss -tlnp | grep 8000
```

看 `Local Address`：

- `0.0.0.0:8000` 或 `*:8000` → Windows 能访问 ✅
- `127.0.0.1:8000` → **只有 WSL 内部能访问**，Windows 连不上 ❌

然后在 Windows PowerShell：

```powershell
curl.exe http://localhost:8000/health
```

期望返回 `{"status":"ok",...}`。

### 10.2 兜底路径

先确认 `C:\Users\<你>\.wslconfig` 没有关掉转发：

```ini
[wsl2]
localhostForwarding=true
```

改完要 `wsl --shutdown` 才生效。

仍然不通再用 portproxy。**注意：WSL2 的 IP 每次重启会变，这条要重新执行**：

```powershell
# Windows PowerShell（管理员）
$ip = (wsl -d Ubuntu-22.04 -e hostname -I).Trim().Split()[0]
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$ip
netsh interface portproxy show v4tov4
# 清理
# netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
```

只在本机 Windows 测试的话到此为止，**不要动防火墙**。只有局域网里其他设备也要访问时才需要：

```powershell
New-NetFirewallRule -DisplayName "BridgeFlow 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 10.3 排查顺序

| 现象 | 先查 |
| --- | --- |
| Windows `curl` 拒绝连接 | `ss -tlnp` 是不是绑在 `127.0.0.1` |
| WSL 内 `curl` 也不通 | 服务根本没起来，看进程日志 |
| 之前能连，现在不行 | WSL 重启过 IP 变了（用了 portproxy 才受影响） |
| 只有别的机器连不上 | Windows 防火墙 |

---

## 11 保证 AWS 部署不受影响

WSL 是开发环境，它的痕迹不能固化进仓库。以下已处理好，**改代码时请维持**。

### 11.1 地址与端口是配置，不是常量

```python
# backend/src/bridgeflow/config.py
api_host: str = "127.0.0.1"                    # 默认不对外暴露
api_port: int = 8000
cors_origins: str = "http://localhost:3000"    # 逗号分隔
```

CORS 源原先硬编码为 `http://localhost:3000` —— **部署到 AWS 会直接坏**，现已改为配置项。

生产环境用环境变量覆盖，不改代码：

```bash
API_HOST=0.0.0.0
CORS_ORIGINS=https://your-domain.example
```

**默认值保持 `127.0.0.1`**：默认不暴露，要暴露必须显式声明。
容器里绑 `0.0.0.0` 是对的（`backend/Dockerfile` 就是这样），但那是**部署层的决定**，
不该写死进应用源码。

### 11.2 `.gitignore` 覆盖的东西

```
.env  .env.*（保留 .env.example）  *.key  *.pem
.venv/  node_modules/
.dsh*/                                  ← dsh home 若被误放进仓库
data/mappings/field-dictionary.yaml     ← 真实 OA 主数据，只跟踪 example
data/uploads/  data/outputs/  *.log
```

`DSH_HOME` 本来就应在仓库之外（`~/Hackathon2026/.dsh-bridgeflow`）。`.dsh*/` 是防呆 ——
万一有人指错，profile、凭据、会话不会被提交。

### 11.3 绝对路径只能出现在 `.env`

`DSH_HOME` 必须是绝对路径，但它只存在于 `.env`，而 `.env` 不进仓库。
**任何 `/home/<用户名>/...` 都不该出现在被跟踪的文件里。**

### 11.4 换行符

`.gitattributes` 已设 `* text=auto eol=lf`。即使有人在 Windows 上编辑，
进仓库的也是 LF，AWS 上不会出现 `bad interpreter: ^M`。

### 11.5 验证：仓库里有没有环境特定的痕迹

```bash
cd ~/Hackathon2026/BridgeFlow-AI
git ls-files | xargs grep -ln "/home/\|/mnt/\|[A-Z]:\\\\" 2>/dev/null
```

**期望：只匹配到文档。** 若匹配到 `backend/src` 或配置文件，说明有环境特定的值被写死。

`0.0.0.0` 单独查，因为它在部署文件里是合法的：

```bash
git ls-files | xargs grep -ln "0\.0\.0\.0" 2>/dev/null
```

**允许**出现在 `Dockerfile`、`.env.example`、文档里；**不允许**出现在 `backend/src/` 下。

---

## 12 常见坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `pip install` 极慢 | 装在了 `/mnt/...` 下 | 确认 `pwd` 不含 `/mnt` |
| `DSH_HOME` 报错必填 | 用了相对路径或未设置 | 必须绝对路径 |
| 文件改动不触发重载 | inotify 跨 `/mnt` 失效 | 同上，别放 `/mnt` |
| `python3` 是 3.10 | 系统默认，正常 | 虚拟环境里用 3.12，别改系统默认 |
| 误用了日常 dsh 的配置 | `DSH_HOME` 没设或指错 | SDK 不会回退到 `~/.dsh`，报错即说明没设 |
| WSL 冷启动很久 | 首次启动发行版 | `wsl -d Ubuntu-22.04 -e true` 预热 |
| Windows 连不上服务 | 服务绑在 `127.0.0.1` | 见 10.1 |
| `claude` 打不开浏览器 | WSL 无默认浏览器 | 复制 URL 到 Windows，或装 `wslu` |

---

## 13 完成后

Windows 上的 `D:\A\1NUS\1Sem\1Hackathon\BridgeFlow-AI` 与 `.dsh-home` 可以删除 ——
工作树已全部推送，没有本地独有的代码。

你 Windows 上日常使用的 dsh 与 Claude Code 均不受影响：
两边的 `DSH_HOME` 和 `~/.claude` 各自独立。

---
