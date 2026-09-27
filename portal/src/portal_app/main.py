"""Unified login portal: Feishu proves who you are, signed app tokens carry it.

Flow: / → pick a sign-in method → /login → Feishu web login → /callback →
session cookie → /token?app=… → short-lived JWT that the named app verifies
against the JWKS published here. The portal never sees app data, and apps
never see Feishu credentials — decoupling in both directions.

/verify exists for the reverse proxy's forward_auth: it is how the main site
asks "does this browser hold a signed-in session?" before serving anything —
and, once PORTAL_CONSOLE_CHECK_URL is set, "may this person reach the agent
console?" as well (issue #229, docs/34 §二 第 1 步).

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
from portal_app.seats import Assignments, Seats, load_seats
from portal_app.tokens import Signer, seal, seal_secret, unseal, unseal_secret

SESSION_COOKIE = "portal_session"
# A login state lives only for the redirect round-trip.
STATE_TTL_SECONDS = 600
#: Feishu codes that mean the stored refresh token is dead (invalid, revoked or
#: expired) — only these justify sending the browser back through login (401).
#: Rate limits (429) and every other refusal are transient upstream trouble (502).
_DEAD_GRANT_CODES = {20037}
#: Cached console decisions are small, but the map is still bounded so a long-lived
#: portal cannot accumulate one entry per person who ever signed in.
_DECISION_CACHE_MAX = 256

logger = logging.getLogger("portal_app")


class ConsoleUnavailable(Exception):
    """The console grant could not be established — distinct from "not granted".

    Withholding is not refusing: the browser must be told which of the two
    happened, because only one of them is fixed by waiting or by an admin.
    """


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


def create_app(cfg: Settings, transport: httpx.AsyncBaseTransport | None = None,
               check_transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    registry = load_registry(cfg.apps_path)
    signer = Signer(cfg.key_path) if cfg.key_path else None
    origins = sorted({o for entry in registry.values() for o in entry["origins"]})
    # Where a login ends up is the single most misconfigured fact of a deploy
    # (docs/22 §9b) — say it out loud at boot, not after a bug report.
    logger.info("portal registry: %s",
                {name: entry["redirect_uri"] for name, entry in registry.items()})
    # Seats share the portal's URL scheme: an https portal fronts https seats.
    seats: Seats | None = None
    if cfg.seats_path:
        scheme = "https" if cfg.external_base_url.startswith("https") else "http"
        seats = load_seats(cfg.seats_path, cfg.seat_base_domain, scheme)
        if not cfg.seat_assignments_path:
            raise RuntimeError("PORTAL_SEAT_ASSIGNMENTS is required when PORTAL_SEATS_PATH is set "
                               "(scripts/provision_seat.sh --init writes it into env.sh)")
        # One validating read at boot; requests re-read so an ops release lands
        # without a portal restart.
        def seat_state() -> Assignments:
            return Assignments(cfg.seat_assignments_path)

        logger.info("portal seats: %s capacity, %s claimed",
                    len(seats), len(seat_state().as_map()))
        # Seat pages fetch the portal cross-origin with credentials (the
        # browser trades its session cookie for an app token) and Caddy puts
        # no portal route on seat hosts, so every seat origin must be in the
        # CORS list — derived from the fleet, not hand-kept in the registry.
        origins = sorted({*origins, *(seats.url(s) for name in seats.names()
                                      if (s := seats.seat(name)))})
    else:
        def seat_state() -> Assignments:  # pragma: no cover - unreachable without seats
            raise RuntimeError("seat state requested without a seat fleet")

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

    def user_claims(app_name: str, session: dict) -> dict:
        now = int(time.time())
        return {"iss": cfg.external_base_url, "aud": registry[app_name]["audience"],
                "iat": now, "exp": now + cfg.app_token_ttl_seconds,
                **{k: session[k] for k in ("sub", "open_id", "name", "email")}}

    # subject -> (expires_at, allowed). Only answers land here; a failure is
    # re-asked on the next request, so an outage never sticks to a session.
    console_decisions: dict[str, tuple[float, bool]] = {}

    async def console_allowed(session: dict) -> bool:
        """Ask the app whether this person may reach its console (#229).

        The question travels as a token this portal just signed, which the app
        verifies against the JWKS it already trusts — no new credential, and the
        role rules stay where they are declared (`access-control.yaml`), not
        copied into the portal.
        """
        now = time.monotonic()
        cached = console_decisions.get(session["sub"])
        if cached is not None and cached[0] > now:
            return cached[1]
        name = resolve_app("")
        if name is None:
            raise ConsoleUnavailable("The portal has no default application, so console access cannot be checked (apps.yaml).")
        if signer is None:
            raise ConsoleUnavailable("The portal signing key is not configured (PORTAL_KEY_PATH), so the application cannot be asked.")
        try:
            async with httpx.AsyncClient(transport=check_transport, timeout=10) as client:
                response = await client.get(cfg.console_check_url,
                                            headers={"x-bridgeflow-user": signer.sign(user_claims(name, session))})
        except httpx.HTTPError as exc:
            raise ConsoleUnavailable(f"The application is unreachable right now: {exc}.") from exc
        if response.status_code != 200:
            detail = ""
            try:
                body = response.json()
                detail = body.get("detail", "") if isinstance(body, dict) else ""
            except ValueError:
                detail = ""
            raise ConsoleUnavailable(detail or f"The application answered HTTP {response.status_code}.")
        try:
            allowed = response.json()["allowed"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ConsoleUnavailable("The application's access answer could not be read.") from exc
        if not isinstance(allowed, bool):
            raise ConsoleUnavailable("The application's access answer is not a boolean.")
        if len(console_decisions) >= _DECISION_CACHE_MAX:
            console_decisions.clear()
        console_decisions[session["sub"]] = (now + cfg.console_check_ttl_seconds, allowed)
        return allowed

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "feishu": bool(cfg.feishu_app_id), "signer": signer is not None,
                # Whether /verify enforces the console grant, so preflight can see
                # the gate's state without reading the deploy's environment.
                "console_gate": bool(cfg.console_check_url),
                # Seat fleet (docs/35): 0 = single-console behaviour; with a
                # fleet, assigned counts the first-come-first-served claims.
                "seats": len(seats) if seats is not None else 0,
                "seats_assigned": len(seat_state().as_map()) if seats is not None else 0}

    # response_model=None: the union return annotation is not a Pydantic field type.
    @app.get("/", response_model=None)
    async def index(request: Request) -> HTMLResponse:
        return HTMLResponse(pages.index(read_session(request), registry, bool(cfg.feishu_app_id),
                                        guest=bool(cfg.guest_app_uri)))

    @app.get("/guest", response_model=None)
    async def guest() -> HTMLResponse:
        """Into the guest console (docs/22 §9e), without signing in.

        Nothing is issued: no session cookie, no app token. The guest instance is a
        separate backend and console with sample data only, so entering it grants
        nothing the real service guards.
        """
        if not cfg.guest_app_uri:
            return error(404, "Guest mode is off", "This deployment has no guest entry. Sign in with Feishu.")
        # The public demo sends every browser without a dsh session here (docs/36 §4), so
        # entering without a token would bounce straight back: a loop, not a degraded entry.
        # No token means the instance is (re)starting — say so and let the page retry.
        if not (cfg.guest_token_file and read_token_file(cfg.guest_token_file)):
            return HTMLResponse(pages.restarting(), status_code=503,
                                headers={"cache-control": "no-store", "retry-after": "15"})
        return handover(cfg.guest_app_uri, cfg.guest_token_file, cfg.guest_token_file)

    @app.get("/login", response_model=None)
    async def login(request: Request, app: Annotated[str, Query()] = "") -> HTMLResponse | RedirectResponse:
        name = resolve_app(app)
        if name is None:
            return error(404, "Unknown application", f"Application {app!r} is not registered with the portal.")
        if read_session(request) is not None:
            # Already signed in: skip the Feishu round-trip and go straight to the app.
            return RedirectResponse(registry[name]["redirect_uri"], status_code=302)
        try:
            client = feishu()
        except NotConfigured as exc:
            return error(503, "Sign-in is not configured", str(exc))
        await client.close()  # the URL is pure string work; no call is made here
        state = seal({"app": name, "nonce": secrets.token_hex(8)}, cfg.session_secret, STATE_TTL_SECONDS)
        return RedirectResponse(client.authorize_url(state), status_code=302)

    @app.get("/callback", response_model=None)
    async def callback(code: str = "", state: str = "") -> HTMLResponse | RedirectResponse:
        proven = unseal(state, cfg.session_secret)
        if proven is None or proven.get("app") not in registry or not code:
            return error(403, "Sign-in link invalid or expired",
                         "A sign-in link is valid for 10 minutes after it starts. Please sign in again.")
        client = feishu()
        try:
            exchanged = await client.exchange_code(code)
        except NotConfigured as exc:
            return error(503, "Sign-in is not configured", str(exc))
        except FeishuError as exc:
            return error(502, "Feishu refused this sign-in", str(exc))
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
        """Caddy forward_auth target: 200 lets the request through, anything else blocks it.

        Three questions, in order: is this browser signed in (401 if not);
        when PORTAL_SEATS_PATH is set, is the requested host this person's own
        seat (403 if the subdomain belongs to someone else — docs/35); and —
        while PORTAL_CONSOLE_CHECK_URL is set — may this person reach the
        console (403 if not granted, 503 if the answer could not be obtained).

        The seat binding runs before the console gate and independently of it:
        it is a local fact about routing, not a role question, and it must hold
        even on a deployment that has not turned the gate on yet.

        503 withholds the whole site rather than the console alone, and that is
        the intended reading: everything behind forward_auth *is* the app shell
        (docs/22 §7 routes one site to dsh web), so there is no read-only surface
        being taken away here that would otherwise survive.

        Browsers (Accept: text/html) get a page; API callers get plain JSON.
        """
        session = read_session(request)
        if session is None:
            if "text/html" in request.headers.get("accept", ""):
                return HTMLResponse(pages.login_required(cfg.external_base_url), status_code=401)
            return JSONResponse({"detail": "Sign in through the portal first"}, status_code=401)

        def blocked(status: int, title: str, detail: str) -> Response:
            if "text/html" in request.headers.get("accept", ""):
                return HTMLResponse(pages.console_blocked(title, detail, cfg.external_base_url),
                                    status_code=status)
            return JSONResponse({"detail": detail}, status_code=status)

        if seats is not None:
            # The original Host is preserved through Caddy's forward_auth; the
            # forwarded variant is read as a fallback for other front doors.
            host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
            host = host.split(":", 1)[0]
            seat = seats.for_host(host)
            if seat is not None:
                # Binding is a fact about the claim state, re-read per request:
                # an ops release takes effect on the very next request, not at
                # the next portal restart. An unclaimed seat belongs to nobody.
                owner = seat_state().sub_for_seat(seat.name)
                if owner != session["sub"]:
                    logger.warning("seat %s (owner=%s) denied to subject %s",
                                   seat.name, owner or "unclaimed", session["sub"])
                    return blocked(403, "This workspace seat belongs to someone else",
                                   "Each seat belongs to the first person who claims it, and you are signed in "
                                   "as someone else. Open your own workspace from the portal home page. If all "
                                   "seats are taken or one needs releasing, contact the General Manager's Office.")

        if not cfg.console_check_url:
            return JSONResponse({"ok": True, "sub": session["sub"]})

        try:
            allowed = await console_allowed(session)
        except ConsoleUnavailable as exc:
            logger.warning("console access undetermined for %s: %s", session["sub"], exc)
            return blocked(503, "Your access cannot be confirmed right now",
                           f"{exc} This is not a refusal: the system could not confirm your access. "
                           "Try again later or contact an administrator.")
        if not allowed:
            return blocked(403, "No console access",
                           "You are signed in but have not been granted access to the AI console. An "
                           "administrator grants it on a role in the access configuration. Contact the "
                           "General Manager's Office if you need it.")
        return JSONResponse({"ok": True, "sub": session["sub"]})

    def read_token_file(path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def handover(target: str, token_path: str, token_source: str) -> HTMLResponse:
        """The entering page: navigate the browser to the console with its launch token.

        A missing token is not a dead end. A browser that already holds dsh's
        session cookie only needs the address; a first-time one pays a single
        401 it can retry. Failing closed here locked everybody out instead.
        """
        token = read_token_file(token_path) if token_path else ""
        url = httpx.URL(target)
        if token:
            url = url.copy_add_param("token", token)
        else:
            logger.warning("dsh launch token unavailable (%s): entering %s without one",
                           token_source, target)
        return HTMLResponse(pages.entering(str(url)), headers={"cache-control": "no-store"})

    @app.get("/enter", response_model=None)
    async def enter(request: Request, app: Annotated[str, Query()] = "") -> HTMLResponse | RedirectResponse:
        """Hand a signed-in browser over to the app's own session.

        Seat deployments (docs/35) are first come first served: the first
        authorized person to enter claims a free seat and keeps it; later
        entries reuse the claim. Without a seat fleet the single-console
        behaviour is unchanged.

        dsh web mints its native session only from the launch token it prints
        once per boot; start_web.py captures that token into the seat's own
        DSH_HOME (per seat) or cfg.dsh_token_file (single console).

        The handover is a PAGE, not a redirect: dsh's cookie is SameSite=Strict
        and this navigation started at Feishu, so a 302 from here would land the
        browser on the app without its cookie (see pages.entering).
        """
        session = read_session(request)
        if session is None:
            # Absolute, not "/": Caddy may serve this route on the app's own
            # domain (docs/22 §9b), where "/" is the app, not the portal.
            return RedirectResponse(cfg.external_base_url.rstrip("/") + "/", status_code=302)
        if seats is not None:
            # First come first served (docs/35): an authorized person claims a
            # free seat on first entry and keeps it — their sessions live in
            # that seat's home. Release is an ops act (provision_seat.sh
            # --release), never a request the portal serves.
            state = seat_state()
            seat_name = state.seat_for(session["sub"])
            if seat_name is None:
                if cfg.console_check_url:
                    try:
                        allowed = await console_allowed(session)
                    except ConsoleUnavailable as exc:
                        return error(503, "Your access cannot be confirmed right now",
                                     f"{exc} This is not a refusal: the system could not confirm your "
                                     "access. Try again later or contact an administrator.")
                    if not allowed:
                        return error(403, "No console access",
                                     "You are signed in but have not been granted access to the AI console. "
                                     "An administrator grants it on a role in the access configuration. "
                                     "Contact the General Manager's Office if you need it.")
                seat_name = state.claim(session["sub"], seats.names())
                if seat_name is None:
                    return error(403, "All seats are taken",
                                 f"All {len(seats)} seats are claimed. Ask an administrator to release an "
                                 "idle seat (scripts/provision_seat.sh --release <union_id>) and try again.")
                logger.info("seat %s claimed by subject %s", seat_name, session["sub"])
            seat = seats.seat(seat_name)
            if seat is None:
                return error(503, "Seat configuration is inconsistent",
                             f"The claim record points to seat {seat_name!r}, which does not exist. Check "
                             "whether seats.yaml or seats-assigned.json was edited by hand.")
            return handover(seats.url(seat), str(seat.token_file), f"seat {seat.name} home")
        name = resolve_app(app)
        if name is None:
            return error(404, "Unknown application", f"Application {app!r} is not registered with the portal.")
        target = registry[name]["app_uri"]
        if not target:
            return error(503, "Application entry not configured", f"Application {name!r} has no app_uri (docs/22 §9b).")
        return handover(target, cfg.dsh_token_file,
                        cfg.dsh_token_file or "PORTAL_DSH_TOKEN_FILE unset")

    @app.get("/token")
    async def token(app: Annotated[str, Query()], session: Annotated[dict, Depends(current_session)]) -> dict:
        """Mint the short-lived JWT an app trusts. The browser calls this with its cookie."""
        if app not in registry:
            raise HTTPException(404, f"Unknown application: {app!r}")
        if signer is None:
            raise HTTPException(503, "Portal signing key is not configured: set PORTAL_KEY_PATH")
        return {"token": signer.sign(user_claims(app, session)), "token_type": "Bearer",
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
