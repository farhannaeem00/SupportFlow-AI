from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SupportFlow AI"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 30

    upload_dir: str = "storage/uploads"
    max_upload_size_mb: int = 10
    allowed_document_extensions: str = ".pdf,.docx,.txt"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    vector_store_dir: str = "storage/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    document_chunk_size: int = 1000
    document_chunk_overlap: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()