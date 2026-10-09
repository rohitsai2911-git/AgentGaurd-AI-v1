from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENTGUARD_",
        extra="ignore",
        populate_by_name=True,
    )

    name: str = "AgentGuard AI"
    version: str = "0.2.0"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./agentguard.db"
    auto_seed: bool = False

    # --- Optional OpenRouter LLM judge (never required) ---
    # Reads OPENROUTER_API_KEY / OPENROUTER_MODEL directly, with
    # AGENTGUARD_-prefixed variants accepted as well.
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OPENROUTER_API_KEY", "AGENTGUARD_OPENROUTER_API_KEY"
        ),
    )
    openrouter_model: str = Field(
        default="openai/gpt-4o-mini",
        validation_alias=AliasChoices(
            "OPENROUTER_MODEL", "AGENTGUARD_OPENROUTER_MODEL"
        ),
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices(
            "OPENROUTER_BASE_URL", "AGENTGUARD_OPENROUTER_BASE_URL"
        ),
    )
    openrouter_timeout_seconds: float = Field(
        default=20.0,
        validation_alias=AliasChoices(
            "OPENROUTER_TIMEOUT_SECONDS",
            "AGENTGUARD_OPENROUTER_TIMEOUT_SECONDS",
        ),
    )
    openrouter_max_tokens: int = Field(
        default=1200,
        validation_alias=AliasChoices(
            "OPENROUTER_MAX_TOKENS", "AGENTGUARD_OPENROUTER_MAX_TOKENS"
        ),
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_api_key.strip())

    # --- Optional Laya local decision engine (never required) ---
    # Opt-in via LAYA_ENABLED=true. Lazy Router, local checkpoints, no keys.
    laya_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LAYA_ENABLED", "AGENTGUARD_LAYA_ENABLED"),
    )
    laya_model: str = Field(
        default="",
        validation_alias=AliasChoices("LAYA_MODEL", "AGENTGUARD_LAYA_MODEL"),
    )
    laya_timeout_seconds: float = Field(
        default=60.0,
        validation_alias=AliasChoices(
            "LAYA_TIMEOUT_SECONDS", "AGENTGUARD_LAYA_TIMEOUT_SECONDS"
        ),
    )
    laya_min_confidence: float = Field(
        default=0.0,
        validation_alias=AliasChoices(
            "LAYA_MIN_CONFIDENCE", "AGENTGUARD_LAYA_MIN_CONFIDENCE"
        ),
    )

    # --- Auth / multi-tenancy ---
    # JWT signing secret. Override in production via AGENTGUARD_JWT_SECRET.
    jwt_secret: str = Field(
        default="agentguard-dev-secret-change-me-in-production-0123456789",
        validation_alias=AliasChoices("JWT_SECRET", "AGENTGUARD_JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias=AliasChoices(
            "JWT_EXPIRE_MINUTES", "AGENTGUARD_JWT_EXPIRE_MINUTES"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()