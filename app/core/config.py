from functools import lru_cache
from pathlib import Path

from pydantic import Field
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

    search_index_path: Path = Field(
        default_factory=lambda: CONFIG_DIR / "files.txt",
        validation_alias="SEARCH_INDEX_PATH",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
