"""Feishu Drive: bring department files in, send results back (#140).

Scope as agreed on 2026-09-13 (`docs/24`): upload and download shortcuts only. Feishu
owns storage and who may see what; BridgeFlow neither mirrors its permissions nor
keeps its files beyond the batch they were imported into.

Credentials are the app id and secret of a Feishu self-built app, exported by the
launching shell as `FEISHU_APP_ID` / `FEISHU_APP_SECRET` — never written to a file in
the repository. Without them every call says "not configured" instead of pretending.

The client is deliberately small and synchronous-free of framework state: one class,
a handful of calls, errors surfaced with Feishu's own code and message. The transport is
injectable so the protocol can be tested without a tenant.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from bridgeflow.config import settings

MAX_FILE_BYTES = 25 * 1024 * 1024
#: One range read of an online sheet covers at most this many rows (docs/33).
SHEET_CHUNK_ROWS = 5000
#: Frequency control answers worth one bounded backoff-and-retry, never an endless loop.
_RATE_LIMIT_CODES = {99991400, 99991401}
_MAX_ATTEMPTS = 3


class FeishuError(Exception):
    """Feishu refused, or could not be reached. Nothing was imported or uploaded."""


class NotConfigured(FeishuError):
    pass


@dataclass
class _Token:
    value: str
    expires_at: float


class FeishuDrive:
    def __init__(self, app_id: str = "", app_secret: str = "", base_url: str = "https://open.feishu.cn",
                 user_token: str = "", transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not user_token and not (app_id and app_secret):
            raise NotConfigured("Feishu is not configured: export FEISHU_APP_ID and FEISHU_APP_SECRET")
        self._app_id, self._app_secret = app_id, app_secret
        # User-identity mode (docs/30): the token comes from the signed-in browser,
        # scopes every call to what that person may see, and is never cached beyond
        # this client's lifetime.
        self._user_token = user_token
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=30)
        self._token: _Token | None = None

    @classmethod
    def for_user(cls, user_token: str, base_url: str = "https://open.feishu.cn",
                 transport: httpx.AsyncBaseTransport | None = None) -> FeishuDrive:
        if not user_token:
            raise NotConfigured("A Feishu user token is required: sign in again")
        return cls(base_url=base_url, user_token=user_token, transport=transport)

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
        if self._user_token:
            return {"authorization": f"Bearer {self._user_token}"}
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

    async def list_files(self, folder_token: str = "", page_token: str = "", page_size: int = 50) -> dict:
        """One folder's children, metadata only (docs/30).

        The reply carries token, name, type, size and modification time — never
        cell content, so the answer stays bounded no matter how large the files are.
        Feishu filters by the caller's own permissions when a user token is used.
        """
        params: dict[str, str] = {"page_size": str(min(max(page_size, 1), 200))}
        if folder_token:
            params["folder_token"] = folder_token
        if page_token:
            params["page_token"] = page_token
        body = await self._json(await self._client.get(
            "/open-apis/drive/v1/files", headers=await self._headers(), params=params))
        data = body.get("data") or {}
        files = [{"token": str(item.get("token", "")), "name": str(item.get("name", "")),
                  "type": str(item.get("type", "")), "size": int(item.get("size") or 0),
                  "modified_time": str(item.get("modified_time", ""))}
                 for item in data.get("files") or []]
        return {"files": files, "has_more": bool(data.get("has_more")),
                "next_page_token": str(data.get("next_page_token") or "")}

    # --- Wiki (docs/31): two-level addressing ----------------------------------------
    # A wiki node is browsed by its node token but the file body lives at obj_token,
    # which download() accepts directly. The two never substitute for each other.

    async def list_wiki_spaces(self, page_token: str = "", page_size: int = 50) -> dict:
        """The knowledge bases the caller may see, metadata only (docs/31)."""
        params: dict[str, str] = {"page_size": str(min(max(page_size, 1), 50))}
        if page_token:
            params["page_token"] = page_token
        body = await self._json(await self._client.get(
            "/open-apis/wiki/v2/spaces", headers=await self._headers(), params=params))
        data = body.get("data") or {}
        spaces = [{"space_id": str(item.get("space_id", "")), "name": str(item.get("name", "")),
                   "description": str(item.get("description", ""))}
                  for item in data.get("items") or []]
        return {"spaces": spaces, "has_more": bool(data.get("has_more")),
                "next_page_token": str(data.get("page_token") or "")}

    async def list_wiki_nodes(self, space_id: str, parent_node_token: str = "",
                              page_token: str = "", page_size: int = 50) -> dict:
        """One level of a wiki's node tree, metadata only — never the content behind it."""
        params: dict[str, str] = {"page_size": str(min(max(page_size, 1), 50))}
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        if page_token:
            params["page_token"] = page_token
        body = await self._json(await self._client.get(
            f"/open-apis/wiki/v2/spaces/{space_id}/nodes", headers=await self._headers(), params=params))
        data = body.get("data") or {}
        nodes = [{"token": str(item.get("node_token", "")), "obj_token": str(item.get("obj_token", "")),
                  "obj_type": str(item.get("obj_type", "")), "title": str(item.get("title", "")),
                  "has_child": bool(item.get("has_child"))}
                 for item in data.get("items") or []]
        return {"nodes": nodes, "has_more": bool(data.get("has_more")),
                "next_page_token": str(data.get("page_token") or "")}

    async def move_to_wiki(self, space_id: str, parent_wiki_token: str, obj_token: str) -> str:
        """Attach an existing Drive file into a wiki position; returns the new node token."""
        payload = {"obj_type": "file", "obj_token": obj_token}
        if parent_wiki_token:
            payload["parent_wiki_token"] = parent_wiki_token
        body = await self._json(await self._client.post(
            f"/open-apis/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki",
            headers=await self._headers(), json=payload))
        data = body.get("data") or {}
        node = data.get("node") or {}
        return str(node.get("token") or data.get("wiki_token") or "")

    # --- Online sheets & bitables (docs/33): paged reads, metadata stays metadata --------

    async def _get_json(self, path: str, params: dict[str, str] | None = None) -> dict:
        """GET with bounded backoff on frequency control; every other refusal surfaces as-is."""
        delay = 0.5
        for attempt in range(_MAX_ATTEMPTS):
            response = await self._client.get(path, headers=await self._headers(), params=params)
            try:
                body = response.json()
            except ValueError as exc:
                raise FeishuError(f"Feishu returned HTTP {response.status_code} without a JSON body") from exc
            code = body.get("code", 0)
            if response.status_code < 400 and code == 0:
                return body
            retryable = response.status_code == 429 or code in _RATE_LIMIT_CODES
            if not retryable or attempt == _MAX_ATTEMPTS - 1:
                raise FeishuError(f"Feishu refused (code {code}): {body.get('msg', 'no message')}")
            await asyncio.sleep(delay)
            delay *= 2
        raise FeishuError("unreachable")  # pragma: no cover

    async def sheet_meta(self, spreadsheet_token: str) -> list[dict]:
        """One online sheet's worksheets: id, title, dimensions — never cell content (docs/33)."""
        body = await self._get_json(f"/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query")
        sheets = []
        for item in (body.get("data") or {}).get("sheets") or []:
            grid = item.get("grid_properties") or {}
            sheets.append({"sheet_id": str(item.get("sheet_id", "")), "title": str(item.get("title", "")),
                           "rows": int(grid.get("row_count") or 0), "cols": int(grid.get("column_count") or 0)})
        return sheets

    async def sheet_values(self, spreadsheet_token: str, sheet_id: str, rows: int, cols: int,
                           chunk: int = SHEET_CHUNK_ROWS):
        """One worksheet's values, chunk by chunk, exactly as Feishu displays them.

        FormattedValue means a formula arrives as the result Feishu computed — it is
        never re-evaluated here. The caller passes the dimensions from sheet_meta.
        """
        if rows <= 0:
            return
        if chunk <= 0:
            raise ValueError("chunk must be a positive row count")
        last_col = _column_letter(max(cols, 1))
        start = 1
        while start <= rows:
            stop = min(start + chunk - 1, rows)
            body = await self._get_json(
                f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!A{start}:{last_col}{stop}",
                params={"valueRenderOption": "FormattedValue"})
            yield ((body.get("data") or {}).get("valueRange") or {}).get("values") or []
            start = stop + 1

    async def bitable_tables(self, app_token: str) -> list[dict]:
        """A bitable's data tables: id and name only, paged (docs/33)."""
        tables: list[dict] = []
        page_token = ""
        while True:
            params = {"page_size": "100"}
            if page_token:
                params["page_token"] = page_token
            body = await self._get_json(f"/open-apis/bitable/v1/apps/{app_token}/tables", params)
            data = body.get("data") or {}
            tables += [{"table_id": str(item.get("table_id", "")), "name": str(item.get("name", ""))}
                       for item in data.get("items") or []]
            if not data.get("has_more"):
                return tables
            page_token = str(data.get("page_token") or "")

    async def bitable_fields(self, app_token: str, table_id: str) -> list[dict]:
        """One table's field definitions: name and type, paged, never record content."""
        fields: list[dict] = []
        page_token = ""
        while True:
            params = {"page_size": "100"}
            if page_token:
                params["page_token"] = page_token
            body = await self._get_json(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields", params)
            data = body.get("data") or {}
            fields += [{"name": str(item.get("field_name", "")), "type": int(item.get("type") or 0),
                        "ui_type": str(item.get("ui_type", ""))} for item in data.get("items") or []]
            if not data.get("has_more"):
                return fields
            page_token = str(data.get("page_token") or "")

    async def bitable_records(self, app_token: str, table_id: str, page_size: int = 500):
        """One table's records, page by page: record_id plus the raw fields mapping."""
        page_token = ""
        while True:
            params = {"page_size": str(min(max(page_size, 1), 500))}
            if page_token:
                params["page_token"] = page_token
            body = await self._get_json(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records", params)
            data = body.get("data") or {}
            yield [{"record_id": str(item.get("record_id", "")), "fields": item.get("fields") or {}}
                   for item in data.get("items") or []]
            if not data.get("has_more"):
                return
            page_token = str(data.get("page_token") or "")

    async def _root_folder_token(self) -> str:
        """The caller's Drive root: the staging point every wiki upload passes through."""
        body = await self._json(await self._client.get(
            "/open-apis/drive/explorer/v2/root_folder/meta", headers=await self._headers()))
        return str(body["data"]["token"])

    async def upload_to_wiki(self, space_id: str, parent_wiki_token: str,
                             filename: str, payload: bytes) -> str:
        """Feishu has no direct-to-wiki upload: land in the Drive root, then attach (docs/31).

        If the attach fails the file stays in the caller's own Drive root — visible to
        them, never auto-deleted, and the error says so."""
        file_token = await self.upload(await self._root_folder_token(), filename, payload)
        try:
            return await self.move_to_wiki(space_id, parent_wiki_token, file_token)
        except FeishuError as exc:
            raise FeishuError(
                f"{filename!r} reached your Feishu My Space root but could not be attached "
                f"to the wiki ({exc}); move it manually or try again") from exc


def _column_letter(index: int) -> str:
    """1-based column number as spreadsheet letters: 1 → A, 27 → AA."""
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters or "A"


def from_settings(transport: httpx.AsyncBaseTransport | None = None) -> FeishuDrive:
    return FeishuDrive(settings.feishu_app_id, settings.feishu_app_secret,
                       settings.feishu_base_url, transport=transport)
