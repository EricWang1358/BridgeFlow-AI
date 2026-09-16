"""Report expired discovery staging, or delete it with --apply; formal evidence is untouched.

Run with the same RESULT_STORE_PATH as the service. This command does not install
schedulers or compact SQLite; deleted pages are reused, not securely erased.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from bridgeflow.api.discovery import uploads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete expired staging records after reporting")
    args = parser.parse_args()
    print(json.dumps(uploads().cleanup(apply=args.apply)))


if __name__ == "__main__":
    main()
