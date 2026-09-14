#!/usr/bin/env bash
# Read-only checks on the instance before enabling CI deploys (docs/22 §13). Changes nothing.
#
#   bash deploy/preflight.sh <domain>
#
# Prints one line per check and exits non-zero if any fails.
set -uo pipefail

DOMAIN="${1:?usage: bash deploy/preflight.sh <domain>}"
ROOT="$HOME/Hackathon2026/BridgeFlow-AI"
failed=0
check() {  # check <description> <command...>
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $what"; else echo "FAIL  $what"; failed=1; fi
}

cd "$ROOT" || { echo "FAIL  repository at $ROOT"; exit 1; }
check "env.sh exists and is private (600)" test "$(stat -c %a env.sh 2>/dev/null)" = 600
check "no bootstrap variables in any .env" bash -c '! grep -qsE "^(export )?(DSH_[A-Z_]*|DEEPSEEK_BASE_URL)=" .env backend/.env'
# shellcheck disable=SC1091
check "DSH_HOME is absolute and outside the repository" bash -c 'source env.sh && [[ "$DSH_HOME" = /* && "$DSH_HOME" != "'"$ROOT"'"* && -d "$DSH_HOME" ]]'
check "DEEPSEEK_API_KEY is filled" bash -c 'source env.sh && [[ -n "${DEEPSEEK_API_KEY:-}" && "$DEEPSEEK_API_KEY" != "..." ]]'
check "dsh CLI is the pinned 0.1.2-rc.1" bash -c 'dsh --version | grep -q 0.1.2-rc.1'
check "client bundle is built" test -f plugins/dist/client.js
check "working tree is clean (instance state is gitignored)" bash -c '[[ -z "$(git status --porcelain)" ]]'
check "bridgeflow unit is active" systemctl is-active --quiet bridgeflow
check "portal unit is active" systemctl is-active --quiet bridgeflow-portal
check "unit names the real domain" grep -q -- "--trusted-host $DOMAIN" /etc/systemd/system/bridgeflow.service
check "domain service answers on loopback" curl -fsS --max-time 5 http://127.0.0.1:8000/health
check "portal answers on loopback" curl -fsS --max-time 5 http://127.0.0.1:8100/health
# shellcheck disable=SC1091
check "portal env is complete (env.sh)" bash -c 'source env.sh && [[ -n "${PORTAL_FEISHU_APP_ID:-}" && -n "${PORTAL_FEISHU_APP_SECRET:-}" && -n "${PORTAL_SESSION_SECRET:-}" && -f "${PORTAL_KEY_PATH:-/nonexistent}" && "${PORTAL_BASE_URL:-}" = "https://portal.'"${DOMAIN}"'" && "${PORTAL_EXTERNAL_BASE_URL:-}" = "$PORTAL_BASE_URL" ]]'
check "portal is configured (feishu credentials + signing key loaded)" bash -c 'curl -fsS --max-time 5 http://127.0.0.1:8100/health | grep -q "\"feishu\": *true" && curl -fsS --max-time 5 http://127.0.0.1:8100/health | grep -q "\"signer\": *true"'
check "nothing but ssh and caddy listens publicly" bash -c '! ss -tlnH | awk "{print \$4}" | grep -vE "^(127\.0\.0\.1|\[::1\]):" | grep -vE ":(22|80|443)$"'
check "main site answers 200 on https://$DOMAIN" bash -c 'test "$(curl -s -o /dev/null -w %{http_code} --max-time 10 https://'"$DOMAIN"'/)" = 200'
check "portal health answers on https://portal.$DOMAIN" curl -fsS --max-time 10 "https://portal.$DOMAIN/health"
exit $failed
