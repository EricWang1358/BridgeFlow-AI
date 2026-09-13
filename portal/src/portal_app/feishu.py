"""Feishu OAuth (web login): the portal's first identity provider.

Credentials come from the launching shell (PORTAL_FEISHU_APP_ID / _SECRET),
never from a file in the repository. The transport is injectable so the
protocol can be tested without a tenant — same pattern as the backend's
FeishuDrive, duplicated deliberately: the portal stays decoupled and does not
import the app it serves.
"""

from __future__ import annotations

import httpx


class FeishuError(Exception):
    """Feishu refused, or could not be reached. No session was created."""


class NotConfigured(FeishuError):
    pass


class FeishuOAuth:
    """Three calls: authorize URL, code exchange, user profile."""

    def __init__(self, app_id: str, app_secret: str, base_url: str, redirect_uri: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not app_id or not app_secret:
            raise NotConfigured(
                "Feishu is not configured: export PORTAL_FEISHU_APP_ID and PORTAL_FEISHU_APP_SECRET"
            )
        self._app_id, self._app_secret = app_id, app_secret
        self._base_url = base_url
        self._redirect_uri = redirect_uri
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=30)

    async def close(self) -> None:
        await self._client.aclose()

    def authorize_url(self, state: str) -> str:
        return str(httpx.URL(f"{self._base_url}/open-apis/authen/v1/index", params={
            "app_id": self._app_id, "redirect_uri": self._redirect_uri, "state": state}))

    @staticmethod
    async def _json(response: httpx.Response) -> dict:
        try:
            body = response.json()
        except ValueError as exc:
            raise FeishuError(f"Feishu returned HTTP {response.status_code} without a JSON body") from exc
        if response.status_code >= 400 or body.get("code", 0) != 0:
            raise FeishuError(f"Feishu refused (code {body.get('code')}): {body.get('msg', 'no message')}")
        return body

    async def _app_access_token(self) -> str:
        body = await self._json(await self._client.post(
            "/open-apis/auth/v3/app_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret}))
        return str(body["app_access_token"])

    async def fetch_user(self, code: str) -> dict:
        """Exchange a one-time login code for the user's profile."""
        app_token = await self._app_access_token()
        token_body = await self._json(await self._client.post(
            "/open-apis/authen/v1/oidc/access_token",
            headers={"authorization": f"Bearer {app_token}"},
            json={"grant_type": "authorization_code", "code": code}))
        user_token = str(token_body["data"]["access_token"])
        info = await self._json(await self._client.get(
            "/open-apis/authen/v1/user_info", headers={"authorization": f"Bearer {user_token}"}))
        data = info["data"]
        if not data.get("union_id"):
            raise FeishuError("Feishu returned no union_id; the app needs contact scopes")
        return data
