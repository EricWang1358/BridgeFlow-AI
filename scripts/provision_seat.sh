#!/usr/bin/env bash
# Provision or remove one seat: one person's isolated console (docs/35 §8).
#
#   scripts/provision_seat.sh <name> <sub>          # add; port auto-assigned 3101+
#   scripts/provision_seat.sh --remove <name>       # disable, archive home, drop from registry
#
# What a seat needs besides this script (the script says so when it matters):
#   - a DNS record  <name>.console.<domain>  → the instance (Caddy gets its own
#     cert per explicit hostname; no wildcard needed for seven seats);
#   - the owner's role declares console_access in access-control.yaml (#229);
#   - env.sh exports PORTAL_SEATS_PATH and PORTAL_SEAT_BASE_DOMAIN (appended
#     here when missing — paths and a domain, never a credential);
#   - seats.yaml committed back through a PR: provisioning is a reviewed act.
#
# Removal archives the home under data/homes/_archive/<name>-<date>/ — a seat's
# sessions are a customer asset with the same retention duty as #232's configs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${BRIDGEFLOW_DOMAIN:?set BRIDGEFLOW_DOMAIN=<your apex domain>, e.g. example.com}"
SEATS="$ROOT/data/mappings/seats.yaml"
HOMES="$ROOT/data/homes"
VENV_PY="$ROOT/../.venv/bin/python"

die() { echo "provision_seat: $*" >&2; exit 1; }

seat_names() { "$VENV_PY" - "$SEATS" << 'PY'
import sys, yaml
try:
    seats = (yaml.safe_load(open(sys.argv[1])) or {}).get("seats") or []
except FileNotFoundError:
    seats = []
print(" ".join(s["name"] for s in seats))
PY
}

render_caddy() {
  local rendered
  rendered="$("$VENV_PY" "$ROOT/deploy/render_caddy.py" "$DOMAIN")"
  printf '%s\n' "$rendered" | sudo tee /etc/caddy/Caddyfile >/dev/null
  sudo systemctl reload caddy
}

ensure_portal_env() {
  cd "$ROOT"
  local added=0
  for entry in "export PORTAL_SEATS_PATH=\"$SEATS\"" "export PORTAL_SEAT_BASE_DOMAIN=\"$DOMAIN\""; do
    if ! grep -qF "$entry" env.sh; then
      printf '%s\n' "$entry" >> env.sh
      added=1
    fi
  done
  if [[ $added = 1 ]]; then
    sudo systemctl restart bridgeflow-portal
    echo "portal env extended with seat settings; portal restarted"
  fi
}

add_seat() {
  local name="$1" sub="$2"
  [[ "$name" =~ ^[a-z0-9][a-z0-9-]{0,30}$ ]] || die "seat name must be [a-z0-9-], got: $name"
  [[ -n "$sub" ]] || die "usage: provision_seat.sh <name> <sub>  (sub = the owner's union_id)"
  [[ " $(seat_names) " != *" $name "* ]] || die "seat $name already exists"
  mkdir -p "$HOMES"
  local home="$HOMES/$name"
  [[ ! -e "$home" ]] || die "$home already exists; remove it first with --remove"

  local port
  port="$("$VENV_PY" - "$SEATS" << 'PY'
import sys, yaml
try:
    seats = (yaml.safe_load(open(sys.argv[1])) or {}).get("seats") or []
except FileNotFoundError:
    seats = []
ports = [s["port"] for s in seats]
print(max(ports, default=3100) + 1)
PY
)"
  mkdir -p "$home"
  cat > "$home/seat.env" << EOF
# Written by scripts/provision_seat.sh; the seat unit reads both values.
DSH_SEAT_PORT=$port
DSH_SEAT_HOST=$name.console.$DOMAIN
EOF
  "$VENV_PY" - "$SEATS" "$name" "$sub" "$port" "$home" << 'PY'
import sys, yaml
path, name, sub, port, home = sys.argv[1:6]
try:
    registry = yaml.safe_load(open(path)) or {}
except FileNotFoundError:
    registry = {}
seats = registry.setdefault("seats", [])
if any(s["name"] == name or s["sub"] == sub for s in seats):
    raise SystemExit("duplicate name or sub already in the registry")
seats.append({"name": name, "sub": sub, "port": int(port), "home": home})
with open(path, "w") as stream:
    yaml.safe_dump(registry, stream, allow_unicode=True, sort_keys=False)
PY

  ensure_portal_env
  render_caddy
  sudo cp "$ROOT/deploy/bridgeflow-dsh.slice" /etc/systemd/system/
  sudo cp "$ROOT/deploy/bridgeflow-dsh@.service" /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now "bridgeflow-dsh@$name"

  echo
  echo "Seat $name provisioned (port $port, home $home)."
  echo "Still yours to do:"
  echo "  1. DNS record: $name.console.$DOMAIN -> this instance"
  echo "  2. access-control.yaml: the owner's role ($sub) must declare console_access"
  echo "  3. Commit data/mappings/seats.yaml through a PR"
  echo "  4. Verify: bash deploy/preflight.sh $DOMAIN"
}

remove_seat() {
  local name="$1"
  [[ " $(seat_names) " == *" $name "* ]] || die "no such seat: $name"
  sudo systemctl disable --now "bridgeflow-dsh@$name" 2>/dev/null || true
  local home="$HOMES/$name"
  if [[ -d "$home" ]]; then
    mkdir -p "$HOMES/_archive"
    mv "$home" "$HOMES/_archive/$name-$(date +%Y%m%d)"
    echo "home archived under $HOMES/_archive/ (customer asset; retention per #232)"
  fi
  "$VENV_PY" - "$SEATS" "$name" << 'PY'
import sys, yaml
path, name = sys.argv[1:3]
registry = yaml.safe_load(open(path)) or {}
registry["seats"] = [s for s in registry.get("seats") or [] if s["name"] != name]
with open(path, "w") as stream:
    yaml.safe_dump(registry, stream, allow_unicode=True, sort_keys=False)
PY
  render_caddy
  echo "Seat $name removed. Commit data/mappings/seats.yaml through a PR."
}

case "${1:-}" in
  --remove) [[ $# = 2 ]] || die "usage: provision_seat.sh --remove <name>"; remove_seat "$2" ;;
  *) [[ $# = 2 ]] || die "usage: provision_seat.sh <name> <sub>"; add_seat "$1" "$2" ;;
esac
