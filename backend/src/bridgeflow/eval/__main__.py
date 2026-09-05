"""`python -m bridgeflow.eval` — run the acceptance suite and exit non-zero if red."""

from __future__ import annotations

import sys

from bridgeflow.eval import main

if __name__ == "__main__":
    sys.exit(main())
