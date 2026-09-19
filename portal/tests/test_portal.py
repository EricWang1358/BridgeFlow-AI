"""Portal flow, tested against a simulated Feishu — no real tenant, no network."""

import json

import httpx
import jwt
import pytest
import yaml
from fastapi.testclient import TestClient

from portal_app import tokens
from portal_app.config import Settings
from portal_app.main import SESSION_COOKIE, create_app

UNION_ID = "ou_test_user_1"
PROFILE = {"union_id": UNION_ID, "open_id": "o-1", "name": "测试用户",
           "email": "u@example.com", "avatar_url": ""}


class Tenant:
    """A fake Feishu: app token, code exchange, user profile."""

    def __init__(self, users: dict[str, dict] | None = None):
        self.users = users or {"code-good": PROFILE}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/app_access_token/internal"):
            return httpx.Response(200, json={"code": 0, "app_access_token": "a-1", "expire": 7200})
        if path.endswith("/oidc/access_token"):
            code = json.loads(request.content)["code"]
            if code not in self.users:
                return httpx.Response(400, json={"code": 20003, "msg": "invalid code"})
            return httpx.Response(200, json={"code": 0, "data": {"access_token": "u-1", "refresh_token": "r-1",
                                                                 "expires_in": 7200, "refresh_expires_in": 2592000}})
        if path.endswith("/user_info"):
            if request.headers.get("authorization") != "Bearer u-1":
                return httpx.Response(401, json={"code": 99991663, "msg": "invalid token"})
            return httpx.Response(200, json={"code": 0, "data": self.users["code-good"]})
        return httpx.Response(404, json={"code": 404, "msg": "unknown"})


@pytest.fixture
def portal(tmp_path):
    tokens.generate_keypair(tmp_path / "portal.pem")
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": {
        "audience": "bridgeflow", "redirect_uri": "http://web.test/after-login",
        "origins": ["http://web.test"]}}}), encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   feishu_base_url="https://feishu.test", key_path=str(tmp_path / "portal.pem"),
                   session_secret="s" * 32, external_base_url="http://portal.test",
                   apps_path=str(apps))
    app = create_app(cfg, transport=httpx.MockTransport(Tenant()))
    with TestClient(app, follow_redirects=False) as client:
        yield client


def public_key(client) -> dict:
    return client.get("/.well-known/jwks.json").json()["keys"][0]


def decode(client, token: str) -> dict:
    jwk = public_key(client)
    key = jwt.algorithms.OKPAlgorithm.from_jwk(json.dumps({k: jwk[k] for k in ("kty", "crv", "x")}))
    return jwt.decode(token, key, algorithms=["EdDSA"], audience="bridgeflow",
                      issuer="http://portal.test")


def login(client) -> None:
    """Drive the whole Feishu round-trip; the session cookie lands on the client."""
    redirect = client.get("/login", params={"app": "bridgeflow"})
    state = httpx.URL(redirect.headers["location"]).params["state"]
    client.get("/callback", params={"code": "code-good", "state": state})


def test_login_redirects_to_feishu_with_a_signed_state(portal):
    response = portal.get("/login", params={"app": "bridgeflow"})
    assert response.status_code == 302
    target = httpx.URL(response.headers["location"])
    assert target.host == "feishu.test" and target.path == "/open-apis/authen/v1/index"
    state = tokens.unseal(target.params["state"], "s" * 32)
    assert state["app"] == "bridgeflow" and state["nonce"]


def test_the_app_defaults_to_the_only_registered_one(portal):
    response = portal.get("/login")
    assert response.status_code == 302
    target = httpx.URL(response.headers["location"])
    assert target.host == "feishu.test"
    state = tokens.unseal(target.params["state"], "s" * 32)
    assert state["app"] == "bridgeflow"


def test_an_unregistered_app_is_turned_away(portal):
    assert portal.get("/login", params={"app": "stranger"}).status_code == 404
    login(portal)
    assert portal.get("/token", params={"app": "stranger"}).status_code == 404


def test_a_tampered_state_cannot_complete_login(portal):
    redirect = portal.get("/login", params={"app": "bridgeflow"})
    state = httpx.URL(redirect.headers["location"]).params["state"]
    response = portal.get("/callback", params={"code": "code-good", "state": state + "x"})
    assert response.status_code == 403
    assert "text/html" in response.headers["content-type"]
    assert "重新登录" in response.text
    assert SESSION_COOKIE not in portal.cookies


def test_full_flow_mints_a_token_the_app_can_verify(portal):
    login(portal)
    assert portal.cookies.get(SESSION_COOKIE)
    minted = portal.get("/token", params={"app": "bridgeflow"})
    assert minted.status_code == 200 and minted.json()["expires_in"] == 900
    claims = decode(portal, minted.json()["token"])
    assert claims["sub"] == UNION_ID and claims["name"] == "测试用户"
    assert claims["aud"] == "bridgeflow" and claims["exp"] - claims["iat"] == 900


def test_a_token_without_a_session_is_refused(portal):
    assert portal.get("/token", params={"app": "bridgeflow"}).status_code == 401


def test_anonymous_visitors_get_the_login_page(portal):
    response = portal.get("/")
    assert response.status_code == 200 and "飞书登录" in response.text
    # The official Feishu mark, in the brand's own colours (docs/design/01-portal P01).
    # A generic glyph in its place is a different product's button.
    assert "#00D6B9" in response.text and "#3370FF" in response.text


def test_a_signed_in_user_skips_feishu_on_login(portal):
    login(portal)
    response = portal.get("/login", params={"app": "bridgeflow"})
    assert response.status_code == 302
    assert response.headers["location"] == "http://web.test/after-login"


def test_a_signed_in_user_sees_the_way_into_the_app(portal):
    login(portal)
    response = portal.get("/")
    assert response.status_code == 200
    assert "测试用户" in response.text
    assert 'href="http://web.test/after-login"' in response.text


def test_a_signed_in_user_sees_every_app_when_several_exist(tmp_path):
    tokens.generate_keypair(tmp_path / "portal.pem")
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {
        "bridgeflow": {"audience": "bridgeflow", "redirect_uri": "http://web.test/after-login",
                       "origins": ["http://web.test"]},
        "other": {"audience": "other", "redirect_uri": "http://other.test/",
                  "origins": []},
    }}), encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   feishu_base_url="https://feishu.test", key_path=str(tmp_path / "portal.pem"),
                   session_secret="s" * 32, external_base_url="http://portal.test",
                   apps_path=str(apps))
    with TestClient(create_app(cfg, transport=httpx.MockTransport(Tenant())),
                    follow_redirects=False) as client:
        login(client)
        response = client.get("/")
        assert response.status_code == 200 and "测试用户" in response.text
        assert 'href="http://web.test/after-login"' in response.text
        assert 'href="http://other.test/"' in response.text
        # The direct /login shortcut still skips Feishu per app.
        assert client.get("/login", params={"app": "other"}).headers["location"] == "http://other.test/"


def make_portal(tmp_path, entry_extra: dict | None = None, **cfg_overrides):
    """A second portal instance with its own registry/config, for one-off scenarios."""
    tokens.generate_keypair(tmp_path / "portal.pem")
    entry = {"audience": "bridgeflow", "redirect_uri": "http://web.test/after-login",
             "origins": ["http://web.test"], **(entry_extra or {})}
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": entry}}), encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   feishu_base_url="https://feishu.test", key_path=str(tmp_path / "portal.pem"),
                   session_secret="s" * 32, external_base_url="http://portal.test",
                   apps_path=str(apps), **cfg_overrides)
    return create_app(cfg, transport=httpx.MockTransport(Tenant()))


def test_enter_hands_a_signed_in_browser_to_the_app(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("tok-1\n", encoding="utf-8")
    app = make_portal(tmp_path, entry_extra={"app_uri": "http://web.test/"},
                      dsh_token_file=str(token_file))
    with TestClient(app, follow_redirects=False) as client:
        # Anonymous → the portal itself, absolutely: this route can be served on
        # the app's domain, where a relative "/" would loop into the app.
        assert client.get("/enter").headers["location"] == "http://portal.test/"
        login(client)
        response = client.get("/enter")
        assert response.status_code == 200
        # The whole point: no Location header. dsh's session cookie is
        # SameSite=Strict, and one more redirect keeps the browser inside the
        # cross-site chain that started at Feishu, so the cookie would be
        # withheld and dsh would answer its own 401. The handover must be a
        # document that starts a fresh, same-site navigation.
        assert "location" not in response.headers
        assert response.headers["cache-control"] == "no-store"
        assert "http://web.test/?token=tok-1" in response.text
        assert '<meta name="referrer" content="no-referrer">' in response.text


def test_enter_still_lands_the_browser_when_the_token_is_missing(tmp_path):
    """A browser that already holds dsh's cookie needs only the address; failing
    closed on a missing token locked returning users out of a working site."""
    app = make_portal(tmp_path, entry_extra={"app_uri": "http://web.test/"},
                      dsh_token_file=str(tmp_path / "missing"))
    with TestClient(app, follow_redirects=False) as client:
        login(client)
        response = client.get("/enter")
        assert response.status_code == 200 and "location" not in response.headers
        assert "http://web.test/" in response.text and "token=" not in response.text


def test_enter_fails_closed_without_an_app_uri(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("tok-2\n", encoding="utf-8")
    app = make_portal(tmp_path, dsh_token_file=str(token_file))
    with TestClient(app, follow_redirects=False) as client:
        login(client)
        assert client.get("/enter").status_code == 503


def test_logout_ends_the_session(portal):
    login(portal)
    portal.post("/logout")
    assert portal.get("/token", params={"app": "bridgeflow"}).status_code == 401


def test_a_feishu_refusal_creates_no_session(portal):
    redirect = portal.get("/login", params={"app": "bridgeflow"})
    state = httpx.URL(redirect.headers["location"]).params["state"]
    response = portal.get("/callback", params={"code": "code-bogus", "state": state})
    assert response.status_code == 502 and "invalid code" in response.text
    assert SESSION_COOKIE not in portal.cookies


def test_verify_blocks_anonymous_and_admits_the_signed_in(portal):
    anonymous = portal.get("/verify")
    assert anonymous.status_code == 401
    assert anonymous.json()["detail"]
    login(portal)
    signed_in = portal.get("/verify")
    assert signed_in.status_code == 200
    assert signed_in.json() == {"ok": True, "sub": UNION_ID}


def test_verify_steers_browsers_to_the_portal(portal):
    response = portal.get("/verify", headers={"accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 401
    assert "text/html" in response.headers["content-type"]
    assert "http://portal.test/" in response.text


def test_a_cookie_domain_is_set_only_when_configured(tmp_path, portal):
    tokens.generate_keypair(tmp_path / "portal.pem")
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": {
        "audience": "bridgeflow", "redirect_uri": "http://web.test/after-login",
        "origins": ["http://web.test"]}}}), encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   feishu_base_url="https://feishu.test", key_path=str(tmp_path / "portal.pem"),
                   session_secret="s" * 32, external_base_url="http://portal.test",
                   apps_path=str(apps), cookie_domain=".web.test")
    with TestClient(create_app(cfg, transport=httpx.MockTransport(Tenant())),
                    follow_redirects=False) as client:
        redirect = client.get("/login")
        state = httpx.URL(redirect.headers["location"]).params["state"]
        response = client.get("/callback", params={"code": "code-good", "state": state})
        assert "Domain=.web.test" in response.headers["set-cookie"]
    # The shared fixture (no cookie_domain) must keep the cookie host-only.
    redirect = portal.get("/login")
    state = httpx.URL(redirect.headers["location"]).params["state"]
    response = portal.get("/callback", params={"code": "code-good", "state": state})
    assert "Domain=" not in response.headers["set-cookie"]


def test_missing_credentials_say_not_configured(tmp_path):
    tokens.generate_keypair(tmp_path / "portal.pem")
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": {
        "audience": "bridgeflow", "redirect_uri": "http://web.test/", "origins": []}}}),
        encoding="utf-8")
    cfg = Settings(feishu_app_id="", feishu_app_secret="",
                   key_path=str(tmp_path / "portal.pem"), session_secret="s" * 32,
                   apps_path=str(apps))
    with TestClient(create_app(cfg)) as client:
        response = client.get("/login", params={"app": "bridgeflow"})
        assert response.status_code == 503 and "not configured" in response.text

        # The home page draws no button that cannot be pressed: it names the
        # deployment problem and tells the operator WHICH variable is missing —
        # names and set/unset only, never a value.
        home = client.get("/")
        assert home.status_code == 200
        assert "飞书登录未配置" in home.text and "飞书登录</span>" not in home.text
        assert "PORTAL_FEISHU_APP_ID" in home.text and "未设置" in home.text
        assert "s" * 32 not in home.text


def test_missing_signing_key_fails_closed(tmp_path):
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": {
        "audience": "bridgeflow", "redirect_uri": "http://web.test/", "origins": []}}}),
        encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   key_path="", session_secret="s" * 32, apps_path=str(apps))
    with TestClient(create_app(cfg)) as client:
        assert client.get("/.well-known/jwks.json").status_code == 503


def test_an_invalid_registry_fails_fast(tmp_path):
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"broken": {"redirect_uri": "http://web.test/"}}}),
                    encoding="utf-8")
    cfg = Settings(apps_path=str(apps), session_secret="s" * 32)
    with pytest.raises(RuntimeError, match="audience"):
        create_app(cfg)


# --- Feishu user-token custody (docs/30) -----------------------------------------------

class RefreshingTenant(Tenant):
    """A fake Feishu that also rotates refresh tokens."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oidc/refresh_access_token"):
            self.refresh_calls += 1
            if json.loads(request.content)["refresh_token"] != "r-1":
                return httpx.Response(400, json={"code": 20037, "msg": "invalid refresh token"})
            return httpx.Response(200, json={"code": 0, "data": {"access_token": "u-2",
                                             "refresh_token": "r-2", "expires_in": 7200}})
        return super().__call__(request)


def test_seal_secret_round_trips_and_resists_tampering():
    blob = tokens.seal_secret('{"refresh_token":"r-1"}', "s" * 32)
    assert json.loads(tokens.unseal_secret(blob, "s" * 32))["refresh_token"] == "r-1"
    assert tokens.unseal_secret(blob, "t" * 32) is None           # wrong key
    assert tokens.unseal_secret(blob[:-4] + "AAAA", "s" * 32) is None  # tampered
    assert tokens.unseal_secret("garbage", "s" * 32) is None


def test_session_cookie_never_carries_tokens_in_plaintext(portal):
    login(portal)
    cookie = portal.cookies.get(SESSION_COOKIE)
    assert "u-1" not in cookie and "r-1" not in cookie
    session = tokens.unseal(cookie, "s" * 32)
    data = json.loads(tokens.unseal_secret(session["feishu"], "s" * 32))
    assert data["access_token"] == "u-1" and data["refresh_token"] == "r-1"


def test_user_token_endpoint_serves_the_cached_token(portal):
    assert portal.get("/feishu/user-token").status_code == 401  # no session
    login(portal)
    body = portal.get("/feishu/user-token").json()
    assert body["access_token"] == "u-1" and body["expires_at"] > 0


def test_user_token_endpoint_refreshes_and_rotates(tmp_path):
    tokens.generate_keypair(tmp_path / "portal.pem")
    apps = tmp_path / "apps.yaml"
    apps.write_text(yaml.safe_dump({"apps": {"bridgeflow": {
        "audience": "bridgeflow", "redirect_uri": "http://web.test/after-login",
        "origins": ["http://web.test"]}}}), encoding="utf-8")
    cfg = Settings(feishu_app_id="cli_test", feishu_app_secret="secret",
                   feishu_base_url="https://feishu.test", key_path=str(tmp_path / "portal.pem"),
                   session_secret="s" * 32, external_base_url="http://portal.test",
                   apps_path=str(apps))
    fake = RefreshingTenant()
    with TestClient(create_app(cfg, transport=httpx.MockTransport(fake)), follow_redirects=False) as client:
        login(client)
        # Force the cached access token into the past; the next call must refresh.
        session = tokens.unseal(client.cookies.get(SESSION_COOKIE), "s" * 32)
        data = json.loads(tokens.unseal_secret(session["feishu"], "s" * 32))
        data["access_exp"] = 1
        session["feishu"] = tokens.seal_secret(json.dumps(data), "s" * 32)
        client.cookies.clear()
        client.cookies.set(SESSION_COOKIE, tokens.seal(session, "s" * 32, 3600))
        response = client.get("/feishu/user-token")
        assert response.json()["access_token"] == "u-2" and fake.refresh_calls == 1
        # The rotated refresh token was persisted into the replacement cookie.
        replacement = httpx.Cookies()
        replacement.extract_cookies(response)
        refreshed = json.loads(tokens.unseal_secret(
            tokens.unseal(replacement.get(SESSION_COOKIE), "s" * 32)["feishu"], "s" * 32))
        assert refreshed["refresh_token"] == "r-2"
