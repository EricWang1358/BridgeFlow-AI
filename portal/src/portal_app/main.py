"""Unified login portal: Feishu proves who you are, signed app tokens carry it.

Flow: / → pick a sign-in method → /login → Feishu web login → /callback →
session cookie → /token?app=… → short-lived JWT that the named app verifies
against the JWKS published here. The portal never sees app data, and apps
never see Feishu credentials — decoupling in both directions.

/verify exists for the reverse proxy's forward_auth: it is how the main site
asks "does this browser hold a signed-in session?" before serving anything.

Run:  uvicorn portal_app.main:app --port 8100   (after sourcing env.sh)
"""

# NOTE: no `from __future__ import annotations` here — FastAPI resolves route
# annotations by name at runtime, and the Depends() closures below live inside
# create_app, unreachable from module globals.

import json
import logging
import secrets
import time
from pathlib import Path
from typing import Annotated

import httpx
import yaml
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from portal_app import pages
from portal_app.config import Settings, settings
from portal_app.feishu import FeishuError, FeishuOAuth, NotConfigured
from portal_app.tokens import Signer, seal, seal_secret, unseal, unseal_secret

SESSION_COOKIE = "portal_session"
# A login state lives only for the redirect round-trip.
STATE_TTL_SECONDS = 600
#: Feishu codes that mean the stored refresh token is dead (invalid, revoked or
#: expired) — only these justify sending the browser back through login (401).
#: Rate limits (429) and every other refusal are transient upstream trouble (502).
_DEAD_GRANT_CODES = {20037}

logger = logging.getLogger("portal_app")


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
            # Where /enter ultimately lands the browser. Optional: local dev points
            # redirect_uri straight at the app and never uses /enter.
            "app_uri": str(entry["app_uri"]) if entry.get("app_uri") else "",
            "origins": [str(o) for o in entry.get("origins") or []],
        }
    return registry


def create_app(cfg: Settings, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    registry = load_registry(cfg.apps_path)
    signer = Signer(cfg.key_path) if cfg.key_path else None
    origins = sorted({o for entry in registry.values() for o in entry["origins"]})
    # Where a login ends up is the single most misconfigured fact of a deploy
    # (docs/22 §9b) — say it out loud at boot, not after a bug report.
    logger.info("portal registry: %s",
                {name: entry["redirect_uri"] for name, entry in registry.items()})

    app = FastAPI(title="BridgeFlow login portal", version="0.2.0")
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

    def resolve_app(name: str) -> str | None:
        """Explicit names must be registered; an omitted name is unambiguous only
        when one app exists (the common case: BridgeFlow alone)."""
        if name:
            return name if name in registry else None
        if len(registry) == 1:
            return next(iter(registry))
        return "bridgeflow" if "bridgeflow" in registry else None

    def error(status: int, title: str, detail: str) -> HTMLResponse:
        return HTMLResponse(pages.error_page(title, detail), status_code=status)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "feishu": bool(cfg.feishu_app_id), "signer": signer is not None}

    # response_model=None: the union return annotation is not a Pydantic field type.
    @app.get("/", response_model=None)
    async def index(request: Request) -> HTMLResponse:
        return HTMLResponse(pages.index(read_session(request), registry, bool(cfg.feishu_app_id)))

    @app.get("/login", response_model=None)
    async def login(request: Request, app: Annotated[str, Query()] = "") -> HTMLResponse | RedirectResponse:
        name = resolve_app(app)
        if name is None:
            return error(404, "未知应用", f"应用 {app!r} 未在门户注册。")
        if read_session(request) is not None:
            # Already signed in: skip the Feishu round-trip and go straight to the app.
            return RedirectResponse(registry[name]["redirect_uri"], status_code=302)
        try:
            client = feishu()
        except NotConfigured as exc:
            return error(503, "登录未配置", str(exc))
        await client.close()  # the URL is pure string work; no call is made here
        state = seal({"app": name, "nonce": secrets.token_hex(8)}, cfg.session_secret, STATE_TTL_SECONDS)
        return RedirectResponse(client.authorize_url(state), status_code=302)

    @app.get("/callback", response_model=None)
    async def callback(code: str = "", state: str = "") -> HTMLResponse | RedirectResponse:
        proven = unseal(state, cfg.session_secret)
        if proven is None or proven.get("app") not in registry or not code:
            return error(403, "登录状态无效或已过期", "登录链接只在发起后 10 分钟内有效，请重新发起登录。")
        client = feishu()
        try:
            exchanged = await client.exchange_code(code)
        except NotConfigured as exc:
            return error(503, "登录未配置", str(exc))
        except FeishuError as exc:
            return error(502, "飞书拒绝了这次登录", str(exc))
        finally:
            await client.close()
        user = exchanged["user"]
        session = seal({
            "sub": user["union_id"], "open_id": user.get("open_id", ""),
            "name": user.get("name", ""), "email": user.get("email", ""),
            "avatar": user.get("avatar_url", ""),
            # Drive-capable tokens, AEAD-encrypted inside the signed session (docs/30).
            # Empty refresh_token = the app lacks offline_access; /feishu/user-token
            # says so instead of guessing.
            "feishu": seal_secret(json.dumps({
                "refresh_token": exchanged["refresh_token"],
                "access_token": exchanged["access_token"],
                "access_exp": int(time.time()) + exchanged["access_expires_in"],
            }), cfg.session_secret),
        }, cfg.session_secret, cfg.session_ttl_seconds)
        response = RedirectResponse(registry[proven["app"]]["redirect_uri"], status_code=302)
        response.set_cookie(SESSION_COOKIE, session, httponly=True, samesite="lax",
                            secure=cfg.cookie_secure, max_age=cfg.session_ttl_seconds,
                            domain=cfg.cookie_domain or None)
        return response

    @app.get("/verify", response_model=None)
    async def verify(request: Request) -> Response:
        """Caddy forward_auth target: 200 lets the request through, 401 blocks it.

        Browsers (Accept: text/html) get a page that steers them to the portal;
        API callers get plain JSON.
        """
        session = read_session(request)
        if session is not None:
            return JSONResponse({"ok": True, "sub": session["sub"]})
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(pages.login_required(cfg.external_base_url), status_code=401)
        return JSONResponse({"detail": "Sign in through the portal first"}, status_code=401)

    @app.get("/enter", response_model=None)
    async def enter(request: Request, app: Annotated[str, Query()] = "") -> HTMLResponse | RedirectResponse:
        """Hand a signed-in browser over to the app's own session.

        dsh web mints its native session only from the launch token it prints
        once per boot; start_web.py captures that token into cfg.dsh_token_file.
        The browser detours through the app's URL with the token attached, then
        never needs it again — the session cookie survives restarts (the signing
        secret persists in dsh's credentials store).

        The handover is a PAGE, not a redirect: dsh's cookie is SameSite=Strict
        and this navigation started at Feishu, so a 302 from here would land the
        browser on the app without its cookie (see pages.entering).
        """
        if read_session(request) is None:
            # Absolute, not "/": Caddy may serve this route on the app's own
            # domain (docs/22 §9b), where "/" is the app, not the portal.
            return RedirectResponse(cfg.external_base_url.rstrip("/") + "/", status_code=302)
        name = resolve_app(app)
        if name is None:
            return error(404, "未知应用", f"应用 {app!r} 未在门户注册。")
        target = registry[name]["app_uri"]
        if not target:
            return error(503, "应用入口未配置", f"应用 {name!r} 缺少 app_uri（docs/22 §9b）。")
        token = ""
        if cfg.dsh_token_file:
            try:
                token = Path(cfg.dsh_token_file).read_text(encoding="utf-8").strip()
            except OSError:
                token = ""
        # A missing token is not a dead end. A browser that already holds dsh's
        # session cookie only needs the address; a first-time one pays a single
        # 401 it can retry. Failing closed here locked everybody out instead.
        url = httpx.URL(target)
        if token:
            url = url.copy_add_param("token", token)
        else:
            logger.warning("dsh launch token unavailable (%s): entering %s without one",
                           cfg.dsh_token_file or "PORTAL_DSH_TOKEN_FILE unset", name)
        return HTMLResponse(pages.entering(str(url)), headers={"cache-control": "no-store"})

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

    @app.get("/feishu/user-token")
    async def feishu_user_token(request: Request, response: Response) -> dict:
        """Hand the signed-in browser its own Feishu user access token (docs/30).

        The token is the user's, scoped to what Feishu lets them see; the browser
        relays it to the backend per call. Cached in the encrypted session blob and
        refreshed when it is about to expire — a dead refresh token means re-login,
        never silent renewal.
        """
        session = read_session(request)
        if session is None:
            raise HTTPException(401, "Sign in through the portal first")
        blob = session.get("feishu", "")
        tokens = json.loads(raw) if (raw := unseal_secret(blob, cfg.session_secret)) else None
        if tokens is None:
            # A session from before this feature carries no blob: say re-login, not 500.
            raise HTTPException(401, "Sign in again to grant Feishu Drive access")
        now = time.time()
        if float(tokens.get("access_exp", 0)) < now + 60:
            if not tokens.get("refresh_token"):
                raise HTTPException(503, "Feishu granted no refresh token; the app needs the "
                                         "offline_access scope, then sign in again")
            try:
                client = feishu()
            except NotConfigured as exc:
                raise HTTPException(503, str(exc)) from exc
            try:
                fresh = await client.refresh(tokens["refresh_token"])
            except FeishuError as exc:
                # A dead grant (invalid or revoked refresh token) means
                # re-login — the browser's recovery flow keys off 401.
                # Rate limits and other transient refusals must NOT force
                # re-login; they are upstream trouble and stay 502.
                if exc.code in _DEAD_GRANT_CODES:
                    raise HTTPException(401, str(exc)) from exc
                raise HTTPException(502, str(exc)) from exc
            finally:
                await client.close()
            tokens = {"refresh_token": fresh["refresh_token"],
                      "access_token": fresh["access_token"],
                      "access_exp": int(now) + fresh["access_expires_in"]}
            session["feishu"] = seal_secret(json.dumps(tokens), cfg.session_secret)
            # Feishu rotates the refresh token on use: persist the new one now.
            # The reseal keeps the session's original expiry — a token refresh
            # must not extend how long the session itself lives.
            remaining = max(1, int(session.get("exp", now)) - int(now))
            response.set_cookie(SESSION_COOKIE, seal(session, cfg.session_secret, remaining),
                                httponly=True, samesite="lax", secure=cfg.cookie_secure,
                                max_age=remaining, domain=cfg.cookie_domain or None)
        return {"access_token": tokens["access_token"], "expires_at": tokens["access_exp"]}

    @app.post("/logout")
    async def logout() -> RedirectResponse:
        response = RedirectResponse("/")
        response.delete_cookie(SESSION_COOKIE)
        return response

    return app


app = create_app(settings)
