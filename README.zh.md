<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

# BridgeFlow AI

BridgeFlow 将生产、物资、财务、市场四个部门的月度表格整理为可追溯的跨部门主表。官方 DeepSeek Harness 提供 Web 工作区、代理、会话和审批；Python 按已声明的业务规则计算数字。

**正式版本：** [v1.0.0](https://github.com/EricWang1358/BridgeFlow-AI/releases/tag/v1.0.0) · [发布说明](docs/releases/1.0.0.md)

## 主要功能

- 导入部门表格，确认字段映射，检查清洗结果，并追溯数字的来源。
- 运行四部门 AI 研判，核对结论引用，导出月度简报和工作簿。
- 审核并发布字段字典，通过原生审批卡确认代理发起的写入。
- 从材料立项、候选评分和范围确认，衔接到填报与部门交接。
- 保存笔记本，跟随示例引导操作，使用中英文界面与内置说明书。

仓库附带演示数据与声明式模板，供开发和演示使用，不包含客户业务导出。用于自己的业务前，请先阅读[适用范围与已知限制](docs/limitations.md)。

## 快速开始

需要 Linux 或 WSL2、Python 3.12 或 3.13、Node.js 22。WSL 下请将代码放在 Linux 文件系统中。包管理器版本由 `plugins/package.json` 锁定。

```bash
mkdir -p ~/Hackathon2026
cd ~/Hackathon2026
git clone --branch v1.0.0 https://github.com/EricWang1358/BridgeFlow-AI.git
cd BridgeFlow-AI
python3.12 -m venv ../.venv
source ../.venv/bin/activate
python -m pip install -U pip
python -m pip install -e 'backend[dsh,dev]'
bash scripts/install_dsh.sh
corepack enable
pnpm --dir plugins install --frozen-lockfile
pnpm --dir plugins build
cp env.sh.example env.sh
```

编辑 `env.sh`，配置模型凭据，并将 `DSH_HOME` 设为仓库外的绝对路径。然后启动示例工作区：

```bash
source env.sh
python scripts/start_web.py --demo --port 3082
```

打开进程打印的启动链接。链接含有本机会话令牌，请勿公开分享。只想浏览示例、不调用模型时，可改用 `python scripts/start_web.py --guest --port 3090`。

先在左侧选择 **来源 → 打开示例笔记本**，再查看 **数据 → 跨部门总表**。样例文件和操作引导无需调用模型；**发起研判**会调用已配置的模型服务并产生费用。

详细安装与排错见[安装说明](docs/setup.md)。日常操作见[中文使用说明书](docs/user-guide.zh.md)，产品内也可从 **会话与设置 → 使用说明书** 打开。

## 文档

| 内容 | 入口 |
| --- | --- |
| 安装与配置 | [安装说明](docs/setup.md) |
| 日常使用 | [使用说明书](docs/user-guide.zh.md) |
| 架构与数据边界 | [技术架构](docs/architecture.md) |
| 测试与开发 | [开发说明](docs/development.md) |
| 自行部署、登录门户与访客模式 | [部署说明](docs/deployment.md) |
| 适用范围与已知缺口 | [限制说明](docs/limitations.md) |
| 字段字典与配置模板 | [映射配置](data/mappings/README.md) |

DeepSeek Harness 固定为 `0.1.2-rc.1`，Python SDK 固定为 `deepseek-harness-sdk==0.1.2rc1`。复现此版本时请使用仓库提供的安装脚本与锁文件。
