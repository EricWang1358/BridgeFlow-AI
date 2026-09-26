"""The gate itself: one ASGI app, built from an explicit config so tests need no environment."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import secrets
import sqlite3
import time
from collections import deque
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from bridgeflow.llm_gate import CLIENT_TOKEN_FILE, KILL_SWITCH_FILE, guest_model, state_dir

PUBLIC_UPSTREAM = "https://api.deepseek.com"


@dataclass(frozen=True)
class Policy:
    """data/mappings/llm-gate.yaml — limits are declared there, not in code."""

    models: frozenset[str]
    paths: frozenset[str] = frozenset({"/chat/completions"})
    max_tokens_cap: int = 32768
    max_request_bytes: int = 2_000_000
    rpm: int = 60
    concurrency: int = 6
    queue_seconds: float = 60.0
    daily_tokens: int | None = None
    timezone: str = "Asia/Singapore"


@dataclass
class GateConfig:
    upstream_url: str
    upstream_key: str
    client_token: str
    policy: Policy
    state: Path
    transport: httpx.AsyncBaseTransport | None = None
    clock: object = field(default=time.monotonic)


def load_policy(path: Path, env: Mapping[str, str]) -> Policy:
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}
    if not isinstance(raw, dict):
        raise SystemExit(f"llm-gate policy is not a mapping: {path}")
    models = frozenset(str(m) for m in raw.get("models") or []) or frozenset({guest_model(env)})
    known = {name for name in Policy.__dataclass_fields__ if name != "models"}
    unknown = set(raw) - known - {"models"}
    if unknown:
        raise SystemExit(f"llm-gate policy has unknown keys {sorted(unknown)}: {path}")
    values = {key: raw[key] for key in known if raw.get(key) is not None}
    if "paths" in values:
        values["paths"] = frozenset(values["paths"])
    return Policy(models=models, **values)


def ensure_client_token(state: Path) -> str:
    """Created once and kept: the guest launcher reads the same file at every start."""
    state.mkdir(parents=True, exist_ok=True)
    path = state / CLIENT_TOKEN_FILE
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        path.write_text(secrets.token_urlsafe(32) + "\n", encoding="utf-8")
        path.chmod(0o600)
    return path.read_text(encoding="utf-8").strip()


def config_from_env(env: Mapping[str, str] | None = None) -> GateConfig:
    env = dict(os.environ if env is None else env)
    key = env.get("LLM_GATE_UPSTREAM_KEY") or env.get("DEEPSEEK_API_KEY") or ""
    if not key:
        raise SystemExit("llm-gate needs the operator's model key: DEEPSEEK_API_KEY (or LLM_GATE_UPSTREAM_KEY) in env.sh")
    url = env.get("LLM_GATE_UPSTREAM_URL") or env.get("DEEPSEEK_BASE_URL") or PUBLIC_UPSTREAM
    state = Path(state_dir(env))
    from bridgeflow.config import REPO_ROOT
    policy_path = Path(env.get("LLM_GATE_POLICY_PATH") or REPO_ROOT / "data/mappings/llm-gate.yaml")
    return GateConfig(upstream_url=url.rstrip("/"), upstream_key=key, client_token=ensure_client_token(state),
                      policy=load_policy(policy_path, env), state=state)


class Ledger:
    """Per-day counts. No bodies, no prompts, no cell values — only numbers."""

    def __init__(self, path: Path) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("""create table if not exists usage (
            day text primary key, requests integer not null default 0, denied integer not null default 0,
            prompt_tokens integer not null default 0, cached_tokens integer not null default 0,
            completion_tokens integer not null default 0, estimated integer not null default 0)""")
        self._db.commit()

    def _bump(self, day: str, **counts: int) -> None:
        self._db.execute("insert or ignore into usage(day) values (?)", (day,))
        sets = ", ".join(f"{name} = {name} + ?" for name in counts)
        self._db.execute(f"update usage set {sets} where day = ?", (*counts.values(), day))
        self._db.commit()

    def denied(self, day: str) -> None:
        self._bump(day, denied=1)

    def record(self, day: str, prompt: int, cached: int, completion: int, estimated: bool) -> None:
        self._bump(day, requests=1, prompt_tokens=prompt, cached_tokens=cached,
                   completion_tokens=completion, estimated=int(estimated))

    def day(self, day: str) -> dict[str, int]:
        row = self._db.execute("select requests, denied, prompt_tokens, cached_tokens, completion_tokens, estimated "
                               "from usage where day = ?", (day,)).fetchone() or (0,) * 6
        names = ("requests", "denied", "prompt_tokens", "cached_tokens", "completion_tokens", "estimated")
        return dict(zip(names, row, strict=True))


def billable(counts: Mapping[str, int]) -> int:
    """Tokens counted against a budget: cache hits at a tenth, as providers bill them."""
    fresh = counts["prompt_tokens"] - counts["cached_tokens"]
    return fresh + counts["cached_tokens"] // 10 + counts["completion_tokens"]


def refusal(status: int, kind: str, message: str, retry_after: int | None = None) -> JSONResponse:
    headers = {"retry-after": str(retry_after)} if retry_after else None
    return JSONResponse({"error": {"message": message, "type": kind, "code": kind}}, status_code=status, headers=headers)


BUDGET_MESSAGE = ("今日演示 AI 额度已用完；示例、回放与所有页面仍可使用，次日 00:00 恢复。 "
                  "Today's demo AI allowance is used up; samples and every page still work. It resets at 00:00.")
PAUSED_MESSAGE = "演示 AI 已暂停，示例与所有页面仍可使用。 The demo AI is paused; samples and every page still work."


def usage_of(payload: object) -> tuple[int, int, int] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("usage"), dict):
        return None
    usage = payload["usage"]
    cached = usage.get("prompt_cache_hit_tokens")
    if cached is None:
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return int(usage.get("prompt_tokens") or 0), int(cached or 0), int(usage.get("completion_tokens") or 0)


def create_app(config: GateConfig) -> FastAPI:
    policy = config.policy
    ledger = Ledger(config.state / "usage.sqlite")
    slots = asyncio.Semaphore(policy.concurrency)
    recent: deque[float] = deque()
    zone = ZoneInfo(policy.timezone)
    app = FastAPI(title="BridgeFlow demo model gate", docs_url=None, redoc_url=None, openapi_url=None)

    def today() -> str:
        return datetime.now(zone).date().isoformat()

    def paused() -> bool:
        return (config.state / KILL_SWITCH_FILE).exists()

    def over_budget(day: str) -> bool:
        return policy.daily_tokens is not None and billable(ledger.day(day)) >= policy.daily_tokens

    @app.get("/status")
    async def status() -> dict:
        day = today()
        counts = ledger.day(day)
        used = billable(counts)
        return {"day": day, **counts, "billable_tokens": used, "daily_tokens": policy.daily_tokens,
                "used_ratio": round(used / policy.daily_tokens, 4) if policy.daily_tokens else None,
                "paused": paused(), "models": sorted(policy.models)}

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def forward(path: str, request: Request) -> Response:
        day = today()

        def deny(response: JSONResponse) -> JSONResponse:
            ledger.denied(day)
            return response

        supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not supplied or not hmac.compare_digest(supplied, config.client_token):
            return deny(refusal(401, "unauthorized", "unknown client"))
        if paused():
            return deny(refusal(503, "demo_ai_paused", PAUSED_MESSAGE))
        route = "/" + path.strip("/")
        if request.method != "POST" or route not in policy.paths:
            return deny(refusal(403, "path_not_allowed", f"{request.method} {route} is not offered by the demo gate"))
        body = await request.body()
        if len(body) > policy.max_request_bytes:
            return deny(refusal(413, "request_too_large", f"request exceeds {policy.max_request_bytes} bytes"))
        try:
            payload = json.loads(body)
        except ValueError:
            return deny(refusal(400, "invalid_json", "request body is not JSON"))
        if not isinstance(payload, dict) or payload.get("model") not in policy.models:
            model = payload.get("model") if isinstance(payload, dict) else None
            return deny(refusal(403, "model_not_allowed", f"model {model!r} is not offered in the demo"))
        cap = policy.max_tokens_cap
        for key in ("max_tokens", "max_completion_tokens"):
            if key in payload and (not isinstance(payload[key], int) or payload[key] > cap):
                payload[key] = cap
        if "max_tokens" not in payload and "max_completion_tokens" not in payload:
            payload["max_tokens"] = cap
        streaming = payload.get("stream") is True
        if streaming:
            payload["stream_options"] = {**(payload.get("stream_options") or {}), "include_usage": True}
        if over_budget(day):
            return deny(refusal(429, "demo_budget_exhausted", BUDGET_MESSAGE, retry_after=3600))
        now = config.clock()
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= policy.rpm:
            return deny(refusal(429, "rate_limited", "demo rate limit reached; retry shortly",
                                retry_after=max(1, int(60 - (now - recent[0])) + 1)))
        recent.append(now)
        try:
            await asyncio.wait_for(slots.acquire(), timeout=policy.queue_seconds)
        except TimeoutError:
            return deny(refusal(429, "busy", "the demo model is busy; retry shortly", retry_after=10))

        outbound = json.dumps(payload).encode()
        client = httpx.AsyncClient(transport=config.transport, timeout=httpx.Timeout(300, connect=10))
        upstream = client.build_request("POST", config.upstream_url + route, content=outbound, headers={
            "authorization": f"Bearer {config.upstream_key}", "content-type": "application/json",
            "accept": request.headers.get("accept", "application/json")})
        try:
            response = await client.send(upstream, stream=True)
        except httpx.HTTPError as exc:
            slots.release()
            await client.aclose()
            return refusal(502, "upstream_unreachable", f"model provider unreachable: {type(exc).__name__}")

        async def relay() -> AsyncIterator[bytes]:
            seen: tuple[int, int, int] | None = None
            size, pending = 0, b""
            try:
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    yield chunk
                    if streaming:
                        pending += chunk
                        *lines, pending = pending.split(b"\n")
                        for line in lines:
                            if line.startswith(b"data:") and b'"usage"' in line:
                                try:
                                    seen = usage_of(json.loads(line[5:])) or seen
                                except ValueError:
                                    pass
                    else:
                        pending += chunk
                if not streaming:
                    try:
                        seen = usage_of(json.loads(pending))
                    except ValueError:
                        seen = None
            finally:
                if response.status_code < 400:
                    if seen is None:  # interrupted or silent: over-count rather than under-count
                        ledger.record(day, len(outbound) // 3, 0, size // 3, estimated=True)
                    else:
                        ledger.record(day, *seen, estimated=False)
                await response.aclose()
                await client.aclose()
                slots.release()

        headers = {k: v for k, v in response.headers.items()
                   if k.lower() in ("content-type", "cache-control", "x-request-id")}
        return StreamingResponse(relay(), status_code=response.status_code, headers=headers)

    return app
