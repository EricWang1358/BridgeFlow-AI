"""`python -m bridgeflow.llm_gate [--port N]` — loopback only, by construction (docs/36 §6)."""

from __future__ import annotations

import argparse

import uvicorn

from bridgeflow.llm_gate import DEFAULT_PORT
from bridgeflow.llm_gate.app import config_from_env, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    config = config_from_env()
    print(f"llm-gate: 127.0.0.1:{args.port} → {config.upstream_url}; models {sorted(config.policy.models)}; "
          f"daily budget {config.policy.daily_tokens or 'none'}; state {config.state}", flush=True)
    # No --host flag on purpose: the gate holds the real key and must never listen publicly.
    uvicorn.run(create_app(config), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
