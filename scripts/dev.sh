#!/usr/bin/env bash
# One-command local bring-up and restart: rebuild the plugin bundle, stop any
# previous instances, then run the login portal (:8100) plus backend + dsh web
# (:3082). Ctrl-C stops everything. Logs land in logs/{portal,web}.log.
#
#   scripts/dev.sh                # start (or restart)
#   PYTHON=/path/to/python scripts/dev.sh   # override the interpreter
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-$(pwd)/../.venv/bin/python}"
[[ -x "$PY" ]] || { echo "venv python not found at $PY — set PYTHON=/path/to/python" >&2; exit 1; }
[[ -f env.sh ]] || { echo "env.sh missing — copy env.sh.example and fill in credentials" >&2; exit 1; }
source ./env.sh

echo "==> building plugin bundle"
pnpm --dir plugins build

echo "==> stopping previous instances"
pkill -f "uvicorn portal_app.main" 2>/dev/null || true
pkill -f "start_web.py" 2>/dev/null || true
sleep 1

# The portal cannot boot without its Ed25519 key; mint a local one if absent.
# A relative PORTAL_KEY_PATH means repository-root-relative — the check below and
# the keygen (which runs from portal/) must agree, so normalize to absolute first.
if [[ -n "${PORTAL_KEY_PATH:-}" && "$PORTAL_KEY_PATH" != /* ]]; then
  PORTAL_KEY_PATH="$(pwd)/$PORTAL_KEY_PATH"
fi
if [[ -n "${PORTAL_KEY_PATH:-}" ]]; then
  export PORTAL_KEY_PATH
fi
if [[ -n "${PORTAL_KEY_PATH:-}" && ! -f "$PORTAL_KEY_PATH" ]]; then
  echo "==> generating portal key at $PORTAL_KEY_PATH"
  (cd portal && PYTHONPATH=src "$PY" -m portal_app.keygen "$PORTAL_KEY_PATH")
fi

mkdir -p logs
echo "==> portal :8100 (logs/portal.log)"
# --ws none matches deploy/portal.service (the portal has no WebSocket route;
# see that unit's header). Local dev has no forward_auth in front of it, so the
# flag changes nothing here — which is the point: this bug survived because the
# dev flow and the instance launched the same process differently.
(cd portal && PYTHONPATH=src "$PY" -m uvicorn portal_app.main:app --host 127.0.0.1 --port 8100 --ws none) > logs/portal.log 2>&1 &
PORTAL_PID=$!
trap 'kill "$PORTAL_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 50); do
  curl -sf http://127.0.0.1:8100/health > /dev/null 2>&1 && break
  sleep 0.2
done
curl -sf http://127.0.0.1:8100/health > /dev/null || { echo "portal did not become ready; see logs/portal.log" >&2; exit 1; }

echo "==> backend + dsh web :3082 (logs/web.log)"
"$PY" scripts/start_web.py --demo --port 3082 2>&1 | tee logs/web.log
