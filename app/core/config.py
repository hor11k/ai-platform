from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(CONFIG_DIR / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-platform"
    environment: str = Field(default="development", validation_alias="ENV")
    log_level: str = "INFO"
    log_file: Path | None = None

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(
        default=None, validation_alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-5.5", validation_alias="OPENAI_MODEL")
    openai_timeout: float = Field(default=120.0, validation_alias="OPENAI_TIMEOUT")

    search_index_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "files.txt",
        validation_alias="SEARCH_INDEX_PATH",
    )
    content_index_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "content",
        validation_alias="CONTENT_INDEX_PATH",
    )
    rag_max_sources: int = Field(default=5, validation_alias="RAG_MAX_SOURCES")
    rag_max_context_chars: int = Field(
        default=12000,
        validation_alias="RAG_MAX_CONTEXT_CHARS",
    )
    ingest_wrk_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "wrk",
        validation_alias="INGEST_WRK_PATH",
    )
    ingest_downloads_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "downloads",
        validation_alias="INGEST_DOWNLOADS_PATH",
    )
    ingest_state_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "ingest_state.json",
        validation_alias="INGEST_STATE_PATH",
    )
    ingest_max_workers: int = Field(default=4, validation_alias="INGEST_MAX_WORKERS")
    session_state_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "session.json",
        validation_alias="SESSION_STATE_PATH",
    )
    exchange_server: str | None = Field(
        default=None, validation_alias="EXCHANGE_SERVER"
    )
    exchange_username: str | None = Field(
        default=None, validation_alias="EXCHANGE_USERNAME"
    )
    exchange_email: str | None = Field(
        default=None, validation_alias="EXCHANGE_EMAIL"
    )
    exchange_password: str | None = Field(
        default=None, validation_alias="EXCHANGE_PASSWORD"
    )
    exchange_autodiscover_cache_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "exchange_autodiscover.json",
        validation_alias="EXCHANGE_AUTODISCOVER_CACHE_PATH",
    )

    @field_validator("openai_base_url", "exchange_server", "exchange_email", mode="before")
    @classmethod
    def normalize_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator(
        "search_index_path",
        "content_index_path",
        "ingest_wrk_path",
        "ingest_downloads_path",
        "ingest_state_path",
        "session_state_path",
        "exchange_autodiscover_cache_path",
        mode="before",
    )
    @classmethod
    def resolve_relative_paths(cls, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.openai_base_url is None:
        os.environ.pop("OPENAI_BASE_URL", None)
    return settings
