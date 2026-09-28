<p align="center"><strong>English</strong> · <a href="README.zh.md">简体中文</a></p>

# BridgeFlow AI

BridgeFlow combines monthly spreadsheets from production, procurement, finance and marketing into a traceable master table. It uses the official DeepSeek Harness for the Web workspace, AI agents, sessions and approvals; Python performs calculations from declared business rules.

**Release:** [v1.0.0](https://github.com/EricWang1358/BridgeFlow-AI/releases/tag/v1.0.0) · [Release notes](docs/releases/1.0.0.md)

## What you can do

- Import department spreadsheets, resolve column mappings, inspect cleaning results and trace a figure to its source.
- Run a four-department AI review, inspect cited findings and export a monthly brief or workbook.
- Review and publish a field dictionary; approve model-initiated writes through native approval cards.
- Explore discovery materials, opportunity scoring, approved scope, record filling and department handoffs.
- Save notebooks, follow guided sample tasks, and use the Chinese or English interface and built-in user guide.

The repository includes sample datasets and declared template schemas. They are examples for development and demonstration, not customer exports. Read the [limitations](docs/limitations.md) before using your own business data.

## Quick start

Use Linux or WSL2, Python 3.12 or 3.13, and Node.js 22. Keep the checkout in the Linux filesystem when using WSL. The package manager version is pinned in `plugins/package.json`.

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

Edit `env.sh` to set your model credentials and an absolute `DSH_HOME` outside the checkout. Then start the sample workspace:

```bash
source env.sh
python scripts/start_web.py --demo --port 3082
```

Open the launch URL printed by the process. The URL contains a local session token; keep it private. For a sample-only workspace with AI disabled, use `python scripts/start_web.py --guest --port 3090` instead.

Choose **Sources → Open sample notebook**, then **Data → Cross-department master**. Explore the sample files and guided tours without model calls. **Start the review** uses the configured model and incurs provider charges.

For detailed setup and troubleshooting, see [Setup](docs/setup.md). The [English user guide](docs/user-guide.en.md) and [中文使用说明书](docs/user-guide.zh.md) are also available inside **Sessions & settings → User guide**.

## Documentation

| Topic | Guide |
| --- | --- |
| Installation and configuration | [Setup](docs/setup.md) |
| Everyday use | [User guide](docs/user-guide.en.md) |
| Architecture and data boundaries | [Architecture](docs/architecture.md) |
| Tests and development | [Development](docs/development.md) |
| Self-hosting, portal and guest mode | [Deployment](docs/deployment.md) |
| Supported scope and known gaps | [Limitations](docs/limitations.md) |
| Field dictionary and configuration examples | [Mapping configuration](data/mappings/README.md) |

DeepSeek Harness remains pinned to `0.1.2-rc.1` (`deepseek-harness-sdk==0.1.2rc1`). Use the supplied installer and lockfiles when reproducing this release.
