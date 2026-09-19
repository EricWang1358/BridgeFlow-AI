#!/usr/bin/env bash
# Validate-then-atomically-replace one instance-side config file (docs/22 §5b).
#
# The file content arrives base64-encoded on stdin, so YAML quoting never
# crosses a shell: apostrophes in comments, CJK text and multi-line documents
# survive byte-exact. Validation runs the product's own loaders — the same code
# paths the running service uses — so an invalid file fails the deploy instead
# of reaching the runtime (fail closed, same rule as the services themselves).
# Because it imports the product, the caller must run this AFTER deploy.sh has
# updated the checkout: validating against the previous commit's code is what
# silently dropped a configuration sync on 2026-09-19.
#
# Only the field dictionary travels this way — it is real business data and
# stays out of the repo. access-control.yaml is tracked and ships with the code.
#
# Usage: printf '%s' <base64> | config-put.sh field-dictionary.yaml
#        (called by .github/workflows/deploy.yml "Sync instance configuration";
#         the file lives as a production-environment secret, never in the repo)
set -euo pipefail
ROOT="$HOME/Hackathon2026/BridgeFlow-AI"
VENV="$HOME/Hackathon2026/.venv/bin/python"
NAME="${1:?usage: config-put.sh field-dictionary.yaml}"
TARGET="$ROOT/data/mappings/$NAME"
NEW="/tmp/bf-config-$NAME.new"

base64 -d > "$NEW"

case "$NAME" in
  field-dictionary.yaml)
    # _load_dictionary is import's own loader: YAML shape, dictionary fields,
    # date_order values. Private but deliberately reused — a second validator
    # would drift from what import actually enforces.
    BF_CONFIG_PUT_PATH="$NEW" "$VENV" -c \
      'import os
from pathlib import Path
from bridgeflow.api.batches import _load_dictionary
_load_dictionary(Path(os.environ["BF_CONFIG_PUT_PATH"]))' ;;
  *) echo "config-put: unknown file $NAME" >&2; exit 2 ;;
esac

mkdir -p "$(dirname "$TARGET")"
if [ ! -f "$TARGET" ]; then
  mv "$NEW" "$TARGET"
  echo "config-put: $NAME created"
elif cmp -s "$NEW" "$TARGET"; then
  echo "config-put: $NAME unchanged"
else
  cp "$TARGET" "$TARGET.bak"
  mv "$NEW" "$TARGET"
  echo "config-put: $NAME updated (previous kept as $NAME.bak)"
fi
