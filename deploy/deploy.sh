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
# its sources, which start_web.py checks at launch. The portal is installed
# into the same venv so bridgeflow-portal.service can import portal_app.
uv pip install -e "backend[dsh,dev]" -e portal --python "$VENV"
(
  cd plugins
  # Resolve the committed packageManager pin, not the instance-global pnpm.
  corepack pnpm install --frozen-lockfile
  corepack pnpm run build
)

sudo systemctl restart bridgeflow bridgeflow-portal

ok=""
for _ in $(seq 1 30); do
  sleep 2
  # Bounded curl: without --max-time a stalled request could outlast the
  # whole 30×2s retry budget.
  if curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1 \
     && curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:8100/health >/dev/null 2>&1 \
     && systemctl is-active --quiet bridgeflow \
     && systemctl is-active --quiet bridgeflow-portal; then
    ok=1
    break
  fi
done

if [ -z "$ok" ]; then
  echo "health check failed after deploy" >&2
  journalctl -u bridgeflow -u bridgeflow-portal -n 60 --no-pager >&2
  exit 1
fi

echo "deployed $(git rev-parse --short HEAD)"
