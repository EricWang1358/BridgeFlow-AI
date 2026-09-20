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
# The instance registry is a hand-written file deploy.sh never touches, and the
# one thing it must say is "send logins through /enter with an app_uri" — without
# that, a login lands on the site with no dsh launch token (docs/22 §9b).
# shellcheck disable=SC1091
check "portal registry sends logins through /enter" bash -c 'source env.sh && grep -qE "redirect_uri: *\"?[^\"]*/enter/?\"? *$" "${PORTAL_APPS_PATH:-portal/apps.yaml}"'
# shellcheck disable=SC1091
check "portal registry names app_uri" bash -c 'source env.sh && grep -qE "^ *app_uri: *\"?https?://" "${PORTAL_APPS_PATH:-portal/apps.yaml}"'
# start_web.py captures dsh web's launch token by regex; an empty file means the
# capture missed and first-time browsers will meet dsh's own 401. A seat
# deployment has no shared console — each seat's own file is checked instead.
# shellcheck disable=SC1091
if bash -c 'source env.sh && [[ -z "${PORTAL_SEATS_PATH:-}" ]]'; then
  check "dsh launch token was captured" bash -c 'source env.sh && test -s "${PORTAL_DSH_TOKEN_FILE:-$DSH_HOME/.web-launch-token}"'
else
  # --- seat isolation (docs/35); these hold only when the registry is on ---
  VENV_PY="$HOME/Hackathon2026/.venv/bin/python"
  SEATS_PATH="data/mappings/seats.yaml"
  seat_count=$("$VENV_PY" -c "import yaml;print(len((yaml.safe_load(open('$SEATS_PATH')) or {}).get('seats') or []))" 2>/dev/null || echo 999)
  seat_names=$("$VENV_PY" -c "import yaml;print(' '.join(s['name'] for s in (yaml.safe_load(open('$SEATS_PATH')) or {}).get('seats') or []))" 2>/dev/null || true)
  seat_ports=$("$VENV_PY" -c "import yaml;print(' '.join(str(s['port']) for s in (yaml.safe_load(open('$SEATS_PATH')) or {}).get('seats') or []))" 2>/dev/null || true)
  check "seat registry parses and names its seats" test -n "$seat_names"
  # shellcheck disable=SC1091
  check "seat base domain is set alongside the registry" bash -c 'source env.sh && [[ -n "${PORTAL_SEAT_BASE_DOMAIN:-}" && -n "${PORTAL_SEAT_ASSIGNMENTS:-}" ]]'
  # The claims file is the runtime truth of who holds which seat: parseable,
  # pointing only at seats that exist, at most one seat per subject, and never
  # more claims than the fleet.
  claims_ok=$("$VENV_PY" - << 'PY'
import json, yaml
try:
    claims = json.load(open("data/seats-assigned.json"))
    fleet = {s["name"] for s in yaml.safe_load(open("data/mappings/seats.yaml"))["seats"]}
    assert all(v in fleet for v in claims.values()), "claim points outside the fleet"
    assert len(set(claims.values())) == len(claims), "one seat is claimed twice"
    assert len(claims) <= len(fleet), "more claims than seats"
except Exception as exc:
    print(f"claims file unusable: {exc}")
    raise SystemExit(1)
print("ok")
PY
  ) || claims_ok=bad
  check "seat claims are consistent with the fleet" test "$claims_ok" = ok
  claim_count=$("$VENV_PY" -c 'import json;print(len(json.load(open("data/seats-assigned.json"))))' 2>/dev/null || echo none)
  check "portal reports the registry's seat count" test "$(curl -fsS --max-time 5 http://127.0.0.1:8100/health | "$VENV_PY" -c 'import json,sys;print(json.load(sys.stdin)["seats"])' 2>/dev/null || echo none)" = "$seat_count"
  check "portal reports the claims count" test "$(curl -fsS --max-time 5 http://127.0.0.1:8100/health | "$VENV_PY" -c 'import json,sys;print(json.load(sys.stdin)["seats_assigned"])' 2>/dev/null || echo missing)" = "$claim_count"
  # The capacity plan (docs/35 §3): 7 seats on the 4GB instance. Per-seat
  # MemoryMax is a ceiling, not a reservation — ceilings may sum past the slice.
  check "seat count is within the capacity plan (<=7)" test "$seat_count" -le 7
  check "seat slice memory fence is in force (MemoryMax=2G)" bash -c 'test "$(systemctl show bridgeflow-dsh.slice -p MemoryMax --value)" = 2147483648'
  check "each seat unit is active" bash -c 'for seat in '"$seat_names"'; do systemctl is-active --quiet "bridgeflow-dsh@$seat" || exit 1; done'
  check "each seat captured its launch token" bash -c 'for seat in '"$seat_names"'; do test -s "data/homes/$seat/.web-launch-token" || exit 1; done'
  check "each seat listens on its loopback port" bash -c "for port in $seat_ports; do ss -tlnH | grep -q \"127.0.0.1:\$port \" || exit 1; done"
  check "each seat subdomain is gated (cookie-less curl is 401)" bash -c 'for seat in '"$seat_names"'; do test "$(curl -s -o /dev/null -w %{http_code} --max-time 10 "https://$seat.console.$DOMAIN/")" = 401 || exit 1; done'
  check "swap is at least 2G (idle seat pages page out, docs/35 §3)" bash -c 'test "$(awk "/SwapTotal/{print \$2}" /proc/meminfo)" -ge 2097151'
fi
check "portal is configured (feishu credentials + signing key loaded)" bash -c 'curl -fsS --max-time 5 http://127.0.0.1:8100/health | grep -q "\"feishu\": *true" && curl -fsS --max-time 5 http://127.0.0.1:8100/health | grep -q "\"signer\": *true"'
# The console gate refuses whoever holds no console_access grant, so enabling it
# before any role declares that operation locks every employee out of the whole
# site (docs/22 §9d). Asked through the app's own loader, not a grep, so the
# answer cannot drift from what /verify will decide — and so an unparseable ACL
# fails here too. Silent when the gate is off: that is the supported default.
# shellcheck disable=SC1091
check "console gate, when on, has a role that can pass it" bash -c '
  curl -fsS --max-time 5 http://127.0.0.1:8100/health | grep -q "\"console_gate\": *true" || exit 0
  source env.sh
  "$HOME/Hackathon2026/.venv/bin/python" -c "
import sys
from bridgeflow.access import CONSOLE_OPERATION
from bridgeflow.access_resolver import structure
roles = structure()[\"roles\"].values()
sys.exit(0 if any(CONSOLE_OPERATION in (r.get(\"operations\") or []) for r in roles) else 1)"'
# 127.0.0.53/54:53 are systemd-resolved's DNS stubs — loopback like any other
# 127.x, so the whole range is private, not just 127.0.0.1.
check "nothing but ssh and caddy listens publicly" bash -c '! ss -tlnH | awk "{print \$4}" | grep -vE "^(127\.|\[::1\]):" | grep -vE ":(22|80|443)$"'
# The anonymous-answer expectation differs by shape (docs/35 §3): a seat
# deployment redirects the apex to the portal (3xx), the legacy shape answers
# dsh's own 401 through forward_auth.
if bash -c 'source env.sh && [[ -n "${PORTAL_SEATS_PATH:-}" ]]'; then
  check "main site redirects to the portal on https://$DOMAIN" bash -c 'code=$(curl -s -o /dev/null -w %{http_code} --max-time 10 "https://'"$DOMAIN"'/"); case "$code" in 301|302|307|308) exit 0;; *) exit 1;; esac'
else
  check "main site is gated by the portal on https://$DOMAIN" bash -c 'test "$(curl -s -o /dev/null -w %{http_code} --max-time 10 https://'"$DOMAIN"'/)" = 401'
fi
check "portal health answers on https://portal.$DOMAIN" curl -fsS --max-time 10 "https://portal.$DOMAIN/health"
exit $failed
