from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Relative settings paths are anchored at the portal/ directory.
PORTAL_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from the process environment only.

    Deliberately no env_file: these credentials decide who can sign in and what
    the portal's signatures mean, so they follow the same boundary as DSH_* —
    exported by the launching shell (env.sh), never carried by a file in the repo.
    """

    model_config = SettingsConfigDict(env_prefix="PORTAL_", extra="ignore")

    # Feishu self-built app with web-login enabled. May be the same app the
    # BridgeFlow backend uses for Drive shortcuts; the scopes differ.
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_base_url: str = "https://open.feishu.cn"

    # Ed25519 private key PEM signing app tokens. Generate with:
    #   python -m portal_app.keygen <path>   — outside the repository.
    key_path: str = ""
    # HMAC secret sealing the login state and the session cookie.
    session_secret: str = ""

    # This portal as the outside world reaches it; also the JWT issuer claim.
    external_base_url: str = "http://127.0.0.1:8100"
    apps_path: str = str(PORTAL_ROOT / "apps.yaml")

    session_ttl_seconds: int = 12 * 3600
    app_token_ttl_seconds: int = 900
    # True behind HTTPS; False only for localhost development.
    cookie_secure: bool = False

    host: str = "127.0.0.1"
    port: int = 8100

    @property
    def callback_uri(self) -> str:
        return f"{self.external_base_url}/callback"


settings = Settings()
