"""Smoke-test the dsh runtime: does a real turn come back?

Verifies the JSON-RPC handshake, profile boot, and that our DshProvider's
structured-output path survives a live reply.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import time
import traceback

from pydantic import BaseModel


class Verdict(BaseModel):
    confidence: float
    justification: str


def step(label: str) -> None:
    print(f"\n--- {label} ---", flush=True)


def main() -> int:
    home = os.environ.get("DSH_HOME")
    if not home:
        print("DSH_HOME is not set. See docs/14-wsl-setup.md step 7.")
        return 2
    print(f"DSH_HOME = {home}")
    print(f"DEEPSEEK_API_KEY set: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend/src"))
    from bridgeflow.dsh_runtime import native_command
    dsh = native_command()

    step("1. raw SDK: plain turn")
    from deepseek_harness import DeepSeekHarness

    t0 = time.time()
    with DeepSeekHarness(
        dsh_home=home,
        dsh_bin=dsh,
        profile=os.environ.get("DSH_PROFILE", "sdk-minimal"),
        provider=os.environ.get("DSH_PROVIDER", "deepseek-official"),
        model=os.environ.get("DSH_MODEL", "deepseek-v4-flash"),
        initialize_timeout_seconds=180.0,
        request_timeout_seconds=180.0,
    ) as harness:
        print(f"  started in {time.time() - t0:.1f}s", flush=True)
        t1 = time.time()
        result = harness.run("Reply with exactly the word: ok", session_id="smoke-1")
        print(f"  turn took {time.time() - t1:.1f}s")
        print(f"  finish_reason = {result.finish_reason!r}")
        print(f"  final_response = {result.final_response!r}")
        print(f"  events = {len(result.events)}, notifications = {len(result.notifications)}")

    step("2. our DshProvider: structured output")
    from bridgeflow.llm.base import Message
    from bridgeflow.llm.providers.dsh import DshProvider

    async def run_provider() -> None:
        provider = DshProvider()
        try:
            response = await provider.complete(
                system=(
                    "You decide whether two identifiers from different departments "
                    "refer to the same real-world thing."
                ),
                messages=[
                    Message(
                        role="user",
                        content='{"source": ["SKU-A1"], "target": ["sku a1", "SKU A1"]}',
                    )
                ],
                schema=Verdict,
            )
            print(f"  provider = {response.provider}, model = {response.model}")
            print(f"  raw text = {response.text[:300]!r}")
            print(f"  parsed   = {response.parsed!r}")
            assert isinstance(response.parsed, Verdict), "structured output failed"
        finally:
            provider.close()

    asyncio.run(run_provider())

    print("\n=== SMOKE TEST PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("\n=== SMOKE TEST FAILED ===")
        traceback.print_exc()
        raise
