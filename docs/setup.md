# Setup

## Requirements

Use Linux or WSL2 with Python 3.12 or 3.13 and Node.js 22. Python packages declare a minimum of 3.11; CI exercises Python 3.13. Under WSL, use a Linux path rather than `/mnt` for the repository, virtual environment and runtime home.

Follow the [README quick start](../README.md#quick-start). Install the `dsh` extra with the backend: it provides the pinned Python SDK. `scripts/install_dsh.sh` installs the matching CLI beside the repository using its lockfile. It does not replace a global installation. `bash scripts/install_dsh.sh --check` reports the selected CLI.

The default layout is:

```text
~/Hackathon2026/
├── BridgeFlow-AI/
├── .venv/
├── .dsh-cli/
└── .dsh-bridgeflow/
```

## Launch configuration

Copy `env.sh.example` to `env.sh`, edit it locally, and run `source env.sh` before starting a process. This file is ignored by Git.

| Variable | Purpose |
| --- | --- |
| `DSH_HOME` | Absolute runtime-home path outside the checkout |
| `DSH_PROFILE` | Use `sdk-minimal` for the supplied configuration |
| `DSH_PROVIDER`, `DSH_MODEL` | Default provider and model; select values your provider supports |
| `DEEPSEEK_API_KEY` | Model credential; keep it local |
| `DEEPSEEK_BASE_URL` | Optional alternate endpoint; leave unset for the provider default |
| `FIELD_DICTIONARY_PATH` | Your declared field dictionary for real imports |

The model last selected in the Web interface takes precedence over shell defaults. To switch models, use **Sessions & settings**. Never place `DSH_*` or `DEEPSEEK_BASE_URL` in a `.env` file: the runtime requires these bootstrap settings to come from the launching shell.

```bash
source ../.venv/bin/activate
source env.sh
python scripts/start_web.py --demo --port 3082
```

`--demo` selects the included sample dictionary. Use a business-approved dictionary for your own imports; see [mapping configuration](../data/mappings/README.md). Open the token-bearing URL printed by the launcher, rather than typing a bare URL on first access.

## Sample-only guest workspace

```bash
python scripts/start_web.py --guest --port 3090
```

Guest mode uses separate runtime/data directories, blocks file uploads and disables AI by default. Built-in sample notebooks and tours remain available. AI-enabled public guest deployments require the separate model gate described in [Deployment](deployment.md).

## Common startup problems

| Symptom | Check |
| --- | --- |
| Wrong CLI version | Run `bash scripts/install_dsh.sh --check`; use `BRIDGEFLOW_DSH` only for an explicitly installed matching CLI |
| Client bundle is missing or older than its source | Run `pnpm --dir plugins build` |
| Model credential missing | Check the model selected in the interface and its provider credentials |
| Dictionary is not configured | Use `--demo` for examples or configure an approved dictionary |
| Opening the console returns 401 | Use the current launch URL; for hosted staff access, sign in through the configured portal |
| Port already in use | Stop the process that owns the port or choose another `--port` |

Configuration files, uploaded data, runtime sessions and model credentials belong to the installation, not to source control.
