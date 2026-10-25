"""Application settings, loaded from the environment (and the repo-root `.env` in local dev)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    admin_user_ids: str = ""
    log_level: str = "INFO"
    sentry_dsn: SecretStr | None = None

    # Supabase
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_jwks_url: str = ""
    supabase_jwt_secret: SecretStr | None = None
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
    # Per process. The Supabase session pooler caps clients per project (about 15 on the dev
    # plan) across the API, worker and test runs, so keep pool_size + max_overflow small there.
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    db_pool_timeout_seconds: float = Field(default=10, gt=0)
    storage_bucket_captures: str = "captures"

    # Redis / workers
    redis_url: str = "redis://localhost:6379/0"

    # AI
    ai_mode: Literal["fake", "live"] = "fake"
    groq_api_key: SecretStr | None = None
    model_small: str = ""
    model_fallback_small: str = ""
    model_draft: str = ""
    model_fallback_draft: str = ""
    model_stt: str = ""
    model_stt_fallback: str = ""
    ai_timeout_llm_seconds: float = 20
    ai_timeout_stt_seconds: float = 60
    # Cost estimates for ai_calls (INR). LLM: per 1M tokens [input, output]; STT: per audio hour.
    ai_price_inr_per_mtok: dict[str, tuple[float, float]] = {
        "openai/gpt-oss-20b": (6.6, 26.4),
        "openai/gpt-oss-120b": (13.2, 52.8),
    }
    ai_price_inr_per_audio_hour: dict[str, float] = {
        "whisper-large-v3-turbo": 3.5,
        "whisper-large-v3": 9.8,
    }

    # WhatsApp Cloud API
    wa_graph_version: str = ""
    wa_phone_number_id: str = ""
    wa_business_account_id: str = ""
    wa_access_token: SecretStr | None = None
    wa_app_secret: SecretStr | None = None
    wa_verify_token: SecretStr | None = None
    wa_display_number: str = ""
    wa_briefs_enabled: bool = False
    wa_template_language: str = "en"
    wa_link_code_minutes: int = 15

    # Payments and limits
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None
    price_sprint_paise: int = Field(default=79900, gt=0)
    price_pro_monthly_paise: int = Field(default=29900, gt=0)
    price_pro_yearly_paise: int = Field(default=249900, gt=0)
    sprint_days: int = Field(default=60, gt=0)
    sprint_fair_use_drafts: int = Field(default=400, gt=0)
    free_drafts_per_month: int = Field(default=3, ge=0)
    free_regenerations_per_draft: int = Field(default=3, ge=0)
    daily_send_cap: int = Field(default=20, gt=0)
    pro_enabled: bool = False
    price_test_enabled: bool = False
    pro_monthly_days: int = 30
    pro_yearly_days: int = 365

    # Privacy (bump when the notice or consent texts change; users are asked again)
    privacy_notice_version: str = "2026-10-25"
    consent_version: str = "2026-10-25"

    # Notifications
    vapid_public_key: str = ""
    vapid_private_key: SecretStr | None = None
    vapid_subject: str = ""
    resend_api_key: SecretStr | None = None
    email_from: str = ""
    unsubscribe_secret: SecretStr | None = None  # signs one-click unsubscribe links
    digest_weekday: int = Field(default=0, ge=0, le=6)  # Monday
    digest_hour: int = Field(default=9, ge=0, le=23)

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg(cls, value: str) -> str:
        """Accept the plain postgres:// URL copied from the Supabase dashboard."""
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value.removeprefix(prefix)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
