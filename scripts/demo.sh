#!/usr/bin/env bash
# One-command local rehearsal of the six-step CSV demo (demo-walkthrough): rebuild
# the plugin bundle, stop previous instances, regenerate the 2025-11 case, then run
# the login portal (:8100) plus backend + dsh web (:3082) against the CASE
# dictionary with a throwaway DSH_HOME. Ctrl-C stops everything. Logs land in
# logs/{portal,web}.log.
#
#   scripts/demo.sh                # start (or restart)
#   PYTHON=/path/to/python scripts/demo.sh
#
# This is the scripts/dev.sh shape with the case flipped: dev.sh boots --demo
# (the concrete-supplier template tour, its own dictionary); this script boots the
# risk/balanced CSV walkthrough. Do not mix them: importing the walkthrough CSVs
# under the --demo dictionary imports fine and then gets refused at review time
# with needs_configuration — the classic pitfall (demo-walkthrough/README.md).
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

echo "==> regenerating the 2025-11 case (deterministic)"
"$PY" scripts/make_business_case.py

# A throwaway home per run: rehearsal must not write synthetic mappings into your
# own business memory or leave sessions next to your real work (docs/17 演示准备).
# Portal and web share it — /enter reads this home's launch token for handover.
export DSH_HOME="$(mktemp -d /tmp/bridgeflow-demo-dsh-XXXXXX)"
export RESULT_STORE_PATH="$DSH_HOME/business-output"
export MAPPING_MEMORY_PATH="$DSH_HOME/mappings.json"
export FIELD_DICTIONARY_PATH="$PWD/data/business_demo/dictionary.yaml"

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
(cd portal && PYTHONPATH=src "$PY" -m uvicorn portal_app.main:app --host 127.0.0.1 --port 8100) > logs/portal.log 2>&1 &
PORTAL_PID=$!
trap 'kill "$PORTAL_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 50); do
  curl -sf http://127.0.0.1:8100/health > /dev/null 2>&1 && break
  sleep 0.2
done
curl -sf http://127.0.0.1:8100/health > /dev/null || { echo "portal did not become ready; see logs/portal.log" >&2; exit 1; }

echo "==> backend + dsh web :3082 (logs/web.log), case dictionary, home: $DSH_HOME"
"$PY" scripts/start_web.py --port 3082 2>&1 | tee logs/web.log &
WEB_PID=$!
trap 'kill "$PORTAL_PID" "$WEB_PID" 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 100); do
  grep -q "dsh web:" logs/web.log 2>/dev/null && break
  sleep 0.2
done

cat << 'EOF'

==> Ready. The walkthrough in six steps (demo-walkthrough/README.md):
    1. 亮字典：单位、正数约定、公式、阈值、责任人 —— 映射由人声明，模型不猜。
    2. 部门文件 → 上传 data/business_demo/risk/ 四份 CSV，业务月份 2025-11，记下 batch_id。
    3. 粘贴研判话术（README 六步第 3 步，替换批次号）→ 观察四次原生 Spawn。
    4. 业务状态页签 → 风险节点 → 核对报告（答案在 data/business_demo/expected.json，禁止喂给模型）。
    5. balanced 四份 CSV 再来一遍；旧批次报告仍可重开。
    6. 审批话术：先拒（填理由）再批 —— 拒绝不写映射，批准一次才写入。

    浏览器从门户进：http://127.0.0.1:8100  （飞书登录后 /enter 自动交接进 3082）
    聊天请求走真实模型、真计费；导入与规则计算免费。
EOF
wait "$WEB_PID"
