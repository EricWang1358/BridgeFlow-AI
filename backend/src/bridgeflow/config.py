from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "mock"

    # Per-agent overrides. Empty means "use llm_provider".
    llm_provider_sanitizer: str = ""
    llm_provider_resolver: str = ""
    llm_provider_evaluator: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    deepseek_model: str = ""

    hermes_api_key: str = ""
    hermes_base_url: str = ""
    hermes_model: str = ""

    openclaw_api_key: str = ""
    openclaw_base_url: str = ""
    openclaw_model: str = ""

    # DeepSeek Harness (dsh) — the agent runtime. dsh_home is mandatory: the SDK
    # never falls back to ~/.dsh, so there is no safe default to invent here.
    dsh_home: str = ""
    dsh_profile: str = "sdk"
    dsh_provider: str = "deepseek-official"
    dsh_model: str = "deepseek-v4-flash"
    dsh_reasoning_effort: str = ""
    dsh_max_tokens: int = 0
    dsh_cwd: str = ""

    # Cross-department mappings come from the OA field dictionary, not from
    # guessing. Empty means "not exported yet" — the resolver then falls back to
    # column-name hints so sample data still runs. See data/mappings/README.md.
    field_dictionary_path: str = "data/mappings/field-dictionary.yaml"

    resolver_confidence_threshold: float = 0.75

    def provider_for(self, agent: str) -> str:
        """Provider name for one agent, falling back to the global default."""
        return getattr(self, f"llm_provider_{agent}", "") or self.llm_provider


settings = Settings()
