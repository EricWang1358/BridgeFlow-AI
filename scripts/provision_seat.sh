#!/usr/bin/env bash
# Provision the seat fleet: a FIXED capacity of generic consoles, claimed
# first-come-first-served by authorized people (docs/deployment.md). No person is named
# anywhere in a config file; who may claim at all is the #229 console_access
# gate, and who holds which seat lives only in the runtime claims file.
#
#   scripts/provision_seat.sh --init <N>      # seat-1..seat-N: homes, units, Caddy, env.sh
#   scripts/provision_seat.sh --status        # fleet, claims, unit states
#   scripts/provision_seat.sh --release <sub> # free one seat: unclaim, archive its home, restart
#
# --release is the only way a seat ever changes hands. The archived home is a
# customer asset with the same retention duty as #232's configs; the seat then
# serves a fresh home to the next claimer.
#
# DNS: one A record per seat (<seat>.console.<domain> -> the instance) is still
# a human step; Caddy takes its own cert per explicit hostname.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SEATS="$ROOT/data/mappings/seats.yaml"
CLAIMS="${PORTAL_SEAT_ASSIGNMENTS:-$ROOT/data/seats-assigned.json}"
HOMES="$ROOT/data/homes"
VENV_PY="$ROOT/../.venv/bin/python"

die() { echo "provision_seat: $*" >&2; exit 1; }

# Only --init/--release need the domain (seat.env hosts, Caddy rendering);
# --status works without it, so demanding it there just gets in the way.
DOMAIN="${BRIDGEFLOW_DOMAIN:-}"
need_domain() { [[ -n "$DOMAIN" ]] || die "set BRIDGEFLOW_DOMAIN=<your apex domain>, e.g. example.com"; }

fleet_names()  { "$VENV_PY" - "$SEATS" << 'PY'
import sys, yaml
try:
    seats = (yaml.safe_load(open(sys.argv[1])) or {}).get("seats") or []
except FileNotFoundError:
    seats = []
print(" ".join(s["name"] for s in seats))
PY
}

fleet_ports()  { "$VENV_PY" - "$SEATS" << 'PY'
import sys, yaml
try:
    seats = (yaml.safe_load(open(sys.argv[1])) or {}).get("seats") or []
except FileNotFoundError:
    seats = []
print(" ".join(str(s["port"]) for s in seats))
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
  for entry in "export PORTAL_SEATS_PATH=\"$SEATS\"" \
               "export PORTAL_SEAT_BASE_DOMAIN=\"$DOMAIN\"" \
               "export PORTAL_SEAT_ASSIGNMENTS=\"$CLAIMS\""; do
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

init_fleet() {
  need_domain
  local count="${1:?usage: provision_seat.sh --init <N>}"
  [[ "$count" =~ ^[1-9][0-9]*$ ]] || die "N must be a positive integer (got: $count)"
  [[ "$count" -le 16 ]] || die "refusing >16 seats on one box — revisit the capacity plan (docs/deployment.md)"
  if [[ -f "$CLAIMS" ]] && [[ "$("$VENV_PY" -c "import json;print(len(json.load(open('$CLAIMS'))))")" -gt 0 ]]; then
    local current
    current="$("$VENV_PY" -c "import yaml;print(len(yaml.safe_load(open('$SEATS')).get('seats') or []))" 2>/dev/null || echo 0)"
    [[ "$count" -ge "$current" ]] || die "fleet is in use ($current seats, claims exist) — shrinking needs --release first"
  fi

  mkdir -p "$HOMES" "$(dirname "$CLAIMS")"
  [[ -f "$CLAIMS" ]] || printf '{}\n' > "$CLAIMS"
  "$VENV_PY" - "$SEATS" "$count" "$HOMES" << 'PY'
import sys, yaml
path, count, homes = sys.argv[1], int(sys.argv[2]), sys.argv[3]
fleet = [{"name": f"seat-{i}", "port": 3100 + i, "home": f"{homes}/seat-{i}"}
         for i in range(1, count + 1)]
with open(path, "w") as stream:
    yaml.safe_dump({"seats": fleet}, stream, allow_unicode=True, sort_keys=False)
PY
  for name in $(fleet_names); do
    local home="$HOMES/$name" port
    port="$("$VENV_PY" -c "import yaml;print(next(s['port'] for s in yaml.safe_load(open('$SEATS'))['seats'] if s['name']=='$name'))")"
    mkdir -p "$home"
    cat > "$home/seat.env" << EOF
# Written by scripts/provision_seat.sh; the seat unit reads both values.
DSH_SEAT_PORT=$port
DSH_SEAT_HOST=$name.console.$DOMAIN
EOF
  done

  ensure_portal_env
  render_caddy
  sudo cp "$ROOT/deploy/bridgeflow-dsh.slice" /etc/systemd/system/
  sudo cp "$ROOT/deploy/bridgeflow-dsh@.service" /etc/systemd/system/
  sudo systemctl daemon-reload
  for name in $(fleet_names); do
    sudo systemctl enable --now "bridgeflow-dsh@$name"
  done

  echo
  echo "Fleet of $count seats provisioned (seat-1..seat-$count, ports 3101+, homes $HOMES)."
  echo "Still yours to do:"
  echo "  1. DNS: one A record per seat — seat-1.console.$DOMAIN .. seat-$count.console.$DOMAIN"
  echo "  2. Who MAY claim is the console gate: console_access in access-control.yaml (#229)"
  echo "  3. Back up data/mappings/seats.yaml privately; instance configuration must not be committed"
  echo "  4. Verify: bash deploy/preflight.sh $DOMAIN"
}

release_seat() {
  need_domain
  local sub="${1:?usage: provision_seat.sh --release <union_id>}"
  [[ -f "$CLAIMS" ]] || die "no claims file at $CLAIMS"
  local name
  name="$("$VENV_PY" - "$CLAIMS" "$sub" << 'PY'
import json, sys
claims = json.load(open(sys.argv[1]))
name = claims.get(sys.argv[2])
if name is None:
    raise SystemExit(f"subject {sys.argv[2]!r} holds no seat")
print(name)
PY
)" || die "subject $sub holds no seat"
  sudo systemctl stop "bridgeflow-dsh@$name"
  local home="$HOMES/$name"
  if [[ -d "$home" ]]; then
    mkdir -p "$HOMES/_archive"
    mv "$home" "$HOMES/_archive/$name-$(date +%Y%m%d-%H%M%S)"
    echo "home archived under $HOMES/_archive/ (customer asset; retention per #232)"
  fi
  mkdir -p "$home"
  "$VENV_PY" - "$SEATS" "$name" "$home" "$DOMAIN" << 'PY'
import sys, yaml
path, name, home, domain = sys.argv[1:5]
seat = next(s for s in yaml.safe_load(open(path))["seats"] if s["name"] == name)
with open(f"{home}/seat.env", "w") as stream:
    stream.write("# Written by scripts/provision_seat.sh; the seat unit reads both values.\n"
                 f"DSH_SEAT_PORT={seat['port']}\nDSH_SEAT_HOST={name}.console.{domain}\n")
PY
  "$VENV_PY" - "$CLAIMS" "$sub" << 'PY'
import json, sys
path, sub = sys.argv[1:3]
claims = json.load(open(path))
claims.pop(sub, None)
with open(path, "w") as stream:
    json.dump(claims, stream, ensure_ascii=False, indent=2, sort_keys=True)
    stream.write("\n")
PY
  sudo systemctl start "bridgeflow-dsh@$name"
  echo "Seat $name released for $sub; fresh home, unit restarted, next claimer gets it."
}

show_status() {
  echo "fleet ($SEATS):"
  fleet_names | tr ' ' '\n' | sed 's/^/  /'
  echo "claims ($CLAIMS):"
  if [[ -f "$CLAIMS" ]]; then
    "$VENV_PY" - "$CLAIMS" << 'PY'
import json, sys
claims = json.load(open(sys.argv[1]))
for sub, name in sorted(claims.items()):
    shown = sub if len(sub) <= 12 else sub[:12] + "…"
    print(f"  {name}: {shown}")
if not claims:
    print("  (nobody has claimed yet)")
PY
  else
    echo "  (no claims file — fleet not initialized?)"
  fi
}

case "${1:-}" in
  --init)   [[ $# = 2 ]] || die "usage: provision_seat.sh --init <N>"; init_fleet "$2" ;;
  --release) [[ $# = 2 ]] || die "usage: provision_seat.sh --release <sub>"; release_seat "$2" ;;
  --status) show_status ;;
  *) die "usage: provision_seat.sh --init <N> | --status | --release <sub>" ;;
esac
