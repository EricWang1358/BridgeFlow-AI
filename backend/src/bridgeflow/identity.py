"""Employee identity from the login portal: a signed JWT in X-BridgeFlow-User.

The portal (portal/) proves who somebody is through Feishu and signs a short-lived
token; this service only ever sees the public half, pulled from the portal's JWKS
endpoint. A name in a request body is a claim, never an identity (docs/13) — only
a valid signature counts.

The layer is off while portal_base_url is unset: local development and offline
tests behave as before. Once configured, every browser data route needs a valid
token — fail closed, the same posture as Feishu's "not configured".
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import HTTPException, Request

from bridgeflow.config import settings

JWKS_CACHE_SECONDS = 300

_cache_url = ""
_cache_at = 0.0
_cache_keys: list[dict] = []


@dataclass(frozen=True)
class UserIdentity:
    """Who the portal says this browser session is. sub = Feishu union_id."""

    sub: str
    name: str
    email: str


async def _fetch_jwks(url: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{url}/.well-known/jwks.json")
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"Login portal is unreachable: {exc}") from exc
    if response.status_code != 200:
        raise HTTPException(503, "Login portal did not publish its keys")
    return list(response.json().get("keys", []))


async def _keys(refresh: bool = False) -> list[dict]:
    global _cache_url, _cache_at, _cache_keys
    url = settings.portal_base_url.rstrip("/")
    if refresh or url != _cache_url or time.monotonic() - _cache_at > JWKS_CACHE_SECONDS:
        _cache_keys = await _fetch_jwks(url)
        _cache_url, _cache_at = url, time.monotonic()
    return _cache_keys


def reset_cache() -> None:
    """Tests and key rotation both need to drop the cached JWKS."""
    global _cache_url, _cache_at, _cache_keys
    _cache_url, _cache_at, _cache_keys = "", 0.0, []


async def require_user(request: Request) -> UserIdentity | None:
    """The portal-signed identity, or None while the identity layer is off."""
    if not settings.portal_base_url:
        return None
    token = request.headers.get("x-bridgeflow-user", "")
    if not token:
        raise HTTPException(401, "Sign in through the login portal")
    try:
        header = jwt.get_unverified_header(token)
        keys = await _keys()
        match = [k for k in keys if k.get("kid") == header.get("kid")]
        if not match:
            # An unknown kid may be newer than our cache: one refresh, then refuse.
            match = [k for k in await _keys(refresh=True) if k.get("kid") == header.get("kid")]
        key = jwt.algorithms.OKPAlgorithm.from_jwk(json.dumps(match[0]))
        claims = jwt.decode(token, key, algorithms=["EdDSA"], audience=settings.portal_audience,
                            issuer=settings.portal_base_url.rstrip("/"))
    except (jwt.PyJWTError, IndexError, KeyError, ValueError) as exc:
        raise HTTPException(401, "Portal token is invalid or expired") from exc
    if not claims.get("sub"):
        raise HTTPException(401, "Portal token carries no identity")
    return UserIdentity(sub=str(claims["sub"]), name=str(claims.get("name", "")),
                        email=str(claims.get("email", "")))
