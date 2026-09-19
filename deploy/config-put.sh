#!/usr/bin/env bash
# Validate-then-atomically-replace one instance-side config file (docs/22 §5/§9c).
#
# The file content arrives base64-encoded on stdin, so YAML quoting never
# crosses a shell: apostrophes in comments, CJK text and multi-line documents
# survive byte-exact. Validation runs the product's own loaders — the same code
# paths the running service uses — so an invalid file fails the deploy instead
# of reaching the runtime (fail closed, same rule as the services themselves).
#
# Usage: printf '%s' <base64> | config-put.sh <access-control.yaml|field-dictionary.yaml>
#        (called by .github/workflows/deploy.yml "Sync instance configuration";
#         the file lives as a production-environment secret, never in the repo)
set -euo pipefail
ROOT="$HOME/Hackathon2026/BridgeFlow-AI"
VENV="$HOME/Hackathon2026/.venv/bin/python"
NAME="${1:?usage: config-put.sh <access-control.yaml|field-dictionary.yaml>}"
TARGET="$ROOT/data/mappings/$NAME"
NEW="/tmp/bf-config-$NAME.new"

base64 -d > "$NEW"

case "$NAME" in
  access-control.yaml)
    # structure() re-reads and re-validates whatever path the setting names;
    # the env var (no prefix, cf. FIELD_DICTIONARY_PATH) points it at the new file.
    ACCESS_CONTROL_PATH="$NEW" "$VENV" -c \
      'from bridgeflow import access_resolver; access_resolver.structure()' ;;
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
