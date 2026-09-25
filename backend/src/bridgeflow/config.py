from __future__ import annotations

from pathlib import Path

from pydantic import Field
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
    cors_origins: str = ""
    # Shared only by the DSH host and Python, never delivered to a browser/model.
    bridgeflow_service_token: str = ""
    bridgeflow_allow_sample_data: bool = False
    bridgeflow_enable_legacy_console: bool = False
    bridgeflow_enable_legacy_pipeline: bool = False
    bridgeflow_allow_mapping_write: bool = True
    bridgeflow_allow_workflow_write: bool = True
    # Guest mode (docs/22 §9e): an isolated sample-only instance started by
    # `scripts/start_web.py --guest`. Feishu is refused outright; the launcher also strips
    # its credentials. Whether guests may reach the model is decided by the launcher.
    bridgeflow_guest_mode: bool = False
    # Feishu Drive shortcuts (#140). Exported by the launching shell, never committed.
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_base_url: str = "https://open.feishu.cn"
    # Login portal (docs/27). Empty = identity layer off and browser routes behave
    # as before; set = every browser data route needs a portal-signed user token.
    portal_base_url: str = ""
    portal_audience: str = "bridgeflow"
    # Who may see which departments — human-preset, same rule as the field dictionary.
    access_control_path: str = "data/mappings/access-control.yaml"
    bridgeflow_max_upload_bytes: int = 25 * 1024 * 1024
    bridgeflow_max_batch_rows: int = 200_000

    llm_provider: str = "mock"

    # Per-agent overrides. Empty means "use llm_provider".
    llm_provider_sanitizer: str = ""
    llm_provider_resolver: str = ""
    llm_provider_evaluator: str = ""
    # Drafts dictionary declarations from column statistics (#205). A separate knob so
    # drafting can run on a stronger model than the pipeline agents without touching them.
    llm_provider_dictionary_drafter: str = ""

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
    discovery_scoring_policy_path: str = ""
    discovery_decision_policy_path: str = ""
    discovery_upload_owner_count: int = Field(20, ge=1)
    discovery_upload_owner_bytes: int = Field(100 * 1024 * 1024, ge=1)
    discovery_upload_total_bytes: int = Field(1024 * 1024 * 1024, ge=1)
    # Confirmed mappings, kept between months. A confirmation that does not survive
    # its run means every month asks the same questions.
    mapping_memory_path: str = "data/outputs/mappings.json"
    # Uploaded columns a person matched onto declared columns. Never the dictionary.
    column_match_path: str = "data/outputs/column-matches.json"
    # Dictionary drafts (#205, E05-UC07/UC08): proposed declarations decided entry by
    # entry, published as versions. Never the active dictionary itself.
    dictionary_draft_path: str = "data/outputs/dictionary-drafts"
    # Approved workflow declarations (#143–#145). Unset means the workflow API reports
    # "not configured" rather than running on guessed stages or templates.
    workflow_catalogue_path: str = ""
    # The business dictionary transcribed for the 跨部门业务整合总表 (2026-09-13 templates).
    integration_spec_path: str = "data/company_templates/integration.yaml"
    # English display names beside the business's Chinese names (display only; see the file).
    display_labels_path: str = "data/company_templates/labels.en.yaml"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dsh_patch_paths(self) -> list[str]:
        """Resolve every configured policy layer; missing security policy fails closed."""
        paths = (p.strip() for p in self.dsh_patches.split(","))
        resolved = (REPO_ROOT / p if not Path(p).is_absolute() else Path(p) for p in paths if p)
        result = []
        for path in resolved:
            if not path.is_file():
                raise FileNotFoundError(f"required DSH policy patch is missing: {path}")
            result.append(str(path))
        return result

    def provider_for(self, agent: str) -> str:
        """Provider name for one agent, falling back to the global default."""
        return getattr(self, f"llm_provider_{agent}", "") or self.llm_provider


settings = Settings()
