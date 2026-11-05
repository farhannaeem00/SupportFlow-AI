from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SupportFlow AI"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )

    upload_dir: str = "storage/uploads"
    max_upload_size_mb: int = 10
    allowed_document_extensions: str = ".pdf,.docx,.txt"

    vector_store_dir: str = "storage/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    document_chunk_size: int = 1000
    document_chunk_overlap: int = 200

    # Knowledge retrieval
    knowledge_max_distance: float = Field(default=0.7, ge=0.0, le=2.0)

    # Public website widget rate limits
    widget_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
    )
    widget_session_rate_limit: int = Field(default=10, ge=1)
    widget_conversation_rate_limit: int = Field(default=5, ge=1)
    widget_message_rate_limit: int = Field(default=20, ge=1)

    # Document processing
    document_processing_timeout_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )
        # Password reset
    password_reset_token_expire_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
    )
    password_reset_rate_limit: int = Field(default=5, ge=1)

    # Password reset email
    password_reset_frontend_url: str = "http://localhost:5173/reset-password"

    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None

    # AI provider reliability
    ai_provider_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        le=120,
    )
    ai_provider_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    ai_provider_max_tokens: int = Field(
        default=800,
        ge=1,
        le=8192,
    )

    # Authentication rate limits
    auth_rate_limit_window_seconds: int = Field(
        default=900,
        ge=1,
        le=3600,
    )
    auth_register_rate_limit: int = Field(default=5, ge=1)
    auth_login_rate_limit: int = Field(default=10, ge=1)
    auth_token_rate_limit: int = Field(default=10, ge=1)

    # Global API rate limits
    api_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
    )
    api_global_rate_limit: int = Field(default=120, ge=1)

    # Expensive AI analysis rate limits
    ai_analysis_rate_limit_window_seconds: int = Field(
        default=3600,
        ge=1,
        le=86400,
    )
    ai_analysis_rate_limit: int = Field(default=10, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
