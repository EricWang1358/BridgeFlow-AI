"""The public demo's model gate (docs/36 §6).

The guest instance is public on purpose, so it must never hold the operator's model key. This
process does: it listens on loopback only, accepts one client token that the guest launcher reads
from its state directory, and forwards OpenAI-style `/chat/completions` calls upstream with the
real key. On the way it enforces what a public link needs — a model allowlist, a `max_tokens`
cap, a request size cap, a rate and a concurrency limit, an optional daily token budget, and a
kill switch — and keeps a per-day ledger of counts (never request or response bodies).

It is an HTTP hop in front of the provider, not an `LLMProvider` and not part of dsh: dsh's
DeepSeek provider simply gets `DEEPSEEK_BASE_URL` pointed here by the launching process.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

DEFAULT_GUEST_MODEL = "deepseek-v4-flash"


def guest_model(env: Mapping[str, str]) -> str:
    """The one model a guest instance runs on, and therefore the one the gate lets through.

    BRIDGEFLOW_GUEST_MODEL wins; else env.sh's DSH_MODEL when it names a DeepSeek-official route
    (the provider whose endpoint the gate replaces); else DEEPSEEK_MODEL; else the public default.
    The launcher and the gate both call this on the same env.sh, so they cannot disagree.
    """
    if env.get("BRIDGEFLOW_GUEST_MODEL"):
        return env["BRIDGEFLOW_GUEST_MODEL"]
    if env.get("DSH_PROVIDER") == "deepseek-official" and env.get("DSH_MODEL"):
        return env["DSH_MODEL"]
    return env.get("DEEPSEEK_MODEL") or DEFAULT_GUEST_MODEL


def state_dir(env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    from bridgeflow.config import REPO_ROOT
    return env.get("LLM_GATE_STATE_DIR") or str(REPO_ROOT / "data" / "gate")


CLIENT_TOKEN_FILE = "client-token"
KILL_SWITCH_FILE = "OFF"
DEFAULT_PORT = 8300
