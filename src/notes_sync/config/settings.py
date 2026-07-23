from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class RetryConfig(BaseModel):
    limit: int = 2
    delay: int = 10


class LogConfig(BaseModel):
    file_path: str = str(PROJECT_ROOT / "output" / "notes_sync.log")
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


class GlobalSettings(BaseSettings):
    # Sync Defaults
    LOOKBACK_WINDOW_DAYS: int = 0
    DRY_RUN: bool = False
    USE_MOCK_SOURCE: bool = False

    # Secrets (Loaded from .env automatically)
    TOGGL_API_TOKEN: str
    NOTION_TOKEN: str
    NOTION_DATABASE_ID: str

    # Paths (Default values, scan from env first)
    # Default to None to allow Optional behavior or Pydantic validation
    OBSIDIAN_VAULT_PATH: Path
    STEPS_DATA_FILE: Optional[Path] = None

    # 安全守卫：最早同步日期
    # 脚本遇到这一天(含)之前的日期，会直接跳过，防止污染历史数据。
    EARLIEST_SYNC_DATE: str

    retry: RetryConfig = RetryConfig()
    log: LogConfig = LogConfig()
    CACHE_DIR: Path = PROJECT_ROOT / ".cache"

    DATE_ICON_BASE_URL: str

    # Location for Weather
    LATITUDE: float = 31.2304
    LONGITUDE: float = 121.4737

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings():
    return GlobalSettings()
