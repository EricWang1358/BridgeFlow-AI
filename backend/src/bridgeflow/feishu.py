"""Feishu Drive: bring department files in, send results back (#140).

Scope as agreed on 2026-09-13 (`docs/24`): upload and download shortcuts only. Feishu
owns storage and who may see what; BridgeFlow neither mirrors its permissions nor
keeps its files beyond the batch they were imported into.

Credentials are the app id and secret of a Feishu self-built app, exported by the
launching shell as `FEISHU_APP_ID` / `FEISHU_APP_SECRET` — never written to a file in
the repository. Without them every call says "not configured" instead of pretending.

The client is deliberately small and synchronous-free of framework state: one class,
three calls, errors surfaced with Feishu's own code and message. The transport is
injectable so the protocol can be tested without a tenant.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import httpx

from bridgeflow.config import settings

MAX_FILE_BYTES = 25 * 1024 * 1024


class FeishuError(Exception):
    """Feishu refused, or could not be reached. Nothing was imported or uploaded."""


class NotConfigured(FeishuError):
    pass


@dataclass
class _Token:
    value: str
    expires_at: float


class FeishuDrive:
    def __init__(self, app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn",
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not app_id or not app_secret:
            raise NotConfigured("Feishu is not configured: export FEISHU_APP_ID and FEISHU_APP_SECRET")
        self._app_id, self._app_secret = app_id, app_secret
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=30)
        self._token: _Token | None = None

    async def close(self) -> None:
        await self._client.aclose()

    async def _tenant_token(self) -> str:
        if self._token and self._token.expires_at > time.monotonic() + 60:
            return self._token.value
        body = await self._json(await self._client.post(
            "/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret}))
        self._token = _Token(str(body["tenant_access_token"]), time.monotonic() + float(body.get("expire", 0)))
        return self._token.value

    async def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {await self._tenant_token()}"}

    @staticmethod
    async def _json(response: httpx.Response) -> dict:
        try:
            body = response.json()
        except ValueError as exc:
            raise FeishuError(f"Feishu returned HTTP {response.status_code} without a JSON body") from exc
        if response.status_code >= 400 or body.get("code", 0) != 0:
            raise FeishuError(f"Feishu refused (code {body.get('code')}): {body.get('msg', 'no message')}")
        return body

    async def download(self, file_token: str) -> tuple[str, bytes]:
        """A Drive file's name and bytes. The name comes from Feishu, never from the caller."""
        response = await self._client.get(f"/open-apis/drive/v1/files/{file_token}/download",
                                          headers=await self._headers())
        if response.status_code != 200 or response.headers.get("content-type", "").startswith("application/json"):
            await self._json(response)  # raises with Feishu's reason
            raise FeishuError("Feishu did not return file content")
        if len(response.content) > MAX_FILE_BYTES:
            raise FeishuError("File exceeds the import size limit")
        disposition = response.headers.get("content-disposition", "")
        match = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disposition)
        name = httpx.URL("file:///" + (match.group(1) if match else file_token)).path.rsplit("/", 1)[-1]
        return name, response.content

    async def upload(self, folder_token: str, filename: str, payload: bytes) -> str:
        """Upload into a Drive folder; returns the new file token."""
        body = await self._json(await self._client.post(
            "/open-apis/drive/v1/files/upload_all", headers=await self._headers(),
            data={"file_name": filename, "parent_type": "explorer", "parent_node": folder_token, "size": str(len(payload))},
            files={"file": (filename, payload)}))
        return str(body["data"]["file_token"])


def from_settings(transport: httpx.AsyncBaseTransport | None = None) -> FeishuDrive:
    return FeishuDrive(settings.feishu_app_id, settings.feishu_app_secret, settings.feishu_base_url, transport)
