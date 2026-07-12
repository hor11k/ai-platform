from functools import lru_cache
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

    @field_validator("search_index_path", "content_index_path", mode="before")
    @classmethod
    def resolve_relative_paths(cls, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
