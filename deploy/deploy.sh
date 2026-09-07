#!/usr/bin/env bash
# Deploy (and rollback) script, run ON the Lightsail instance.
# Invoked by .github/workflows/deploy.yml over SSH, or manually:
#
#   bash deploy/deploy.sh              # deploy origin/main
#   bash deploy/deploy.sh <sha>        # roll back to a previous commit
#
# Never `git clean` here: env.sh, data/mappings/field-dictionary.yaml,
# data/uploads/, data/outputs/ and plugins/dist are gitignored instance
# state that must survive every deploy (see docs/22-lightsail-deploy.md).
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"  # uv
ROOT="$HOME/Hackathon2026/BridgeFlow-AI"
VENV="$HOME/Hackathon2026/.venv/bin/python"

cd "$ROOT"
git fetch origin main
git reset --hard "${1:-origin/main}"

# Dependencies and the client bundle are rebuilt every deploy: both are
# cached and take seconds, and the rebuild keeps dist/client.js newer than
# its sources, which start_web.py checks at launch.
uv pip install -e "backend[dsh,dev]" --python "$VENV"
pnpm --dir plugins install --frozen-lockfile
pnpm --dir plugins run build

sudo systemctl restart bridgeflow

ok=""
for _ in $(seq 1 30); do
  sleep 2
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 \
     && systemctl is-active --quiet bridgeflow; then
    ok=1
    break
  fi
done

if [ -z "$ok" ]; then
  echo "health check failed after deploy" >&2
  journalctl -u bridgeflow -n 60 --no-pager >&2
  exit 1
fi

echo "deployed $(git rev-parse --short HEAD)"
