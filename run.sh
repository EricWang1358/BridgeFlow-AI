#!/usr/bin/env bash
# One-command local launcher: venv + bootstrap env + native DSH Web.
#
#   ./run.sh              # default ports (backend 8000)
#   ./run.sh --demo       # use the business-demo dictionary explicitly
#   ./run.sh --port 3082  # pick the Web port
#
# Prerequisites (one-time), see HANDOFF.md:
#   uv venv --python 3.13 ../.venv
#   uv pip install -e "backend[dsh,dev]" --python ../.venv/bin/python
#   npm install -g pnpm @deepseek-ai/dsh@0.1.2-rc.1
#   (cd plugins && pnpm install --frozen-lockfile && pnpm run build)
#   cp env.sh.example env.sh   # then fill DEEPSEEK_API_KEY

set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f env.sh ]]; then
  echo "env.sh missing. Run: cp env.sh.example env.sh  (then fill DEEPSEEK_API_KEY)" >&2
  exit 1
fi
if [[ ! -x ../.venv/bin/python ]]; then
  echo "../.venv missing. Run: uv venv --python 3.13 ../.venv && uv pip install -e \"backend[dsh,dev]\" --python ../.venv/bin/python" >&2
  exit 1
fi

# shellcheck disable=SC1091
source env.sh
exec ../.venv/bin/python scripts/start_web.py "$@"
