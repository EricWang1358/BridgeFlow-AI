from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Relative settings paths are anchored here, so they mean the same thing whether
# the process starts in backend/ or at the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration, read from the environment and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bind address and allowed origins differ per environment (WSL, EC2, CI),
    # so they are configuration rather than constants. Comma-separated origins.
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

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
    # Patch layers applied after every bundle layer, comma-separated paths relative
    # to the repository root. Defaults to the layer that takes the shells away —
    # see dsh/no-shell.patch.yml for the measurement that justifies it.
    dsh_patches: str = "dsh/no-shell.patch.yml,dsh/approval.patch.yml,dsh/bridgeflow.patch.yml"

    # Cross-department mappings come from the OA field dictionary, not from
    # guessing. Empty means "not exported yet" — the resolver then falls back to
    # column-name hints so sample data still runs. See data/mappings/README.md.
    field_dictionary_path: str = "data/mappings/field-dictionary.yaml"

    resolver_confidence_threshold: float = 0.75

    # Where analysed periods are kept. A file per period rather than a process-local
    # dict: the dict was lost on restart and wrong with more than one worker.
    result_store_path: str = "data/outputs"
    # Confirmed mappings, kept between months. A confirmation that does not survive
    # its run means every month asks the same questions.
    mapping_memory_path: str = "data/outputs/mappings.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dsh_patch_paths(self) -> list[str]:
        """Absolute paths of the patch layers, dropping any that do not exist.

        A missing patch would otherwise fail the runtime at boot for everyone who
        set a path we no longer ship.
        """
        paths = (p.strip() for p in self.dsh_patches.split(","))
        resolved = (REPO_ROOT / p if not Path(p).is_absolute() else Path(p) for p in paths if p)
        return [str(p) for p in resolved if p.is_file()]

    def provider_for(self, agent: str) -> str:
        """Provider name for one agent, falling back to the global default."""
        return getattr(self, f"llm_provider_{agent}", "") or self.llm_provider


settings = Settings()
