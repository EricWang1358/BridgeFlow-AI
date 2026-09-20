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
# The seat fleet (data/mappings/seats.yaml) is static capacity committed via PR,
# so reset --hard is safe for it; the runtime claims (data/seats-assigned.json)
# are untracked instance state and survive every reset untouched.
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
# Seat consoles load the host-side plugin and the client bundle at their own
# boot; without this they keep serving the previous deploy's code until an
# unlucky per-unit restart (docs/35 §8: backend and portal first, then seats).
SEAT_UNITS=()
while IFS= read -r unit; do
  [ -n "$unit" ] && SEAT_UNITS+=("$unit")
done < <(systemctl list-units 'bridgeflow-dsh@*' --no-legend --plain 2>/dev/null | awk '{print $1}')
if [ "${#SEAT_UNITS[@]}" -gt 0 ]; then
  sudo systemctl restart "${SEAT_UNITS[@]}"
fi

ok=""
for _ in $(seq 1 30); do
  sleep 2
  # Bounded curl: without --max-time a stalled request could outlast the
  # whole 30×2s retry budget.
  #
  # Web liveness depends on the deployed shape (docs/35): with --backend-only
  # in bridgeflow.service the consoles live in bridgeflow-dsh@* units and 3080
  # is legitimately dead. Between this deploy's arrival and the first
  # provisioning there is no web surface at all — warn and pass; preflight
  # owns that window. Legacy shape keeps the old bar on 3080: "someone
  # answers" (status != 000), not 200 — its session fence may refuse.
  web_ok=""
  if grep -q -- "--backend-only" deploy/bridgeflow.service; then
    for unit in "${SEAT_UNITS[@]}"; do
      if systemctl is-active --quiet "$unit"; then web_ok=1; break; fi
    done
    if [ -z "$web_ok" ] && [ "${#SEAT_UNITS[@]}" -eq 0 ]; then
      echo "seat mode deployed but no seat provisioned yet — web liveness skipped (bootstrap + provision_seat, docs/35 §8)" >&2
      web_ok=1
    fi
  else
    web_code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 \
      http://127.0.0.1:3080/ || true)
    [ "$web_code" != "000" ] && web_ok=1
  fi
  if [ -n "$web_ok" ] \
     && curl -fsS --connect-timeout 2 --max-time 5 http://127.0.0.1:8000/health >/dev/null 2>&1 \
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
