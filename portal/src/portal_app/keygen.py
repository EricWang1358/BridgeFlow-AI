"""Generate the portal's Ed25519 signing key: python -m portal_app.keygen <path>."""

import sys
from pathlib import Path

from portal_app.tokens import generate_keypair

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m portal_app.keygen <private-key.pem>")
    target = Path(sys.argv[1])
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing key: {target}")
    generate_keypair(target)
    print(f"wrote {target} (mode 600); export PORTAL_KEY_PATH={target.resolve()}")
