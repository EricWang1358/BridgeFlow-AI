"""Unified login portal: Feishu proves who you are, signed app tokens carry it.

Flow: /login?app=… → Feishu web login → /callback → session cookie →
/token?app=… → short-lived JWT that the named app verifies against the JWKS
published here. The portal never sees app data, and apps never see Feishu
credentials — decoupling in both directions.

Run:  uvicorn portal_app.main:app --port 8100   (after sourcing env.sh)
"""

# NOTE: no `from __future__ import annotations` here — FastAPI resolves route
# annotations by name at runtime, and the Depends() closures below live inside
# create_app, unreachable from module globals.

import secrets
import time
from pathlib import Path
from typing import Annotated

import httpx
import yaml
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from portal_app.config import Settings, settings
from portal_app.feishu import FeishuError, FeishuOAuth, NotConfigured
from portal_app.tokens import Signer, seal, unseal

SESSION_COOKIE = "portal_session"
# A login state lives only for the redirect round-trip.
STATE_TTL_SECONDS = 600


def load_registry(path: str) -> dict[str, dict]:
    """apps.yaml → {name: {audience, redirect_uri, origins}}. Invalid config fails fast."""
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"portal app registry cannot be read ({path}): {exc}") from exc
    apps = raw.get("apps") or {}
    if not isinstance(apps, dict):
        raise TypeError(f"portal app registry is invalid ({path}): 'apps' must be a mapping")
    registry = {}
    for name, entry in apps.items():
        if not isinstance(entry, dict) or not entry.get("audience") or not entry.get("redirect_uri"):
            raise RuntimeError(f"portal app {name!r} needs both audience and redirect_uri")
        registry[str(name)] = {
            "audience": str(entry["audience"]),
            "redirect_uri": str(entry["redirect_uri"]),
            "origins": [str(o) for o in entry.get("origins") or []],
        }
    return registry


def create_app(cfg: Settings, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    registry = load_registry(cfg.apps_path)
    signer = Signer(cfg.key_path) if cfg.key_path else None
    origins = sorted({o for entry in registry.values() for o in entry["origins"]})

    app = FastAPI(title="BridgeFlow login portal", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # the session cookie rides /token cross-origin
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    def feishu() -> FeishuOAuth:
        return FeishuOAuth(cfg.feishu_app_id, cfg.feishu_app_secret,
                           cfg.feishu_base_url, cfg.callback_uri, transport)

    def read_session(request: Request) -> dict | None:
        """The non-raising half of current_session, for pages that adapt to sign-in state."""
        return unseal(request.cookies.get(SESSION_COOKIE, ""), cfg.session_secret)

    async def current_session(request: Request) -> dict:
        session = read_session(request)
        if session is None:
            raise HTTPException(401, "Sign in through the portal first")
        return session

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "feishu": bool(cfg.feishu_app_id), "signer": signer is not None}

    # response_model=None: the union return annotation is not a Pydantic field type.
    @app.get("/", response_model=None)
    async def index(request: Request) -> HTMLResponse | RedirectResponse:
        session = read_session(request)
        if session is not None and len(registry) == 1:
            # One app and a live session: there is nothing to choose — go straight in.
            return RedirectResponse(next(iter(registry.values()))["redirect_uri"], status_code=302)
        links = "".join(f'<li><a href="/login?app={name}">{name}</a></li>' for name in registry)
        if session is None:
            body = "<p>选择要登录的应用，将跳转飞书扫码/授权。</p>"
        else:
            who = session.get("name") or session["sub"]
            body = (f"<p>已登录为 {who}，可直接进入应用。</p>"
                    '<form method="post" action="/logout"><button type="submit">退出登录</button></form>')
        return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><title>BridgeFlow 登录门户</title>
<h1>统一登录门户</h1>{body}<ul>{links}</ul>""")

    @app.get("/login")
    async def login(request: Request, app: Annotated[str, Query()]) -> RedirectResponse:
        if app not in registry:
            raise HTTPException(404, f"Unknown application: {app!r}")
        if read_session(request) is not None:
            # Already signed in: skip the Feishu round-trip and go straight to the app.
            return RedirectResponse(registry[app]["redirect_uri"], status_code=302)
        try:
            client = feishu()
        except NotConfigured as exc:
            raise HTTPException(503, str(exc)) from exc
        await client.close()  # the URL is pure string work; no call is made here
        state = seal({"app": app, "nonce": secrets.token_hex(8)}, cfg.session_secret, STATE_TTL_SECONDS)
        return RedirectResponse(client.authorize_url(state), status_code=302)

    @app.get("/callback")
    async def callback(code: str = "", state: str = "") -> RedirectResponse:
        proven = unseal(state, cfg.session_secret)
        if proven is None or proven.get("app") not in registry or not code:
            raise HTTPException(403, "Login state is invalid or expired; start from /login again")
        client = feishu()
        try:
            user = await client.fetch_user(code)
        except NotConfigured as exc:
            raise HTTPException(503, str(exc)) from exc
        except FeishuError as exc:
            raise HTTPException(502, str(exc)) from exc
        finally:
            await client.close()
        session = seal({
            "sub": user["union_id"], "open_id": user.get("open_id", ""),
            "name": user.get("name", ""), "email": user.get("email", ""),
            "avatar": user.get("avatar_url", ""),
        }, cfg.session_secret, cfg.session_ttl_seconds)
        response = RedirectResponse(registry[proven["app"]]["redirect_uri"], status_code=302)
        response.set_cookie(SESSION_COOKIE, session, httponly=True, samesite="lax",
                            secure=cfg.cookie_secure, max_age=cfg.session_ttl_seconds)
        return response

    @app.get("/token")
    async def token(app: Annotated[str, Query()], session: Annotated[dict, Depends(current_session)]) -> dict:
        """Mint the short-lived JWT an app trusts. The browser calls this with its cookie."""
        if app not in registry:
            raise HTTPException(404, f"Unknown application: {app!r}")
        if signer is None:
            raise HTTPException(503, "Portal signing key is not configured: set PORTAL_KEY_PATH")
        now = int(time.time())
        claims = {"iss": cfg.external_base_url, "aud": registry[app]["audience"],
                  "iat": now, "exp": now + cfg.app_token_ttl_seconds,
                  **{k: session[k] for k in ("sub", "open_id", "name", "email")}}
        return {"token": signer.sign(claims), "token_type": "Bearer",
                "expires_in": cfg.app_token_ttl_seconds}

    @app.get("/.well-known/jwks.json")
    async def jwks() -> dict:
        if signer is None:
            raise HTTPException(503, "Portal signing key is not configured: set PORTAL_KEY_PATH")
        return {"keys": [signer.jwk()]}

    @app.get("/me")
    async def me(session: Annotated[dict, Depends(current_session)]) -> dict:
        return {k: session.get(k, "") for k in ("sub", "open_id", "name", "email", "avatar")}

    @app.post("/logout")
    async def logout() -> RedirectResponse:
        response = RedirectResponse("/")
        response.delete_cookie(SESSION_COOKIE)
        return response

    return app


app = create_app(settings)
