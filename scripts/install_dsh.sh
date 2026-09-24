#!/usr/bin/env bash
# Install the dsh CLI version BridgeFlow is pinned to, privately, beside the repository.
#
# BridgeFlow needs exactly @deepseek-ai/dsh@0.1.2-rc.1 (pre-release, breaking changes between
# versions). `npm install -g` would replace whatever dsh a person already uses every day, so
# this installs into ../.dsh-cli instead — the same "outside the repo, beside .venv" layout as
# DSH_HOME. scripts/start_web.py and the browser tests look there first; a global dsh of any
# version is left untouched, and so is ~/.dsh (BridgeFlow keeps its own DSH_HOME).
#
#     bash scripts/install_dsh.sh           # install or repair
#     bash scripts/install_dsh.sh --check   # report which dsh BridgeFlow would use
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="0.1.2-rc.1"
PREFIX="$(cd .. && pwd)/.dsh-cli"
BIN="$PREFIX/node_modules/.bin/dsh"

if [[ "${1:-}" == "--check" ]]; then
  if [[ -x "$BIN" ]]; then echo "private dsh: $BIN ($("$BIN" --version))"; else echo "private dsh: not installed"; fi
  if command -v dsh >/dev/null; then echo "dsh on PATH: $(command -v dsh) ($(dsh --version 2>/dev/null || echo unknown)) — left as it is"; fi
  exit 0
fi
command -v npm >/dev/null || { echo "npm is required (Node.js 22); see docs/14-wsl-setup.md" >&2; exit 1; }
if [[ -x "$BIN" && "$("$BIN" --version)" == "$VERSION" ]] && cmp -s scripts/dsh-cli/package-lock.json "$PREFIX/package-lock.json"; then
  echo "dsh $VERSION already installed privately at $BIN"
else
  # Exactly the dependency tree BridgeFlow was verified on (scripts/dsh-cli/package-lock.json):
  # the pre-release declares loose ranges, and a fresh resolve on 2026-09-24 pulled 50 newer
  # packages (cordis 4.0.4 among them) that stop `dsh web` from booting.
  mkdir -p "$PREFIX"
  cp scripts/dsh-cli/package.json scripts/dsh-cli/package-lock.json "$PREFIX/"
  (cd "$PREFIX" && npm ci --no-audit --no-fund >/dev/null)
  echo "installed dsh $("$BIN" --version) at $BIN"
fi
if command -v dsh >/dev/null && [[ "$(dsh --version 2>/dev/null)" != "$VERSION" ]]; then
  echo "note: the dsh on your PATH ($(dsh --version 2>/dev/null)) is untouched; BridgeFlow uses the private one."
fi
