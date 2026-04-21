"""Runtime configuration loaded from environment (12-factor style)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings. Instantiate once via :func:`get_settings`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    regulations_gov_api_key: str = Field(default="", alias="REGULATIONS_GOV_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    data_dir: Path = Field(default=Path("./data/raw"), alias="FEDCOMMENT_DATA_DIR")
    db_path: Path = Field(default=Path("./data/fedcomment.db"), alias="FEDCOMMENT_DB_PATH")

    log_level: str = Field(default="INFO", alias="FEDCOMMENT_LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance."""
    return Settings()
