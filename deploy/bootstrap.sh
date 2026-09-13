#!/usr/bin/env bash
# First-time instance setup, run ON a fresh Ubuntu 24.04 Lightsail instance as `ubuntu`.
# Automates docs/22 §2–§8. Idempotent: rerunning skips what is already in place.
#
#   bash deploy/bootstrap.sh <domain>
#
# What it does NOT do, on purpose:
#   - write any secret: DEEPSEEK_API_KEY goes into env.sh by hand (chmod 600), and the
#     basic-auth password is read from the terminal and only its bcrypt hash is stored;
#   - touch GitHub: Actions secrets and DEPLOY_ENABLED stay a human step (docs/22 §9);
#   - start serving before env.sh is complete: it stops and says what is missing.
#
# Afterwards run `bash deploy/preflight.sh <domain>`.
set -euo pipefail

DOMAIN="${1:?usage: bash deploy/bootstrap.sh <domain>}"
BASE="$HOME/Hackathon2026"
ROOT="$BASE/BridgeFlow-AI"
VENV="$BASE/.venv"
RUNTIME_HOME="$BASE/.dsh-bridgeflow"
REPO="git@github.com:EricWang1358/BridgeFlow-AI.git"
CLI_VERSION="0.1.2-rc.1"
WEB_PORT=3080
AUTH_USER="demo"

step() { printf '\n== %s\n' "$*"; }

step "system packages"
sudo apt-get update -y
sudo apt-get install -y git curl ca-certificates debian-keyring debian-archive-keyring apt-transport-https gnupg

step "Node 22, corepack, dsh $CLI_VERSION"
if ! node --version 2>/dev/null | grep -q '^v22\.'; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo corepack enable
if ! dsh --version 2>/dev/null | grep -q "$CLI_VERSION"; then
  sudo npm install -g "@deepseek-ai/dsh@$CLI_VERSION"
fi

step "uv"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

step "repository (read-only deploy key)"
if [[ ! -d "$ROOT/.git" ]]; then
  if [[ ! -f "$HOME/.ssh/id_ed25519" ]]; then
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N ""
  fi
  if ! ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "Add this public key as a read-only Deploy key (GitHub → Settings → Deploy keys), then rerun:" >&2
    cat "$HOME/.ssh/id_ed25519.pub" >&2
    exit 1
  fi
  mkdir -p "$BASE"
  git clone "$REPO" "$ROOT"
fi

step "virtualenv and backend"
[[ -x "$VENV/bin/python" ]] || uv venv --python 3.13 "$VENV"
uv pip install -e "$ROOT/backend[dsh,dev]" --python "$VENV/bin/python"
mkdir -p "$RUNTIME_HOME"

step "env.sh"
cd "$ROOT"
if [[ ! -f env.sh ]]; then
  cp env.sh.example env.sh
  chmod 600 env.sh
  sed -i "s#^export DSH_HOME=.*#export DSH_HOME=$RUNTIME_HOME#" env.sh
  printf '\nexport BRIDGEFLOW_DSH=%s\n' "$(command -v dsh)" >> env.sh
fi
# shellcheck disable=SC1091
if ! (source env.sh && [[ -n "${DEEPSEEK_API_KEY:-}" && "$DEEPSEEK_API_KEY" != "..." ]]); then
  echo "Fill DEEPSEEK_API_KEY (and FIELD_DICTIONARY_PATH) in $ROOT/env.sh, then rerun." >&2
  exit 1
fi

step "client bundle"
(cd plugins && corepack pnpm install --frozen-lockfile && corepack pnpm run build)

step "Caddy"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y caddy
fi
if ! sudo grep -q "^$DOMAIN {" /etc/caddy/Caddyfile 2>/dev/null; then
  read -r -s -p "Shared demo password for basic auth (not stored, only its hash): " password; echo
  hash="$(caddy hash-password --plaintext "$password")"
  unset password
  sed -e "s#__DOMAIN__#$DOMAIN#" -e "s#__USER__#$AUTH_USER#" -e "s#__HASH__#$hash#" -e "s#__WEB_PORT__#$WEB_PORT#" \
    deploy/Caddyfile.template | grep -v '^#' | sudo tee /etc/caddy/Caddyfile >/dev/null
  sudo systemctl reload caddy
fi

step "systemd unit"
sed "s#<domain>#$DOMAIN#" deploy/bridgeflow.service | sudo tee /etc/systemd/system/bridgeflow.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now bridgeflow

echo
echo "Bootstrap done. Next: bash deploy/preflight.sh $DOMAIN, then docs/22 §9 (GitHub secrets, DEPLOY_ENABLED)."
